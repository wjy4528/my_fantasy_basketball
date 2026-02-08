"""
TradeSimulator - Simulate trades and project their impact on Roto standings.

Handles the nuances of Roto trade analysis:
- Projects rest-of-season stats based on player averages
- Updates team totals by swapping players
- Recalculates standings to determine net Roto score changes
- Properly handles FG% and FT% by tracking component stats (FGM/FGA, FTM/FTA)
"""
from copy import deepcopy

from roto_calculator import RotoCalculator


# Component stat IDs for percentage recalculation
PERCENTAGE_COMPONENTS = {
    '5': {'made': '3', 'attempted': '4'},   # FG% = FGM / FGA
    '8': {'made': '6', 'attempted': '7'},   # FT% = FTM / FTA
}


class TradeSimulator:
    """
    Simulates trades between teams and evaluates their impact.

    Args:
        league_data: A populated LeagueData instance
        remaining_games: Estimated remaining games in the season (default: 30)
    """

    def __init__(self, league_data, remaining_games=30):
        self.ld = league_data
        self.remaining_games = remaining_games
        self.calculator = RotoCalculator(league_data)

    def project_player_ros(self, player_key):
        """
        Project a player's rest-of-season (ROS) stats.

        Multiplies season averages by remaining games to estimate
        the player's remaining contribution.

        Args:
            player_key: Yahoo player key

        Returns:
            dict: {stat_id: projected_remaining_value}
        """
        averages = self.ld.player_stats.get(player_key, {})
        projected = {}
        for stat_id, avg_val in averages.items():
            # For percentage stats, keep as-is (handled via components)
            if stat_id in ('5', '8'):
                projected[stat_id] = avg_val
            else:
                projected[stat_id] = avg_val * self.remaining_games
        return projected

    def simulate_trade(self, my_players, their_players, my_team_key, their_team_key):
        """
        Simulate a trade and return the impact on Roto scores.

        Process:
        1. Project ROS stats for all players involved
        2. Create modified team_stats by removing/adding projected contributions
        3. Recalculate Roto standings with modified stats
        4. Return the net change in Roto score for both teams

        For FG% and FT%, we track FGM/FGA and FTM/FTA components to
        properly recalculate percentages after player swaps.

        Args:
            my_players: List of player_keys I'm trading away
            their_players: List of player_keys I'm receiving
            my_team_key: My team's Yahoo key
            their_team_key: Opponent team's Yahoo key

        Returns:
            dict: {
                'my_old_score': float,
                'my_new_score': float,
                'my_delta': float,
                'their_old_score': float,
                'their_new_score': float,
                'their_delta': float,
                'my_players_traded': [player_names],
                'their_players_traded': [player_names],
            }
        """
        # Calculate current standings
        old_result = self.calculator.calculate_standings()
        old_my_score = old_result['roto_scores'].get(my_team_key, 0)
        old_their_score = old_result['roto_scores'].get(their_team_key, 0)

        # Create a copy of team stats to modify
        new_team_stats = deepcopy(self.ld.team_stats)

        # Project ROS stats for traded players
        my_projected = {}
        for pkey in my_players:
            my_projected[pkey] = self.project_player_ros(pkey)

        their_projected = {}
        for pkey in their_players:
            their_projected[pkey] = self.project_player_ros(pkey)

        # Update team stats:
        # My team: remove my_players' projections, add their_players' projections
        # Their team: remove their_players' projections, add my_players' projections
        for stat_id in self.ld.roto_stat_ids:
            # Skip percentage stats - handle via components
            if stat_id in PERCENTAGE_COMPONENTS:
                continue

            # My team adjustments
            if my_team_key in new_team_stats:
                current = new_team_stats[my_team_key].get(stat_id, 0)
                # Remove my players' projected contribution
                for pkey in my_players:
                    current -= my_projected.get(pkey, {}).get(stat_id, 0)
                # Add their players' projected contribution
                for pkey in their_players:
                    current += their_projected.get(pkey, {}).get(stat_id, 0)
                new_team_stats[my_team_key][stat_id] = current

            # Their team adjustments
            if their_team_key in new_team_stats:
                current = new_team_stats[their_team_key].get(stat_id, 0)
                # Remove their players' projected contribution
                for pkey in their_players:
                    current -= their_projected.get(pkey, {}).get(stat_id, 0)
                # Add my players' projected contribution
                for pkey in my_players:
                    current += my_projected.get(pkey, {}).get(stat_id, 0)
                new_team_stats[their_team_key][stat_id] = current

        # Handle percentage stats via component recalculation
        for pct_stat_id, components in PERCENTAGE_COMPONENTS.items():
            made_id = components['made']
            attempted_id = components['attempted']

            for team_key, remove_players, add_players in [
                (my_team_key, my_players, their_players),
                (their_team_key, their_players, my_players),
            ]:
                if team_key not in new_team_stats:
                    continue

                made = new_team_stats[team_key].get(made_id, 0)
                attempted = new_team_stats[team_key].get(attempted_id, 0)

                for pkey in remove_players:
                    p_stats = self.ld.player_stats.get(pkey, {})
                    made -= p_stats.get(made_id, 0) * self.remaining_games
                    attempted -= p_stats.get(attempted_id, 0) * self.remaining_games

                for pkey in add_players:
                    p_stats = self.ld.player_stats.get(pkey, {})
                    made += p_stats.get(made_id, 0) * self.remaining_games
                    attempted += p_stats.get(attempted_id, 0) * self.remaining_games

                new_team_stats[team_key][made_id] = made
                new_team_stats[team_key][attempted_id] = attempted

                # Recalculate percentage
                if attempted > 0:
                    new_team_stats[team_key][pct_stat_id] = made / attempted
                else:
                    new_team_stats[team_key][pct_stat_id] = 0.0

        # Recalculate standings with modified stats
        new_result = self.calculator.calculate_standings(new_team_stats)
        new_my_score = new_result['roto_scores'].get(my_team_key, 0)
        new_their_score = new_result['roto_scores'].get(their_team_key, 0)

        # Get player names for display
        my_names = [
            self.ld.player_info.get(pk, {}).get('name', pk)
            for pk in my_players
        ]
        their_names = [
            self.ld.player_info.get(pk, {}).get('name', pk)
            for pk in their_players
        ]

        return {
            'my_old_score': old_my_score,
            'my_new_score': new_my_score,
            'my_delta': new_my_score - old_my_score,
            'their_old_score': old_their_score,
            'their_new_score': new_their_score,
            'their_delta': new_their_score - old_their_score,
            'my_players_traded': my_names,
            'their_players_traded': their_names,
        }

    def find_best_trades(self, my_team_key, max_results=5):
        """
        Iterate through possible 1-for-1 trades and find the best ones.

        Strategy:
        - Start with opponents who are strong in categories where
          my team is weak (using RotoCalculator safety margins).
        - Simulate all 1-for-1 trades.
        - Filter: trade must increase MY Roto score.
        - Prefer: trade also doesn't hurt opponent's score (trade likelihood).

        Args:
            my_team_key: My team's Yahoo key
            max_results: Maximum number of trade suggestions to return

        Returns:
            list of trade result dicts, sorted by my_delta descending
        """
        my_player_keys = self.ld.get_team_player_keys(my_team_key)
        all_trades = []

        for opp_team_key in self.ld.teams:
            if opp_team_key == my_team_key:
                continue

            opp_player_keys = self.ld.get_team_player_keys(opp_team_key)

            for my_pk in my_player_keys:
                for their_pk in opp_player_keys:
                    result = self.simulate_trade(
                        [my_pk], [their_pk],
                        my_team_key, opp_team_key,
                    )

                    # Must-Have: trade increases MY Roto score
                    if result['my_delta'] <= 0:
                        continue

                    result['opponent_team'] = self.ld.teams.get(opp_team_key, opp_team_key)
                    result['opponent_team_key'] = opp_team_key
                    result['my_team'] = self.ld.teams.get(my_team_key, my_team_key)

                    # Nice-to-Have flag: doesn't hurt opponent
                    result['mutually_beneficial'] = result['their_delta'] >= 0

                    all_trades.append(result)

        # Sort: prioritize mutual benefit, then by my_delta
        all_trades.sort(
            key=lambda x: (x['mutually_beneficial'], x['my_delta']),
            reverse=True,
        )

        return all_trades[:max_results]
