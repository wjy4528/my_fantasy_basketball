"""
Tests for RotoCalculator and TradeSimulator.

These tests verify the core Roto scoring logic using mock data,
without requiring Yahoo Fantasy API access.
"""
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add parent directory to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class MockLeagueData:
    """Mock LeagueData for testing without API access."""

    def __init__(self):
        self.teams = {
            'team.1': 'Team Alpha',
            'team.2': 'Team Beta',
            'team.3': 'Team Gamma',
            'team.4': 'Team Delta',
        }
        self.roto_stat_ids = ['12', '15', '16', '17', '18', '19']
        # stat names: PTS, REB, AST, STL, BLK, TO
        self.stat_id_map = {
            '12': 'PTS', '15': 'REB', '16': 'AST',
            '17': 'STL', '18': 'BLK', '19': 'TO',
        }
        self.negative_stats = {'19'}  # TO is negative (lower is better)

        # Season totals for each team
        self.team_stats = {
            'team.1': {'12': 5000, '15': 2000, '16': 1200, '17': 400, '18': 300, '19': 600},
            'team.2': {'12': 4800, '15': 2200, '16': 1100, '17': 350, '18': 500, '19': 500},
            'team.3': {'12': 5200, '15': 1800, '16': 1300, '17': 450, '18': 200, '19': 700},
            'team.4': {'12': 4600, '15': 2100, '16': 1000, '17': 300, '18': 400, '19': 550},
        }

        # Rosters (player keys per team)
        self.rosters = {
            'team.1': [{'player_key': 'p1'}, {'player_key': 'p2'}],
            'team.2': [{'player_key': 'p3'}, {'player_key': 'p4'}],
            'team.3': [{'player_key': 'p5'}, {'player_key': 'p6'}],
            'team.4': [{'player_key': 'p7'}, {'player_key': 'p8'}],
        }

        # Player season averages
        self.player_stats = {
            'p1': {'12': 25.0, '15': 10.0, '16': 6.0, '17': 2.0, '18': 1.5, '19': 3.0},
            'p2': {'12': 20.0, '15': 8.0,  '16': 5.0, '17': 1.5, '18': 1.0, '19': 2.5},
            'p3': {'12': 22.0, '15': 11.0, '16': 4.0, '17': 1.8, '18': 2.5, '19': 2.0},
            'p4': {'12': 18.0, '15': 9.0,  '16': 7.0, '17': 1.0, '18': 2.0, '19': 3.5},
            'p5': {'12': 28.0, '15': 7.0,  '16': 8.0, '17': 2.5, '18': 0.5, '19': 4.0},
            'p6': {'12': 15.0, '15': 6.0,  '16': 3.0, '17': 1.0, '18': 0.5, '19': 2.0},
            'p7': {'12': 20.0, '15': 10.0, '16': 5.0, '17': 1.5, '18': 2.0, '19': 2.5},
            'p8': {'12': 16.0, '15': 8.0,  '16': 4.0, '17': 1.0, '18': 1.5, '19': 3.0},
        }

        self.player_info = {
            'p1': {'name': 'Player One', 'position': 'PG', 'team': 'LAL', 'team_key': 'team.1'},
            'p2': {'name': 'Player Two', 'position': 'SG', 'team': 'BOS', 'team_key': 'team.1'},
            'p3': {'name': 'Player Three', 'position': 'SF', 'team': 'MIA', 'team_key': 'team.2'},
            'p4': {'name': 'Player Four', 'position': 'PF', 'team': 'GSW', 'team_key': 'team.2'},
            'p5': {'name': 'Player Five', 'position': 'C', 'team': 'PHX', 'team_key': 'team.3'},
            'p6': {'name': 'Player Six', 'position': 'PG', 'team': 'DAL', 'team_key': 'team.3'},
            'p7': {'name': 'Player Seven', 'position': 'SG', 'team': 'DEN', 'team_key': 'team.4'},
            'p8': {'name': 'Player Eight', 'position': 'SF', 'team': 'MIL', 'team_key': 'team.4'},
        }

    def get_team_player_keys(self, team_key):
        roster = self.rosters.get(team_key, [])
        return [p['player_key'] for p in roster]

    def get_stat_name(self, stat_id):
        return self.stat_id_map.get(str(stat_id), f'Stat {stat_id}')

    def is_negative_stat(self, stat_id):
        return str(stat_id) in self.negative_stats


class TestRotoCalculator(unittest.TestCase):
    """Test the RotoCalculator class."""

    def setUp(self):
        self.ld = MockLeagueData()
        from roto_calculator import RotoCalculator
        self.calc = RotoCalculator(self.ld)

    def test_calculate_standings_returns_all_teams(self):
        """All teams should have Roto scores."""
        result = self.calc.calculate_standings()
        self.assertEqual(set(result['roto_scores'].keys()), set(self.ld.teams.keys()))

    def test_roto_scores_sum_correctly(self):
        """Total Roto points across all teams should equal N*(N+1)/2 per category."""
        result = self.calc.calculate_standings()
        n = len(self.ld.teams)
        expected_total_per_cat = n * (n + 1) / 2  # 1+2+3+4 = 10

        total_roto = sum(result['roto_scores'].values())
        num_cats = len(self.ld.roto_stat_ids)
        self.assertAlmostEqual(total_roto, expected_total_per_cat * num_cats, places=1)

    def test_positive_stat_ranking(self):
        """For PTS (stat 12), higher value should get higher rank points."""
        result = self.calc.calculate_standings()
        # PTS: team.3=5200, team.1=5000, team.2=4800, team.4=4600
        pts_points = result['category_points']
        self.assertEqual(pts_points['team.3']['12'], 4)  # Best: 4 pts
        self.assertEqual(pts_points['team.1']['12'], 3)
        self.assertEqual(pts_points['team.2']['12'], 2)
        self.assertEqual(pts_points['team.4']['12'], 1)  # Worst: 1 pt

    def test_negative_stat_ranking(self):
        """For TO (stat 19), lower value should get higher rank points."""
        result = self.calc.calculate_standings()
        # TO: team.2=500 (best), team.4=550, team.1=600, team.3=700 (worst)
        to_points = result['category_points']
        self.assertEqual(to_points['team.2']['19'], 4)  # Lowest TO = best
        self.assertEqual(to_points['team.4']['19'], 3)
        self.assertEqual(to_points['team.1']['19'], 2)
        self.assertEqual(to_points['team.3']['19'], 1)  # Highest TO = worst

    def test_tied_values_average_rank_points(self):
        """Teams tied in a stat should share averaged rank points."""
        # Create a tie scenario
        self.ld.team_stats['team.1']['12'] = 5000
        self.ld.team_stats['team.2']['12'] = 5000  # Tie with team.1

        result = self.calc.calculate_standings()
        pts_a = result['category_points']['team.1']['12']
        pts_b = result['category_points']['team.2']['12']

        # Both should get the same averaged points
        self.assertEqual(pts_a, pts_b)
        # They share positions 2 and 3 (team.3=5200 is #1), so average = 2.5
        self.assertAlmostEqual(pts_a, 2.5, places=1)

    def test_standings_table_sorted_by_roto_score(self):
        """Standings table should be sorted by total Roto score descending."""
        table = self.calc.get_roto_standings_table()
        scores = [entry['roto_score'] for entry in table]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_standings_gaps_structure(self):
        """get_standings_gaps should return correct structure for each stat."""
        gaps = self.calc.get_standings_gaps('team.1')
        self.assertEqual(set(gaps.keys()), set(self.ld.roto_stat_ids))

        for stat_id, gap in gaps.items():
            self.assertIn('current_rank', gap)
            self.assertIn('current_value', gap)
            self.assertIn('to_gain_rank', gap)
            self.assertIn('to_lose_rank', gap)
            self.assertIn('rank_points', gap)

    def test_best_team_has_no_gain_opportunity(self):
        """The #1 ranked team in a category should have to_gain_rank=None."""
        gaps = self.calc.get_standings_gaps('team.3')
        # team.3 has 5200 PTS (rank 1)
        self.assertIsNone(gaps['12']['to_gain_rank'])
        self.assertEqual(gaps['12']['current_rank'], 1)

    def test_worst_team_has_no_safety_margin(self):
        """The last-ranked team in a category should have to_lose_rank=None."""
        gaps = self.calc.get_standings_gaps('team.4')
        # team.4 has 4600 PTS (rank 4, worst)
        self.assertIsNone(gaps['12']['to_lose_rank'])

    def test_safety_margins_sorted_by_opportunity(self):
        """Safety margins should be sorted by opportunity (easiest gains first)."""
        margins = self.calc.get_safety_margins('team.1')
        opportunities = [
            m['opportunity'] for m in margins
            if m['opportunity'] is not None
        ]
        self.assertEqual(opportunities, sorted(opportunities))

    def test_custom_team_stats_override(self):
        """calculate_standings should accept custom team_stats."""
        custom_stats = {
            'team.1': {'12': 9999, '15': 9999, '16': 9999, '17': 9999, '18': 9999, '19': 1},
            'team.2': {'12': 1, '15': 1, '16': 1, '17': 1, '18': 1, '19': 9999},
        }
        result = self.calc.calculate_standings(custom_stats)
        # team.1 should dominate
        self.assertGreater(
            result['roto_scores']['team.1'],
            result['roto_scores']['team.2']
        )


class TestTradeSimulator(unittest.TestCase):
    """Test the TradeSimulator class."""

    def setUp(self):
        self.ld = MockLeagueData()
        from trade_simulator import TradeSimulator
        self.sim = TradeSimulator(self.ld, remaining_games=30)

    def test_project_player_ros(self):
        """ROS projection should multiply averages by remaining games."""
        proj = self.sim.project_player_ros('p1')
        # p1 averages 25.0 PTS, so ROS = 25.0 * 30 = 750
        self.assertAlmostEqual(proj['12'], 750.0)
        self.assertAlmostEqual(proj['15'], 300.0)  # 10.0 * 30

    def test_simulate_trade_returns_correct_keys(self):
        """Trade simulation result should contain all expected keys."""
        result = self.sim.simulate_trade(
            ['p1'], ['p3'], 'team.1', 'team.2'
        )
        expected_keys = {
            'my_old_score', 'my_new_score', 'my_delta',
            'their_old_score', 'their_new_score', 'their_delta',
            'my_players_traded', 'their_players_traded',
        }
        self.assertTrue(expected_keys.issubset(set(result.keys())))

    def test_simulate_trade_player_names(self):
        """Trade simulation should return correct player names."""
        result = self.sim.simulate_trade(
            ['p1'], ['p3'], 'team.1', 'team.2'
        )
        self.assertEqual(result['my_players_traded'], ['Player One'])
        self.assertEqual(result['their_players_traded'], ['Player Three'])

    def test_simulate_trade_identity(self):
        """Trading a player for themselves should not change scores."""
        result = self.sim.simulate_trade(
            ['p1'], ['p1'], 'team.1', 'team.2'
        )
        # Net change on my team should be 0 (giving away and receiving same stats)
        self.assertAlmostEqual(result['my_delta'], 0.0, places=1)

    def test_find_best_trades_filters_negative(self):
        """find_best_trades should only return trades that increase my Roto score."""
        trades = self.sim.find_best_trades('team.1', max_results=10)
        for trade in trades:
            self.assertGreater(trade['my_delta'], 0)

    def test_find_best_trades_sorted(self):
        """Results should be sorted by (mutually_beneficial, my_delta) desc."""
        trades = self.sim.find_best_trades('team.1', max_results=20)
        if len(trades) > 1:
            for i in range(len(trades) - 1):
                a = trades[i]
                b = trades[i + 1]
                # Mutually beneficial trades come first
                if a['mutually_beneficial'] == b['mutually_beneficial']:
                    self.assertGreaterEqual(a['my_delta'], b['my_delta'])
                else:
                    # a must be mutually beneficial if b is not
                    self.assertTrue(a['mutually_beneficial'])

    def test_find_best_trades_max_results(self):
        """Should not return more results than max_results."""
        trades = self.sim.find_best_trades('team.1', max_results=2)
        self.assertLessEqual(len(trades), 2)


class TestShowRostersHelpers(unittest.TestCase):
    """Test helper functions from show_rosters.py."""

    @classmethod
    def setUpClass(cls):
        """Mock yahoo_oauth and yahoo_fantasy_api so show_rosters can be imported."""
        import types
        cls._mock_modules = {}
        for mod_name in ['yahoo_oauth', 'yahoo_fantasy_api', 'yahoo_fantasy_api.league',
                         'yahoo_fantasy_api.game', 'yahoo_fantasy_api.team', 'dotenv',
                         'objectpath']:
            if mod_name not in sys.modules:
                cls._mock_modules[mod_name] = sys.modules.get(mod_name)
                sys.modules[mod_name] = types.ModuleType(mod_name)

        # Add required attributes
        sys.modules['yahoo_oauth'].OAuth2 = MagicMock
        sys.modules['dotenv'].load_dotenv = lambda: None
        sys.modules['objectpath'].Tree = MagicMock

    @classmethod
    def tearDownClass(cls):
        for mod_name, original in cls._mock_modules.items():
            if original is None:
                sys.modules.pop(mod_name, None)
            else:
                sys.modules[mod_name] = original

    def test_build_stat_id_map(self):
        from show_rosters import build_stat_id_map
        categories = [
            {'stat_id': '12', 'display_name': 'PTS'},
            {'stat_id': '15', 'display_name': 'REB'},
        ]
        result = build_stat_id_map(categories)
        self.assertEqual(result['12'], 'PTS')
        self.assertEqual(result['15'], 'REB')

    def test_format_stat_value_percentage(self):
        from show_rosters import format_stat_value
        self.assertEqual(format_stat_value('5', 0.456), '0.456')
        self.assertEqual(format_stat_value('8', 0.8), '0.800')

    def test_format_stat_value_integer(self):
        from show_rosters import format_stat_value
        self.assertEqual(format_stat_value('12', 100.0), '100')

    def test_format_stat_value_decimal(self):
        from show_rosters import format_stat_value
        self.assertEqual(format_stat_value('12', 10.5), '10.5')


class TestLeagueDataExtractStats(unittest.TestCase):
    """Test LeagueData._extract_stats and _compute_team_stats."""

    @classmethod
    def setUpClass(cls):
        """Mock external modules so league_data can be imported."""
        import types
        cls._mock_modules = {}
        for mod_name in ['yahoo_oauth', 'yahoo_fantasy_api', 'yahoo_fantasy_api.league',
                         'yahoo_fantasy_api.game', 'yahoo_fantasy_api.team', 'dotenv',
                         'objectpath']:
            if mod_name not in sys.modules:
                cls._mock_modules[mod_name] = sys.modules.get(mod_name)
                sys.modules[mod_name] = types.ModuleType(mod_name)

        sys.modules['yahoo_oauth'].OAuth2 = MagicMock
        sys.modules['dotenv'].load_dotenv = lambda: None
        sys.modules['objectpath'].Tree = MagicMock

    @classmethod
    def tearDownClass(cls):
        for mod_name, original in cls._mock_modules.items():
            if original is None:
                sys.modules.pop(mod_name, None)
            else:
                sys.modules[mod_name] = original

    def _make_ld(self):
        """Create a LeagueData-like object with reverse_stat_map set."""
        from league_data import LeagueData
        ld = LeagueData.__new__(LeagueData)
        ld.reverse_stat_map = {'PTS': '12', 'REB': '15', 'ST': '17', 'GP': '0'}
        ld.stat_id_map = {'12': 'PTS', '15': 'REB', '17': 'ST', '0': 'GP'}
        ld.roto_stat_ids = ['5', '12', '15', '17']
        ld.negative_stats = set()
        ld.teams = {'team.1': 'Team A'}
        ld.rosters = {'team.1': [{'player_id': 101}, {'player_id': 102}]}
        ld.player_stats = {
            101: {'0': 50.0, '3': 200.0, '4': 400.0, '5': 0.500,
                  '12': 500.0, '15': 300.0, '17': 50.0},
            102: {'0': 40.0, '3': 100.0, '4': 250.0, '5': 0.400,
                  '12': 300.0, '15': 200.0, '17': 30.0},
        }
        ld.player_info = {
            101: {'name': 'Player A', 'position': 'PG', 'team': 'LAL',
                  'team_key': 'team.1'},
            102: {'name': 'Player B', 'position': 'SG', 'team': 'BOS',
                  'team_key': 'team.1'},
        }
        return ld

    def test_flat_format_extraction(self):
        ld = self._make_ld()
        player_data = {
            'player_id': 123,
            'name': 'Test Player',
            'PTS': 25.0,
            'REB': 10.0,
            'ST': 2.0,
            'GP': 50.0,
        }
        stats = ld._extract_stats(player_data)
        self.assertAlmostEqual(stats['12'], 25.0)
        self.assertAlmostEqual(stats['15'], 10.0)
        self.assertAlmostEqual(stats['17'], 2.0)
        self.assertAlmostEqual(stats['0'], 50.0)

    def test_nested_format_still_works(self):
        ld = self._make_ld()
        player_data = {
            'player_stats': {
                'stats': [
                    {'stat_id': '12', 'value': '30.0'},
                ]
            }
        }
        stats = ld._extract_stats(player_data)
        self.assertAlmostEqual(stats['12'], 30.0)

    def test_compute_team_stats_sums_players(self):
        """team_stats should be sum of player season totals."""
        ld = self._make_ld()
        ld._compute_team_stats()
        ts = ld.team_stats['team.1']
        # PTS: 500 + 300 = 800
        self.assertAlmostEqual(ts['12'], 800.0)
        # REB: 300 + 200 = 500
        self.assertAlmostEqual(ts['15'], 500.0)
        # ST: 50 + 30 = 80
        self.assertAlmostEqual(ts['17'], 80.0)

    def test_compute_team_stats_recalculates_fg_pct(self):
        """FG% should be recalculated from FGM/FGA, not averaged."""
        ld = self._make_ld()
        ld._compute_team_stats()
        ts = ld.team_stats['team.1']
        # FGM: 200 + 100 = 300, FGA: 400 + 250 = 650
        # FG% = 300 / 650 ≈ 0.4615
        expected_fg = 300.0 / 650.0
        self.assertAlmostEqual(ts['5'], expected_fg, places=4)

    def test_compute_team_stats_sums_gp(self):
        """GP should be summed across all players."""
        ld = self._make_ld()
        ld._compute_team_stats()
        ts = ld.team_stats['team.1']
        # GP: 50 + 40 = 90
        self.assertAlmostEqual(ts['0'], 90.0)


if __name__ == '__main__':
    unittest.main()
