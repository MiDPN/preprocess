# README

The `preprocess.py` file will examine uploaded tar files for validity, make a manifest, add entry into titledb, and move files into production.

## Overview

This script is designed to automate the processing of archival units (AUs) for LOCKSS preservation. It performs validation, virus scanning, format identification, manifest generation, and metadata extraction for tar-based bag files.

### Key Features

- **File Validation**: Checks filename safety, file size limits, and tarball integrity
- **Virus Scanning**: Uses ClamAV to scan all uploaded files
- **Format Identification**: Uses DROID to identify and log file formats
- **Metadata Extraction**: Parses bag-info.txt and creates titledb entries
- **Manifest Generation**: Creates HTML manifests for LOCKSS crawling
- **Email Notifications**: Sends notifications to depositors with processing results and attachments
- **Email Debug Mode**: Test email notifications offline by saving to files
- **Comprehensive Logging**: Maintains CSV and HTML logs of all processing activity

## Requirements

### System Requirements

- **Python 3.x** (tested with Python 3.8+)
- **Java OpenJDK 21** - Required for DROID
  ```bash
  sudo apt install openjdk-21-jdk
  ```
- **ClamAV** - For virus scanning
  ```bash
  sudo apt install clamav clamav-daemon
  ```

### Python Dependencies

Install Python dependencies using:
```bash
pip install -r requirements.txt
```

### External Tools

#### DROID (Digital Record Object Identification)

also requires droid: https://tna-cdn-live-uk.s3.eu-west-2.amazonaws.com/documents/droid-binary-6.8.0-bin.zip

**Latest version (6.8.1)**: https://cdn.nationalarchives.gov.uk/documents/droid-binary-6.8.1-bin.zip

droid uses java openjdk version 21

droid needs to be updated periodically(daily?), create a cron job simular to the following: java -Xmx1024m -jar /PATH/TO/droid-command-line-6.8.0.jar -d

**Example cron job** (run daily at 2 AM):
```bash
0 2 * * * java -Xmx1024m -jar /path/to/droid-command-line-6.8.1.jar -d
```

## Installation and Setup

### 1. Clone or Download the Repository

Place the preprocess files in your desired location.

### 2. Install System Dependencies

```bash
# Install Java OpenJDK 21
sudo apt install openjdk-21-jdk

# Install ClamAV
sudo apt install clamav clamav-daemon

# Update ClamAV virus definitions
sudo freshclam

# Start ClamAV daemon (optional, for faster scanning)
sudo systemctl start clamav-daemon
sudo systemctl enable clamav-daemon
```

### 3. Install Python Dependencies

```bash
cd /path/to/preprocess
pip install -r requirements.txt
```

### 4. Download and Setup DROID

```bash
# Download DROID
wget https://cdn.nationalarchives.gov.uk/documents/droid-binary-6.8.1-bin.zip

# Extract DROID
unzip droid-binary-6.8.1-bin.zip -d DROID/

# Update DROID signature files
java -Xmx1024m -jar DROID/droid-command-line-6.8.1.jar -d
```

### 5. Create Directory Structure

Create the necessary directories for operation:

```bash
# Create source directory (where files are uploaded)
mkdir -p /path/to/uploads

# Create destination directory (staging area for LOCKSS)
mkdir -p /path/to/staging

# Create log directory
mkdir -p /path/to/logs
```

### 6. Configure the Application

## Configuration values

The default configuration keys are in `default-config.ini`. You will need to copy those into a local `config.ini` file and assign the values suited for your environment. Comments should be on different lines, and values should not use escape characters (no quotes)

```bash
# Copy default configuration
cp default-config.ini config.ini

# Edit configuration with your paths
vi config.ini
```

### Configuration Sections

#### [DEFAULT] Section

```ini
[DEFAULT]
# Directory where files are uploaded
source_dir = /home/sftpuser/uploads/

# Directory where processed files are staged for LOCKSS
destination_dir = /var/www/html/staging

# Path to titledb.xml file
titledb = /var/www/html/mdpn/titledb/titledb.xml

# LOCKSS crawlable URL for staging area
staging_url = http://192.168.60.130/staging/

# Path to CSV log file
logfile = /var/www/html/mdpn/log/log.csv

# Path to HTML log file
weblog = /var/www/html/mdpn/log/log.html

# Maximum AU size in bytes (example: 5000000000 = 50GB)
max_au_size = 5000000000
```

#### [DROID] Section

```ini
[DROID]
# Path to Java executable
java_path = /usr/lib/jvm/java-21-openjdk-amd64/bin/java

# Path to DROID command line jar
droid_path = /home/user1/droid/droid-command-line-6.8.1.jar

# Path to DROID CSV log
droid_log = /var/www/html/mdpn/log/droid_log.csv
```

#### [EMAIL] Section

```ini
[EMAIL]
# Enable or disable email notifications
enabled = true

# SMTP server hostname
smtp_host = smtp.example.com

# SMTP server port (587 for TLS, 465 for SSL, 25 for unencrypted)
smtp_port = 587

# SMTP authentication credentials
smtp_username = your_username
smtp_password = your_password

# Use TLS/STARTTLS (true) or SSL (false)
use_tls = true

# CC email addresses (comma-separated)
# Primary To: address comes from Contact-Email in bag-info.txt
cc_emails = admin@example.com,backup@example.com

# Debug mode - saves emails to files instead of sending them
debug_mode = false

# Directory where debug email files are saved
debug_output_dir = /path/to/email_debug
```

## Usage

### Running the Script

Execute the script manually:

```bash
python3 preprocess.py
```

The script will:
1. Scan the `source_dir` for .tar files
2. Validate each file (filename, size, virus scan)
3. Extract and parse bag-info.txt and manifest
4. Generate HTML manifests
5. Run DROID format identification
6. Move files to staging area
7. Update titledb.xml
8. Send email notifications
9. Log all activities

### Running as a Cron Job

To run automatically, add to crontab:

```bash
# Edit crontab
crontab -e

# Add entry to run every hour
0 * * * * /usr/bin/python3 /path/to/preprocess/preprocess.py >> /path/to/preprocess/preprocess.log 2>&1
```

## Email Notifications

The script sends email notifications after processing each archival unit:

- **To**: Contact-Email from the AU's bag-info.txt
- **CC**: Addresses specified in config.ini
- **Subject**: "AU Processing Complete" or "AU Processing Failed"
- **Attachments**: bag-info.txt, clamav.txt, droid_report.csv

Email notifications can be disabled by setting `enabled = false` in the [EMAIL] section of config.ini.

### Debug Mode

For testing and development purposes, email notifications can be saved to local files instead of being sent via SMTP:

1. Set `debug_mode = true` in the [EMAIL] section of config.ini
2. Set `debug_output_dir` to your desired output directory
3. Run the script normally

When debug mode is enabled:
- Emails are saved as text files instead of being sent
- No SMTP configuration is required
- Files are named: `email_{au_name}_{timestamp}.txt`
- Each file contains full email details: headers, body, and attachment information

**Example debug output:**
```
================================================================================
EMAIL DEBUG OUTPUT
================================================================================

From: do_not_reply@mipres.org
To: depositor@university.edu
Cc: admin@example.com
Subject: AU Processing Complete
Date: Thu, 06 Nov 2025 14:30:45

Recipient list: depositor@university.edu, admin@example.com

--------------------------------------------------------------------------------
MESSAGE BODY:
--------------------------------------------------------------------------------

AU processing is complete for example-au-name

--------------------------------------------------------------------------------
ATTACHMENTS:
--------------------------------------------------------------------------------
  - bag-info.txt (2048 bytes)
  - clamav.txt (512 bytes)
  - droid_report.csv (10240 bytes)

================================================================================
END OF EMAIL DEBUG OUTPUT
================================================================================
```

This is useful for:
- Testing email notifications without SMTP credentials
- Verifying email content before production use
- Troubleshooting email formatting issues
- Offline development and testing

## File Processing Workflow

1. **Validation Checks**:
   - Web-safe filename (alphanumeric, hyphens, underscores only)
   - File size within limits (0 < size < max_au_size)
   - ClamAV virus scan passes

2. **Extraction**:
   - Extract bag-info.txt
   - Extract manifest-sha256.txt
   - Parse bag-info fields into dictionary

3. **Processing**:
   - Generate HTML manifest with LOCKSS permission statement
   - Move files into AU folder structure
   - Run DROID format identification

4. **Finalization**:
   - Move AU folder to staging area
   - Insert entry into titledb.xml
   - Update CSV and HTML logs
   - Send email notification

5. **Error Handling**:
   - Files failing validation are deleted
   - Processing errors are logged
   - Email failures don't interrupt processing

## Logging

The script maintains several log files:

- **CSV Log** (`logfile`): Machine-readable log with date, package name, organization, identifier, size, status, and LOCKSS AU ID
- **HTML Log** (`weblog`): Web-viewable version of CSV log
- **DROID Log** (`droid_log`): Detailed format identification data for all files processed

## Testing and Validation

The `scripts/validate_staging.py` script provides comprehensive validation of processed archival units to ensure production readiness.

### What It Validates

**Staging Directory:**
- All required files present (tarball, bag-info.txt, clamav.txt, droid_report.csv)
- All files are non-zero bytes
- Optional files checked with warnings (manifest.html)

**titledb.xml:**
- Valid XML structure
- Correct number of AU entries matches staging
- All required fields present for each AU
- Parameter structures validated (base_url, directory)

### Running Validation

```bash
# Validate using config.ini settings
python3 scripts/validate_staging.py

# Validate specific directory
python3 scripts/validate_staging.py /path/to/staging

# Make executable and run
chmod +x scripts/validate_staging.py
./scripts/validate_staging.py
```

### Output

The validation script provides:
- Color-coded terminal output (✓ success, ✗ errors, ⚠ warnings)
- File-by-file validation with sizes
- Summary statistics
- JSON report saved to `scripts/validation_report.json`
- Exit code 0 for success, 1 for errors (CI/CD compatible)

### Integration Example

```bash
#!/bin/bash
# Process and validate
python3 preprocess.py
python3 scripts/validate_staging.py

if [ $? -eq 0 ]; then
    echo "Validation passed - ready for production"
else
    echo "Validation failed - review errors"
    exit 1
fi
```

See [scripts/README.md](scripts/README.md) for complete validation documentation.

## Troubleshooting

### ClamAV Issues

```bash
# Update virus definitions
sudo freshclam

# Check ClamAV status
clamscan --version

# Test scanning
clamscan /path/to/test/file
```

### DROID Issues

```bash
# Update DROID signatures
java -Xmx1024m -jar /path/to/droid-command-line-6.8.1.jar -d

# Test DROID
java -Xmx1024m -jar /path/to/droid-command-line-6.8.1.jar -R -A /path/to/test/folder
```

### Email Issues

- Verify SMTP settings are correct
- Check firewall rules for SMTP ports
- Test SMTP authentication separately
- Review logs for specific error messages
- Email failures won't stop processing - check warnings in output
- **Use debug mode to test without SMTP**: Set `debug_mode = true` in config.ini to save emails to files for testing

### Permission Issues

Ensure the script has:
- Read access to source_dir
- Write access to destination_dir
- Write access to log files
- Write access to titledb.xml

### File Processing Errors

Common issues:
- **Invalid filename**: Use only alphanumeric, hyphens, and underscores
- **File too large**: Check max_au_size setting
- **Corrupted tarball**: Verify tar file integrity before upload
- **Missing bag-info.txt**: Ensure proper bag structure
- **Missing Contact-Email**: Add Contact-Email field to bag-info.txt

## Security Considerations

- All uploaded files are scanned with ClamAV
- Files with viruses are automatically deleted
- File size limits prevent resource exhaustion
- Filename validation prevents path traversal attacks
- SMTP credentials should be kept secure
- Consider using app-specific passwords for email
- Run script with minimal necessary permissions

## Version History

- **v0.9** (November 2025):
  - Added email notifications with Contact-Email routing
  - Email debug mode for offline testing
  - Improved bag-info.txt parsing with dictionary-based approach
  - Enhanced error handling for email failures
  - Added CC support for email notifications
- **v0.8** (April 2025): Updated to DROID 6.8.1, improved error handling

## License

CC0 - Openly shared into the public domain on behalf of MDPN

## Support

For issues or questions, refer to the script comments or contact the MDPN technical team.