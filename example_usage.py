#!/usr/bin/env python3
"""
Example script showing how to use the Fantasy Basketball Client programmatically.

This demonstrates the basic API usage if you want to build your own analysis tools.
"""
from client import FantasyBasketballClient


def main():
    # Initialize the client
    client = FantasyBasketballClient()
    
    print(f"Connected to League: {client.league_id}")
    print(f"League Key: {client.league_key}\n")
    
    # Get all teams
    teams = client.get_teams()
    print("Teams:")
    for team_key, team_name in teams.items():
        print(f"  - {team_name} ({team_key})")
    
    # Get standings
    print("\nStandings:")
    standings = client.get_standings()
    for i, team in enumerate(standings, 1):
        name = team.get('name', 'Unknown')
        record = team.get('team_standings', {}).get('outcome_totals', {})
        wins = record.get('wins', 0)
        losses = record.get('losses', 0)
        print(f"  {i}. {name} ({wins}-{losses})")
    
    # Get league settings
    settings = client.get_league_settings()
    print(f"\nLeague Scoring Type: {settings.get('scoring_type', 'Unknown')}")
    
    # Show stat categories
    stat_cats = settings.get('stat_categories', {}).get('stats', [])
    print("\nScoring Categories:")
    for cat in stat_cats:
        print(f"  - {cat.get('display_name', 'Unknown')}")
    
    # Example: Get roster for first team
    if teams:
        first_team_key = list(teams.keys())[0]
        print(f"\nRoster for {teams[first_team_key]}:")
        roster = client.get_team_roster(first_team_key)
        for player in roster[:5]:  # Show first 5 players
            player_name = player.get('name', {}).get('full', 'Unknown')
            position = player.get('selected_position', {}).get('position', 'N/A')
            print(f"  - {player_name} ({position})")


if __name__ == '__main__':
    main()
