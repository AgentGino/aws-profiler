"""Unit tests for aws_profiler.profiles module."""

import pytest
import configparser
from pathlib import Path
from unittest.mock import patch, MagicMock

from aws_profiler.profiles import (
    get_aws_profiles,
    is_sso_profile,
    get_current_access_key_id
)


class TestGetAwsProfiles:
    """Tests for get_aws_profiles() function."""
    
    def test_get_profiles_both_files_exist(self, mock_aws_dir, mock_credentials_file, mock_config_file):
        """Test P-01: Both credentials and config files exist with profiles."""
        profiles = get_aws_profiles()
        
        # Should have profiles from both files (default, dev from credentials; prod, sso-dev from config)
        assert 'default' in profiles
        assert 'dev' in profiles
        assert 'prod' in profiles
        assert 'sso-dev' in profiles
        assert len(profiles) == 4
        
        # Should be sorted
        assert profiles == sorted(profiles)
    
    def test_get_profiles_only_credentials(self, mock_aws_dir, mock_credentials_file):
        """Test P-02: Only credentials file exists."""
        profiles = get_aws_profiles()
        
        # Should have only profiles from credentials file
        assert 'default' in profiles
        assert 'dev' in profiles
        assert len(profiles) == 2
    
    def test_get_profiles_only_config(self, mock_aws_dir, mock_config_file):
        """Test P-03: Only config file exists."""
        profiles = get_aws_profiles()
        
        # Should have only profiles from config file
        assert 'prod' in profiles
        assert 'sso-dev' in profiles
        assert len(profiles) == 2
    
    def test_get_profiles_no_files(self, mock_empty_aws_dir):
        """Test P-04: Neither file exists."""
        profiles = get_aws_profiles()
        
        # Should return empty list
        assert profiles == []
    
    def test_get_profiles_with_profile_prefix(self, mock_aws_dir):
        """Test P-05: Config has 'profile name' sections."""
        config_path = mock_aws_dir / 'config'
        config = configparser.ConfigParser()
        
        config['profile staging'] = {
            'region': 'us-west-2'
        }
        config['profile prod'] = {
            'region': 'us-east-1'
        }
        
        with open(config_path, 'w') as f:
            config.write(f)
        
        profiles = get_aws_profiles()
        
        # Should strip 'profile ' prefix
        assert 'staging' in profiles
        assert 'prod' in profiles
        assert 'profile staging' not in profiles
        assert 'profile prod' not in profiles
    
    def test_get_profiles_deduplication(self, mock_aws_dir):
        """Test P-06: Same profile in both files."""
        # Create credentials file with 'prod' profile
        credentials_path = mock_aws_dir / 'credentials'
        cred_config = configparser.ConfigParser()
        cred_config['prod'] = {
            'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        }
        with open(credentials_path, 'w') as f:
            cred_config.write(f)
        
        # Create config file with 'prod' profile
        config_path = mock_aws_dir / 'config'
        config = configparser.ConfigParser()
        config['profile prod'] = {
            'region': 'us-east-1'
        }
        with open(config_path, 'w') as f:
            config.write(f)
        
        profiles = get_aws_profiles()
        
        # Should have only one 'prod' entry (deduplicated)
        assert profiles.count('prod') == 1
        assert len(profiles) == 1
    
    def test_get_profiles_sorting(self, mock_aws_dir):
        """Test P-07: Profiles in random order."""
        credentials_path = mock_aws_dir / 'credentials'
        config = configparser.ConfigParser()
        
        # Add profiles in non-alphabetical order
        config['zebra'] = {'aws_access_key_id': 'KEY1'}
        config['alpha'] = {'aws_access_key_id': 'KEY2'}
        config['mike'] = {'aws_access_key_id': 'KEY3'}
        config['bravo'] = {'aws_access_key_id': 'KEY4'}
        
        with open(credentials_path, 'w') as f:
            config.write(f)
        
        profiles = get_aws_profiles()
        
        # Should be sorted alphabetically
        assert profiles == ['alpha', 'bravo', 'mike', 'zebra']


class TestIsSsoProfile:
    """Tests for is_sso_profile() function."""
    
    def test_is_sso_profile_with_start_url(self, mock_aws_dir):
        """Test P-08: Profile has sso_start_url."""
        config_path = mock_aws_dir / 'config'
        config = configparser.ConfigParser()
        
        config['profile sso-dev'] = {
            'sso_start_url': 'https://example.awsapps.com/start',
            'sso_region': 'us-east-1',
            'region': 'us-west-2'
        }
        
        with open(config_path, 'w') as f:
            config.write(f)
        
        assert is_sso_profile('sso-dev') is True
    
    def test_is_sso_profile_with_session(self, mock_aws_dir):
        """Test P-09: Profile has sso_session."""
        config_path = mock_aws_dir / 'config'
        config = configparser.ConfigParser()
        
        config['profile sso-prod'] = {
            'sso_session': 'my-session',
            'region': 'us-east-1'
        }
        
        with open(config_path, 'w') as f:
            config.write(f)
        
        assert is_sso_profile('sso-prod') is True
    
    def test_is_sso_profile_with_both(self, mock_aws_dir):
        """Test P-10: Profile has both SSO keys."""
        config_path = mock_aws_dir / 'config'
        config = configparser.ConfigParser()
        
        config['profile sso-full'] = {
            'sso_start_url': 'https://example.awsapps.com/start',
            'sso_session': 'my-session',
            'sso_region': 'us-east-1',
            'region': 'us-west-2'
        }
        
        with open(config_path, 'w') as f:
            config.write(f)
        
        assert is_sso_profile('sso-full') is True
    
    def test_is_sso_profile_non_sso(self, mock_aws_dir):
        """Test P-11: Regular IAM user profile."""
        config_path = mock_aws_dir / 'config'
        config = configparser.ConfigParser()
        
        config['profile iam-user'] = {
            'region': 'us-east-1',
            'output': 'json'
        }
        
        with open(config_path, 'w') as f:
            config.write(f)
        
        assert is_sso_profile('iam-user') is False
    
    def test_is_sso_profile_no_config(self, mock_empty_aws_dir):
        """Test P-12: Config file doesn't exist."""
        assert is_sso_profile('any-profile') is False
    
    def test_is_sso_profile_with_prefix(self, mock_aws_dir):
        """Test P-13: Profile stored as 'profile name'."""
        config_path = mock_aws_dir / 'config'
        config = configparser.ConfigParser()
        
        # Store with 'profile ' prefix
        config['profile my-sso'] = {
            'sso_start_url': 'https://example.awsapps.com/start',
            'region': 'us-east-1'
        }
        
        with open(config_path, 'w') as f:
            config.write(f)
        
        # Should find it by name without prefix
        assert is_sso_profile('my-sso') is True
    
    def test_is_sso_profile_exception(self, mock_aws_dir):
        """Test P-14: ConfigParser throws exception."""
        config_path = mock_aws_dir / 'config'
        
        # Create invalid config file
        with open(config_path, 'w') as f:
            f.write('[invalid\nmalformed config')
        
        # Should return False on exception
        assert is_sso_profile('any-profile') is False


class TestGetCurrentAccessKeyId:
    """Tests for get_current_access_key_id() function."""
    
    def test_get_key_id_success(self, mock_aws_dir, mock_credentials_file):
        """Test P-15: Valid profile with key."""
        key_id = get_current_access_key_id('default')
        
        assert key_id == 'AKIAIOSFODNN7EXAMPLE'
    
    def test_get_key_id_no_file(self, mock_empty_aws_dir):
        """Test P-16: Credentials file missing."""
        key_id = get_current_access_key_id('default')
        
        assert key_id is None
    
    def test_get_key_id_profile_not_found(self, mock_aws_dir, mock_credentials_file):
        """Test P-17: Profile doesn't exist."""
        key_id = get_current_access_key_id('nonexistent')
        
        assert key_id is None
    
    def test_get_key_id_no_key_field(self, mock_aws_dir):
        """Test P-18: Profile missing aws_access_key_id."""
        credentials_path = mock_aws_dir / 'credentials'
        config = configparser.ConfigParser()
        
        config['incomplete'] = {
            'aws_secret_access_key': 'SECRET_KEY_ONLY'
            # Missing aws_access_key_id
        }
        
        with open(credentials_path, 'w') as f:
            config.write(f)
        
        key_id = get_current_access_key_id('incomplete')
        
        assert key_id is None
    
    def test_get_key_id_exception(self, mock_aws_dir):
        """Test P-19: Parse error."""
        credentials_path = mock_aws_dir / 'credentials'
        
        # Create invalid credentials file
        with open(credentials_path, 'w') as f:
            f.write('[invalid\nmalformed credentials')
        
        # Should return None on exception
        key_id = get_current_access_key_id('any-profile')
        
        assert key_id is None
