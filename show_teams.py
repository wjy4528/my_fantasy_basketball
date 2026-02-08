#!/usr/bin/env python3
"""
Show all teams in your fantasy basketball league.

Usage:
    python show_teams.py
"""
import sys
from client import FantasyBasketballClient


def main():
    """Display all teams in the league"""
    try:
        print("Connecting to Yahoo Fantasy Basketball API...")
        client = FantasyBasketballClient()
        
        print(f"\n{'='*60}")
        print(f"League ID: {client.league_id}")
        print(f"{'='*60}\n")
        
        # Get teams
        teams = client.get_teams()
        
        print("Teams in your league:")
        print("-" * 60)
        for team_key, team_name in teams.items():
            print(f"  {team_name} (Key: {team_key})")
        
        print(f"\nTotal teams: {len(teams)}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nMake sure you have:")
        print("1. Created a .env file with your credentials")
        print("2. Set up your Yahoo Fantasy Sports API app at https://developer.yahoo.com/apps/")
        print("3. Run the authentication flow (oauth2.json will be created)")
        sys.exit(1)


if __name__ == '__main__':
    main()
