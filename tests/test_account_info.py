"""Unit tests for aws_profiler.account_info module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

from aws_profiler.account_info import get_account_info


class TestGetAccountInfo:
    """Tests for get_account_info() function."""
    
    @patch('aws_profiler.account_info.get_credential_expiration')
    @patch('aws_profiler.account_info.get_credential_age')
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_iam_user_success(self, mock_session, mock_age, mock_expiration):
        """Test A-01: Active IAM user."""
        # Setup mocks
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/john-doe',
            'UserId': 'AIDAI123456789EXAMPLE'
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        
        mock_age.return_value = '3d 5h'
        mock_expiration.return_value = {
            'expires_in': 'Permanent',
            'expiration_date': 'Never'
        }
        
        # Execute
        result = get_account_info('test-profile')
        
        # Verify
        assert result['profile'] == 'test-profile'
        assert result['account_id'] == '123456789012'
        assert result['user_name'] == 'john-doe'
        assert result['credential_type'] == 'User'
        assert result['arn'] == 'arn:aws:iam::123456789012:user/john-doe'
        assert result['status'] == 'Active'
        assert result['credential_age'] == '3d 5h'
        assert result['expires_in'] == 'Permanent'
        assert result['expiration_date'] == 'Never'
    
    @patch('aws_profiler.account_info.get_credential_expiration')
    @patch('aws_profiler.account_info.get_credential_age')
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_assumed_role(self, mock_session, mock_age, mock_expiration):
        """Test A-02: Assumed role credentials."""
        # Setup mocks
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/session-name',
            'UserId': 'AROAI123456789EXAMPLE:session-name'
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        
        mock_age.return_value = '2h'
        mock_expiration.return_value = {
            'expires_in': '10h 30m',
            'expiration_date': '2025-11-25 22:30:00 UTC'
        }
        
        # Execute
        result = get_account_info('role-profile')
        
        # Verify
        assert result['credential_type'] == 'Role'
        assert result['user_name'] == 'session-name'
        assert 'assumed-role' in result['arn']
        assert result['status'] == 'Active'
    
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_expired_token(self, mock_session):
        """Test A-03: Expired credentials."""
        # Setup mock to raise ExpiredToken error
        mock_sts = Mock()
        error_response = {'Error': {'Code': 'ExpiredToken', 'Message': 'Token expired'}}
        mock_sts.get_caller_identity.side_effect = ClientError(error_response, 'GetCallerIdentity')
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        
        # Execute
        result = get_account_info('expired-profile')
        
        # Verify
        assert result['profile'] == 'expired-profile'
        assert result['status'] == 'Expired'
        assert result['account_id'] == 'N/A'
        assert result['user_name'] == 'N/A'
        assert result['expires_in'] == 'Expired'
    
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_invalid_token(self, mock_session):
        """Test A-04: Invalid credentials."""
        # Setup mock to raise InvalidClientTokenId error
        mock_sts = Mock()
        error_response = {'Error': {'Code': 'InvalidClientTokenId', 'Message': 'Invalid token'}}
        mock_sts.get_caller_identity.side_effect = ClientError(error_response, 'GetCallerIdentity')
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        
        # Execute
        result = get_account_info('invalid-profile')
        
        # Verify
        assert result['status'] == 'Expired'
        assert result['account_id'] == 'N/A'
    
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_no_credentials(self, mock_session):
        """Test A-05: Profile has no credentials."""
        # Setup mock to raise NoCredentialsError
        mock_session.side_effect = NoCredentialsError()
        
        # Execute
        result = get_account_info('no-creds-profile')
        
        # Verify
        assert result['profile'] == 'no-creds-profile'
        assert result['status'] == 'No Credentials'
        assert result['account_id'] == 'N/A'
        assert result['credential_age'] == 'N/A'
    
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_profile_not_found(self, mock_session):
        """Test A-06: Profile doesn't exist."""
        # Setup mock to raise ProfileNotFound error
        mock_session.side_effect = ProfileNotFound(profile='missing-profile')
        
        # Execute
        result = get_account_info('missing-profile')
        
        # Verify
        assert result['status'] == 'No Credentials'
        assert result['account_id'] == 'N/A'
    
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_access_denied(self, mock_session):
        """Test A-07: Insufficient permissions."""
        # Setup mock to raise AccessDenied error
        mock_sts = Mock()
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        mock_sts.get_caller_identity.side_effect = ClientError(error_response, 'GetCallerIdentity')
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        
        # Execute
        result = get_account_info('denied-profile')
        
        # Verify
        assert result['status'] == 'Error: AccessDenied'
        assert result['account_id'] == 'N/A'
    
    @patch('aws_profiler.account_info.get_credential_expiration')
    @patch('aws_profiler.account_info.get_credential_age')
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_with_credential_age(self, mock_session, mock_age, mock_expiration):
        """Test A-08: Verify age calculation."""
        # Setup mocks
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test',
            'UserId': 'AIDAI123456789EXAMPLE'
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        
        mock_age.return_value = '5d 12h'
        mock_expiration.return_value = {
            'expires_in': 'Permanent',
            'expiration_date': 'Never'
        }
        
        # Execute
        result = get_account_info('test-profile')
        
        # Verify
        assert 'credential_age' in result
        assert result['credential_age'] == '5d 12h'
        mock_age.assert_called_once_with('test-profile')
    
    @patch('aws_profiler.account_info.get_credential_expiration')
    @patch('aws_profiler.account_info.get_credential_age')
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_with_expiration(self, mock_session, mock_age, mock_expiration):
        """Test A-09: Verify expiration data."""
        # Setup mocks
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/session',
            'UserId': 'AROAI123456789EXAMPLE:session'
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        
        mock_age.return_value = '1h'
        mock_expiration.return_value = {
            'expires_in': '11h 45m',
            'expiration_date': '2025-11-25 23:45:00 UTC'
        }
        
        # Execute
        result = get_account_info('temp-profile')
        
        # Verify
        assert 'expires_in' in result
        assert 'expiration_date' in result
        assert result['expires_in'] == '11h 45m'
        assert result['expiration_date'] == '2025-11-25 23:45:00 UTC'
        mock_expiration.assert_called_once_with(mock_session_instance)
    
    @patch('aws_profiler.account_info.get_credential_expiration')
    @patch('aws_profiler.account_info.get_credential_age')
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_unknown_arn_format(self, mock_session, mock_age, mock_expiration):
        """Test A-10: ARN doesn't match user/role."""
        # Setup mocks with unusual ARN
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:something-unusual',
            'UserId': 'AIDAI123456789EXAMPLE'
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        
        mock_age.return_value = '1d'
        mock_expiration.return_value = {
            'expires_in': 'N/A',
            'expiration_date': 'N/A'
        }
        
        # Execute
        result = get_account_info('unusual-profile')
        
        # Verify
        assert result['credential_type'] == 'Unknown'
        assert result['user_name'] == 'N/A'
    
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_generic_exception(self, mock_session):
        """Test A-11: Unexpected error."""
        # Setup mock to raise generic exception
        mock_session.side_effect = Exception('Something unexpected happened with details')
        
        # Execute
        result = get_account_info('error-profile')
        
        # Verify
        assert result['profile'] == 'error-profile'
        assert result['status'].startswith('Error:')
        assert len(result['status']) <= 38  # "Error: " + 30 chars + potential truncation
        assert result['account_id'] == 'N/A'
    
    @patch('aws_profiler.account_info.get_credential_expiration')
    @patch('aws_profiler.account_info.get_credential_age')
    @patch('aws_profiler.account_info.boto3.Session')
    def test_get_info_arn_parsing(self, mock_session, mock_age, mock_expiration):
        """Test A-12: Extract user name from ARN."""
        # Setup mocks with complex ARN
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/engineering/developers/john',
            'UserId': 'AIDAI123456789EXAMPLE'
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        
        mock_age.return_value = '2d'
        mock_expiration.return_value = {
            'expires_in': 'Permanent',
            'expiration_date': 'Never'
        }
        
        # Execute
        result = get_account_info('test-profile')
        
        # Verify - should extract last part after final /
        assert result['user_name'] == 'john'
        assert result['credential_type'] == 'User'
