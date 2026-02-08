"""
RotoCalculator - Rotisserie Scoring Analysis Class.

Calculates Roto standings, rankings per category, standings gaps,
and safety margins for each team.

In Rotisserie scoring, teams are ranked 1 to N in each statistical
category. A team's total Roto score is the sum of their ranks across
all categories. Higher total = better standing.

Reference: https://help.yahoo.com/kb/rotisserie-scoring-sln6187.html
"""
from copy import deepcopy


class RotoCalculator:
    """
    Analyzes Rotisserie scoring standings and gaps.

    Args:
        league_data: A populated LeagueData instance
    """

    def __init__(self, league_data):
        self.ld = league_data
        self.num_teams = len(self.ld.teams)

    def calculate_standings(self, team_stats=None):
        """
        Rank teams in each Roto category and compute total Roto scores.

        In each category, the team with the best value gets N points
        (where N = number of teams), second-best gets N-1, etc.
        For negative stats (like TO), lower values get higher ranks.

        Args:
            team_stats: Optional dict of {team_key: {stat_id: value}}.
                        If None, uses self.ld.team_stats.

        Returns:
            dict: {
                'rankings': {stat_id: [(team_key, value, rank_points), ...]},
                'roto_scores': {team_key: total_roto_score},
                'category_points': {team_key: {stat_id: rank_points}},
            }
        """
        if team_stats is None:
            team_stats = self.ld.team_stats

        num_teams = len(team_stats)
        rankings = {}
        category_points = {tk: {} for tk in team_stats}

        for stat_id in self.ld.roto_stat_ids:
            # Gather (team_key, value) for teams that have this stat
            teams_values = []
            for tk, stats in team_stats.items():
                val = stats.get(stat_id)
                if val is not None:
                    teams_values.append((tk, val))

            if not teams_values:
                continue

            # Sort: for negative stats (TO), lower is better -> ascending
            # For positive stats, higher is better -> descending
            reverse = not self.ld.is_negative_stat(stat_id)
            teams_values.sort(key=lambda x: x[1], reverse=reverse)

            # Assign rank points: best team gets num_teams, worst gets 1
            # Handle ties by averaging rank points
            ranked = []
            i = 0
            while i < len(teams_values):
                # Find all teams tied at this value
                j = i + 1
                while j < len(teams_values) and teams_values[j][1] == teams_values[i][1]:
                    j += 1

                # Average the rank points for tied teams
                # Positions i through j-1 correspond to rank points
                # (num_teams - i) down to (num_teams - j + 1)
                avg_points = sum(num_teams - k for k in range(i, j)) / (j - i)

                for k in range(i, j):
                    tk = teams_values[k][0]
                    val = teams_values[k][1]
                    ranked.append((tk, val, avg_points))
                    category_points[tk][stat_id] = avg_points

                i = j

            rankings[stat_id] = ranked

        # Calculate total Roto scores
        roto_scores = {}
        for tk in team_stats:
            roto_scores[tk] = sum(category_points.get(tk, {}).values())

        return {
            'rankings': rankings,
            'roto_scores': roto_scores,
            'category_points': category_points,
        }

    def get_standings_gaps(self, team_key):
        """
        Identify how much a team needs to gain/lose in each category to
        move up or down one rank.

        Returns:
            dict: {
                stat_id: {
                    'current_rank': int,
                    'current_value': float,
                    'to_gain_rank': float or None,  # units needed to move up
                    'to_lose_rank': float or None,  # units before dropping down
                    'next_above_value': float or None,
                    'next_below_value': float or None,
                    'rank_points': float,
                }
            }
        """
        result = self.calculate_standings()
        rankings = result['rankings']
        gaps = {}

        for stat_id in self.ld.roto_stat_ids:
            ranked = rankings.get(stat_id, [])
            if not ranked:
                continue

            # Find current team position
            team_idx = None
            for idx, (tk, val, pts) in enumerate(ranked):
                if tk == team_key:
                    team_idx = idx
                    break

            if team_idx is None:
                continue

            current_val = ranked[team_idx][1]
            rank_points = ranked[team_idx][2]
            is_negative = self.ld.is_negative_stat(stat_id)

            # To gain rank: look at team_idx - 1 (the one ranked above)
            to_gain = None
            next_above_val = None
            if team_idx > 0:
                next_above_val = ranked[team_idx - 1][1]
                if is_negative:
                    # Lower is better; need to reduce value below the team above
                    to_gain = current_val - next_above_val + 0.001
                else:
                    # Higher is better; need to exceed the team above
                    to_gain = next_above_val - current_val + 0.001

            # To lose rank: look at team_idx + 1 (the one ranked below)
            to_lose = None
            next_below_val = None
            if team_idx < len(ranked) - 1:
                next_below_val = ranked[team_idx + 1][1]
                if is_negative:
                    # Lower is better; would lose if value exceeds team below
                    to_lose = next_below_val - current_val
                else:
                    # Higher is better; would lose if value drops below team below
                    to_lose = current_val - next_below_val

            gaps[stat_id] = {
                'current_rank': team_idx + 1,
                'current_value': current_val,
                'to_gain_rank': round(to_gain, 3) if to_gain is not None else None,
                'to_lose_rank': round(to_lose, 3) if to_lose is not None else None,
                'next_above_value': next_above_val,
                'next_below_value': next_below_val,
                'rank_points': rank_points,
            }

        return gaps

    def get_safety_margins(self, team_key):
        """
        For each category, calculate the safety margin (how much the team
        can afford to lose before dropping a rank) and the opportunity
        (how little they need to gain to move up a rank).

        Returns:
            list of dicts sorted by opportunity (easiest gains first):
            [{
                'stat_id': str,
                'stat_name': str,
                'current_rank': int,
                'safety_margin': float or None,
                'opportunity': float or None,
                'rank_points': float,
            }]
        """
        gaps = self.get_standings_gaps(team_key)
        margins = []

        for stat_id, gap in gaps.items():
            margins.append({
                'stat_id': stat_id,
                'stat_name': self.ld.get_stat_name(stat_id),
                'current_rank': gap['current_rank'],
                'safety_margin': gap['to_lose_rank'],
                'opportunity': gap['to_gain_rank'],
                'rank_points': gap['rank_points'],
            })

        # Sort by opportunity (smallest gap = easiest to gain a rank)
        margins.sort(key=lambda x: x['opportunity'] if x['opportunity'] is not None else float('inf'))

        return margins

    def get_roto_standings_table(self):
        """
        Build a comprehensive standings table with Roto scores and
        per-category rank points.

        Returns:
            list of dicts sorted by total Roto score (descending):
            [{
                'team_key': str,
                'team_name': str,
                'roto_score': float,
                'category_points': {stat_id: float},
            }]
        """
        result = self.calculate_standings()
        table = []

        for tk in self.ld.teams:
            table.append({
                'team_key': tk,
                'team_name': self.ld.teams[tk],
                'roto_score': result['roto_scores'].get(tk, 0),
                'category_points': result['category_points'].get(tk, {}),
            })

        table.sort(key=lambda x: x['roto_score'], reverse=True)
        return table
