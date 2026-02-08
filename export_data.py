#!/usr/bin/env python3
"""
Export all league data (rosters, player stats, team stats) as JSON.

Generates a single JSON file that can be fed into an AI assistant
(e.g., ChatGPT, Claude) for trade analysis and strategy suggestions.

Usage:
    python export_data.py
    python export_data.py --output my_league.json
"""
import argparse
import json
import sys
from datetime import datetime

from league_data import LeagueData


NBA_TOTAL_GAMES = 82


def main():
    parser = argparse.ArgumentParser(
        description="Export all league data as JSON for AI-assisted trade analysis"
    )
    parser.add_argument(
        '--output', '-o',
        default='league_export.json',
        help='Output JSON file path (default: league_export.json)'
    )
    args = parser.parse_args()

    try:
        print("Connecting to Yahoo Fantasy Basketball API...")
        ld = LeagueData()

        print("Fetching league settings...")
        ld.fetch_settings()

        print("Fetching standings...")
        ld.fetch_standings()

        print(f"Found {len(ld.teams)} teams in league {ld.client.league_id}")

        print("Fetching rosters for all teams...")
        ld.fetch_rosters()

        print("Fetching player season stats...")
        ld.fetch_player_stats()

        total_players = sum(len(r) for r in ld.rosters.values())
        print(f"Loaded stats for {len(ld.player_stats)} of {total_players} players")

        # Build export data
        export = {
            'metadata': {
                'league_id': ld.client.league_id,
                'exported_at': datetime.now().isoformat(),
                'season': '2025-2026',
                'nba_total_games': NBA_TOTAL_GAMES,
                'stat_categories': [
                    ld.get_stat_name(sid) for sid in ld.roto_stat_ids
                ],
                'stat_id_map': ld.stat_id_map,
                'roto_stat_ids': ld.roto_stat_ids,
                'negative_stats': list(ld.negative_stats),
            },
            'teams': {},
        }

        for team_key, team_name in ld.teams.items():
            team_data = {
                'name': team_name,
                'team_key': team_key,
                'team_totals': {},
                'roster': [],
            }

            # Team totals (computed from player sums)
            team_stats = ld.team_stats.get(team_key, {})
            for sid in ld.roto_stat_ids:
                stat_name = ld.get_stat_name(sid)
                val = team_stats.get(sid)
                if val is not None:
                    team_data['team_totals'][stat_name] = val
            # Include GP and component stats in team totals
            gp_total = team_stats.get('0')
            if gp_total is not None:
                team_data['team_totals']['GP'] = gp_total
            for comp_id, comp_name in [('3', 'FGM'), ('4', 'FGA'),
                                       ('6', 'FTM'), ('7', 'FTA')]:
                val = team_stats.get(comp_id)
                if val is not None:
                    team_data['team_totals'][comp_name] = val

            # Player details
            player_keys = ld.get_team_player_keys(team_key)
            for pkey in player_keys:
                info = ld.player_info.get(pkey, {})
                pstats = ld.player_stats.get(pkey, {})

                gp = pstats.get('0', 0)
                games_left = (NBA_TOTAL_GAMES - int(gp)
                              if isinstance(gp, (int, float)) else None)

                player_entry = {
                    'player_id': pkey,
                    'name': info.get('name', 'Unknown'),
                    'position': info.get('position', 'N/A'),
                    'nba_team': info.get('team', ''),
                    'games_played': (int(gp) if isinstance(gp, (int, float))
                                     else None),
                    'games_left': games_left,
                    'season_totals': {},
                    'per_game_averages': {},
                }

                for sid in ld.roto_stat_ids:
                    stat_name = ld.get_stat_name(sid)
                    val = pstats.get(sid)
                    if val is not None:
                        player_entry['season_totals'][stat_name] = val
                        # Per-game averages (skip percentages)
                        if (sid not in ('5', '8')
                                and isinstance(gp, (int, float)) and gp > 0):
                            player_entry['per_game_averages'][stat_name] = (
                                round(val / gp, 2))

                # Component stats
                for comp_id, comp_name in [('3', 'FGM'), ('4', 'FGA'),
                                           ('6', 'FTM'), ('7', 'FTA')]:
                    val = pstats.get(comp_id)
                    if val is not None:
                        player_entry['season_totals'][comp_name] = val

                team_data['roster'].append(player_entry)

            export['teams'][team_key] = team_data

        # Write JSON
        with open(args.output, 'w') as f:
            json.dump(export, f, indent=2, default=str)

        print(f"\n✅ Data exported to {args.output}")
        print(f"   {len(ld.teams)} teams, {len(ld.player_stats)} players with stats")
        print(f"\n   You can feed this file into an AI assistant for trade analysis.")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
