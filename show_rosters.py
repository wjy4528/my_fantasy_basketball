#!/usr/bin/env python3
"""
Show the roster for each manager with player season stats for 2025-2026.

Displays every team's roster with each player's total season statistics,
formatted for Rotisserie (Roto) league analysis.

Usage:
    python show_rosters.py
"""
import sys
from client import FantasyBasketballClient


# Standard Roto stat categories with display names
# These map Yahoo stat_id values to human-readable names
ROTO_STAT_NAMES = {
    '5': 'FG%',
    '8': 'FT%',
    '10': '3PTM',
    '12': 'PTS',
    '15': 'REB',
    '16': 'AST',
    '17': 'STL',
    '18': 'BLK',
    '19': 'TO',
}

# Component stat IDs
COMPONENT_STAT_NAMES = {
    '3': 'FGM',
    '4': 'FGA',
    '6': 'FTM',
    '7': 'FTA',
}

# Games played stat
GP_STAT_ID = '0'

# NBA regular season games per team
NBA_TOTAL_GAMES = 82


def build_stat_id_map(stat_categories):
    """
    Build a mapping of stat_id to display_name from raw API stat categories.

    Args:
        stat_categories: List of stat category dicts from raw API settings

    Returns:
        dict: Mapping of stat_id (str) to display_name (str)
    """
    stat_map = {}
    for cat in stat_categories:
        stat_id = str(cat.get('stat_id', ''))
        display_name = cat.get('display_name', f'Stat {stat_id}')
        stat_map[stat_id] = display_name
    return stat_map


def format_stat_value(stat_id, value):
    """Format a stat value for display based on its type."""
    if stat_id in ('5', '8'):  # FG%, FT% are percentages
        if isinstance(value, (int, float)):
            return f"{value:.3f}"
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def main():
    """Display rosters for all managers with player season stats."""
    try:
        print("Connecting to Yahoo Fantasy Basketball API...")
        client = FantasyBasketballClient()

        print(f"\n{'='*100}")
        print(f"  Rosters & Player Stats (Season 2025-2026) - League ID: {client.league_id}")
        print(f"{'='*100}")

        # Get raw stat categories with stat_ids from the API
        raw_categories = client.get_stat_categories_raw()
        stat_id_map = build_stat_id_map(raw_categories)

        # Build Roto stat IDs from API categories (non-display-only stats)
        roto_stat_ids = []
        for cat in raw_categories:
            sid = str(cat.get('stat_id', ''))
            is_display_only = str(cat.get('is_only_display_stat', '0'))
            if sid and is_display_only != '1':
                roto_stat_ids.append(sid)
        if not roto_stat_ids:
            roto_stat_ids = list(ROTO_STAT_NAMES.keys())

        # Per-player columns: only Roto scoring categories
        display_stat_ids = list(roto_stat_ids)

        # Get all teams
        teams = client.get_teams()

        if not teams:
            print("\nNo teams found in the league.")
            sys.exit(0)

        # Build stat header
        stat_headers = []
        for sid in display_stat_ids:
            name = stat_id_map.get(sid, ROTO_STAT_NAMES.get(sid, f'S{sid}'))
            stat_headers.append(name)

        # Process each team
        for team_key, team_name in teams.items():
            print(f"\n{'─'*100}")
            print(f"  📋 {team_name}")
            print(f"     Team Key: {team_key}")
            print(f"{'─'*100}")

            # Get roster
            try:
                roster = client.get_team_roster(team_key)
            except Exception as e:
                print(f"     ⚠ Could not fetch roster: {e}")
                continue

            if not roster:
                print("     No players on roster.")
                continue

            # Collect player keys/info from roster
            player_keys = []
            player_info = {}
            for player in roster:
                pkey = player.get('player_key', '')
                if not pkey:
                    pkey = player.get('player_id', '')
                pname = player.get('name', 'Unknown')
                if isinstance(pname, dict):
                    pname = pname.get('full', 'Unknown')
                position = player.get('selected_position', {})
                if isinstance(position, dict):
                    position = position.get('position', 'N/A')
                else:
                    position = str(position) if position else 'N/A'
                editorial_team = player.get('editorial_team_abbr', '')

                if pkey:
                    player_keys.append(pkey)
                    player_info[pkey] = {
                        'name': pname,
                        'position': position,
                        'team': editorial_team,
                    }

            # Fetch season stats (raw — includes ALL stat IDs)
            player_season_stats = {}
            if player_keys:
                try:
                    stats_response = client.get_players_stats_all(
                        player_keys, 'season')
                    for ps in stats_response:
                        pid = ps.get('player_id', '')
                        if pid and pid in player_info:
                            pstats = {str(k): v for k, v in ps.items()
                                      if k not in ('player_id', 'name',
                                                    'position_type')
                                      and isinstance(v, (int, float))}
                            player_season_stats[pid] = pstats
                        elif pid:
                            pname = ps.get('name', '')
                            for k, v in player_info.items():
                                if v['name'] == pname:
                                    pstats = {str(sk): sv
                                              for sk, sv in ps.items()
                                              if sk not in ('player_id',
                                                            'name',
                                                            'position_type')
                                              and isinstance(sv,
                                                             (int, float))}
                                    player_season_stats[k] = pstats
                                    break
                except Exception as e:
                    print(f"     ⚠ Could not fetch player stats: {e}")

            # Print header row
            header = f"  {'Player':<28} {'Pos':<6} {'Team':<5}"
            for sh in stat_headers:
                header += f" {sh:>7}"
            print(header)
            print(f"  {'─'*28} {'─'*5} {'─'*4}", end="")
            for _ in stat_headers:
                print(f" {'─'*7}", end="")
            print()

            # Print each player with stats
            team_totals = {}
            total_gp = 0
            for pkey in player_keys:
                info = player_info.get(pkey, {})
                pname = info.get('name', 'Unknown')
                pos = info.get('position', 'N/A')
                eteam = info.get('team', '')
                pstats = player_season_stats.get(pkey, {})

                # Accumulate GP
                gp = pstats.get(GP_STAT_ID, 0)
                if isinstance(gp, (int, float)):
                    total_gp += int(gp)

                row = f"  {pname:<28} {pos:<6} {eteam:<5}"
                for sid in display_stat_ids:
                    val = pstats.get(sid, '-')
                    if val != '-':
                        row += f" {format_stat_value(sid, val):>7}"
                        # Accumulate totals (skip percentages)
                        if sid not in ('5', '8'):
                            team_totals[sid] = team_totals.get(sid, 0) + (
                                float(val)
                                if isinstance(val, (int, float)) else 0
                            )
                        # Also accumulate components for percentage recalc
                    else:
                        row += f" {'—':>7}"
                print(row)

                # Accumulate component stats for team totals
                for cid in ('3', '4', '6', '7'):
                    cval = pstats.get(cid)
                    if cval is not None and isinstance(cval, (int, float)):
                        team_totals[cid] = team_totals.get(cid, 0) + cval

            # Print team totals
            num_players = len(player_keys)
            total_gl = (num_players * NBA_TOTAL_GAMES) - total_gp
            print(f"  {'─'*28} {'─'*5} {'─'*4}", end="")
            for _ in stat_headers:
                print(f" {'─'*7}", end="")
            print()

            totals_row = f"  {'TEAM TOTALS':<28} {'':6} {'':5}"
            for sid in display_stat_ids:
                if sid == '5':
                    # Recalculate FG% from FGM/FGA
                    if '3' in team_totals and '4' in team_totals:
                        fgm = team_totals['3']
                        fga = team_totals['4']
                        pct = fgm / fga if fga > 0 else 0
                        totals_row += f" {format_stat_value(sid, pct):>7}"
                    else:
                        totals_row += f" {'—':>7}"
                elif sid == '8':
                    # Recalculate FT% from FTM/FTA
                    if '6' in team_totals and '7' in team_totals:
                        ftm = team_totals['6']
                        fta = team_totals['7']
                        pct = ftm / fta if fta > 0 else 0
                        totals_row += f" {format_stat_value(sid, pct):>7}"
                    else:
                        totals_row += f" {'—':>7}"
                elif sid in team_totals:
                    totals_row += (
                        f" {format_stat_value(sid, team_totals[sid]):>7}")
                else:
                    totals_row += f" {'—':>7}"
            print(totals_row)

            # Print team GP / GL summary and component stats
            summary_parts = [f"  Team GP: {total_gp}",
                             f"GL: {total_gl}"]
            if '3' in team_totals and '4' in team_totals:
                summary_parts.append(
                    f"FGM/FGA: {int(team_totals['3'])}"
                    f"/{int(team_totals['4'])}")
            if '6' in team_totals and '7' in team_totals:
                summary_parts.append(
                    f"FTM/FTA: {int(team_totals['6'])}"
                    f"/{int(team_totals['7'])}")
            print(f"  {'  |  '.join(summary_parts)}")

        print(f"\n{'='*100}")
        print("  Roto Scoring: Teams are ranked 1-N in each category.")
        print("  GP = total Games Played across all roster slots, "
              "GL = Games Left")
        print("  Categories: FG%, FT%, 3PTM, PTS, REB, AST, STL, BLK, TO")
        print("  Reference: https://help.yahoo.com/kb/"
              "rotisserie-scoring-sln6187.html")
        print(f"{'='*100}\n")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
