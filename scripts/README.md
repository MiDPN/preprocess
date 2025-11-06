# Scripts Directory

This directory contains utility scripts for testing and validating the MDPN preprocess system.

## Available Scripts

### validate_staging.py

Comprehensive validation script for processed archival units in the staging directory.

**Purpose:**
- Validates that all AUs have required files
- Checks that all files are not empty (non-zero bytes)
- Generates detailed reports on validation status
- Saves JSON report for automated processing

**Required Files Checked:**
- `{au_name}.tar` - Original tarball
- `bag-info.txt` - Bag metadata
- `clamav.txt` - Virus scan results
- `droid_report.csv` - Format identification report

**Optional Files Checked:**
- `manifest.html` - LOCKSS manifest (warning if missing)

**titledb.xml Validation:**
- Validates XML structure and parsing
- Checks that all AUs in staging have corresponding entries
- Verifies all required fields are present:
  - `attributes.publisher`
  - `journalTitle`
  - `title`
  - `type`
  - `plugin`
  - `param.1` (with base_url configuration)
  - `param.2` (with directory configuration)
- Validates parameter structures and values

**Usage:**

```bash
# Validate using staging directory from config.ini
python3 validate_staging.py

# Validate a specific directory
python3 validate_staging.py /path/to/staging

# Make executable and run directly
chmod +x validate_staging.py
./validate_staging.py
```

**Output:**

The script provides:
- Color-coded terminal output (✓ for success, ✗ for errors, ⚠ for warnings)
- File-by-file validation with sizes
- Summary statistics
- JSON report saved to `validation_report.json`

**Exit Codes:**
- `0` - All AUs valid or no AUs found
- `1` - One or more AUs have validation errors

**Example Output:**

```
================================================================================
Validating Staging Directory: /var/www/html/staging
================================================================================
ℹ Found 3 potential archival unit(s)

Validating AU: example-au-2024
--------------------------------------------------------------------------------
✓ AU 'example-au-2024' is valid

  Files:
    ✓ tarball              125.43 MB
    ✓ bag-info.txt           2.05 KB
    ✓ clamav.txt             0.51 KB
    ✓ droid_report.csv      10.24 KB
    ✓ manifest.html          3.12 KB

================================================================================
Validation Summary
================================================================================
Total AUs:   3
Valid AUs:   3
Invalid AUs: 0

✓ All archival units are valid!

================================================================================
Validating titledb.xml: /var/www/html/mdpn/titledb/titledb.xml
================================================================================
✓ titledb.xml is valid XML

Expected entries: 3
Found entries:    3
✓ All AUs found in titledb.xml

✓ AU 'example-au-2024' - all required fields present
✓ AU 'example-au-2025' - all required fields present
✓ AU 'example-au-2026' - all required fields present

================================================================================
Overall Validation Result
================================================================================
✓ ✓ All validations passed!
✓ Validation report saved to: validation_report.json
```

### check_config.py

Validates the configuration file (`config.ini`) to ensure all required settings are present and paths exist.

**Usage:**
```bash
python3 check_config.py
```

### reset_after_test.py

Cleans up test data and resets the environment after testing.

**Usage:**
```bash
python3 reset_after_test.py
```

**Warning:** This script may delete data. Use with caution and only in test environments.

## Integration with CI/CD

The `validate_staging.py` script can be integrated into automated testing pipelines:

```bash
#!/bin/bash
# Run preprocess
python3 preprocess.py

# Validate results
python3 scripts/validate_staging.py

# Check exit code
if [ $? -eq 0 ]; then
    echo "Validation passed"
else
    echo "Validation failed"
    exit 1
fi
```

## JSON Report Format

The validation report is saved as `validation_report.json` with the following structure:

```json
{
  "staging_dir": "/path/to/staging",
  "total_aus": 3,
  "valid_aus": 3,
  "invalid_aus": 0,
  "timestamp": "2025-11-06T14:30:45.123456",
  "return_code": 0,
  "aus": [
    {
      "au_name": "example-au-2024",
      "path": "/path/to/staging/example-au-2024",
      "valid": true,
      "errors": [],
      "warnings": [],
      "files": {
        "tarball": {
          "path": "/path/to/staging/example-au-2024/example-au-2024.tar",
          "exists": true,
          "size": 131457280,
          "valid": true
        },
        "bag-info.txt": {
          "path": "/path/to/staging/example-au-2024/bag-info.txt",
          "exists": true,
          "size": 2099,
          "valid": true
        }
      }
    }
  ],
  "titledb": {
    "titledb_path": "/path/to/titledb.xml",
    "exists": true,
    "valid_xml": true,
    "total_entries": 3,
    "expected_entries": 3,
    "matching_entries": 3,
    "missing_aus": [],
    "entries": {
      "example-au-2024": {
        "found": true,
        "valid": true,
        "missing_fields": [],
        "present_fields": [
          "attributes.publisher",
          "journalTitle",
          "title",
          "type",
          "plugin",
          "param.1",
          "param.2"
        ]
      }
    },
    "errors": [],
    "warnings": []
  }
}
```

## Troubleshooting

### Script not executable

```bash
chmod +x validate_staging.py
```

### Config.ini not found

Ensure you're running the script from the correct location or specify the staging directory:

```bash
python3 validate_staging.py /path/to/staging
```

### Colors not displaying

If colors aren't showing in your terminal, the script will still work but without color formatting. This is common in some CI/CD environments.

### titledb.xml validation errors

**Missing AUs in titledb:**
- Check that preprocess.py completed successfully for all files
- Review preprocess.py logs for errors during titledb insertion
- Verify titledb.xml has write permissions

**XML parsing errors:**
- titledb.xml may be corrupted
- Check for backup files (titledb.xml_YYYYMMDD-HHMMSS)
- Restore from a recent backup or regenerate

**Missing required fields:**
- Indicates incomplete AU entry in titledb
- May require manual correction of titledb.xml
- Or reprocess the affected AU

**Parameter structure warnings:**
- Check that base_url in param.1 matches staging_url in config
- Verify directory in param.2 matches AU name
- These are usually configuration issues, not critical errors

## Contributing

When adding new validation checks:

1. Add the check to `validate_au_directory()` function
2. Update the `required_files` or `optional_files` dictionaries
3. Add appropriate error or warning messages
4. Update this README with the new checks
