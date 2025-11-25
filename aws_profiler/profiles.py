"""AWS profile discovery and configuration."""

import configparser
from pathlib import Path


def get_aws_profiles():
    """Get list of all AWS profiles from credentials and config files."""
    profiles = set()
    
    # Check credentials file
    credentials_path = Path.home() / '.aws' / 'credentials'
    if credentials_path.exists():
        config = configparser.ConfigParser()
        config.read(credentials_path)
        profiles.update(config.sections())
    
    # Check config file
    config_path = Path.home() / '.aws' / 'config'
    if config_path.exists():
        config = configparser.ConfigParser()
        config.read(config_path)
        for section in config.sections():
            if section.startswith('profile '):
                profiles.add(section.replace('profile ', ''))
            else:
                profiles.add(section)
    
    return sorted(list(profiles))


def is_sso_profile(profile_name):
    """Check if a profile is configured for SSO."""
    config_path = Path.home() / '.aws' / 'config'
    
    if not config_path.exists():
        return False
    
    try:
        config = configparser.ConfigParser()
        config.read(config_path)
        
        # Check both 'profile name' and 'name' sections
        section_name = f'profile {profile_name}' if f'profile {profile_name}' in config.sections() else profile_name
        
        if section_name in config.sections():
            # Check for SSO configuration keys
            return any(key in config[section_name] for key in ['sso_start_url', 'sso_session'])
    
    except Exception:
        pass
    
    return False


def get_current_access_key_id(profile_name):
    """Get the current access key ID for a profile."""
    credentials_path = Path.home() / '.aws' / 'credentials'
    
    if not credentials_path.exists():
        return None
    
    try:
        config = configparser.ConfigParser()
        config.read(credentials_path)
        
        if profile_name in config.sections():
            return config[profile_name].get('aws_access_key_id')
    except Exception:
        return None
    
    return None
