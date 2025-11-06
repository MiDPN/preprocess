#!/usr/bin/env python3
"""Reset staging and uploads by deleting their contents and copying test_files -> staging.

This script performs destructive actions immediately (no interactive confirmation).
Use with care.
"""
import os
import shutil
import sys


def info(msg):
    print(f"[INFO] {msg}")


def err(msg):
    print(f"[ERROR] {msg}")
    sys.exit(1)


def rm_contents(path):
    if not os.path.isdir(path):
        return
    for name in os.listdir(path):
        full = os.path.join(path, name)
        try:
            if os.path.isdir(full) and not os.path.islink(full):
                shutil.rmtree(full)
            else:
                os.remove(full)
        except Exception as e:
            err(f"Failed to remove {full}: {e}")


def main():
    # Run relative to the user's ~/preprocess directory (explicit override)
    repo_root = os.path.expanduser('~/preprocess')
    info(f"Using repo root: {repo_root}")

    staging = os.path.join(repo_root, 'staging')
    uploads = os.path.join(repo_root, 'uploads')
    test_files = os.path.join(repo_root, 'test_files')

    if not os.path.isdir(test_files):
        err(f"test_files directory not found: {test_files}")

    # Ensure directories exist
    os.makedirs(staging, exist_ok=True)
    os.makedirs(uploads, exist_ok=True)

    info(f"Removing contents of {staging}")
    rm_contents(staging)
    info(f"Removing contents of {uploads}")
    rm_contents(uploads)

    # Copy test files into uploads (used as the source upload directory)
    info(f"Copying contents of {test_files} -> {uploads}")
    try:
        for item in os.listdir(test_files):
            s = os.path.join(test_files, item)
            d = os.path.join(uploads, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
    except Exception as e:
        err(f"Failed copying test files: {e}")

    # Replace titledb.xml with titledb-prod.xml (overwrite)
    prod_titledb = os.path.join(repo_root, 'titledb-prod.xml')
    target_titledb = os.path.join(repo_root, 'titledb.xml')
    info(f"Replacing {target_titledb} with {prod_titledb}")
    if not os.path.isfile(prod_titledb):
        err(f"titledb-prod.xml not found at {prod_titledb}")
    try:
        shutil.copy2(prod_titledb, target_titledb)
        info(f"Replaced titledb.xml with titledb-prod.xml")
    except Exception as e:
        err(f"Failed to replace titledb: {e}")

    info("Reset complete.")


if __name__ == '__main__':
    main()
