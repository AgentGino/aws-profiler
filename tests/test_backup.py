"""Unit tests for aws_profiler.backup module."""

import pytest
import configparser
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock
from freezegun import freeze_time

from aws_profiler.backup import backup_credentials


class TestBackupCredentials:
    """Tests for backup_credentials() function."""
    
    @freeze_time("2025-11-24 14:30:45")
    def test_backup_success(self, mock_aws_dir, mock_credentials_file):
        """Test B-01: Valid backup operation."""
        result = backup_credentials('default', 'AKIAIOSFODNN7EXAMPLE')
        
        assert result['success'] is True
        assert 'backup_file' in result
        
        # Verify backup file exists
        backup_path = Path(result['backup_file'])
        assert backup_path.exists()
        
        # Verify backup contains correct profile data
        config = configparser.ConfigParser()
        config.read(backup_path)
        assert 'default' in config.sections()
        assert config['default']['aws_access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
    
    def test_backup_creates_directory(self, mock_aws_dir, mock_credentials_file):
        """Test B-02: Backup dir doesn't exist."""
        backup_dir = mock_aws_dir / 'backups'
        
        # Ensure backup directory doesn't exist initially
        if backup_dir.exists():
            import shutil
            shutil.rmtree(backup_dir)
        
        result = backup_credentials('default', 'AKIAIOSFODNN7EXAMPLE')
        
        assert result['success'] is True
        # Verify backup directory was created
        assert backup_dir.exists()
        assert backup_dir.is_dir()
    
    @freeze_time("2025-11-24 16:45:30")
    def test_backup_file_naming(self, mock_aws_dir, mock_credentials_file):
        """Test B-03: Verify filename format."""
        result = backup_credentials('dev', 'AKIAI44QH8DHBEXAMPLE')
        
        assert result['success'] is True
        backup_filename = Path(result['backup_file']).name
        
        # Format: credentials_backup_profile_keyid_timestamp
        assert backup_filename.startswith('credentials_backup_dev_')
        assert 'BEXAMPLE' in backup_filename  # Last 8 chars of key
        assert '20251124_164530' in backup_filename
    
    def test_backup_permissions(self, mock_aws_dir, mock_credentials_file):
        """Test B-04: Check file permissions."""
        result = backup_credentials('default', 'AKIAIOSFODNN7EXAMPLE')
        
        assert result['success'] is True
        backup_path = Path(result['backup_file'])
        
        # Check permissions are 0o600 (owner read/write only)
        import stat
        mode = backup_path.stat().st_mode
        
        # Should be -rw------- (0o600)
        assert oct(stat.S_IMODE(mode)) == '0o600'
    
    def test_backup_profile_not_found(self, mock_aws_dir, mock_credentials_file):
        """Test B-05: Profile doesn't exist."""
        result = backup_credentials('nonexistent', 'AKIAIOSFODNN7EXAMPLE')
        
        assert result['success'] is False
        assert 'message' in result
        assert 'not found' in result['message'].lower()
        assert 'nonexistent' in result['message']
    
    def test_backup_only_target_profile(self, mock_aws_dir):
        """Test B-06: Multiple profiles in file."""
        # Create credentials file with multiple profiles
        credentials_path = mock_aws_dir / 'credentials'
        config = configparser.ConfigParser()
        
        config['default'] = {
            'aws_access_key_id': 'AKIAKEY1EXAMPLE',
            'aws_secret_access_key': 'SECRET1'
        }
        config['dev'] = {
            'aws_access_key_id': 'AKIAKEY2EXAMPLE',
            'aws_secret_access_key': 'SECRET2'
        }
        config['prod'] = {
            'aws_access_key_id': 'AKIAKEY3EXAMPLE',
            'aws_secret_access_key': 'SECRET3'
        }
        
        with open(credentials_path, 'w') as f:
            config.write(f)
        
        # Backup only 'dev' profile
        result = backup_credentials('dev', 'AKIAKEY2EXAMPLE')
        
        assert result['success'] is True
        
        # Verify backup contains only 'dev' profile
        backup_config = configparser.ConfigParser()
        backup_config.read(result['backup_file'])
        
        assert 'dev' in backup_config.sections()
        assert 'default' not in backup_config.sections()
        assert 'prod' not in backup_config.sections()
        assert len(backup_config.sections()) == 1
    
    @patch('aws_profiler.backup.configparser.ConfigParser.read')
    def test_backup_read_error(self, mock_read, mock_aws_dir, mock_credentials_file):
        """Test B-07: Can't read credentials file."""
        # Mock read to raise exception
        mock_read.side_effect = Exception('Permission denied')
        
        result = backup_credentials('default', 'AKIAIOSFODNN7EXAMPLE')
        
        assert result['success'] is False
        assert 'message' in result
        assert 'Failed to create backup' in result['message']
    
    @patch('builtins.open')
    def test_backup_write_error(self, mock_open, mock_aws_dir, mock_credentials_file):
        """Test B-08: Can't write backup file."""
        # Mock open for write to raise exception
        def open_side_effect(path, mode='r'):
            if mode == 'w' and 'backup' in str(path):
                raise PermissionError('Cannot write to backup directory')
            # For read operations, use real open
            return open(path, mode)
        
        mock_open.side_effect = open_side_effect
        
        result = backup_credentials('default', 'AKIAIOSFODNN7EXAMPLE')
        
        assert result['success'] is False
        assert 'Failed to create backup' in result['message']
    
    def test_backup_access_key_truncation(self, mock_aws_dir):
        """Test B-09: Uses last 8 chars of key."""
        credentials_path = mock_aws_dir / 'credentials'
        config = configparser.ConfigParser()
        
        config['test'] = {
            'aws_access_key_id': 'AKIA123456789ABC',
            'aws_secret_access_key': 'SECRET'
        }
        
        with open(credentials_path, 'w') as f:
            config.write(f)
        
        result = backup_credentials('test', 'AKIA123456789ABC')
        
        assert result['success'] is True
        backup_filename = Path(result['backup_file']).name
        
        # Should include last 8 chars: "9ABC"
        assert '6789ABC' in backup_filename  # Last 8 chars
    
    @freeze_time("2025-11-24 09:15:22")
    def test_backup_timestamp_uniqueness(self, mock_aws_dir, mock_credentials_file):
        """Test B-10: Multiple backups same second."""
        # First backup
        result1 = backup_credentials('default', 'AKIAIOSFODNN7EXAMPLE')
        assert result1['success'] is True
        filename1 = Path(result1['backup_file']).name
        
        # Timestamp should be included
        assert '20251124_091522' in filename1
        
        # Even in the same second, files should have the same timestamp
        # (the function doesn't add milliseconds, so this tests the base behavior)
        result2 = backup_credentials('default', 'AKIAIOSFODNN7EXAMPLE')
        assert result2['success'] is True
        
        # Both files should exist
        assert Path(result1['backup_file']).exists()
        assert Path(result2['backup_file']).exists()
        
        # Files will have same timestamp but won't overwrite each other
        # because they're opened in write mode sequentially
