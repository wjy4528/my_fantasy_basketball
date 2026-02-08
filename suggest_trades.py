#!/usr/bin/env python3
"""
Analyze teams and suggest trades based on team needs and strengths.

This script analyzes each team's performance in different statistical categories
and suggests potential trades where both teams could benefit.

Usage:
    python suggest_trades.py
"""
import sys
from collections import defaultdict
from client import FantasyBasketballClient


def analyze_team_strengths(standings, stat_categories):
    """
    Analyze each team's strengths and weaknesses in different categories.
    
    Args:
        standings: List of teams with their stats
        stat_categories: List of stat categories used in the league
        
    Returns:
        dict: Team analysis with strengths and weaknesses
    """
    team_analysis = {}
    
    # Extract stat values for each team
    team_stats = {}
    for team in standings:
        team_key = team.get('team_key', '')
        team_name = team.get('name', 'Unknown')
        stats = team.get('team_stats', {}).get('stats', [])
        
        team_stats[team_key] = {
            'name': team_name,
            'stats': {stat['stat_id']: float(stat.get('value', 0)) for stat in stats if stat.get('value') != '-'}
        }
    
    # For each stat category, rank teams
    stat_rankings = defaultdict(list)
    for stat_id in set(s for t in team_stats.values() for s in t['stats'].keys()):
        # Get all teams that have this stat
        teams_with_stat = [(tk, tv['name'], tv['stats'].get(stat_id, 0)) 
                          for tk, tv in team_stats.items() if stat_id in tv['stats']]
        
        # Sort by stat value (descending)
        teams_with_stat.sort(key=lambda x: x[2], reverse=True)
        stat_rankings[stat_id] = teams_with_stat
    
    # Determine strengths and weaknesses for each team
    for team_key, team_data in team_stats.items():
        strengths = []
        weaknesses = []
        
        for stat_id, rankings in stat_rankings.items():
            if stat_id not in team_data['stats']:
                continue
                
            # Find team's rank in this stat
            team_rank = next((i for i, (tk, _, _) in enumerate(rankings) if tk == team_key), None)
            
            if team_rank is not None:
                total_teams = len(rankings)
                # Top 25% = strength, Bottom 25% = weakness
                if team_rank < total_teams * 0.25:
                    strengths.append(stat_id)
                elif team_rank > total_teams * 0.75:
                    weaknesses.append(stat_id)
        
        team_analysis[team_key] = {
            'name': team_data['name'],
            'strengths': strengths,
            'weaknesses': weaknesses,
            'stats': team_data['stats']
        }
    
    return team_analysis, stat_rankings


def suggest_trade_partners(team_analysis, your_team_key=None):
    """
    Suggest potential trade partners based on complementary needs.
    
    Args:
        team_analysis: Analysis of all teams
        your_team_key: Your team key (if None, suggests trades for all teams)
        
    Returns:
        list: List of trade suggestions
    """
    suggestions = []
    
    teams_to_analyze = [your_team_key] if your_team_key else list(team_analysis.keys())
    
    for team_a_key in teams_to_analyze:
        team_a = team_analysis[team_a_key]
        
        for team_b_key, team_b in team_analysis.items():
            if team_a_key == team_b_key:
                continue
            
            # Find complementary strengths/weaknesses
            # Team A is weak where Team B is strong
            beneficial_cats_for_a = set(team_a['weaknesses']) & set(team_b['strengths'])
            # Team B is weak where Team A is strong  
            beneficial_cats_for_b = set(team_b['weaknesses']) & set(team_a['strengths'])
            
            if beneficial_cats_for_a and beneficial_cats_for_b:
                suggestions.append({
                    'team_a': team_a['name'],
                    'team_a_key': team_a_key,
                    'team_b': team_b['name'],
                    'team_b_key': team_b_key,
                    'team_a_gets': list(beneficial_cats_for_a),
                    'team_b_gets': list(beneficial_cats_for_b),
                    'synergy_score': len(beneficial_cats_for_a) + len(beneficial_cats_for_b)
                })
    
    # Sort by synergy score
    suggestions.sort(key=lambda x: x['synergy_score'], reverse=True)
    
    return suggestions


def get_stat_name(stat_id, stat_categories):
    """Get human-readable stat name"""
    for cat in stat_categories:
        if str(cat.get('stat_id')) == str(stat_id):
            return cat.get('display_name', f'Stat {stat_id}')
    return f'Stat {stat_id}'


def main():
    """Analyze teams and suggest trades"""
    try:
        print("Connecting to Yahoo Fantasy Basketball API...")
        client = FantasyBasketballClient()
        
        print(f"\n{'='*80}")
        print(f"Trade Analysis - League ID: {client.league_id}")
        print(f"{'='*80}\n")
        
        # Get data
        print("Fetching league data...")
        standings = client.get_standings()
        settings = client.get_league_settings()
        stat_categories = settings.get('stat_categories', {}).get('stats', [])
        
        # Analyze teams
        print("Analyzing team strengths and weaknesses...\n")
        team_analysis, stat_rankings = analyze_team_strengths(standings, stat_categories)
        
        # Display team analysis
        print("="*80)
        print("TEAM ANALYSIS")
        print("="*80)
        
        for team_key, analysis in team_analysis.items():
            print(f"\n{analysis['name']}:")
            print(f"  Strengths (Top 25%):")
            if analysis['strengths']:
                for stat_id in analysis['strengths']:
                    stat_name = get_stat_name(stat_id, stat_categories)
                    print(f"    - {stat_name}")
            else:
                print(f"    - None identified")
            
            print(f"  Weaknesses (Bottom 25%):")
            if analysis['weaknesses']:
                for stat_id in analysis['weaknesses']:
                    stat_name = get_stat_name(stat_id, stat_categories)
                    print(f"    - {stat_name}")
            else:
                print(f"    - None identified")
        
        # Suggest trades
        print(f"\n{'='*80}")
        print("TRADE SUGGESTIONS")
        print("="*80)
        print("\nBased on complementary team needs, here are potential trade partners:\n")
        
        suggestions = suggest_trade_partners(team_analysis)
        
        if not suggestions:
            print("No clear trade opportunities found based on current team stats.")
        else:
            for i, suggestion in enumerate(suggestions[:10], 1):  # Show top 10
                print(f"{i}. {suggestion['team_a']} <--> {suggestion['team_b']}")
                print(f"   Synergy Score: {suggestion['synergy_score']}/10")
                print(f"   {suggestion['team_a']} would improve in:")
                for stat_id in suggestion['team_a_gets']:
                    stat_name = get_stat_name(stat_id, stat_categories)
                    print(f"     - {stat_name}")
                print(f"   {suggestion['team_b']} would improve in:")
                for stat_id in suggestion['team_b_gets']:
                    stat_name = get_stat_name(stat_id, stat_categories)
                    print(f"     - {stat_name}")
                print()
        
        print("="*80)
        print("\nNOTE: These suggestions are based on statistical analysis.")
        print("Consider player values, injury status, and schedule when proposing trades.")
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
