"""Core functionality for AWS profile checking."""

import boto3
import configparser
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound


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


def get_account_info(profile_name):
    """Get AWS account information and credential status for a profile."""
    try:
        session = boto3.Session(profile_name=profile_name)
        sts_client = session.client('sts')
        
        # Get caller identity
        identity = sts_client.get_caller_identity()
        
        account_id = identity.get('Account', 'N/A')
        user_arn = identity.get('Arn', 'N/A')
        user_id = identity.get('UserId', 'N/A')
        
        # Extract user/role name from ARN
        if 'assumed-role' in user_arn:
            user_name = user_arn.split('/')[-1]
            credential_type = 'Role'
        elif 'user' in user_arn:
            user_name = user_arn.split('/')[-1]
            credential_type = 'User'
        else:
            user_name = 'N/A'
            credential_type = 'Unknown'
        
        status = 'Active'
        
        return {
            'profile': profile_name,
            'account_id': account_id,
            'user_name': user_name,
            'credential_type': credential_type,
            'arn': user_arn,
            'status': status
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ['ExpiredToken', 'InvalidClientTokenId']:
            return {
                'profile': profile_name,
                'account_id': 'N/A',
                'user_name': 'N/A',
                'credential_type': 'N/A',
                'arn': 'N/A',
                'status': 'Expired'
            }
        else:
            return {
                'profile': profile_name,
                'account_id': 'N/A',
                'user_name': 'N/A',
                'credential_type': 'N/A',
                'arn': 'N/A',
                'status': f'Error: {error_code}'
            }
    
    except (NoCredentialsError, ProfileNotFound) as e:
        return {
            'profile': profile_name,
            'account_id': 'N/A',
            'user_name': 'N/A',
            'credential_type': 'N/A',
            'arn': 'N/A',
            'status': 'No Credentials'
        }
    
    except Exception as e:
        return {
            'profile': profile_name,
            'account_id': 'N/A',
            'user_name': 'N/A',
            'credential_type': 'N/A',
            'arn': 'N/A',
            'status': f'Error: {str(e)[:30]}'
        }
