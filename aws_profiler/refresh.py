"""Credential refresh functionality for IAM users and SSO profiles."""

import boto3
import configparser
import subprocess
from pathlib import Path
from botocore.exceptions import ClientError

from .profiles import is_sso_profile, get_current_access_key_id
from .backup import backup_credentials


def refresh_sso_profile(profile_name):
    """
    Refresh SSO profile by running aws sso login.
    
    Args:
        profile_name: Name of the AWS profile
        
    Returns:
        dict: Result with success status and message
    """
    try:
        print(f"🔐 Initiating SSO login for profile: {profile_name}")
        print("   Please follow the instructions in your browser...\n")
        
        # Run aws sso login with the profile
        result = subprocess.run(
            ['aws', 'sso', 'login', '--profile', profile_name],
            capture_output=False,  # Allow output to show to user
            text=True
        )
        
        if result.returncode == 0:
            return {
                'success': True,
                'message': f'✓ SSO login successful for profile "{profile_name}"'
            }
        else:
            return {
                'success': False,
                'message': f'SSO login failed with exit code {result.returncode}'
            }
    
    except FileNotFoundError:
        return {
            'success': False,
            'message': 'AWS CLI not found. Please install the AWS CLI to use SSO login.'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error during SSO login: {str(e)}'
        }


def refresh_iam_user_credentials(profile_name, delete_old=False):
    """
    Refresh IAM user credentials by creating new access keys.
    
    Args:
        profile_name: Name of the AWS profile
        delete_old: If True, delete the old access key from AWS after creating new one
        
    Returns:
        dict: Result with success status and message
    """
    credentials_path = Path.home() / '.aws' / 'credentials'
    
    if not credentials_path.exists():
        return {
            'success': False,
            'message': 'Credentials file not found'
        }
    
    try:
        # First, verify this is an IAM user and get current credentials
        session = boto3.Session(profile_name=profile_name)
        sts_client = session.client('sts')
        
        # Get caller identity
        identity = sts_client.get_caller_identity()
        user_arn = identity.get('Arn', '')
        
        # Check if this is an IAM user (not a role)
        if 'assumed-role' in user_arn or ':user/' not in user_arn:
            return {
                'success': False,
                'message': f'Profile "{profile_name}" is not an IAM user. Only IAM user credentials can be refreshed.'
            }
        
        # Extract username from ARN
        username = user_arn.split('/')[-1]
        
        # Get current access key ID
        old_access_key_id = get_current_access_key_id(profile_name)
        
        if not old_access_key_id:
            return {
                'success': False,
                'message': f'Could not find access key ID for profile "{profile_name}"'
            }
        
        # Create IAM client
        iam_client = session.client('iam')
        
        # List current access keys to verify we don't exceed the limit
        keys_response = iam_client.list_access_keys(UserName=username)
        current_keys = keys_response['AccessKeyMetadata']
        
        if len(current_keys) >= 2:
            return {
                'success': False,
                'message': f'User "{username}" already has 2 access keys. Please delete one before creating a new key.'
            }
        
        # Backup current credentials
        backup_result = backup_credentials(profile_name, old_access_key_id)
        
        if not backup_result['success']:
            return backup_result
        
        # Create new access key
        new_key_response = iam_client.create_access_key(UserName=username)
        new_access_key = new_key_response['AccessKey']
        new_access_key_id = new_access_key['AccessKeyId']
        new_secret_access_key = new_access_key['SecretAccessKey']
        
        # Update credentials file with new keys
        config = configparser.ConfigParser()
        config.read(credentials_path)
        
        if profile_name in config.sections():
            config[profile_name]['aws_access_key_id'] = new_access_key_id
            config[profile_name]['aws_secret_access_key'] = new_secret_access_key
            
            # Write updated credentials
            with open(credentials_path, 'w') as f:
                config.write(f)
        else:
            return {
                'success': False,
                'message': f'Profile "{profile_name}" not found in credentials file'
            }
        
        # Delete old key if requested
        if delete_old:
            try:
                iam_client.delete_access_key(
                    UserName=username,
                    AccessKeyId=old_access_key_id
                )
                delete_message = f' Old key {old_access_key_id} deleted from AWS.'
            except Exception as e:
                delete_message = f' Warning: Could not delete old key {old_access_key_id}: {str(e)}'
        else:
            delete_message = f' Old key {old_access_key_id} is still active in AWS. Use --delete to remove it.'
        
        return {
            'success': True,
            'message': f'✓ Credentials refreshed successfully for profile "{profile_name}"\n'
                      f'  New Key: {new_access_key_id}\n'
                      f'  Backup: {backup_result["backup_file"]}\n'
                      f'{delete_message}'
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        return {
            'success': False,
            'message': f'AWS Error ({error_code}): {e.response["Error"]["Message"]}'
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def refresh_credentials(profile_name, delete_old=False):
    """
    Refresh credentials for a profile (auto-detects IAM user vs SSO).
    
    Args:
        profile_name: Name of the AWS profile
        delete_old: If True, delete the old access key from AWS (IAM users only)
        
    Returns:
        dict: Result with success status and message
    """
    # Check if this is an SSO profile
    if is_sso_profile(profile_name):
        return refresh_sso_profile(profile_name)
    else:
        return refresh_iam_user_credentials(profile_name, delete_old)
