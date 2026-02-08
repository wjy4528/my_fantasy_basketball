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

# Additional stat IDs used for percentage calculations
COMPONENT_STAT_NAMES = {
    '3': 'FGM',
    '4': 'FGA',
    '6': 'FTM',
    '7': 'FTA',
}


def build_stat_id_map(stat_categories):
    """
    Build a mapping of stat_id to display_name from league settings.

    Args:
        stat_categories: List of stat category dicts from league settings

    Returns:
        dict: Mapping of stat_id (str) to display_name (str)
    """
    stat_map = {}
    for cat in stat_categories:
        stat_id = str(cat.get('stat_id', ''))
        display_name = cat.get('display_name', f'Stat {stat_id}')
        stat_map[stat_id] = display_name
    return stat_map


def extract_player_stats(player, reverse_stat_map=None):
    """
    Extract stats from a player stats response object.

    Handles two response formats:
    1. Nested: player_stats -> stats -> [{stat_id, value}] (raw Yahoo API)
    2. Flat: stats as top-level keys by display name (yahoo_fantasy_api library)

    Args:
        player: Player data dict from the API
        reverse_stat_map: Optional dict mapping display_name -> stat_id,
            used to convert flat format keys back to stat IDs.

    Returns:
        tuple: (player_name, player_stats_dict keyed by stat_id)
    """
    name = player.get('name', 'Unknown')
    if isinstance(name, dict):
        name = name.get('full', 'Unknown')

    stats = {}
    # Handle nested response structures from raw Yahoo API
    player_stats = player.get('player_stats', {})
    if isinstance(player_stats, dict):
        stat_list = player_stats.get('stats', [])
    elif isinstance(player_stats, list):
        stat_list = player_stats
    else:
        stat_list = []

    # Also check top-level 'stats' key
    if not stat_list:
        stat_list = player.get('stats', [])

    for stat in stat_list:
        if isinstance(stat, dict):
            stat_id = str(stat.get('stat_id', ''))
            value = stat.get('value', '-')
            if value != '-' and value is not None:
                try:
                    stats[stat_id] = float(value)
                except (ValueError, TypeError):
                    stats[stat_id] = value

    # Handle flat format from yahoo_fantasy_api library
    # Stats are directly on the player dict, keyed by display name
    # (e.g., {'PTS': 25.0, 'REB': 10.0, ...})
    if not stats and reverse_stat_map:
        for key, value in player.items():
            if key in reverse_stat_map and isinstance(value, (int, float)):
                stats[reverse_stat_map[key]] = value

    return name, stats


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

        print(f"\n{'='*90}")
        print(f"  Rosters & Player Stats (Season 2025-2026) - League ID: {client.league_id}")
        print(f"{'='*90}")

        # Get league settings for stat category names
        settings = client.get_league_settings()
        stat_categories = settings.get('stat_categories', {}).get('stats', [])
        stat_id_map = build_stat_id_map(stat_categories)

        # Determine which stat IDs to display (use league settings or defaults)
        display_stat_ids = []
        for cat in stat_categories:
            sid = str(cat.get('stat_id', ''))
            if sid:
                display_stat_ids.append(sid)

        if not display_stat_ids:
            display_stat_ids = list(ROTO_STAT_NAMES.keys())

        # Build reverse mapping: display_name -> stat_id for flat API responses
        reverse_stat_map = {}
        for sid, dname in stat_id_map.items():
            reverse_stat_map[dname] = sid
        for sid, dname in ROTO_STAT_NAMES.items():
            if dname not in reverse_stat_map:
                reverse_stat_map[dname] = sid
        for sid, dname in COMPONENT_STAT_NAMES.items():
            if dname not in reverse_stat_map:
                reverse_stat_map[dname] = sid

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
            print(f"\n{'─'*90}")
            print(f"  📋 {team_name}")
            print(f"     Team Key: {team_key}")
            print(f"{'─'*90}")

            # Get roster
            try:
                roster = client.get_team_roster(team_key)
            except Exception as e:
                print(f"     ⚠ Could not fetch roster: {e}")
                continue

            if not roster:
                print("     No players on roster.")
                continue

            # Collect player keys for batch stat retrieval
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

            # Fetch season stats for all players on this roster
            player_season_stats = {}
            if player_keys:
                try:
                    stats_response = client.get_players_stats(player_keys, 'season')
                    if isinstance(stats_response, list):
                        for ps in stats_response:
                            pkey = ps.get('player_key', '')
                            if not pkey:
                                pkey = ps.get('player_id', '')
                            pname, pstats = extract_player_stats(
                                ps, reverse_stat_map)
                            if pkey and pkey in player_info:
                                player_season_stats[pkey] = pstats
                            elif pname:
                                # Try to match by name
                                for k, v in player_info.items():
                                    if v['name'] == pname:
                                        player_season_stats[k] = pstats
                                        break
                    elif isinstance(stats_response, dict):
                        for pkey_resp, ps in stats_response.items():
                            _, pstats = extract_player_stats(
                                ps, reverse_stat_map)
                            player_season_stats[pkey_resp] = pstats
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
            for pkey in player_keys:
                info = player_info.get(pkey, {})
                pname = info.get('name', 'Unknown')
                pos = info.get('position', 'N/A')
                eteam = info.get('team', '')
                pstats = player_season_stats.get(pkey, {})

                row = f"  {pname:<28} {pos:<6} {eteam:<5}"
                for sid in display_stat_ids:
                    val = pstats.get(sid, '-')
                    if val != '-':
                        row += f" {format_stat_value(sid, val):>7}"
                        # Accumulate totals (skip percentages)
                        if sid not in ('5', '8'):
                            team_totals[sid] = team_totals.get(sid, 0) + (
                                float(val) if isinstance(val, (int, float)) else 0
                            )
                    else:
                        row += f" {'—':>7}"
                print(row)

            # Print team totals
            if team_totals:
                print(f"  {'─'*28} {'─'*5} {'─'*4}", end="")
                for _ in stat_headers:
                    print(f" {'─'*7}", end="")
                print()
                totals_row = f"  {'TEAM TOTALS':<28} {'':6} {'':5}"
                for sid in display_stat_ids:
                    if sid in ('5', '8'):
                        totals_row += f" {'—':>7}"
                    elif sid in team_totals:
                        totals_row += f" {format_stat_value(sid, team_totals[sid]):>7}"
                    else:
                        totals_row += f" {'—':>7}"
                print(totals_row)

        print(f"\n{'='*90}")
        print("  Roto Scoring: Teams are ranked 1-N in each category.")
        print("  Categories: FG%, FT%, 3PTM, PTS, REB, AST, STL, BLK, TO")
        print("  Reference: https://help.yahoo.com/kb/rotisserie-scoring-sln6187.html")
        print(f"{'='*90}\n")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
