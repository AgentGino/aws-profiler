"""Unit tests for aws_profiler.refresh module."""

import pytest
import configparser
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from botocore.exceptions import ClientError

from aws_profiler.refresh import (
    refresh_sso_profile,
    refresh_iam_user_credentials,
    refresh_credentials
)


class TestRefreshSsoProfile:
    """Tests for refresh_sso_profile() function."""
    
    @patch('aws_profiler.refresh.subprocess.run')
    def test_sso_refresh_success(self, mock_run):
        """Test R-01: SSO login succeeds."""
        mock_run.return_value = Mock(returncode=0)
        
        result = refresh_sso_profile('sso-dev')
        
        assert result['success'] is True
        assert 'SSO login successful' in result['message']
        assert 'sso-dev' in result['message']
        
        # Verify correct command was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ['aws', 'sso', 'login', '--profile', 'sso-dev']
    
    @patch('aws_profiler.refresh.subprocess.run')
    def test_sso_refresh_failure(self, mock_run):
        """Test R-02: SSO login fails."""
        mock_run.return_value = Mock(returncode=1)
        
        result = refresh_sso_profile('sso-dev')
        
        assert result['success'] is False
        assert 'failed' in result['message'].lower()
        assert 'exit code 1' in result['message']
    
    @patch('aws_profiler.refresh.subprocess.run')
    def test_sso_aws_cli_not_found(self, mock_run):
        """Test R-03: AWS CLI not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        result = refresh_sso_profile('sso-dev')
        
        assert result['success'] is False
        assert 'AWS CLI not found' in result['message']
        assert 'install' in result['message'].lower()
    
    @patch('aws_profiler.refresh.subprocess.run')
    def test_sso_correct_command(self, mock_run):
        """Test R-04: Verify command args."""
        mock_run.return_value = Mock(returncode=0)
        
        refresh_sso_profile('my-profile')
        
        # Capture and verify the command
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == 'aws'
        assert call_args[1] == 'sso'
        assert call_args[2] == 'login'
        assert call_args[3] == '--profile'
        assert call_args[4] == 'my-profile'
    
    @patch('aws_profiler.refresh.subprocess.run')
    def test_sso_generic_exception(self, mock_run):
        """Test R-05: Unexpected error."""
        mock_run.side_effect = Exception('Unexpected error occurred')
        
        result = refresh_sso_profile('sso-dev')
        
        assert result['success'] is False
        assert 'Error during SSO login' in result['message']


class TestRefreshIamUserCredentials:
    """Tests for refresh_iam_user_credentials() function."""
    
    @patch('aws_profiler.refresh.backup_credentials')
    @patch('aws_profiler.refresh.get_current_access_key_id')
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_success(self, mock_session, mock_get_key, mock_backup):
        """Test R-06: Full refresh flow."""
        # Setup mocks
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/john-doe'
        }
        
        mock_iam = Mock()
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [{'AccessKeyId': 'AKIAOLD'}]
        }
        mock_iam.create_access_key.return_value = {
            'AccessKey': {
                'AccessKeyId': 'AKIANEW123',
                'SecretAccessKey': 'newSecretKey456'
            }
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: mock_sts if service == 'sts' else mock_iam
        mock_session.return_value = mock_session_instance
        
        mock_get_key.return_value = 'AKIAOLD'
        mock_backup.return_value = {
            'success': True,
            'backup_file': '/tmp/.aws/backups/backup_file'
        }
        
        # Create mock credentials file
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            
            config = configparser.ConfigParser()
            config['test-profile'] = {
                'aws_access_key_id': 'AKIAOLD',
                'aws_secret_access_key': 'oldSecret'
            }
            with open(creds_path, 'w') as f:
                config.write(f)
            
            result = refresh_iam_user_credentials('test-profile', delete_old=False)
        
        assert result['success'] is True
        assert 'refreshed successfully' in result['message']
        assert 'AKIANEW123' in result['message']
    
    @patch('aws_profiler.refresh.backup_credentials')
    @patch('aws_profiler.refresh.get_current_access_key_id')
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_with_delete(self, mock_session, mock_get_key, mock_backup):
        """Test R-07: Refresh + delete old key."""
        # Setup mocks
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/john-doe'
        }
        
        mock_iam = Mock()
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [{'AccessKeyId': 'AKIAOLD'}]
        }
        mock_iam.create_access_key.return_value = {
            'AccessKey': {
                'AccessKeyId': 'AKIANEW123',
                'SecretAccessKey': 'newSecretKey456'
            }
        }
        mock_iam.delete_access_key.return_value = {}
        
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: mock_sts if service == 'sts' else mock_iam
        mock_session.return_value = mock_session_instance
        
        mock_get_key.return_value = 'AKIAOLD'
        mock_backup.return_value = {
            'success': True,
            'backup_file': '/tmp/.aws/backups/backup_file'
        }
        
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            
            config = configparser.ConfigParser()
            config['test-profile'] = {
                'aws_access_key_id': 'AKIAOLD',
                'aws_secret_access_key': 'oldSecret'
            }
            with open(creds_path, 'w') as f:
                config.write(f)
            
            result = refresh_iam_user_credentials('test-profile', delete_old=True)
        
        assert result['success'] is True
        # Verify delete was called
        mock_iam.delete_access_key.assert_called_once_with(
            UserName='john-doe',
            AccessKeyId='AKIAOLD'
        )
        assert 'Old key AKIAOLD deleted' in result['message']
    
    @patch('aws_profiler.refresh.backup_credentials')
    @patch('aws_profiler.refresh.get_current_access_key_id')
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_without_delete(self, mock_session, mock_get_key, mock_backup):
        """Test R-08: Refresh only."""
        # Setup mocks
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/alice'
        }
        
        mock_iam = Mock()
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [{'AccessKeyId': 'AKIAOLD'}]
        }
        mock_iam.create_access_key.return_value = {
            'AccessKey': {
                'AccessKeyId': 'AKIANEW123',
                'SecretAccessKey': 'newSecretKey456'
            }
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: mock_sts if service == 'sts' else mock_iam
        mock_session.return_value = mock_session_instance
        
        mock_get_key.return_value = 'AKIAOLD'
        mock_backup.return_value = {
            'success': True,
            'backup_file': '/tmp/.aws/backups/backup_file'
        }
        
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            
            config = configparser.ConfigParser()
            config['test-profile'] = {
                'aws_access_key_id': 'AKIAOLD',
                'aws_secret_access_key': 'oldSecret'
            }
            with open(creds_path, 'w') as f:
                config.write(f)
            
            result = refresh_iam_user_credentials('test-profile', delete_old=False)
        
        assert result['success'] is True
        # Verify delete was NOT called
        mock_iam.delete_access_key.assert_not_called()
        assert 'still active' in result['message']
    
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_role_not_user(self, mock_session):
        """Test R-09: Try to refresh assumed role."""
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/session'
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            creds_path.touch()
            
            result = refresh_iam_user_credentials('role-profile')
        
        assert result['success'] is False
        assert 'not an IAM user' in result['message']
    
    def test_iam_refresh_no_credentials_file(self):
        """Test R-10: File doesn't exist."""
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/nonexistent')
            
            result = refresh_iam_user_credentials('test-profile')
        
        assert result['success'] is False
        assert 'Credentials file not found' in result['message']
    
    @patch('aws_profiler.refresh.get_current_access_key_id')
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_no_access_key_id(self, mock_session, mock_get_key):
        """Test R-11: Can't get current key."""
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/john'
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        
        mock_get_key.return_value = None
        
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            creds_path.touch()
            
            result = refresh_iam_user_credentials('test-profile')
        
        assert result['success'] is False
        assert 'Could not find access key ID' in result['message']
    
    @patch('aws_profiler.refresh.get_current_access_key_id')
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_max_keys(self, mock_session, mock_get_key):
        """Test R-12: User already has 2 keys."""
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/john'
        }
        
        mock_iam = Mock()
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [
                {'AccessKeyId': 'AKIAKEY1'},
                {'AccessKeyId': 'AKIAKEY2'}
            ]
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: mock_sts if service == 'sts' else mock_iam
        mock_session.return_value = mock_session_instance
        
        mock_get_key.return_value = 'AKIAKEY1'
        
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            creds_path.touch()
            
            result = refresh_iam_user_credentials('test-profile')
        
        assert result['success'] is False
        assert 'already has 2 access keys' in result['message']
    
    @patch('aws_profiler.refresh.backup_credentials')
    @patch('aws_profiler.refresh.get_current_access_key_id')
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_backup_fails(self, mock_session, mock_get_key, mock_backup):
        """Test R-13: Backup operation fails."""
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/john'
        }
        
        mock_iam = Mock()
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [{'AccessKeyId': 'AKIAOLD'}]
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: mock_sts if service == 'sts' else mock_iam
        mock_session.return_value = mock_session_instance
        
        mock_get_key.return_value = 'AKIAOLD'
        mock_backup.return_value = {
            'success': False,
            'message': 'Backup failed'
        }
        
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            creds_path.touch()
            
            result = refresh_iam_user_credentials('test-profile')
        
        assert result['success'] is False
        assert result['message'] == 'Backup failed'
    
    @patch('aws_profiler.refresh.backup_credentials')
    @patch('aws_profiler.refresh.get_current_access_key_id')
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_create_key_fails(self, mock_session, mock_get_key, mock_backup):
        """Test R-14: IAM create_access_key fails."""
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/john'
        }
        
        mock_iam = Mock()
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [{'AccessKeyId': 'AKIAOLD'}]
        }
        error_response = {'Error': {'Code': 'LimitExceeded', 'Message': 'Limit exceeded'}}
        mock_iam.create_access_key.side_effect = ClientError(error_response, 'CreateAccessKey')
        
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: mock_sts if service == 'sts' else mock_iam
        mock_session.return_value = mock_session_instance
        
        mock_get_key.return_value = 'AKIAOLD'
        mock_backup.return_value = {
            'success': True,
            'backup_file': '/tmp/backup'
        }
        
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            creds_path.touch()
            
            result = refresh_iam_user_credentials('test-profile')
        
        assert result['success'] is False
        assert 'AWS Error' in result['message']
        assert 'LimitExceeded' in result['message']
    
    @patch('aws_profiler.refresh.backup_credentials')
    @patch('aws_profiler.refresh.get_current_access_key_id')
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_update_file_fails(self, mock_session, mock_get_key, mock_backup):
        """Test R-15: Can't write credentials file."""
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/john'
        }
        
        mock_iam = Mock()
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [{'AccessKeyId': 'AKIAOLD'}]
        }
        mock_iam.create_access_key.return_value = {
            'AccessKey': {
                'AccessKeyId': 'AKIANEW',
                'SecretAccessKey': 'newSecret'
            }
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: mock_sts if service == 'sts' else mock_iam
        mock_session.return_value = mock_session_instance
        
        mock_get_key.return_value = 'AKIAOLD'
        mock_backup.return_value = {
            'success': True,
            'backup_file': '/tmp/backup'
        }
        
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create empty credentials file
            config = configparser.ConfigParser()
            # Profile not in file
            with open(creds_path, 'w') as f:
                config.write(f)
            
            result = refresh_iam_user_credentials('test-profile')
        
        assert result['success'] is False
        assert 'not found in credentials file' in result['message']
    
    @patch('aws_profiler.refresh.backup_credentials')
    @patch('aws_profiler.refresh.get_current_access_key_id')
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_delete_fails(self, mock_session, mock_get_key, mock_backup):
        """Test R-16: Delete old key fails."""
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/john'
        }
        
        mock_iam = Mock()
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [{'AccessKeyId': 'AKIAOLD'}]
        }
        mock_iam.create_access_key.return_value = {
            'AccessKey': {
                'AccessKeyId': 'AKIANEW',
                'SecretAccessKey': 'newSecret'
            }
        }
        mock_iam.delete_access_key.side_effect = Exception('Delete failed')
        
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: mock_sts if service == 'sts' else mock_iam
        mock_session.return_value = mock_session_instance
        
        mock_get_key.return_value = 'AKIAOLD'
        mock_backup.return_value = {
            'success': True,
            'backup_file': '/tmp/backup'
        }
        
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            
            config = configparser.ConfigParser()
            config['test-profile'] = {
                'aws_access_key_id': 'AKIAOLD',
                'aws_secret_access_key': 'oldSecret'
            }
            with open(creds_path, 'w') as f:
                config.write(f)
            
            result = refresh_iam_user_credentials('test-profile', delete_old=True)
        
        assert result['success'] is True
        assert 'Warning' in result['message']
        assert 'Could not delete old key' in result['message']
    
    @patch('aws_profiler.refresh.get_current_access_key_id')
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_username_extraction(self, mock_session, mock_get_key):
        """Test R-17: Extract username from ARN."""
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/engineering/alice'
        }
        
        mock_iam = Mock()
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [{'AccessKeyId': 'AKIAOLD'}]
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: mock_sts if service == 'sts' else mock_iam
        mock_session.return_value = mock_session_instance
        
        mock_get_key.return_value = 'AKIAOLD'
        
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            creds_path.touch()
            
            refresh_iam_user_credentials('test-profile')
            
            # Verify username extraction
            mock_iam.list_access_keys.assert_called_once_with(UserName='alice')
    
    @patch('aws_profiler.refresh.backup_credentials')
    @patch('aws_profiler.refresh.get_current_access_key_id')
    @patch('aws_profiler.refresh.boto3.Session')
    def test_iam_refresh_profile_not_in_file(self, mock_session, mock_get_key, mock_backup):
        """Test R-18: Profile missing after creation."""
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/john'
        }
        
        mock_iam = Mock()
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [{'AccessKeyId': 'AKIAOLD'}]
        }
        mock_iam.create_access_key.return_value = {
            'AccessKey': {
                'AccessKeyId': 'AKIANEW',
                'SecretAccessKey': 'newSecret'
            }
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: mock_sts if service == 'sts' else mock_iam
        mock_session.return_value = mock_session_instance
        
        mock_get_key.return_value = 'AKIAOLD'
        mock_backup.return_value = {
            'success': True,
            'backup_file': '/tmp/backup'
        }
        
        with patch('aws_profiler.refresh.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp')
            creds_path = Path('/tmp/.aws/credentials')
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create credentials file without the target profile
            config = configparser.ConfigParser()
            config['other-profile'] = {
                'aws_access_key_id': 'AKIAOTHER',
                'aws_secret_access_key': 'otherSecret'
            }
            with open(creds_path, 'w') as f:
                config.write(f)
            
            result = refresh_iam_user_credentials('test-profile')
        
        assert result['success'] is False
        assert 'not found in credentials file' in result['message']


class TestRefreshCredentials:
    """Tests for refresh_credentials() function."""
    
    @patch('aws_profiler.refresh.refresh_sso_profile')
    @patch('aws_profiler.refresh.is_sso_profile')
    def test_refresh_detects_sso(self, mock_is_sso, mock_refresh_sso):
        """Test R-19: Auto-detect SSO profile."""
        mock_is_sso.return_value = True
        mock_refresh_sso.return_value = {'success': True}
        
        result = refresh_credentials('sso-profile')
        
        mock_is_sso.assert_called_once_with('sso-profile')
        mock_refresh_sso.assert_called_once_with('sso-profile')
        assert result['success'] is True
    
    @patch('aws_profiler.refresh.refresh_iam_user_credentials')
    @patch('aws_profiler.refresh.is_sso_profile')
    def test_refresh_detects_iam(self, mock_is_sso, mock_refresh_iam):
        """Test R-20: Auto-detect IAM user."""
        mock_is_sso.return_value = False
        mock_refresh_iam.return_value = {'success': True}
        
        result = refresh_credentials('iam-profile')
        
        mock_is_sso.assert_called_once_with('iam-profile')
        mock_refresh_iam.assert_called_once_with('iam-profile', False)
        assert result['success'] is True
    
    @patch('aws_profiler.refresh.refresh_iam_user_credentials')
    @patch('aws_profiler.refresh.is_sso_profile')
    def test_refresh_passes_delete_flag(self, mock_is_sso, mock_refresh_iam):
        """Test R-21: Delete flag passed through."""
        mock_is_sso.return_value = False
        mock_refresh_iam.return_value = {'success': True}
        
        result = refresh_credentials('iam-profile', delete_old=True)
        
        mock_refresh_iam.assert_called_once_with('iam-profile', True)
        assert result['success'] is True
