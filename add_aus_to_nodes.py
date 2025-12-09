#!/usr/bin/env python3
"""
Parses titledb.xml, generates AUIDs for each AU entry, and submits them to LOCKSS nodes.
"""

import configparser
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET

import requests
from requests.auth import HTTPBasicAuth
from lockss.pybasic.auidutil import AuidGenerator

# =============================================================================
# Configuration Loading
# =============================================================================

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

TITLEDB_URL = config['DEFAULT']['titledb_url']
LOCKSS_SERVERS = [s.strip() for s in config['LOCKSS']['servers'].split(',')]
LOCKSS_USER = config['LOCKSS']['username']
LOCKSS_PASS = config['LOCKSS']['password']

# =============================================================================
# AUID Encoding Fix (LOCKSS requires periods encoded as %2E, uppercase hex)
# =============================================================================

def _encode_component(s: str) -> str:
    """URL-encode string with periods as %2E and uppercase hex (LOCKSS requirement)."""
    if not s:
        return ""
    encoded = urllib.parse.quote_plus(s, safe='').replace('.', '%2E')
    # Convert hex sequences to uppercase: %2e -> %2E
    return re.sub(r'%([0-9a-fA-F]{2})', lambda m: f'%{m.group(1).upper()}', encoded)

AuidGenerator.encode_component = staticmethod(_encode_component)

# =============================================================================
# Core Functions
# =============================================================================

def fetch_titledb() -> str:
    """Fetch titledb.xml content from configured URL."""
    response = requests.get(TITLEDB_URL, timeout=30)
    response.raise_for_status()
    return response.text


def parse_titledb(xml_content: str) -> list[tuple[str, str, dict]]:
    """
    Parse titledb XML and extract AU entries where pub_down='false'.
    Returns list of (name, plugin, params) tuples.
    """
    root = ET.fromstring(xml_content)
    entries = []

    for au in root.findall('.//property'):
        name = au.get('name')
        if not name:
            continue

        plugin, params, pub_down = None, {}, None

        # Extract plugin ID and parameters from child properties
        for child in au.findall('property'):
            cname, cval = child.get('name'), child.get('value')

            if cname == 'plugin':
                plugin = cval
            elif cname and cname.startswith('param.'):
                # Params have nested key/value properties
                pdata = {p.get('name'): p.get('value') for p in child.findall('property')}
                key, val = pdata.get('key'), pdata.get('value')
                if key == 'pub_down':
                    pub_down = val
                elif key and val:
                    params[key] = val

        # Only include AUs with plugin, params, and pub_down=false
        if plugin and params and pub_down == 'false':
            entries.append((name, plugin, params))

    return entries


def generate_auids(entries: list[tuple[str, str, dict]]) -> list[str]:
    """Generate AUIDs from AU entries. Prints details for each."""
    auids = []
    for name, plugin, params in entries:
        auid = AuidGenerator.generate_auid(plugin, params)
        auids.append(auid)
        print(f"AU: {name}\n  Plugin: {plugin}\n  Params: {params}\n  AUID: {auid}\n{'-'*80}")
    return auids


def submit_auids(auids: list[str]) -> None:
    """Submit AUIDs to all configured LOCKSS servers."""
    auth = HTTPBasicAuth(LOCKSS_USER, LOCKSS_PASS)

    for server in LOCKSS_SERVERS:
        url = f"{server}/ws/aus/add"
        print(f"\nSubmitting {len(auids)} AUIDs to {url}...")
        try:
            resp = requests.post(url, json=auids, auth=auth, timeout=60)
            print(f"Status: {resp.status_code} | Response: {resp.text}")
        except requests.RequestException as e:
            print(f"Error: {e}")

# =============================================================================
# Entry Point
# =============================================================================

def main():
    print(f"Fetching titledb from: {TITLEDB_URL}")
    entries = parse_titledb(fetch_titledb())
    print(f"Found {len(entries)} AU entries\n{'='*80}")

    auids = generate_auids(entries)
    if auids:
        submit_auids(auids)
    else:
        print("No AUIDs to submit.")


if __name__ == "__main__":
    main()
