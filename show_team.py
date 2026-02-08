#!/usr/bin/env python3
"""
Show detailed stats for all players on a specific team.

Includes season totals, per-game averages, GP/GL, and
FGM/FGA / FTM/FTA component stats.

Usage:
    python show_team.py
    python show_team.py --team-key 466.l.21454.t.1
"""
import argparse
import sys
from client import FantasyBasketballClient
from show_rosters import build_stat_id_map, build_reverse_stat_map


# Standard Roto stat categories
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

COMPONENT_STAT_NAMES = {
    '3': 'FGM',
    '4': 'FGA',
    '6': 'FTM',
    '7': 'FTA',
}

GP_STAT_ID = '0'
NBA_TOTAL_GAMES = 82


def fmt(stat_id, value):
    """Format a stat value for display."""
    if stat_id in ('5', '8'):
        return f"{value:.3f}" if isinstance(value, (int, float)) else str(value)
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def main():
    parser = argparse.ArgumentParser(
        description="Show detailed stats for all players on a team"
    )
    parser.add_argument(
        '--team-key',
        help='Yahoo team key. If not provided, you will be prompted.'
    )
    args = parser.parse_args()

    try:
        print("Connecting to Yahoo Fantasy Basketball API...")
        client = FantasyBasketballClient()

        # Get raw stat categories
        raw_categories = client.get_stat_categories_raw()
        stat_id_map = {}
        roto_stat_ids = []
        for cat in raw_categories:
            sid = str(cat.get('stat_id', ''))
            dname = cat.get('display_name', f'Stat {sid}')
            stat_id_map[sid] = dname
            is_display_only = str(cat.get('is_only_display_stat', '0'))
            if sid and is_display_only != '1':
                roto_stat_ids.append(sid)
        if not roto_stat_ids:
            roto_stat_ids = list(ROTO_STAT_NAMES.keys())

        # Get teams
        teams = client.get_teams()

        # Select team
        if args.team_key:
            team_key = args.team_key
            if team_key not in teams:
                print(f"Error: Team key '{team_key}' not found.")
                print("Available teams:")
                for tk, name in teams.items():
                    print(f"  {name} ({tk})")
                sys.exit(1)
        else:
            team_list = list(teams.items())
            print("Select a team:")
            for i, (tk, name) in enumerate(team_list, 1):
                print(f"  {i}. {name} ({tk})")
            while True:
                try:
                    choice = input(
                        f"Enter team number (1-{len(team_list)}): "
                    ).strip()
                    idx = int(choice) - 1
                    if 0 <= idx < len(team_list):
                        team_key = team_list[idx][0]
                        break
                except (ValueError, EOFError):
                    pass
                print("Invalid selection.")

        team_name = teams[team_key]

        # Build display columns: GP + components + Roto categories
        display_ids = [GP_STAT_ID]
        for sid in roto_stat_ids:
            if sid == '5':
                display_ids.extend(['3', '4', '5'])
            elif sid == '8':
                display_ids.extend(['6', '7', '8'])
            elif sid not in ('3', '4', '6', '7'):
                display_ids.append(sid)

        # Get roster
        roster = client.get_team_roster(team_key)
        player_keys = []
        player_info = {}
        for player in roster:
            pkey = player.get('player_key', '') or player.get(
                'player_id', '')
            pname = player.get('name', 'Unknown')
            if isinstance(pname, dict):
                pname = pname.get('full', 'Unknown')
            pos = player.get('selected_position', {})
            if isinstance(pos, dict):
                pos = pos.get('position', 'N/A')
            eteam = player.get('editorial_team_abbr', '')
            if pkey:
                player_keys.append(pkey)
                player_info[pkey] = {
                    'name': pname, 'position': str(pos), 'team': eteam}

        # Build reverse mapping using shared utility
        reverse_stat_map = build_reverse_stat_map(stat_id_map)

        # Fetch stats via library method (augmented stats_id_map includes
        # GP, FGM, FGA, FTM, FTA)
        stats_response = client.get_players_stats(player_keys, 'season')
        player_stats = {}
        if isinstance(stats_response, list):
            for ps in stats_response:
                pid = ps.get('player_id', '')
                if pid:
                    pstats = {}
                    for key, value in ps.items():
                        if (key in reverse_stat_map
                                and isinstance(value, (int, float))):
                            pstats[reverse_stat_map[key]] = value
                    player_stats[pid] = pstats

        # Build header names
        headers = []
        for sid in display_ids:
            name = stat_id_map.get(
                sid, ROTO_STAT_NAMES.get(
                    sid, COMPONENT_STAT_NAMES.get(
                        sid, 'GP' if sid == GP_STAT_ID else f'S{sid}')))
            headers.append(name)

        # Print
        print(f"\n{'='*120}")
        print(f"  {team_name}  ({team_key})")
        print(f"{'='*120}")
        print(f"\n  SEASON TOTALS")
        print(f"  {'─'*116}")

        hdr = f"  {'Player':<24} {'Pos':<5} {'Tm':<4}"
        for h in headers:
            hdr += f" {h:>7}"
        hdr += f"  {'GL':>3}"
        print(hdr)
        print(f"  {'─'*24} {'─'*4} {'─'*3}", end="")
        for _ in headers:
            print(f" {'─'*7}", end="")
        print(f"  {'─'*3}")

        team_totals = {}
        total_gp = 0

        for pkey in player_keys:
            info = player_info.get(pkey, {})
            pstats = player_stats.get(pkey, {})

            gp = pstats.get(GP_STAT_ID, 0)
            if isinstance(gp, (int, float)):
                total_gp += int(gp)
                gl = NBA_TOTAL_GAMES - int(gp)
            else:
                gl = '—'

            row = (f"  {info.get('name', '?'):<24} "
                   f"{info.get('position', '?'):<5} "
                   f"{info.get('team', ''):<4}")
            for sid in display_ids:
                val = pstats.get(sid, '-')
                if val != '-' and isinstance(val, (int, float)):
                    row += f" {fmt(sid, val):>7}"
                    if sid not in ('5', '8'):
                        team_totals[sid] = (
                            team_totals.get(sid, 0) + float(val))
                else:
                    row += f" {'—':>7}"

            # Accumulate components
            for cid in ('3', '4', '6', '7'):
                cval = pstats.get(cid)
                if cval is not None and isinstance(cval, (int, float)):
                    team_totals[cid] = team_totals.get(cid, 0) + cval

            row += f"  {gl:>3}"
            print(row)

        # Team totals row
        print(f"  {'─'*24} {'─'*4} {'─'*3}", end="")
        for _ in headers:
            print(f" {'─'*7}", end="")
        print(f"  {'─'*3}")

        num_players = len(player_keys)
        total_gl = (num_players * NBA_TOTAL_GAMES) - total_gp

        tot_row = f"  {'TOTALS':<24} {'':5} {'':4}"
        for sid in display_ids:
            if sid == '5' and '3' in team_totals and '4' in team_totals:
                pct = (team_totals['3'] / team_totals['4']
                       if team_totals['4'] > 0 else 0)
                tot_row += f" {fmt(sid, pct):>7}"
            elif sid == '8' and '6' in team_totals and '7' in team_totals:
                pct = (team_totals['6'] / team_totals['7']
                       if team_totals['7'] > 0 else 0)
                tot_row += f" {fmt(sid, pct):>7}"
            elif sid in team_totals:
                tot_row += f" {fmt(sid, team_totals[sid]):>7}"
            else:
                tot_row += f" {'—':>7}"
        tot_row += f"  {total_gl:>3}"
        print(tot_row)

        # Per-game averages
        print(f"\n  PER-GAME AVERAGES (season total / GP)")
        print(f"  {'─'*116}")

        hdr2 = f"  {'Player':<24} {'GP':>4}"
        avg_ids = [s for s in roto_stat_ids if s not in ('5', '8')]
        for sid in avg_ids:
            name = stat_id_map.get(sid, ROTO_STAT_NAMES.get(sid, f'S{sid}'))
            hdr2 += f" {name:>7}"
        print(hdr2)
        print(f"  {'─'*24} {'─'*4}", end="")
        for _ in avg_ids:
            print(f" {'─'*7}", end="")
        print()

        for pkey in player_keys:
            info = player_info.get(pkey, {})
            pstats = player_stats.get(pkey, {})
            gp = pstats.get(GP_STAT_ID, 0)

            row = f"  {info.get('name', '?'):<24}"
            if isinstance(gp, (int, float)) and gp > 0:
                row += f" {int(gp):>4}"
                for sid in avg_ids:
                    val = pstats.get(sid)
                    if val is not None and isinstance(val, (int, float)):
                        avg = val / gp
                        row += f" {avg:>7.1f}"
                    else:
                        row += f" {'—':>7}"
            else:
                row += f" {'—':>4}"
                for _ in avg_ids:
                    row += f" {'—':>7}"
            print(row)

        print(f"\n  Team GP: {total_gp}  |  Team GL: {total_gl}")
        if '3' in team_totals and '4' in team_totals:
            print(f"  FGM/FGA: {int(team_totals['3'])}"
                  f"/{int(team_totals['4'])}")
        if '6' in team_totals and '7' in team_totals:
            print(f"  FTM/FTA: {int(team_totals['6'])}"
                  f"/{int(team_totals['7'])}")
        print(f"{'='*120}\n")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
