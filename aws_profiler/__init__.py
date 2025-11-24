"""AWS Profile Checker - A CLI tool to check AWS profile credentials status."""

__version__ = "1.0.0"
__author__ = "AgentGino"
__email__ = "himakar@qwik.tools"

from .checker import get_aws_profiles, get_account_info

__all__ = ["get_aws_profiles", "get_account_info"]
