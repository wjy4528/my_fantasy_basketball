"""
Yahoo Fantasy Basketball API Client
"""
import os
import objectpath
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import league, game, team
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class FantasyBasketballClient:
    """Client for interacting with Yahoo Fantasy Basketball API"""
    
    def __init__(self, league_id=None):
        """
        Initialize the client.
        
        Args:
            league_id: Yahoo Fantasy Basketball league ID (e.g., '21454')
        """
        self.oauth = OAuth2(None, None, from_file='oauth2.json')
        self.gm = game.Game(self.oauth, 'nba')
        self.league_id = league_id or os.getenv('LEAGUE_ID')
        
        if not self.league_id:
            raise ValueError("League ID must be provided or set in .env file")
        
        # Get the current season league key
        self.league_key = self._get_league_key()
        self.lg = league.League(self.oauth, self.league_key)
    
    def _get_league_key(self):
        """
        Get the full league key for the current season.
        Yahoo uses format like 'nba.l.21454' but we need to get the correct game_id.
        """
        # Get current season game key
        game_keys = self.gm.league_ids()
        
        # Find our league in the current season
        for game_key in game_keys:
            if self.league_id in game_key:
                return game_key
        
        # If not found, try constructing it with current season
        # Format: {game_id}.l.{league_id}
        # For NBA, game_id changes each season (e.g., 428 for 2024-25)
        current_season = self.gm.to_league(self.league_id)
        return current_season
    
    def get_teams(self):
        """
        Get all teams in the league.
        
        Returns:
            dict: Dictionary mapping team keys to team names
        """
        return self.lg.teams()
    
    def get_standings(self):
        """
        Get current league standings.
        
        Returns:
            list: List of teams with their standings
        """
        return self.lg.standings()
    
    def get_team_stats(self, team_key):
        """
        Get stats for a specific team.
        
        Args:
            team_key: Yahoo team key
            
        Returns:
            dict: Team statistics
        """
        tm = team.Team(self.oauth, team_key)
        return tm.stats()
    
    def get_team_roster(self, team_key):
        """
        Get roster for a specific team.
        
        Args:
            team_key: Yahoo team key
            
        Returns:
            list: List of players on the team
        """
        tm = team.Team(self.oauth, team_key)
        return tm.roster()
    
    def get_league_settings(self):
        """
        Get league settings including scoring categories.
        
        Returns:
            dict: League settings
        """
        return self.lg.settings()

    def get_stat_categories_raw(self):
        """
        Get raw stat categories with stat_ids from the Yahoo API.

        The library's ``settings()`` method filters out stat_categories,
        so this method fetches them directly from the raw settings JSON.

        Returns:
            list: List of stat category dicts, each containing at least
                  ``stat_id`` and ``display_name``.
        """
        raw = self.lg.yhandler.get_settings_raw(self.lg.league_id)
        t = objectpath.Tree(raw)
        categories = []
        for s in t.execute('$..stat_categories..stat'):
            if isinstance(s, dict) and 'stat_id' in s:
                categories.append(s)
        return categories
    
    def get_player_stats(self, player_key, req_type='season'):
        """
        Get stats for a specific player.

        Args:
            player_key: Yahoo player key
            req_type: Type of stats request ('season' for season totals)

        Returns:
            dict: Player statistics
        """
        return self.lg.player_stats([player_key], req_type)

    def get_players_stats(self, player_keys, req_type='season'):
        """
        Get stats for multiple players.

        Args:
            player_keys: List of Yahoo player keys
            req_type: Type of stats request ('season' for season totals)

        Returns:
            list: List of player statistics
        """
        if not player_keys:
            return []
        return self.lg.player_stats(player_keys, req_type)

    def get_players_stats_all(self, player_keys, req_type='season'):
        """
        Get stats for multiple players, returning ALL stat IDs.

        Unlike ``get_players_stats()`` which only returns stats present in
        the library's ``stats_id_map`` (scoring categories), this method
        parses the raw API response to include every stat: GP, FGM, FGA,
        FTM, FTA, and all other stat IDs.

        Stats are keyed by stat_id strings (e.g. ``'0'`` for GP,
        ``'12'`` for PTS).

        Args:
            player_keys: List of Yahoo player keys/IDs
            req_type: Type of stats request ('season' for season totals)

        Returns:
            list: List of dicts, each with ``player_id``, ``name``, and
                  stat values keyed by stat_id strings.
        """
        if not player_keys:
            return []
        results = []
        for batch_start in range(0, len(player_keys), 25):
            batch = player_keys[batch_start:batch_start + 25]
            raw = self.lg.yhandler.get_player_stats_raw(
                self.lg.league_id, batch, req_type, None, None, None)
            t = objectpath.Tree(raw)
            row = None
            for e in t.execute('$..(full,player_id,position_type,stat)'):
                if 'player_id' in e:
                    if row is not None:
                        results.append(row)
                    row = {'player_id': int(e['player_id'])}
                elif 'full' in e:
                    if row is not None:
                        row['name'] = e['full']
                elif 'position_type' in e:
                    if row is not None:
                        row['position_type'] = e['position_type']
                elif 'stat' in e:
                    if row is not None:
                        stat_id = str(e['stat']['stat_id'])
                        try:
                            val = float(e['stat']['value'])
                        except (ValueError, TypeError):
                            val = e['stat']['value']
                        row[stat_id] = val
            if row is not None:
                results.append(row)
        return results

    def get_all_players(self):
        """
        Get all available players in the league.
        
        Returns:
            list: List of players
        """
        return self.lg.free_agents('PG')  # Returns available players
