"""Command-line interface for AWS Profile Checker."""

import shutil
from tabulate import tabulate
from .checker import get_aws_profiles, get_account_info


def truncate_string(text, max_length):
    """Truncate string to max_length with ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def get_status_symbol(status):
    """Get colored symbol for status."""
    if status == 'Active':
        return '✓ Active'
    elif status == 'Expired':
        return '✗ Expired'
    elif status == 'No Credentials':
        return '⚠ No Creds'
    elif status.startswith('Error:'):
        return '✗ Invalid'
    else:
        return '✗ Invalid'


def main():
    """Main function to list all AWS profiles and their status."""
    # Get terminal width
    terminal_width = shutil.get_terminal_size().columns
    
    print("\n🔍 AWS Profile Status Checker")
    print("=" * min(80, terminal_width))
    print()
    
    # Get all profiles
    profiles = get_aws_profiles()
    
    if not profiles:
        print("❌ No AWS profiles found in ~/.aws/credentials or ~/.aws/config")
        return
    
    print(f"📋 Found {len(profiles)} profile(s)\n")
    
    # Collect information for all profiles
    results = []
    for profile in profiles:
        print(f"   Checking {profile}...", end=' ')
        info = get_account_info(profile)
        results.append(info)
        status_display = get_status_symbol(info['status'])
        print(f"[{status_display}]")
    
    print()
    
    # Prepare table data without truncation
    table_data = []
    for result in results:
        table_data.append([
            result['profile'],
            result['account_id'],
            result['user_name'],
            result['credential_type'],
            get_status_symbol(result['status'])
        ])
    
    # Print table with fancy grid
    headers = ['Profile', 'Account ID', 'User/Role', 'Type', 'Status']
    print(tabulate(table_data, headers=headers, tablefmt='fancy_grid'))
    
    # Summary with emojis
    print()
    active_count = sum(1 for r in results if r['status'] == 'Active')
    expired_count = sum(1 for r in results if r['status'] == 'Expired')
    error_count = len(results) - active_count - expired_count
    
    print(f"📊 Summary: ✓ {active_count} active  |  ✗ {expired_count} expired  |  ⚠ {error_count} error/no credentials\n")


if __name__ == '__main__':
    main()
