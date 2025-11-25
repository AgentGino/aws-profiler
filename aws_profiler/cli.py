"""Command-line interface for AWS Profile Checker."""

import sys
import argparse
import shutil
from tabulate import tabulate
from .checker import get_aws_profiles, get_account_info, refresh_credentials, is_sso_profile


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


def list_profiles():
    """List all AWS profiles and their status."""
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
            get_status_symbol(result['status']),
            result.get('credential_age', 'N/A'),
            result.get('expires_in', 'N/A')
        ])
    
    # Print table with fancy grid
    headers = ['Profile', 'Account ID', 'User/Role', 'Type', 'Status', 'Age', 'Expires In']
    print(tabulate(table_data, headers=headers, tablefmt='fancy_grid'))
    
    # Summary with emojis
    print()
    active_count = sum(1 for r in results if r['status'] == 'Active')
    expired_count = sum(1 for r in results if r['status'] == 'Expired')
    error_count = len(results) - active_count - expired_count
    
    print(f"📊 Summary: ✓ {active_count} active  |  ✗ {expired_count} expired  |  ⚠ {error_count} error/no credentials\n")


def refresh_profile(profile_name, delete_old=False):
    """Refresh credentials for a specific profile."""
    terminal_width = shutil.get_terminal_size().columns
    
    print("\n🔄 AWS Credential Refresh")
    print("=" * min(80, terminal_width))
    print()
    
    # Check if it's SSO - no delete option for SSO
    if is_sso_profile(profile_name):
        if delete_old:
            print("⚠️  Note: --delete flag is ignored for SSO profiles")
            print()
    elif delete_old:
        print("⚠️  Warning: Old access key will be DELETED from AWS after creating new one!")
        confirmation = input("   Type 'yes' to continue: ").strip().lower()
        if confirmation != 'yes':
            print("❌ Operation cancelled.")
            return 1
        print()
    
    print(f"🔑 Refreshing credentials for profile: {profile_name}")
    print()
    
    result = refresh_credentials(profile_name, delete_old=delete_old)
    
    if result['success']:
        print("✅ Success!")
        print(result['message'])
        print()
        return 0
    else:
        print("❌ Failed!")
        print(result['message'])
        print()
        return 1


def refresh_all_profiles(delete_old=False):
    """Refresh credentials for all eligible profiles."""
    terminal_width = shutil.get_terminal_size().columns
    
    print("\n🔄 AWS Credential Refresh - ALL PROFILES")
    print("=" * min(80, terminal_width))
    print()
    
    # Get all profiles
    profiles = get_aws_profiles()
    
    if not profiles:
        print("❌ No AWS profiles found in ~/.aws/credentials or ~/.aws/config")
        return 1
    
    # Check each profile to see if it's eligible for refresh
    print("📋 Analyzing profiles...\n")
    
    iam_users = []
    sso_profiles = []
    roles = []
    errors = []
    
    for profile in profiles:
        info = get_account_info(profile)
        if info['status'] == 'Active':
            if is_sso_profile(profile):
                sso_profiles.append(profile)
            elif info['credential_type'] == 'User':
                iam_users.append(profile)
            elif info['credential_type'] == 'Role':
                roles.append(profile)
        else:
            errors.append(profile)
    
    # Display what was found
    print(f"   IAM Users (can refresh):    {len(iam_users)}")
    print(f"   SSO Profiles (can refresh): {len(sso_profiles)}")
    print(f"   Roles (cannot refresh):     {len(roles)}")
    print(f"   Inactive/Error profiles:    {len(errors)}")
    print()
    
    if not iam_users and not sso_profiles:
        print("❌ No eligible profiles found for refresh")
        if roles:
            print("   Note: Role-based profiles cannot be refreshed automatically")
        return 1
    
    # Confirm with user
    if delete_old and iam_users:
        print("⚠️  WARNING: Old access keys will be DELETED from AWS for IAM users!")
    
    print(f"   Will refresh {len(iam_users)} IAM user(s) and {len(sso_profiles)} SSO profile(s)")
    confirmation = input("   Type 'yes' to continue: ").strip().lower()
    
    if confirmation != 'yes':
        print("❌ Operation cancelled.")
        return 1
    
    print()
    print("=" * min(80, terminal_width))
    
    # Refresh IAM users
    success_count = 0
    fail_count = 0
    
    if iam_users:
        print("\n🔑 Refreshing IAM User Profiles:\n")
        for profile in iam_users:
            print(f"   → {profile}...")
            result = refresh_credentials(profile, delete_old=delete_old)
            if result['success']:
                print(f"      ✓ Success")
                success_count += 1
            else:
                print(f"      ✗ Failed: {result['message']}")
                fail_count += 1
            print()
    
    # Refresh SSO profiles
    if sso_profiles:
        print("\n🔐 Refreshing SSO Profiles:\n")
        for profile in sso_profiles:
            print(f"   → {profile}...")
            result = refresh_credentials(profile, delete_old=False)
            if result['success']:
                print(f"      ✓ Success")
                success_count += 1
            else:
                print(f"      ✗ Failed: {result['message']}")
                fail_count += 1
            print()
    
    # Summary
    print("=" * min(80, terminal_width))
    print(f"\n📊 Summary: ✓ {success_count} refreshed  |  ✗ {fail_count} failed\n")
    
    return 0 if fail_count == 0 else 1


def main():
    """Main function to parse arguments and route to appropriate command."""
    parser = argparse.ArgumentParser(
        description='AWS Profile Status Checker and Credential Refresher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aws-profiler                              # List all profiles and their status
  aws-profiler --refresh myprofile          # Refresh credentials for 'myprofile'
  aws-profiler --refresh myprofile --delete # Refresh and delete old key from AWS
  aws-profiler --refresh --all              # Refresh all IAM users and SSO profiles
  aws-profiler --refresh --all --delete     # Refresh all and delete old keys
        """
    )
    
    parser.add_argument(
        '--refresh',
        nargs='?',
        const='__flag_only__',
        metavar='PROFILE',
        help='Refresh credentials for the specified profile (IAM users and SSO)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Refresh all eligible profiles (use with --refresh)'
    )
    
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Delete old access key from AWS after creating new one (use with --refresh)'
    )
    
    args = parser.parse_args()
    
    # Route to appropriate command
    if args.refresh:
        if args.all or args.refresh == '__flag_only__':
            # Refresh all profiles
            return refresh_all_profiles(delete_old=args.delete)
        else:
            # Refresh specific profile
            return refresh_profile(args.refresh, delete_old=args.delete)
    else:
        if args.delete:
            print("❌ Error: --delete can only be used with --refresh")
            return 1
        if args.all:
            print("❌ Error: --all can only be used with --refresh")
            return 1
        list_profiles()
        return 0


if __name__ == '__main__':
    main()
