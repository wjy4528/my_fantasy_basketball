"""
LeagueData - Data Ingestion Class for Fantasy Basketball Roto Analysis.

Fetches and stores league settings, standings, rosters, and player stats
from the Yahoo Fantasy Sports API.
"""
from client import FantasyBasketballClient


# Default Roto stat categories (Yahoo stat_id -> name)
DEFAULT_ROTO_STATS = {
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

# Component stats needed for percentage recalculations
COMPONENT_STATS = {
    'FG%': {'made': '3', 'attempted': '4'},   # FGM / FGA
    'FT%': {'made': '6', 'attempted': '7'},   # FTM / FTA
}


class LeagueData:
    """
    Fetches and stores all league data required for Roto analysis.

    Attributes:
        client: FantasyBasketballClient instance
        stat_id_map: Mapping of stat_id to display name
        reverse_stat_map: Mapping of display_name to stat_id (for flat API responses)
        roto_stat_ids: List of stat IDs used in Roto scoring
        teams: Dict of team_key -> team_name
        standings_raw: Raw standings data from API
        team_stats: Dict of team_key -> {stat_id: value}
        rosters: Dict of team_key -> list of player dicts
        player_stats: Dict of player_key -> {stat_id: value}
        player_info: Dict of player_key -> {name, position, team, team_key}
    """

    def __init__(self, league_id=None):
        """
        Initialize LeagueData and connect to the Yahoo Fantasy API.

        Args:
            league_id: Yahoo Fantasy Basketball league ID
        """
        self.client = FantasyBasketballClient(league_id)
        self.stat_id_map = {}
        self.reverse_stat_map = {}
        self.roto_stat_ids = []
        self.negative_stats = set()  # Stats where lower is better (e.g., TO)
        self.teams = {}
        self.standings_raw = []
        self.team_stats = {}
        self.rosters = {}
        self.player_stats = {}
        self.player_info = {}

    @staticmethod
    def _get_player_key(player):
        """Get the player key from a player dict, falling back to player_id."""
        pkey = player.get('player_key', '')
        if not pkey:
            pkey = player.get('player_id', '')
        return pkey

    def fetch_all(self):
        """Fetch all data from the API in sequence."""
        self.fetch_settings()
        self.fetch_standings()
        self.fetch_rosters()
        self.fetch_player_stats()

    def fetch_settings(self):
        """
        Fetch league settings and build the stat_id to name mapping.

        Uses get_stat_categories_raw() to get the actual stat_id -> display_name
        mapping from the raw API (since settings() filters out stat_categories).

        Identifies which stats are used for Roto scoring and which
        stats are 'negative' (lower is better, like Turnovers).
        """
        raw_categories = self.client.get_stat_categories_raw()

        self.stat_id_map = {}
        self.roto_stat_ids = []

        for cat in raw_categories:
            stat_id = str(cat.get('stat_id', ''))
            display_name = cat.get('display_name', f'Stat {stat_id}')
            self.stat_id_map[stat_id] = display_name

            # Check if this is a counted stat for Roto
            is_only_display = cat.get('is_only_display_stat', '0')
            if str(is_only_display) != '1' and stat_id:
                self.roto_stat_ids.append(stat_id)

            # Check sort order to identify negative stats (lower is better)
            sort_order = cat.get('sort_order', '1')
            if str(sort_order) == '0':
                self.negative_stats.add(stat_id)

        # If no Roto stats found from settings, use defaults
        if not self.roto_stat_ids:
            self.roto_stat_ids = list(DEFAULT_ROTO_STATS.keys())
            self.stat_id_map.update(DEFAULT_ROTO_STATS)
            self.negative_stats.add('19')  # TO

        # Build reverse mapping: display_name -> stat_id for flat API responses
        self.reverse_stat_map = {}
        for sid, dname in self.stat_id_map.items():
            self.reverse_stat_map[dname] = sid
        # Add defaults for any missing entries
        for sid, dname in DEFAULT_ROTO_STATS.items():
            if dname not in self.reverse_stat_map:
                self.reverse_stat_map[dname] = sid

    def fetch_standings(self):
        """
        Fetch current standings and extract raw stat totals for all teams.

        Populates self.teams and self.team_stats with current season totals.
        """
        self.standings_raw = self.client.get_standings()
        self.teams = {}
        self.team_stats = {}

        for team in self.standings_raw:
            team_key = team.get('team_key', '')
            team_name = team.get('name', 'Unknown')
            self.teams[team_key] = team_name

            # Extract stats
            stats = {}
            stat_list = team.get('team_stats', {}).get('stats', [])
            for stat in stat_list:
                stat_id = str(stat.get('stat_id', ''))
                value = stat.get('value', '-')
                if value != '-' and value is not None:
                    try:
                        stats[stat_id] = float(value)
                    except (ValueError, TypeError):
                        pass
            self.team_stats[team_key] = stats

    def fetch_rosters(self):
        """
        Fetch rosters for all teams in the league.

        Populates self.rosters with player lists and self.player_info
        with basic player metadata.
        """
        self.rosters = {}
        self.player_info = {}

        for team_key in self.teams:
            try:
                roster = self.client.get_team_roster(team_key)
                self.rosters[team_key] = roster

                for player in roster:
                    pkey = self._get_player_key(player)
                    if not pkey:
                        continue
                    pname = player.get('name', 'Unknown')
                    if isinstance(pname, dict):
                        pname = pname.get('full', 'Unknown')
                    position = player.get('selected_position', {})
                    if isinstance(position, dict):
                        position = position.get('position', 'N/A')
                    editorial_team = player.get('editorial_team_abbr', '')

                    self.player_info[pkey] = {
                        'name': pname,
                        'position': str(position),
                        'team': editorial_team,
                        'team_key': team_key,
                    }
            except Exception as e:
                print(f"  Warning: Could not fetch roster for {self.teams.get(team_key, team_key)}: {e}")
                self.rosters[team_key] = []

    def fetch_player_stats(self):
        """
        Fetch season average stats for all rostered players.

        Uses batch requests per team to minimize API calls.
        Populates self.player_stats with {player_key: {stat_id: value}}.
        """
        self.player_stats = {}

        for team_key, roster in self.rosters.items():
            player_keys = self.get_team_player_keys(team_key)
            if not player_keys:
                continue

            try:
                stats_response = self.client.get_players_stats(player_keys, 'season')
                if isinstance(stats_response, list):
                    for ps in stats_response:
                        pkey = self._get_player_key(ps)
                        pstats = self._extract_stats(ps)
                        if pkey:
                            self.player_stats[pkey] = pstats
                elif isinstance(stats_response, dict):
                    for pkey, ps in stats_response.items():
                        pstats = self._extract_stats(ps)
                        self.player_stats[pkey] = pstats
            except Exception as e:
                team_name = self.teams.get(team_key, team_key)
                print(f"  Warning: Could not fetch player stats for {team_name}: {e}")

    def _extract_stats(self, player_data):
        """
        Extract stat values from a player stats API response.

        Handles two formats:
        1. Nested: player_stats -> stats -> [{stat_id, value}]
        2. Flat: stats as top-level keys by display name (yahoo_fantasy_api)

        Args:
            player_data: Player data dict from the API

        Returns:
            dict: {stat_id: float_value}
        """
        stats = {}
        player_stats = player_data.get('player_stats', {})
        if isinstance(player_stats, dict):
            stat_list = player_stats.get('stats', [])
        elif isinstance(player_stats, list):
            stat_list = player_stats
        else:
            stat_list = []

        if not stat_list:
            stat_list = player_data.get('stats', [])

        for stat in stat_list:
            if isinstance(stat, dict):
                stat_id = str(stat.get('stat_id', ''))
                value = stat.get('value', '-')
                if value != '-' and value is not None:
                    try:
                        stats[stat_id] = float(value)
                    except (ValueError, TypeError):
                        pass

        # Handle flat format from yahoo_fantasy_api library
        if not stats and self.reverse_stat_map:
            for key, value in player_data.items():
                if key in self.reverse_stat_map and isinstance(value, (int, float)):
                    stats[self.reverse_stat_map[key]] = value

        return stats

    def get_team_player_keys(self, team_key):
        """Get all player keys for a given team."""
        roster = self.rosters.get(team_key, [])
        keys = []
        for p in roster:
            pkey = self._get_player_key(p)
            if pkey:
                keys.append(pkey)
        return keys

    def get_stat_name(self, stat_id):
        """Get display name for a stat_id."""
        return self.stat_id_map.get(str(stat_id),
                                    DEFAULT_ROTO_STATS.get(str(stat_id),
                                                           f'Stat {stat_id}'))

    def is_negative_stat(self, stat_id):
        """Check if a stat is negative (lower is better, e.g., turnovers)."""
        return str(stat_id) in self.negative_stats
