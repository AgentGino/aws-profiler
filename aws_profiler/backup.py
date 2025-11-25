"""Credential backup functionality."""

import configparser
from pathlib import Path
from datetime import datetime


def backup_credentials(profile_name, access_key_id):
    """
    Backup current credentials to a timestamped backup file.
    
    Args:
        profile_name: Name of the AWS profile
        access_key_id: Access key ID being backed up
        
    Returns:
        dict: Result with success status and backup file path
    """
    credentials_path = Path.home() / '.aws' / 'credentials'
    aws_dir = credentials_path.parent
    backup_dir = aws_dir / 'backups'
    
    # Create backup directory if it doesn't exist
    backup_dir.mkdir(exist_ok=True)
    
    try:
        # Read current credentials
        config = configparser.ConfigParser()
        config.read(credentials_path)
        
        if profile_name not in config.sections():
            return {
                'success': False,
                'message': f'Profile "{profile_name}" not found in credentials file'
            }
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'credentials_backup_{profile_name}_{access_key_id[-8:]}_{timestamp}'
        backup_path = backup_dir / backup_filename
        
        # Create a new config with only the profile being backed up
        backup_config = configparser.ConfigParser()
        backup_config[profile_name] = config[profile_name]
        
        # Write backup
        with open(backup_path, 'w') as f:
            backup_config.write(f)
        
        # Set restrictive permissions (read/write for owner only)
        backup_path.chmod(0o600)
        
        return {
            'success': True,
            'backup_file': str(backup_path)
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to create backup: {str(e)}'
        }
