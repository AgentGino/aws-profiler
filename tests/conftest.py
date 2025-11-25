"""Shared pytest fixtures for aws_profiler tests."""

import pytest
from pathlib import Path
import configparser


@pytest.fixture
def mock_aws_dir(tmp_path, monkeypatch):
    """Create a temporary AWS directory for testing."""
    aws_dir = tmp_path / '.aws'
    aws_dir.mkdir()
    
    # Mock Path.home() to return tmp_path
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    
    return aws_dir


@pytest.fixture
def mock_credentials_file(mock_aws_dir):
    """Create a mock credentials file with test profiles."""
    credentials_path = mock_aws_dir / 'credentials'
    config = configparser.ConfigParser()
    
    config['default'] = {
        'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
        'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
    }
    
    config['dev'] = {
        'aws_access_key_id': 'AKIAI44QH8DHBEXAMPLE',
        'aws_secret_access_key': 'je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY'
    }
    
    with open(credentials_path, 'w') as f:
        config.write(f)
    
    return credentials_path


@pytest.fixture
def mock_config_file(mock_aws_dir):
    """Create a mock config file with test profiles."""
    config_path = mock_aws_dir / 'config'
    config = configparser.ConfigParser()
    
    config['profile prod'] = {
        'region': 'us-east-1',
        'output': 'json'
    }
    
    config['profile sso-dev'] = {
        'sso_start_url': 'https://example.awsapps.com/start',
        'sso_region': 'us-east-1',
        'sso_account_id': '123456789012',
        'sso_role_name': 'Developer',
        'region': 'us-east-1'
    }
    
    with open(config_path, 'w') as f:
        config.write(f)
    
    return config_path


@pytest.fixture
def mock_empty_aws_dir(tmp_path, monkeypatch):
    """Create an empty AWS directory (no files)."""
    aws_dir = tmp_path / '.aws'
    aws_dir.mkdir()
    
    # Mock Path.home() to return tmp_path
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    
    return aws_dir


@pytest.fixture
def mock_no_aws_dir(tmp_path, monkeypatch):
    """Mock home directory with no .aws directory."""
    # Mock Path.home() to return tmp_path (without creating .aws)
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    
    return tmp_path
