#!/usr/bin/env python3
"""
Roto Analyzer - Full Rotisserie League Analysis & Trade Suggestion Engine.

This is the main orchestrator that:
1. Fetches all league data (settings, standings, rosters, player stats)
2. Calculates Roto standings and per-category rankings
3. Identifies standings gaps and safety margins for your team
4. Simulates 1-for-1 trades and suggests the best ones
5. Outputs results in a Pandas DataFrame

Usage:
    python roto_analyzer.py
    python roto_analyzer.py --team-key 428.l.21454.t.1
"""
import argparse
import sys

import pandas as pd

from league_data import LeagueData
from roto_calculator import RotoCalculator
from trade_simulator import TradeSimulator


def select_my_team(league_data):
    """
    Let the user select their team from the league.

    Args:
        league_data: Populated LeagueData instance

    Returns:
        str: Selected team_key
    """
    teams = list(league_data.teams.items())
    print("\nSelect your team:")
    for i, (tk, name) in enumerate(teams, 1):
        print(f"  {i}. {name} ({tk})")

    while True:
        try:
            choice = input(f"\nEnter team number (1-{len(teams)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(teams):
                return teams[idx][0]
        except (ValueError, EOFError):
            pass
        print("Invalid selection. Please try again.")


def print_standings(calculator):
    """Print the current Roto standings table."""
    table = calculator.get_roto_standings_table()

    print(f"\n{'='*90}")
    print("  ROTISSERIE STANDINGS")
    print(f"{'='*90}")

    # Header
    header = f"  {'Rank':<5} {'Team':<25} {'Roto':>6}"
    for stat_id in calculator.ld.roto_stat_ids:
        name = calculator.ld.get_stat_name(stat_id)
        header += f" {name:>6}"
    print(header)
    print(f"  {'─'*5} {'─'*25} {'─'*6}", end="")
    for _ in calculator.ld.roto_stat_ids:
        print(f" {'─'*6}", end="")
    print()

    for rank, entry in enumerate(table, 1):
        row = f"  {rank:<5} {entry['team_name']:<25} {entry['roto_score']:>6.1f}"
        for stat_id in calculator.ld.roto_stat_ids:
            pts = entry['category_points'].get(stat_id, 0)
            row += f" {pts:>6.1f}"
        print(row)


def print_safety_margins(calculator, team_key):
    """Print safety margins and opportunities for a team."""
    margins = calculator.get_safety_margins(team_key)
    team_name = calculator.ld.teams.get(team_key, team_key)

    print(f"\n{'='*90}")
    print(f"  STANDINGS GAPS & SAFETY MARGINS - {team_name}")
    print(f"{'='*90}")
    print(f"  {'Category':<12} {'Rank':>5} {'Pts':>6} {'To Gain Rank':>14} {'Safety Margin':>14}")
    print(f"  {'─'*12} {'─'*5} {'─'*6} {'─'*14} {'─'*14}")

    for m in margins:
        gain_str = f"{m['opportunity']:.1f}" if m['opportunity'] is not None else "Already #1"
        safety_str = f"{m['safety_margin']:.1f}" if m['safety_margin'] is not None else "Already Last"
        print(f"  {m['stat_name']:<12} {m['current_rank']:>5} {m['rank_points']:>6.1f}"
              f" {gain_str:>14} {safety_str:>14}")


def print_trade_suggestions(trades, league_data):
    """Print trade suggestions as a formatted table and DataFrame."""
    if not trades:
        print("\n  No beneficial trades found.")
        return

    print(f"\n{'='*90}")
    print("  TOP TRADE SUGGESTIONS")
    print(f"{'='*90}")

    # Build DataFrame
    rows = []
    for i, trade in enumerate(trades, 1):
        my_give = ', '.join(trade['my_players_traded'])
        my_get = ', '.join(trade['their_players_traded'])

        rows.append({
            'Rank': i,
            'You Give': my_give,
            'You Get': my_get,
            'Opponent': trade.get('opponent_team', ''),
            'Your Δ Roto': f"+{trade['my_delta']:.1f}" if trade['my_delta'] > 0 else f"{trade['my_delta']:.1f}",
            'Their Δ Roto': f"+{trade['their_delta']:.1f}" if trade['their_delta'] > 0 else f"{trade['their_delta']:.1f}",
            'Mutual': '✓' if trade.get('mutually_beneficial') else '✗',
        })

    df = pd.DataFrame(rows)
    print()
    print(df.to_string(index=False))

    # Also print detailed view
    print(f"\n{'─'*90}")
    for i, trade in enumerate(trades, 1):
        mutual = "YES ✓" if trade.get('mutually_beneficial') else "NO"
        print(f"\n  Trade #{i}:")
        print(f"    You give:  {', '.join(trade['my_players_traded'])}")
        print(f"    You get:   {', '.join(trade['their_players_traded'])}")
        print(f"    From:      {trade.get('opponent_team', '')}")
        print(f"    Your Roto: {trade['my_old_score']:.1f} → {trade['my_new_score']:.1f}"
              f" (Δ {trade['my_delta']:+.1f})")
        print(f"    Their Roto: {trade['their_old_score']:.1f} → {trade['their_new_score']:.1f}"
              f" (Δ {trade['their_delta']:+.1f})")
        print(f"    Mutually beneficial: {mutual}")


def main():
    parser = argparse.ArgumentParser(
        description="Roto Fantasy Basketball Analyzer & Trade Suggester"
    )
    parser.add_argument(
        '--team-key',
        help='Your team key (e.g., 428.l.21454.t.1). If not provided, you will be prompted.'
    )
    parser.add_argument(
        '--remaining-games',
        type=int, default=30,
        help='Estimated remaining games per player (default: 30)'
    )
    parser.add_argument(
        '--top-trades',
        type=int, default=5,
        help='Number of top trade suggestions to show (default: 5)'
    )
    args = parser.parse_args()

    try:
        print("=" * 90)
        print("  ROTO FANTASY BASKETBALL ANALYZER")
        print("=" * 90)

        # Step 1: Fetch all league data
        print("\n  Connecting to Yahoo Fantasy Basketball API...")
        ld = LeagueData()

        print("  Fetching league settings...")
        ld.fetch_settings()

        print("  Fetching standings...")
        ld.fetch_standings()

        print(f"  Found {len(ld.teams)} teams in league {ld.client.league_id}")

        print("  Fetching rosters for all teams...")
        ld.fetch_rosters()

        print("  Fetching player season stats...")
        ld.fetch_player_stats()

        total_players = sum(len(r) for r in ld.rosters.values())
        print(f"  Loaded stats for {len(ld.player_stats)} of {total_players} players")

        # Step 2: Calculate Roto standings
        calculator = RotoCalculator(ld)
        print_standings(calculator)

        # Step 3: Select team
        if args.team_key:
            my_team_key = args.team_key
            if my_team_key not in ld.teams:
                print(f"\n  Error: Team key '{my_team_key}' not found in league.")
                print("  Available teams:")
                for tk, name in ld.teams.items():
                    print(f"    {tk} - {name}")
                sys.exit(1)
        else:
            my_team_key = select_my_team(ld)

        my_team_name = ld.teams.get(my_team_key, my_team_key)
        print(f"\n  Analyzing trades for: {my_team_name}")

        # Step 4: Show safety margins
        print_safety_margins(calculator, my_team_key)

        # Step 5: Simulate trades
        print(f"\n  Simulating 1-for-1 trades across all opponents...")
        print(f"  (Remaining games estimate: {args.remaining_games})")

        simulator = TradeSimulator(ld, remaining_games=args.remaining_games)
        trades = simulator.find_best_trades(my_team_key, max_results=args.top_trades)

        print_trade_suggestions(trades, ld)

        print(f"\n{'='*90}")
        print("  NOTES:")
        print("  - Trades are ranked by Roto score improvement")
        print("  - 'Mutual' trades are more likely to be accepted")
        print("  - FG% and FT% are recalculated using FGM/FGA and FTM/FTA components")
        print("  - Projections use season averages × remaining games")
        print("  - Consider injuries, schedule, and player values when proposing trades")
        print("  - Roto reference: https://help.yahoo.com/kb/rotisserie-scoring-sln6187.html")
        print(f"{'='*90}\n")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
