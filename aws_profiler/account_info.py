"""AWS account information retrieval."""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

from .credentials import get_credential_age, get_credential_expiration


def get_account_info(profile_name):
    """Get AWS account information and credential status for a profile."""
    try:
        session = boto3.Session(profile_name=profile_name)
        sts_client = session.client('sts')
        
        # Get caller identity
        identity = sts_client.get_caller_identity()
        
        account_id = identity.get('Account', 'N/A')
        user_arn = identity.get('Arn', 'N/A')
        
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
        
        # Get credential age and expiration info
        credential_age = get_credential_age(profile_name)
        expiration_info = get_credential_expiration(session)
        
        return {
            'profile': profile_name,
            'account_id': account_id,
            'user_name': user_name,
            'credential_type': credential_type,
            'arn': user_arn,
            'status': status,
            'credential_age': credential_age,
            'expires_in': expiration_info['expires_in'],
            'expiration_date': expiration_info['expiration_date']
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
                'status': 'Expired',
                'credential_age': 'N/A',
                'expires_in': 'Expired',
                'expiration_date': 'N/A'
            }
        else:
            return {
                'profile': profile_name,
                'account_id': 'N/A',
                'user_name': 'N/A',
                'credential_type': 'N/A',
                'arn': 'N/A',
                'status': f'Error: {error_code}',
                'credential_age': 'N/A',
                'expires_in': 'N/A',
                'expiration_date': 'N/A'
            }
    
    except (NoCredentialsError, ProfileNotFound):
        return {
            'profile': profile_name,
            'account_id': 'N/A',
            'user_name': 'N/A',
            'credential_type': 'N/A',
            'arn': 'N/A',
            'status': 'No Credentials',
            'credential_age': 'N/A',
            'expires_in': 'N/A',
            'expiration_date': 'N/A'
        }
    
    except Exception as e:
        return {
            'profile': profile_name,
            'account_id': 'N/A',
            'user_name': 'N/A',
            'credential_type': 'N/A',
            'arn': 'N/A',
            'status': f'Error: {str(e)[:30]}',
            'credential_age': 'N/A',
            'expires_in': 'N/A',
            'expiration_date': 'N/A'
        }
