# Command Reference

Quick reference for all available commands in the Fantasy Basketball Analysis Tool.

## Setup Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# (See SETUP_GUIDE.md for detailed instructions)
```

## Analysis Commands

### 1. Show All Teams (`show_teams.py`)

Displays all teams in your league with their Yahoo team keys.

```bash
python show_teams.py
```

**What it shows:**
- League ID
- List of all team names
- Team keys (used for API calls)
- Total number of teams

**Use case:** Quick sanity check to verify API connection and see all teams.

---

### 2. Show Team Statistics (`show_team_stats.py`)

Displays detailed statistics and standings for all teams.

```bash
python show_team_stats.py
```

**What it shows:**
- Team names and managers
- Win-loss-tie records
- League rankings
- Points totals
- Statistical performance in each category
- League scoring categories

**Use case:** Comprehensive overview of league standings and team performance.

---

### 3. Suggest Trades (`suggest_trades.py`)

Analyzes team strengths/weaknesses and suggests potential trade partners.

```bash
python suggest_trades.py
```

**What it shows:**
- Team Analysis Section:
  - Each team's top statistical strengths (top 25%)
  - Each team's weaknesses (bottom 25%)
- Trade Suggestions Section:
  - Potential trade partners
  - Synergy scores (how mutually beneficial)
  - Categories each team would improve
  - Ranked by potential benefit

**Use case:** Data-driven trade proposal planning.

**Algorithm:**
1. Ranks each team in every statistical category
2. Identifies strengths (top 25%) and weaknesses (bottom 25%)
3. Finds complementary matches (Team A weak where Team B strong, and vice versa)
4. Scores trades by mutual benefit potential

---

### 4. Example API Usage (`example_usage.py`)

Demonstrates how to use the client library programmatically.

```bash
python example_usage.py
```

**What it shows:**
- How to initialize the client
- How to fetch teams
- How to get standings
- How to access league settings
- How to get team rosters

**Use case:** Template for building your own custom analysis scripts.

---

## Understanding the Output

### Team Strengths and Weaknesses

Teams are ranked in each statistical category:
- **Strength**: Team ranks in top 25% of league
- **Weakness**: Team ranks in bottom 25% of league
- **Neutral**: Team ranks in middle 50%

### Trade Synergy Score

The synergy score indicates potential mutual benefit:
- **8-10**: Highly complementary - strong trade opportunity
- **5-7**: Moderately complementary - worth exploring
- **2-4**: Slightly complementary - may need additional factors
- **0-1**: Limited complementarity - probably not worth pursuing

### Statistical Categories

Common categories (varies by league settings):
- **FG%**: Field Goal Percentage
- **FT%**: Free Throw Percentage
- **3PTM**: Three Pointers Made
- **PTS**: Points
- **REB**: Rebounds
- **AST**: Assists
- **STL**: Steals
- **BLK**: Blocks
- **TO**: Turnovers (lower is better)

---

## Tips for Using Trade Suggestions

1. **Start with high synergy scores** (7+) - these have the most mutual benefit
2. **Look for multiple categories** - trades that help in 2+ categories are more valuable
3. **Consider player values** - stats are aggregated, individual player trades matter
4. **Check recent performance** - tool uses season-long stats, recent form may differ
5. **Factor in injuries and schedules** - the tool doesn't account for these
6. **Propose win-win trades** - use the mutual benefit data to make fair offers

---

## Advanced Usage

### Custom League ID

To analyze a different league, update `.env`:
```
LEAGUE_ID=your_league_id_here
```

### Programmatic Access

Use `client.py` to build custom tools:

```python
from client import FantasyBasketballClient

client = FantasyBasketballClient()
teams = client.get_teams()
standings = client.get_standings()
# ... your custom analysis
```

### Filtering Trade Suggestions

Modify `suggest_trades.py` to focus on specific teams or categories based on your needs.

---

## Troubleshooting

**Command not found error:**
```bash
# Make sure scripts are executable
chmod +x show_teams.py show_team_stats.py suggest_trades.py example_usage.py
```

**Import errors:**
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

**Authentication issues:**
See SETUP_GUIDE.md for detailed authentication instructions.
