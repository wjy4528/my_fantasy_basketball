# Quick Setup Guide

## What You Need to Provide

To use this Fantasy Basketball Analysis Tool, you need the following from Yahoo:

### 1. Yahoo Developer App Credentials

You must create a Yahoo Developer Application to get API access:

**Step-by-step:**
1. Visit: https://developer.yahoo.com/apps/
2. Sign in with your Yahoo account
3. Click "Create an App"
4. Fill in:
   - **Application Name**: `My Fantasy Basketball Tool` (or any name)
   - **Application Type**: `Web Application`
   - **Redirect URI(s)**: `https://localhost:8080`
   - **API Permissions**: Check "Fantasy Sports" with "Read" access
5. Click "Create App"
6. You will get:
   - **Client ID** (also called Consumer Key)
   - **Client Secret** (also called Consumer Secret)

### 2. Required Files

After getting your credentials, create these files:

#### `.env` file (copy from .env.example):
```bash
cp .env.example .env
```

Then edit `.env`:
```
YAHOO_CLIENT_ID=your_actual_client_id_from_step_1
YAHOO_CLIENT_SECRET=your_actual_client_secret_from_step_1
LEAGUE_ID=21454
```

#### `oauth2.json` file:
Create this file in the project root:
```json
{
  "consumer_key": "your_actual_client_id_from_step_1",
  "consumer_secret": "your_actual_client_secret_from_step_1"
}
```

**Important**: Use the SAME Client ID and Client Secret in both files!

### 3. First-Time Authentication

When you run any command for the first time:

```bash
python show_teams.py
```

You will see:
1. A browser window opens automatically
2. You're asked to log in to Yahoo (if not already logged in)
3. You're asked to authorize the application
4. You'll be redirected to a page with a code/URL
5. Copy the verification code
6. Paste it back into your terminal

After this one-time setup, the token is saved and you won't need to authenticate again (unless the token expires).

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Create your configuration files (see above)
# Then run any command:
python show_teams.py
```

## Available Commands

1. **View all teams**: `python show_teams.py`
2. **View team statistics**: `python show_team_stats.py`
3. **Get trade suggestions**: `python suggest_trades.py`

## Troubleshooting

### "No module named 'yahoo_oauth'"
Run: `pip install -r requirements.txt`

### "Error: League ID must be provided"
Make sure your `.env` file has `LEAGUE_ID=21454`

### Authentication keeps failing
1. Delete `oauth2.json`
2. Check that your Client ID and Secret are correct
3. Make sure they match in both `.env` and `oauth2.json`
4. Try again

### "League not found" or "Access denied"
- Verify you're a member of league 21454
- Make sure the league is active for the current season
- Check that you logged in with the correct Yahoo account

## Security Reminder

- Never share your `.env` or `oauth2.json` files
- Never commit these files to Git (they're in .gitignore)
- Keep your Client ID and Client Secret private
