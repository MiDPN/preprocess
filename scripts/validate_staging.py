#!/usr/bin/env python3
"""
validate_staging.py - Comprehensive validation script for processed archival units

This script validates that all archival units in the staging directory have been
properly processed and contain all required files with valid content.

Usage:
    python3 validate_staging.py [staging_directory]

If staging_directory is not provided, it reads from config.ini

Author: Generated for MDPN preprocess validation
"""

import os
import sys
import configparser
from pathlib import Path
import json
from datetime import datetime
import xml.etree.ElementTree as ET

# ANSI color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(msg):
    """Print success message in green"""
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    """Print error message in red"""
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_warning(msg):
    """Print warning message in yellow"""
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def print_info(msg):
    """Print info message in blue"""
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_header(msg):
    """Print header message"""
    print(f"\n{Colors.BOLD}{msg}{Colors.END}")
    print("=" * 80)

def load_config():
    """Load configuration from config.ini"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
    if not os.path.exists(config_path):
        print_error(f"Configuration file not found: {config_path}")
        return None

    config = configparser.ConfigParser()
    config.read(config_path)
    return config

def validate_file(file_path, file_type, au_name):
    """
    Validate that a file exists and is not empty

    Args:
        file_path: Path to the file
        file_type: Type of file for error messages
        au_name: Name of the archival unit

    Returns:
        tuple: (is_valid, error_message, file_size)
    """
    if not os.path.exists(file_path):
        return False, f"Missing {file_type}", 0

    if not os.path.isfile(file_path):
        return False, f"{file_type} is not a regular file", 0

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return False, f"{file_type} is empty (0 bytes)", 0

    return True, None, file_size

def validate_au_directory(au_path, au_name):
    """
    Validate a single archival unit directory

    Args:
        au_path: Path to the AU directory
        au_name: Name of the AU

    Returns:
        dict: Validation results
    """
    results = {
        'au_name': au_name,
        'path': au_path,
        'valid': True,
        'errors': [],
        'warnings': [],
        'files': {}
    }

    # Required files to check
    required_files = {
        'tarball': f"{au_name}.tar",
        'bag-info.txt': 'bag-info.txt',
        'clamav.txt': 'clamav.txt',
        'droid_report.csv': 'droid_report.csv'
    }

    # Optional files that should be present
    optional_files = {
        'manifest.html': 'manifest.html'
    }

    # Validate required files
    for file_type, filename in required_files.items():
        file_path = os.path.join(au_path, filename)
        is_valid, error_msg, file_size = validate_file(file_path, file_type, au_name)

        results['files'][file_type] = {
            'path': file_path,
            'exists': os.path.exists(file_path),
            'size': file_size,
            'valid': is_valid
        }

        if not is_valid:
            results['valid'] = False
            results['errors'].append(error_msg)

    # Check optional files (warnings only)
    for file_type, filename in optional_files.items():
        file_path = os.path.join(au_path, filename)
        is_valid, error_msg, file_size = validate_file(file_path, file_type, au_name)

        results['files'][file_type] = {
            'path': file_path,
            'exists': os.path.exists(file_path),
            'size': file_size,
            'valid': is_valid
        }

        if not is_valid:
            results['warnings'].append(f"Optional file missing or empty: {file_type}")

    return results

def format_size(size_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def validate_staging_directory(staging_dir, verbose=True):
    """
    Validate all AU directories in the staging directory

    Args:
        staging_dir: Path to staging directory
        verbose: Whether to print detailed output

    Returns:
        dict: Overall validation results
    """
    if not os.path.exists(staging_dir):
        print_error(f"Staging directory does not exist: {staging_dir}")
        return None

    if not os.path.isdir(staging_dir):
        print_error(f"Staging path is not a directory: {staging_dir}")
        return None

    print_header(f"Validating Staging Directory: {staging_dir}")

    # Find all subdirectories (potential AUs)
    au_dirs = []
    for item in os.listdir(staging_dir):
        item_path = os.path.join(staging_dir, item)
        if os.path.isdir(item_path):
            au_dirs.append((item, item_path))

    if not au_dirs:
        print_warning("No archival unit directories found in staging directory")
        return {
            'staging_dir': staging_dir,
            'total_aus': 0,
            'valid_aus': 0,
            'invalid_aus': 0,
            'aus': []
        }

    print_info(f"Found {len(au_dirs)} potential archival unit(s)")
    print()

    # Validate each AU
    all_results = []
    valid_count = 0
    invalid_count = 0

    for au_name, au_path in sorted(au_dirs):
        if verbose:
            print(f"\n{Colors.BOLD}Validating AU: {au_name}{Colors.END}")
            print("-" * 80)

        results = validate_au_directory(au_path, au_name)
        all_results.append(results)

        if results['valid']:
            valid_count += 1
            if verbose:
                print_success(f"AU '{au_name}' is valid")
        else:
            invalid_count += 1
            if verbose:
                print_error(f"AU '{au_name}' has errors:")
                for error in results['errors']:
                    print(f"  • {error}")

        # Display file information
        if verbose:
            print(f"\n  Files:")
            for file_type, file_info in results['files'].items():
                status = "✓" if file_info['valid'] else "✗"
                color = Colors.GREEN if file_info['valid'] else Colors.RED
                size_str = format_size(file_info['size']) if file_info['exists'] else "N/A"
                print(f"    {color}{status}{Colors.END} {file_type:20s} {size_str:>12s}")

        # Display warnings
        if verbose and results['warnings']:
            print(f"\n  {Colors.YELLOW}Warnings:{Colors.END}")
            for warning in results['warnings']:
                print(f"    • {warning}")

    # Summary
    overall_results = {
        'staging_dir': staging_dir,
        'total_aus': len(au_dirs),
        'valid_aus': valid_count,
        'invalid_aus': invalid_count,
        'aus': all_results,
        'timestamp': datetime.now().isoformat()
    }

    print_header("Validation Summary")
    print(f"Total AUs:   {overall_results['total_aus']}")
    print(f"{Colors.GREEN}Valid AUs:   {overall_results['valid_aus']}{Colors.END}")
    if invalid_count > 0:
        print(f"{Colors.RED}Invalid AUs: {overall_results['invalid_aus']}{Colors.END}")
    else:
        print(f"Invalid AUs: {overall_results['invalid_aus']}")
    print()

    if overall_results['valid_aus'] == overall_results['total_aus'] and overall_results['total_aus'] > 0:
        print_success("All archival units are valid!")
        return_code = 0
    elif invalid_count > 0:
        print_error(f"{invalid_count} archival unit(s) have validation errors")
        return_code = 1
    else:
        print_warning("No archival units found to validate")
        return_code = 0

    overall_results['return_code'] = return_code
    return overall_results

def validate_titledb(titledb_path, au_names):
    """
    Validate titledb.xml file

    Args:
        titledb_path: Path to titledb.xml
        au_names: List of AU names that should be in titledb

    Returns:
        dict: Validation results
    """
    results = {
        'titledb_path': titledb_path,
        'exists': False,
        'valid_xml': False,
        'total_entries': 0,
        'expected_entries': len(au_names),
        'matching_entries': 0,
        'missing_aus': [],
        'entries': {},
        'errors': [],
        'warnings': []
    }

    # Check if titledb exists
    if not os.path.exists(titledb_path):
        results['errors'].append(f"titledb.xml not found at: {titledb_path}")
        return results

    results['exists'] = True

    # Try to parse XML
    try:
        tree = ET.parse(titledb_path)
        root = tree.getroot()
        results['valid_xml'] = True
    except ET.ParseError as e:
        results['errors'].append(f"XML parsing error: {e}")
        return results
    except Exception as e:
        results['errors'].append(f"Error reading titledb.xml: {e}")
        return results

    # Find all AU entries (properties with name attributes that match AU names)
    # titledb structure: root > property elements where property.name is the AU name
    au_properties = {}

    # Get all property elements
    for prop in root.findall('.//property'):
        prop_name = prop.get('name')
        if prop_name and prop_name in au_names:
            au_properties[prop_name] = prop

    results['total_entries'] = len(au_properties)
    results['matching_entries'] = len(au_properties)

    # Required fields for each AU entry
    required_fields = [
        'attributes.publisher',
        'journalTitle',
        'title',
        'type',
        'plugin',
        'param.1',
        'param.2'
    ]

    # Validate each AU entry
    for au_name in au_names:
        au_result = {
            'found': False,
            'valid': True,
            'missing_fields': [],
            'present_fields': []
        }

        if au_name not in au_properties:
            results['missing_aus'].append(au_name)
            au_result['valid'] = False
            results['errors'].append(f"AU '{au_name}' not found in titledb.xml")
        else:
            au_result['found'] = True
            au_prop = au_properties[au_name]

            # Check for required fields (sub-properties)
            found_fields = set()
            for sub_prop in au_prop.findall('property'):
                field_name = sub_prop.get('name')
                if field_name:
                    found_fields.add(field_name)
                    au_result['present_fields'].append(field_name)

            # Check for missing required fields
            for required_field in required_fields:
                if required_field not in found_fields:
                    au_result['missing_fields'].append(required_field)
                    au_result['valid'] = False
                    results['errors'].append(f"AU '{au_name}' missing required field: {required_field}")

            # Validate param.1 has correct sub-properties
            param1 = au_prop.find("property[@name='param.1']")
            if param1 is not None:
                param1_props = {p.get('name'): p.get('value') for p in param1.findall('property')}
                if 'key' not in param1_props or param1_props.get('key') != 'base_url':
                    results['warnings'].append(f"AU '{au_name}' param.1 may not have correct structure")
                if 'value' not in param1_props or not param1_props.get('value'):
                    results['warnings'].append(f"AU '{au_name}' param.1 missing value")

            # Validate param.2 has correct sub-properties
            param2 = au_prop.find("property[@name='param.2']")
            if param2 is not None:
                param2_props = {p.get('name'): p.get('value') for p in param2.findall('property')}
                if 'key' not in param2_props or param2_props.get('key') != 'directory':
                    results['warnings'].append(f"AU '{au_name}' param.2 may not have correct structure")
                if 'value' not in param2_props or param2_props.get('value') != au_name:
                    results['warnings'].append(f"AU '{au_name}' param.2 value should match AU name")

        results['entries'][au_name] = au_result

    return results

def save_report(results, output_file):
    """Save validation results to JSON file"""
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print_success(f"Validation report saved to: {output_file}")
    except Exception as e:
        print_error(f"Failed to save report: {e}")

def main():
    """Main entry point"""
    print_header("MDPN Staging Directory Validation Tool")

    # Load config
    config = load_config()
    if not config:
        print_error("Failed to load config.ini")
        sys.exit(1)

    # Determine staging directory
    staging_dir = None
    if len(sys.argv) > 1:
        staging_dir = sys.argv[1]
    else:
        # Try to load from config
        if config.has_option('DEFAULT', 'destination_dir'):
            staging_dir = config['DEFAULT']['destination_dir']
            print_info(f"Using staging directory from config.ini: {staging_dir}")
        else:
            print_error("No staging directory specified and config.ini not found")
            print(f"\nUsage: {sys.argv[0]} [staging_directory]")
            sys.exit(1)

    # Run staging directory validation
    results = validate_staging_directory(staging_dir, verbose=True)

    if results is None:
        sys.exit(1)

    # Validate titledb.xml
    print()
    titledb_path = None
    if config.has_option('DEFAULT', 'titledb'):
        titledb_path = config['DEFAULT']['titledb']
        print_header(f"Validating titledb.xml: {titledb_path}")

        # Get list of AU names from staging validation
        au_names = [au['au_name'] for au in results['aus']]

        # Validate titledb
        titledb_results = validate_titledb(titledb_path, au_names)
        results['titledb'] = titledb_results

        # Display titledb validation results
        if titledb_results['exists']:
            if titledb_results['valid_xml']:
                print_success("titledb.xml is valid XML")
            else:
                print_error("titledb.xml has XML parsing errors")

            print(f"\nExpected entries: {titledb_results['expected_entries']}")
            print(f"Found entries:    {titledb_results['matching_entries']}")

            if titledb_results['matching_entries'] == titledb_results['expected_entries']:
                print_success("All AUs found in titledb.xml")
            else:
                print_error(f"Missing {len(titledb_results['missing_aus'])} AU(s) in titledb.xml")

            # Display per-AU validation
            print()
            for au_name, au_result in titledb_results['entries'].items():
                if au_result['found']:
                    if au_result['valid']:
                        print_success(f"AU '{au_name}' - all required fields present")
                    else:
                        print_error(f"AU '{au_name}' - missing fields: {', '.join(au_result['missing_fields'])}")
                else:
                    print_error(f"AU '{au_name}' - not found in titledb.xml")

            # Display errors
            if titledb_results['errors']:
                print()
                print_error("titledb.xml validation errors:")
                for error in titledb_results['errors']:
                    print(f"  • {error}")

            # Display warnings
            if titledb_results['warnings']:
                print()
                print_warning("titledb.xml validation warnings:")
                for warning in titledb_results['warnings']:
                    print(f"  • {warning}")

        else:
            print_error(f"titledb.xml not found at: {titledb_path}")

        # Update return code based on titledb validation
        if titledb_results['errors'] or not titledb_results['valid_xml']:
            results['return_code'] = 1

    else:
        print_warning("titledb path not configured in config.ini, skipping titledb validation")

    # Final summary
    print_header("Overall Validation Result")
    if results.get('return_code', 0) == 0:
        print_success("✓ All validations passed!")
    else:
        print_error("✗ Validation failed - see errors above")

    # Save report
    report_file = os.path.join(os.path.dirname(__file__), 'validation_report.json')
    save_report(results, report_file)

    sys.exit(results.get('return_code', 0))

if __name__ == "__main__":
    main()
