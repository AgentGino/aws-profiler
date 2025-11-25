"""Credential age and expiration tracking."""

import configparser
from pathlib import Path
from datetime import datetime, timezone


def get_credential_age(profile_name):
    """Get the age of credentials based on file modification time."""
    credentials_path = Path.home() / '.aws' / 'credentials'
    
    if not credentials_path.exists():
        return 'N/A'
    
    try:
        config = configparser.ConfigParser()
        config.read(credentials_path)
        
        if profile_name not in config.sections():
            return 'N/A'
        
        # Get file modification time
        mtime = credentials_path.stat().st_mtime
        mod_time = datetime.fromtimestamp(mtime, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        age = now - mod_time
        
        days = age.days
        hours = age.seconds // 3600
        
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h"
        else:
            minutes = age.seconds // 60
            return f"{minutes}m"
    
    except Exception:
        return 'N/A'


def get_credential_expiration(session):
    """Get credential expiration information."""
    try:
        # For temporary credentials (roles), check session token expiration
        credentials = session.get_credentials()
        
        if credentials.token:  # This is a session token (temporary credentials)
            # Try to get session token expiration from STS
            sts_client = session.client('sts')
            
            # Get session token info
            try:
                # For assumed roles, we can check the expiration
                # Note: This is a best-effort approach
                response = sts_client.get_session_token()
                expiration = response['Credentials']['Expiration']
                
                now = datetime.now(timezone.utc)
                time_left = expiration - now
                
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                
                if hours > 0:
                    expires_in = f"{hours}h {minutes}m"
                else:
                    expires_in = f"{minutes}m"
                
                return {
                    'expires_in': expires_in,
                    'expiration_date': expiration.strftime('%Y-%m-%d %H:%M:%S UTC')
                }
            except Exception:
                # If we can't get exact expiration, return approximate
                return {
                    'expires_in': 'Temporary',
                    'expiration_date': 'N/A'
                }
        else:
            # Permanent credentials (IAM users)
            return {
                'expires_in': 'Permanent',
                'expiration_date': 'Never'
            }
    
    except Exception:
        return {
            'expires_in': 'N/A',
            'expiration_date': 'N/A'
        }
