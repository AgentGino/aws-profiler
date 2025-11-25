"""Unit tests for aws_profiler.credentials module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone, timedelta
from freezegun import freeze_time

from aws_profiler.credentials import (
    get_credential_age,
    get_credential_expiration
)


class TestGetCredentialAge:
    """Tests for get_credential_age() function."""
    
    @freeze_time("2025-11-24 12:00:00")
    def test_age_days_and_hours(self, mock_aws_dir, mock_credentials_file):
        """Test C-01: Credentials 3 days 5 hours old."""
        # Set file modification time to 3 days 5 hours ago
        age_ago = datetime.now(timezone.utc) - timedelta(days=3, hours=5)
        timestamp = age_ago.timestamp()
        
        credentials_path = mock_aws_dir / 'credentials'
        import os
        os.utime(credentials_path, (timestamp, timestamp))
        
        result = get_credential_age('default')
        
        assert result == '3d 5h'
    
    @freeze_time("2025-11-24 12:00:00")
    def test_age_only_hours(self, mock_aws_dir, mock_credentials_file):
        """Test C-02: Credentials 8 hours old."""
        # Set file modification time to 8 hours ago
        age_ago = datetime.now(timezone.utc) - timedelta(hours=8)
        timestamp = age_ago.timestamp()
        
        credentials_path = mock_aws_dir / 'credentials'
        import os
        os.utime(credentials_path, (timestamp, timestamp))
        
        result = get_credential_age('default')
        
        assert result == '8h'
    
    @freeze_time("2025-11-24 12:00:00")
    def test_age_only_minutes(self, mock_aws_dir, mock_credentials_file):
        """Test C-03: Credentials 45 minutes old."""
        # Set file modification time to 45 minutes ago
        age_ago = datetime.now(timezone.utc) - timedelta(minutes=45)
        timestamp = age_ago.timestamp()
        
        credentials_path = mock_aws_dir / 'credentials'
        import os
        os.utime(credentials_path, (timestamp, timestamp))
        
        result = get_credential_age('default')
        
        assert result == '45m'
    
    @freeze_time("2025-11-24 12:00:00")
    def test_age_just_created(self, mock_aws_dir, mock_credentials_file):
        """Test C-04: Credentials less than 1 min old."""
        # Set file modification time to now (30 seconds ago)
        age_ago = datetime.now(timezone.utc) - timedelta(seconds=30)
        timestamp = age_ago.timestamp()
        
        credentials_path = mock_aws_dir / 'credentials'
        import os
        os.utime(credentials_path, (timestamp, timestamp))
        
        result = get_credential_age('default')
        
        assert result == '0m'
    
    def test_age_no_file(self, mock_empty_aws_dir):
        """Test C-05: Credentials file doesn't exist."""
        result = get_credential_age('any-profile')
        
        assert result == 'N/A'
    
    def test_age_profile_not_found(self, mock_aws_dir, mock_credentials_file):
        """Test C-06: Profile not in file."""
        result = get_credential_age('nonexistent-profile')
        
        assert result == 'N/A'
    
    def test_age_exception(self, mock_aws_dir, mock_credentials_file):
        """Test C-07: File stat fails."""
        # Mock configparser to raise exception during parsing
        with patch('aws_profiler.credentials.configparser.ConfigParser') as mock_config:
            mock_config.return_value.read.side_effect = Exception('Permission denied')
            result = get_credential_age('default')
        
        assert result == 'N/A'
    
    @freeze_time("2025-11-24 18:30:00")
    def test_age_timezone_handling(self, mock_aws_dir, mock_credentials_file):
        """Test C-08: Verify UTC timezone usage."""
        # Set file modification time to 2 days ago in UTC
        age_ago = datetime.now(timezone.utc) - timedelta(days=2, hours=3)
        timestamp = age_ago.timestamp()
        
        credentials_path = mock_aws_dir / 'credentials'
        import os
        os.utime(credentials_path, (timestamp, timestamp))
        
        result = get_credential_age('default')
        
        # Should correctly calculate with UTC
        assert result == '2d 3h'


class TestGetCredentialExpiration:
    """Tests for get_credential_expiration() function."""
    
    def test_expiration_permanent_creds(self):
        """Test C-09: IAM user credentials."""
        # Mock session with permanent credentials (no token)
        mock_session = Mock()
        mock_creds = Mock()
        mock_creds.token = None  # No token = permanent credentials
        mock_session.get_credentials.return_value = mock_creds
        
        result = get_credential_expiration(mock_session)
        
        assert result['expires_in'] == 'Permanent'
        assert result['expiration_date'] == 'Never'
    
    @freeze_time("2025-11-24 12:00:00")
    def test_expiration_temporary_with_time(self):
        """Test C-10: Role credentials with expiration."""
        # Mock session with temporary credentials
        mock_session = Mock()
        mock_creds = Mock()
        mock_creds.token = 'temporary-token-abc123'
        mock_session.get_credentials.return_value = mock_creds
        
        # Mock STS client response
        mock_sts = Mock()
        expiration_time = datetime.now(timezone.utc) + timedelta(hours=11, minutes=30)
        mock_sts.get_session_token.return_value = {
            'Credentials': {
                'Expiration': expiration_time
            }
        }
        mock_session.client.return_value = mock_sts
        
        result = get_credential_expiration(mock_session)
        
        assert result['expires_in'] == '11h 30m'
        assert '2025-11-24' in result['expiration_date']
        assert 'UTC' in result['expiration_date']
    
    @freeze_time("2025-11-24 12:00:00")
    def test_expiration_hours_and_minutes(self):
        """Test C-11: 3h 45m remaining."""
        # Mock session with temporary credentials
        mock_session = Mock()
        mock_creds = Mock()
        mock_creds.token = 'temp-token'
        mock_session.get_credentials.return_value = mock_creds
        
        # Mock STS response with 3h 45m expiration
        mock_sts = Mock()
        expiration_time = datetime.now(timezone.utc) + timedelta(hours=3, minutes=45)
        mock_sts.get_session_token.return_value = {
            'Credentials': {
                'Expiration': expiration_time
            }
        }
        mock_session.client.return_value = mock_sts
        
        result = get_credential_expiration(mock_session)
        
        assert result['expires_in'] == '3h 45m'
    
    @freeze_time("2025-11-24 12:00:00")
    def test_expiration_only_minutes(self):
        """Test C-12: 30m remaining."""
        # Mock session with temporary credentials
        mock_session = Mock()
        mock_creds = Mock()
        mock_creds.token = 'temp-token'
        mock_session.get_credentials.return_value = mock_creds
        
        # Mock STS response with 30m expiration
        mock_sts = Mock()
        expiration_time = datetime.now(timezone.utc) + timedelta(minutes=30)
        mock_sts.get_session_token.return_value = {
            'Credentials': {
                'Expiration': expiration_time
            }
        }
        mock_session.client.return_value = mock_sts
        
        result = get_credential_expiration(mock_session)
        
        assert result['expires_in'] == '30m'
    
    def test_expiration_temporary_no_sts(self):
        """Test C-13: Temp credentials, STS call fails."""
        # Mock session with temporary credentials
        mock_session = Mock()
        mock_creds = Mock()
        mock_creds.token = 'temp-token'
        mock_session.get_credentials.return_value = mock_creds
        
        # Mock STS to raise exception
        mock_sts = Mock()
        mock_sts.get_session_token.side_effect = Exception('STS unavailable')
        mock_session.client.return_value = mock_sts
        
        result = get_credential_expiration(mock_session)
        
        # Should return Temporary when token exists but can't get expiration
        assert result['expires_in'] == 'Temporary'
        assert result['expiration_date'] == 'N/A'
    
    def test_expiration_exception(self):
        """Test C-14: Generic error."""
        # Mock session that raises exception
        mock_session = Mock()
        mock_session.get_credentials.side_effect = Exception('Unexpected error')
        
        result = get_credential_expiration(mock_session)
        
        assert result['expires_in'] == 'N/A'
        assert result['expiration_date'] == 'N/A'
    
    @freeze_time("2025-11-24 15:30:00")
    def test_expiration_date_format(self):
        """Test C-15: Check date formatting."""
        # Mock session with temporary credentials
        mock_session = Mock()
        mock_creds = Mock()
        mock_creds.token = 'temp-token'
        mock_session.get_credentials.return_value = mock_creds
        
        # Mock STS response
        mock_sts = Mock()
        expiration_time = datetime(2025, 11, 25, 10, 45, 30, tzinfo=timezone.utc)
        mock_sts.get_session_token.return_value = {
            'Credentials': {
                'Expiration': expiration_time
            }
        }
        mock_session.client.return_value = mock_sts
        
        result = get_credential_expiration(mock_session)
        
        # Verify format: YYYY-MM-DD HH:MM:SS UTC
        assert result['expiration_date'] == '2025-11-25 10:45:30 UTC'
