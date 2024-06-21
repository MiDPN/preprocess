#!/usr/bin/env python
#
#""Preprocess.py - examines uploaded tar files for validity, makes a manifest"
# and moves using RSYNC"
#
#__author__      = "Paul Gallagher"
#--copyright--   = "CC0 - openly shared into the public domain on behalf of MDPN"
#--version--     = 0.1 - MVP base
#########################################################

import os
import subprocess
import tarfile
import shutil

############################## Configuration fields ################################
source_dir = "/home/sftpuser/uploads/"
destination_dir = "/var/www/html/staging"
###############################################################################3###

### functions
def run_clamav_scan(file_path):
    result = subprocess.run(['clamscan', file_path], capture_output=True, text=True)
    return result.returncode == 0

def is_non_zero(file_path):
    return os.path.getsize(file_path) > 0

def extract_and_convert_manifest(tar_file_path, extract_to):
    try:
        with tarfile.open(tar_file_path) as tar:
            file_name = os.path.basename(tar_file_path)
            fname = os.path.splitext(file_name) #filename minus extension
            member = tar.getmember(fname[0] + '/manifest-sha256.txt')
            tar.extract(member, path=extract_to)
            manifest_file_path = os.path.join(extract_to, fname[0], 'manifest-sha256.txt')
            convert_to_html(manifest_file_path)
        return True
    except (tarfile.TarError, KeyError):
        return False

def convert_to_html(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    au_name = os.path.splitext(file_path)

    ## html template for manifest file ##
    html_content = f"<html><head><title>{file_path} MDPN LOCKSS Manifest Page</title></head><body><pre>{content}</pre>"       
    html_content += '<p>LOCKSS system has permission to collect, preserve, and serve this Archival Unit</p></body></html>'    

    html_file_path = os.path.join(os.path.dirname(file_path), 'manifest.html')

    with open(html_file_path, 'w') as html_file:
        html_file.write(html_content)

   # remove the manifest file
    os.remove(file_path)

################################### MAIN ENTRY #################################################
### main entry point triggered by __main__ below, handles all processing as branch statements
### and hands off to functions above
def process_tar_files(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.tar'):
                file_path = os.path.join(root, file)    #file path
                file_name = os.path.basename(file_path) #file_name
                fname = os.path.splitext(file_name)     #file name without path or ext

                if is_non_zero(file_path):
                    if run_clamav_scan(file_path):
                        if extract_and_convert_manifest(file_path, root):
                            #move the tarball into the folder with the manifest file
                            new_file = os.path.join(root, fname[0], file)
                            new_folder = os.path.join(root, fname[0])
                            shutil.move(file_path, new_file)         #move into the AU folder 
                            shutil.move(new_folder, destination_dir) #move into the production folder
                            print(f"Processed {file_path} into {new_file} successfully, and moved to {destination_dir}.")
                        else:
                            print(f"Error: Failed to extract manifest from {file_path}")
                    else:
                        print(f"Error: ClamAV scan failed for {file_path}")
                        os.remove(file_path) #get that stuff out of here!
                else:
                    print(f"Error: {file_path} is zero bytes")

if __name__ == "__main__":
    #do the main processing process_tar_files
    process_tar_files(source_dir)
