# AWS Profiler

A command-line tool to list all AWS profiles, check their credential status, and refresh IAM user access keys.

## Features

- 📋 Lists all AWS profiles from `~/.aws/credentials` and `~/.aws/config`
- 🔍 Retrieves account information for each profile
- ✅ Checks if credentials are active or expired
- ⏱️ Shows credential age and expiration time
- 🔄 Automatically refreshes IAM user access keys
- 💾 Backs up old credentials before rotation
- 🗑️ Optionally deletes old keys from AWS
- 📊 Displays results in a formatted table
- 📈 Provides summary statistics

## Installation

### Install from source

```bash
pip install -e .
```

### Install from PyPI (when published)

```bash
pip install aws-profiler
```

## Usage

### List all profiles and check status

```bash
aws-profiler
```

The tool will scan your AWS configuration files and display a table with:

- Profile name
- Account ID
- User/Role name
- Credential type (User/Role)
- Status (Active/Expired/Error)
- Credential age (how old the credentials are)
- Expiration time (for temporary credentials)

### Refresh specific profile

Refresh credentials for a specific IAM user or SSO profile:

```bash
aws-profiler --refresh myprofile
```

**For IAM Users**, this will:
1. Verify the profile is an IAM user (not a role)
2. Create a new access key
3. Backup the old credentials to `~/.aws/backups/`
4. Update the credentials file with the new key
5. Keep the old key active in AWS (unless `--delete` is used)

**For SSO Profiles**, this will:
1. Detect the profile is SSO-configured
2. Run `aws sso login --profile <name>` 
3. Open your browser for authentication
4. Complete the SSO flow through AWS CLI

### Refresh and delete old key (IAM users only)

To also delete the old access key from AWS after creating the new one:

```bash
aws-profiler --refresh myprofile --delete
```

⚠️ **Warning**: This will permanently delete the old access key from AWS. You'll be prompted for confirmation.

### Refresh all eligible profiles

Automatically refresh credentials for ALL IAM users and SSO profiles:

```bash
aws-profiler --refresh --all
```

Or simply:

```bash
aws-profiler --refresh
```

This will:
1. Scan all profiles and identify eligible ones (IAM users and SSO)
2. Show summary of what will be refreshed
3. Ask for confirmation
4. Refresh all IAM user keys (with backups)
5. Trigger SSO login for all SSO profiles

To also delete old keys from AWS for all IAM users:

```bash
aws-profiler --refresh --all --delete
```

## Example Output

### Listing profiles

```
🔍 AWS Profile Status Checker
================================================================================

📋 Found 3 profile(s)

   Checking default... [✓ Active]
   Checking staging... [✓ Active]
   Checking production... [✗ Expired]

╒═════════════╤══════════════╤════════════╤════════╤═══════════╤═══════╤════════════╕
│ Profile     │ Account ID   │ User/Role  │ Type   │ Status    │ Age   │ Expires In │
╞═════════════╪══════════════╪════════════╪════════╪═══════════╪═══════╪════════════╡
│ default     │ 123456789012 │ admin      │ User   │ ✓ Active  │ 15d 3h│ Permanent  │
├─────────────┼──────────────┼────────────┼────────┼───────────┼───────┼────────────┤
│ staging     │ 234567890123 │ dev-role   │ Role   │ ✓ Active  │ 2h    │ 10h 45m    │
├─────────────┼──────────────┼────────────┼────────┼───────────┼───────┼────────────┤
│ production  │ N/A          │ N/A        │ N/A    │ ✗ Expired │ N/A   │ Expired    │
╘═════════════╧══════════════╧════════════╧════════╧═══════════╧═══════╧════════════╛

📊 Summary: ✓ 2 active  |  ✗ 1 expired  |  ⚠ 0 error/no credentials
```

### Refreshing a single IAM user

```
🔄 AWS Credential Refresh
================================================================================

🔑 Refreshing credentials for profile: myprofile

✅ Success!
✓ Credentials refreshed successfully for profile "myprofile"
  New Key: AKIAIOSFODNN7EXAMPLE
  Backup: /Users/username/.aws/backups/credentials_backup_myprofile_DEXAMPLE_20251124_143022
  Old key AKIAIOSFODNN6EXAMPLE is still active in AWS. Use --delete to remove it.
```

### Refreshing an SSO profile

```
🔄 AWS Credential Refresh
================================================================================

🔑 Refreshing credentials for profile: sso-dev
🔐 Initiating SSO login for profile: sso-dev
   Please follow the instructions in your browser...

Attempting to automatically open the SSO authorization page in your default browser.
If the browser does not open or you wish to use a different device to authorize this request, open the following URL:

https://device.sso.us-east-1.amazonaws.com/

Then enter the code: ABCD-EFGH

✅ Success!
✓ SSO login successful for profile "sso-dev"
```

### Refreshing all profiles

```
🔄 AWS Credential Refresh - ALL PROFILES
================================================================================

📋 Analyzing profiles...

   IAM Users (can refresh):    2
   SSO Profiles (can refresh): 1
   Roles (cannot refresh):     1
   Inactive/Error profiles:    0

   Will refresh 2 IAM user(s) and 1 SSO profile(s)
   Type 'yes' to continue: yes

================================================================================

🔑 Refreshing IAM User Profiles:

   → dev-user...
      ✓ Success

   → prod-user...
      ✓ Success

🔐 Refreshing SSO Profiles:

   → sso-dev...
      [SSO login flow continues...]
      ✓ Success

================================================================================

📊 Summary: ✓ 3 refreshed  |  ✗ 0 failed
```

## Status Values

- **✓ Active**: Credentials are valid and working
- **✗ Expired**: Token or credentials have expired
- **⚠ No Creds**: Profile exists but no credentials are configured
- **✗ Invalid**: Other authentication or authorization errors

## Credential Types

- **User**: IAM user with permanent access keys (can be refreshed)
- **Role**: Assumed role with temporary credentials (cannot be refreshed)

## Backup Files

When refreshing credentials, the old credentials are automatically backed up to:
```
~/.aws/backups/credentials_backup_<profile>_<key-suffix>_<timestamp>
```

Backup files are created with restricted permissions (600) for security.

## Requirements

- Python 3.8+
- AWS credentials configured in `~/.aws/credentials` or `~/.aws/config`
- For refresh functionality: IAM permissions to create and optionally delete access keys

## IAM Permissions Required for Refresh

To use the refresh functionality, your IAM user needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateAccessKey",
        "iam:ListAccessKeys",
        "iam:DeleteAccessKey"
      ],
      "Resource": "arn:aws:iam::*:user/${aws:username}"
    }
  ]
}
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
