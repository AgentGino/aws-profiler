# AWS Profiler

A command-line tool to list all AWS profiles and check their credential status.

## Features

- 📋 Lists all AWS profiles from `~/.aws/credentials` and `~/.aws/config`
- 🔍 Retrieves account information for each profile
- ✅ Checks if credentials are active or expired
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

After installation, run the tool:

```bash
aws-profiler
```

The tool will scan your AWS configuration files and display a table with:

- Profile name
- Account ID
- User/Role name
- Credential type (User/Role)
- Status (Active/Expired/Error)

## Example Output

```
AWS Profiler
================================================================================

Found 3 profile(s)

Checking profile: default... [Active]
Checking profile: staging... [Active]
Checking profile: production... [Expired]

+-------------+--------------+------------+------+----------+
| Profile     | Account ID   | User/Role  | Type | Status   |
+=============+==============+============+======+==========+
| default     | 123456789012 | admin      | User | Active   |
+-------------+--------------+------------+------+----------+
| staging     | 234567890123 | dev-role   | Role | Active   |
+-------------+--------------+------------+------+----------+
| production  | N/A          | N/A        | N/A  | Expired  |
+-------------+--------------+------------+------+----------+

Summary: 2 active, 1 expired, 0 error/no credentials
```

## Status Values

- **Active**: Credentials are valid and working
- **Expired**: Token or credentials have expired
- **No Credentials**: Profile exists but no credentials are configured
- **Error**: Other authentication or authorization errors

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
