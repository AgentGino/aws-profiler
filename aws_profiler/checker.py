"""
Backward compatibility module for AWS profile checking.

This module maintains backward compatibility by re-exporting all functions
from the new modular structure.
"""

# Re-export all public functions for backward compatibility
from .profiles import get_aws_profiles, is_sso_profile, get_current_access_key_id
from .account_info import get_account_info
from .credentials import get_credential_age, get_credential_expiration
from .backup import backup_credentials
from .refresh import refresh_credentials, refresh_sso_profile, refresh_iam_user_credentials

__all__ = [
    'get_aws_profiles',
    'is_sso_profile',
    'get_current_access_key_id',
    'get_account_info',
    'get_credential_age',
    'get_credential_expiration',
    'backup_credentials',
    'refresh_credentials',
    'refresh_sso_profile',
    'refresh_iam_user_credentials',
]
