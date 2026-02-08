#!/usr/bin/env python3
"""
Show detailed stats for all teams in your fantasy basketball league.

Usage:
    python show_team_stats.py
"""
import sys
from client import FantasyBasketballClient


def main():
    """Display team statistics for all teams"""
    try:
        print("Connecting to Yahoo Fantasy Basketball API...")
        client = FantasyBasketballClient()
        
        print(f"\n{'='*80}")
        print(f"League Statistics - League ID: {client.league_id}")
        print(f"{'='*80}\n")
        
        # Get standings (includes stats)
        standings = client.get_standings()
        
        print("Team Standings and Statistics:")
        print("-" * 80)
        
        for i, team in enumerate(standings, 1):
            print(f"\n{i}. {team.get('name', 'Unknown Team')}")
            print(f"   Manager: {team.get('managers', [{}])[0].get('nickname', 'Unknown')}")
            
            # Standings info
            outcome_totals = team.get('team_standings', {}).get('outcome_totals', {})
            print(f"   Record: {outcome_totals.get('wins', 0)}-{outcome_totals.get('losses', 0)}-{outcome_totals.get('ties', 0)}")
            print(f"   Rank: {team.get('team_standings', {}).get('rank', 'N/A')}")
            
            # Points
            if 'team_points' in team.get('team_standings', {}):
                points = team['team_standings']['team_points']
                print(f"   Points: {points.get('total', 'N/A')}")
            
            # Team stats (if available)
            if 'team_stats' in team:
                stats = team['team_stats'].get('stats', [])
                if stats:
                    print(f"   Stats:")
                    for stat in stats[:10]:  # Show first 10 stats
                        stat_id = stat.get('stat_id', 'N/A')
                        value = stat.get('value', 'N/A')
                        print(f"     Stat {stat_id}: {value}")
        
        print("\n" + "="*80)
        
        # Get league settings to show scoring categories
        print("\nLeague Settings:")
        settings = client.get_league_settings()
        print(f"Scoring type: {settings.get('scoring_type', 'Unknown')}")
        
        stat_categories = settings.get('stat_categories', {}).get('stats', [])
        if stat_categories:
            print(f"\nScoring Categories:")
            for cat in stat_categories:
                print(f"  - {cat.get('display_name', 'Unknown')}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
