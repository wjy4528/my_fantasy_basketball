"""
Yahoo Fantasy Sports API Authentication
"""
import os
from yahoo_oauth import OAuth2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_oauth():
    """
    Initialize and return OAuth2 object for Yahoo Fantasy API.
    
    This will open a browser window for the first time to authenticate.
    After that, it will store the token in oauth2.json for reuse.
    
    Returns:
        OAuth2: Authenticated OAuth2 object
    """
    return OAuth2(None, None, from_file='oauth2.json')


def setup_credentials():
    """
    Check if credentials are properly configured.
    Returns True if setup, False otherwise.
    """
    client_id = os.getenv('YAHOO_CLIENT_ID')
    client_secret = os.getenv('YAHOO_CLIENT_SECRET')
    
    if not client_id or not client_secret or 'your_client_id' in client_id:
        return False
    return True
