# My Fantasy Basketball Analysis Tool

A Python-based analysis tool for Yahoo Fantasy Basketball that helps you make data-driven trade decisions.

## Features

- Fetch league data from Yahoo Fantasy Sports API
- View all teams in your league
- Analyze team statistics and standings
- Get trade suggestions based on team strengths and weaknesses
- No UI required - simple command-line tools

## Prerequisites

- Python 3.7 or higher
- A Yahoo Fantasy Basketball league (League ID: 21454 or your own)
- Yahoo Developer Application credentials

## Setup Instructions

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Create Yahoo Developer Application

1. Go to https://developer.yahoo.com/apps/
2. Click "Create an App"
3. Fill in the application details:
   - **Application Name**: My Fantasy Basketball Tool
   - **Application Type**: Web Application
   - **Redirect URI**: `https://localhost:8080` (or any URL you control)
   - **API Permissions**: Select "Fantasy Sports" and check "Read"
4. After creating the app, you'll receive:
   - **Client ID** (Consumer Key)
   - **Client Secret** (Consumer Secret)

### Step 3: Configure Credentials

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```
   YAHOO_CLIENT_ID=your_actual_client_id_here
   YAHOO_CLIENT_SECRET=your_actual_client_secret_here
   LEAGUE_ID=21454
   ```

3. Create an `oauth2.json` file in the project root with the following structure:
   ```json
   {
     "consumer_key": "your_actual_client_id_here",
     "consumer_secret": "your_actual_client_secret_here"
   }
   ```

### Step 4: Authenticate

The first time you run any command, you'll be prompted to authenticate:
1. A browser window will open
2. Log in to your Yahoo account
3. Authorize the application
4. You'll be redirected to a URL - copy the verification code
5. Paste the code back into the terminal

After initial authentication, your token will be saved in `oauth2.json` for future use.

## Usage

### View All Teams

Display all teams in your league:

```bash
python show_teams.py
```

**Output example:**
```
League ID: 21454

Teams in your league:
------------------------------------------------------------
  Team Warriors (Key: 428.l.21454.t.1)
  The Dunkers (Key: 428.l.21454.t.2)
  Hoop Dreams (Key: 428.l.21454.t.3)
  ...

Total teams: 12
```

### View Team Statistics

Show detailed statistics and standings for all teams:

```bash
python show_team_stats.py
```

**Output includes:**
- Team names and managers
- Win-loss records
- League rankings
- Statistical performance
- Scoring categories

### Get Trade Suggestions

Analyze team strengths/weaknesses and get trade recommendations:

```bash
python suggest_trades.py
```

**Output includes:**
- Team analysis (strengths and weaknesses by category)
- Trade partner suggestions based on complementary needs
- Synergy scores for each potential trade
- Statistical categories each team would improve

**Example output:**
```
TRADE SUGGESTIONS
================================================================================

Based on complementary team needs, here are potential trade partners:

1. Team Warriors <--> The Dunkers
   Synergy Score: 6/10
   Team Warriors would improve in:
     - Three Pointers Made (3PTM)
     - Free Throw Percentage (FT%)
   The Dunkers would improve in:
     - Rebounds (REB)
     - Blocks (BLK)
```

## How Trade Suggestions Work

The trade suggestion algorithm:

1. **Analyzes Performance**: Ranks each team in every statistical category
2. **Identifies Strengths**: Categories where team ranks in top 25%
3. **Identifies Weaknesses**: Categories where team ranks in bottom 25%
4. **Finds Complementary Teams**: Matches teams where one's strength is another's weakness
5. **Calculates Synergy**: Scores trades based on mutual benefit potential

## Troubleshooting

### Authentication Issues

If you get authentication errors:
1. Delete `oauth2.json`
2. Re-run any command to re-authenticate
3. Make sure your Client ID and Secret are correct in both `.env` and `oauth2.json`

### League Not Found

If your league isn't found:
1. Verify your League ID is correct
2. Make sure you're a member of the league
3. Check that the league is for the current season

### API Rate Limits

Yahoo has API rate limits. If you hit them:
- Wait a few minutes before trying again
- Don't run commands too frequently

## Security Notes

- **Never commit** `.env` or `oauth2.json` files to version control
- Keep your Client ID and Client Secret private
- The `.gitignore` file is configured to exclude sensitive files

## API Documentation

For more information about the Yahoo Fantasy Sports API:
- Official Guide: https://developer.yahoo.com/fantasysports/guide/
- Python Library: https://github.com/spilchen/yahoo_fantasy_api

## License

This is a personal analysis tool. Use responsibly and in accordance with Yahoo's Terms of Service.