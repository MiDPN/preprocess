#!/usr/bin/env python
#
#"preprocess.py - examines uploaded tar files for validity, makes a manifest"
# adds entry into titledb, and moves into production"
#
#__author__      = "Paul Gallagher"
#__copyright__   = "CC0 - openly shared into the public domain on behalf of MDPN"
#__version__     = 0.9 - Nov 2025
# Runs without any options ie python3 ./preprocess.py
# Expects the below configuration directories exist and have contents to process
# and that there is a titledb.xml file in the location specified. max_au_size sets the
# upper limit of the AU.
#
# REQUIREMENTS:
# install requirments: pip install -r requirements.txt
# also requires clamav: sudo apt install clamav clamav-daemon
# also requires droid: https://cdn.nationalarchives.gov.uk/documents/droid-binary-6.8.1-bin.zip #updated to 6.8.1 Nov 2025
# droid uses java openjdk version 21 - sudo apt install openjdk-21-jdk
# droid needs to be updated periodically(daily?), create a cron job simular to the following: java -Xmx1024m -jar /PATH/TO/droid-command-line-6.8.1.jar -d
#########################################################

import os
import re
import subprocess
import tarfile
import shutil
import urllib.parse
import xml.etree.ElementTree as ET
import csv
import datetime
import pandas as pd
import configparser
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

############################## Obtain configuration file ################################
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__),'config.ini'))
#########################################################################################

### functions
def run_clamav_scan(file_path):
    result = subprocess.run(['clamscan', file_path], capture_output=True, text=True)
    with open(file_path + '-clamav.txt', 'w', encoding='utf-8') as f:
        f.write(result.stdout)
    return result.returncode == 0

#has the file size definitions
def is_right_size(file_path):
    file_size = os.path.getsize(file_path)
    return file_size > 0 and file_size < int(config['DEFAULT']['max_au_size'])

def extract_and_convert_manifest(tar_file_path, extract_to):
    with tarfile.open(tar_file_path) as tar:
        file_name = os.path.basename(tar_file_path)
        fname = os.path.splitext(file_name) #filename minus extension

        #extract the bag-info file
        member = tar.getmember(fname[0] + '/bag-info.txt')
        tar.extract(member, path=extract_to, filter='data')
        baginfo_file_path = os.path.join(extract_to, fname[0], 'bag-info.txt')

        #extract the manifest file
        member = tar.getmember(fname[0] + '/manifest-sha256.txt')
        tar.extract(member, path=extract_to, filter='data')
        manifest_file_path = os.path.join(extract_to, fname[0], 'manifest-sha256.txt')

        #parse bag info, push bag-info fields into html manifest
        with open(baginfo_file_path, 'r') as file:
            content = file.readlines()

        # Parse bag-info into a dictionary for easy access
        baginfo_dict = {}
        for line in content:
            if ':' in line:
                key, value = line.split(':', 1)
                baginfo_dict[key.strip()] = value.strip()

        url = config['DEFAULT']['staging_url'] + fname[0]
        convert_to_html(manifest_file_path, baginfo_file_path, url, content[10].split(" ", 1)[1].strip()) #manifest_file_path, baginfo_file_path, url, title
    return baginfo_dict

def convert_to_html(manifest_file_path, baginfo_file_path, url, title):
    with open(manifest_file_path, 'r') as file:
        content = file.read()
        
    with open(baginfo_file_path, 'r') as file:
        baginfo = file.read()

   ## html template for manifest file ##
    html_content = f"<html><head><title>{title} - LOCKSS Manifest Page</title></head><body><h1><a href='{url}'>{title}</a></h1><a href='bag-info.txt'><h3>bag-info.txt</h3></a><pre>{baginfo}</pre><h3><a href='clamav.txt'>clamav.txt</a></h3><h3>manifest-sha256.txt</h3><pre>{content}</pre>"       
    html_content += '<p>LOCKSS system has permission to collect, preserve, and serve this Archival Unit</p></body></html>'    

    html_file_path = os.path.join(os.path.dirname(manifest_file_path), 'manifest.html')

    with open(html_file_path, 'w') as html_file:
        html_file.write(html_content)

   # remove the manifest file
    os.remove(manifest_file_path)

def insert_into_titledb(publisher, fname, title, journal_title):
        #load the file
        tree = ET.parse(config['DEFAULT']['titledb'])
        tree.write(config['DEFAULT']['titledb'] + '_' + time.strftime("%Y%m%d-%H%M%S"), encoding='utf-8')  #backup the file with a date, copies for each au loaded
        root = tree.getroot()
        parent_element = root.findall("property") 
        
        #append - AU first (fname)
        new_au = ET.Element("property")
        new_au.attrib["name"] = fname #property name for AU element
        #publisher (publisher)
        pub = ET.Element('property')
        pub.attrib["name"] = "attributes.publisher"
        pub.attrib["value"] = publisher
        new_au.append(pub)
        #journal title (title)
        jour = ET.Element('property')
        jour.attrib["name"] = "journalTitle"
        jour.attrib["value"] = journal_title
        new_au.append(jour)
        #title (title)
        titl = ET.Element('property')
        titl.attrib["name"] = "title"
        titl.attrib["value"] = title
        new_au.append(titl)
        #type
        type = ET.Element('property')
        type.attrib["name"] = "type"
        type.attrib["value"] = "journal"
        new_au.append(type)
        #plugin
        plugin = ET.Element('property')
        plugin.attrib["name"] = "plugin"
        plugin.attrib["value"] = "edu.auburn.adpn.directory.AuburnDirectoryPlugin"
        new_au.append(plugin)
        
        #param.1 
        param1 = ET.Element('property')
        param1.attrib["name"] = "param.1"
        #subelements
        sub_param1 = ET.Element('property')
        sub_param1.attrib["name"] = "key"
        sub_param1.attrib["value"] = "base_url"
        param1.append(sub_param1)
        sub_param11 = ET.Element('property')
        sub_param11.attrib["name"] = "value"
        sub_param11.attrib["value"] = config['DEFAULT']['staging_url']
        param1.append(sub_param11)
        new_au.append(param1)
        
        #param.2 (fname)
        param2 = ET.Element('property')
        param2.attrib["name"] = "param.2"
        #subelements
        sub_param2 = ET.Element('property')
        sub_param2.attrib["name"] = "key"
        sub_param2.attrib["value"] = "directory"
        param2.append(sub_param2)
        sub_param21 = ET.Element('property')
        sub_param21.attrib["name"] = "value"
        sub_param21.attrib["value"] = fname
        param2.append(sub_param21)
        new_au.append(param2)

        #param.99 (fname)
        param99 = ET.Element('property')
        param99.attrib["name"] = "param.99"
        #subelements
        sub_param99 = ET.Element('property')
        sub_param99.attrib["name"] = "key"
        sub_param99.attrib["value"] = "pub_down"
        param99.append(sub_param99)
        sub_param991 = ET.Element('property')
        sub_param991.attrib["name"] = "value"
        sub_param991.attrib["value"] = "false"
        param99.append(sub_param991)
        new_au.append(param99)
        
        #merge into the main element
        parent_element[1].append(new_au) #append to the second instance of property
        ET.indent(tree, space="\t", level=0)
        tree.write(config['DEFAULT']['titledb'], encoding='utf-8')

def is_web_safe_filename(filename):
    #check to see if a filename is websafe
    # Define a regular expression for a web-safe file name
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$' #do not include periods
    
    # Check if the filename matches the pattern
    if re.match(pattern, filename) and not filename.startswith(('.', '-')) and not filename.endswith(('.', '-')):
        return True
    return False

def log_to_csv(filename, publisher, title, size, status, au_id, csv_filename=config['DEFAULT']['logfile']):
    # Define the header
    headers = ["Date", "Package Name", "Source-Organization", "External-Identifier", "Size (B)", "Status", "LOCKSS AU Id"]
    
    # Check if the CSV file already exists
    file_exists = False
    try:
        with open(csv_filename, 'r', newline='') as file:
            file_exists = True
    except FileNotFoundError:
        file_exists = False
    
    # Open the CSV file in append mode
    with open(csv_filename, 'a', newline='') as file:
        writer = csv.writer(file)
        
        # Write the header only if the file doesn't exist
        if not file_exists:
            writer.writerow(headers)
        
        # Write the row with the provided information
        writer.writerow([datetime.datetime.now(), filename, publisher, title, size, status, au_id])

def csv_to_html(csv_filename, html_filename):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(csv_filename)
    
    # Convert DataFrame to HTML format with table styling
    html_content = df.to_html(index=False, classes="table table-striped", border=0)
    
    # Create a basic HTML structure and embed the table
    #should refactor this to use a single template
    html_page = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MDPN Import Log</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .table {{ width: 100%; border-collapse: collapse; }}
            .table th, .table td {{ padding: 8px; border: 1px solid #ddd; text-align: left; }}
            .table th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h2>MDPN Import Log</h2>
        {html_content}
        <a href="log.csv">log.csv download</a> 
    </body>
    </html>
    """
    
    # Write the HTML content to a file
    with open(html_filename, "w") as file:
        file.write(html_page)

def send_notification_email(au_name, to_email, success=True, error_message=None, attachments=None):
    """
    Send email notification after AU processing

    Args:
        au_name: Name of the archival unit
        to_email: Primary recipient email address (from Contact-Email in bag-info.txt)
        success: True if processing succeeded, False otherwise
        error_message: Error message to include if success=False
        attachments: List of file paths to attach (bag-info.txt, clamav.txt, droid_report.csv)
    """
    try:
        # Check if email is enabled in config
        if not config.has_section('EMAIL') or not config.getboolean('EMAIL', 'enabled', fallback=False):
            return  # Email notifications disabled

        # Validate to_email
        if not to_email or not to_email.strip():
            print(f"Warning: No Contact-Email found for {au_name}, skipping email notification")
            return

        # Email configuration
        smtp_host = config.get('EMAIL', 'smtp_host', fallback='')
        smtp_port = config.getint('EMAIL', 'smtp_port', fallback=587)
        smtp_username = config.get('EMAIL', 'smtp_username', fallback='')
        smtp_password = config.get('EMAIL', 'smtp_password', fallback='')
        use_tls = config.getboolean('EMAIL', 'use_tls', fallback=True)
        cc_emails = config.get('EMAIL', 'cc_emails', fallback='').strip()
        from_email = "do_not_reply@mipres.org"

        # Debug mode configuration
        debug_mode = config.getboolean('EMAIL', 'debug_mode', fallback=False)
        debug_output_dir = config.get('EMAIL', 'debug_output_dir', fallback='./email_debug')

        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email.strip()
        if cc_emails:
            msg['Cc'] = cc_emails
        msg['Date'] = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

        if success:
            msg['Subject'] = "AU Processing Complete"
            body = f"AU processing is complete for {au_name}"
        else:
            msg['Subject'] = "AU Processing Failed"
            body = f"AU processing failed for {au_name}"
            if error_message:
                body += f"\n\nError details:\n{error_message}"

        msg.attach(MIMEText(body, 'plain'))

        # Attach files if provided
        attachment_info = []
        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
                            msg.attach(part)
                            attachment_info.append(f"{os.path.basename(file_path)} ({os.path.getsize(file_path)} bytes)")
                    except Exception as e:
                        print(f"Warning: Could not attach file {file_path}: {e}")
                        attachment_info.append(f"{os.path.basename(file_path)} (FAILED: {e})")

        # Debug mode: save email to file instead of sending
        if debug_mode:
            # Create debug output directory if it doesn't exist
            os.makedirs(debug_output_dir, exist_ok=True)

            # Generate debug filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            debug_filename = os.path.join(debug_output_dir, f"email_{au_name}_{timestamp}.txt")

            # Build recipient list for debug output
            recipients = [to_email.strip()]
            if cc_emails:
                recipients.extend([email.strip() for email in cc_emails.split(',')])

            # Write email details to debug file
            with open(debug_filename, 'w', encoding='utf-8') as debug_file:
                debug_file.write("=" * 80 + "\n")
                debug_file.write("EMAIL DEBUG OUTPUT\n")
                debug_file.write("=" * 80 + "\n\n")
                debug_file.write(f"From: {from_email}\n")
                debug_file.write(f"To: {to_email.strip()}\n")
                if cc_emails:
                    debug_file.write(f"Cc: {cc_emails}\n")
                debug_file.write(f"Subject: {msg['Subject']}\n")
                debug_file.write(f"Date: {msg['Date']}\n")
                debug_file.write(f"\nRecipient list: {', '.join(recipients)}\n")
                debug_file.write("\n" + "-" * 80 + "\n")
                debug_file.write("MESSAGE BODY:\n")
                debug_file.write("-" * 80 + "\n\n")
                debug_file.write(body)
                debug_file.write("\n\n" + "-" * 80 + "\n")
                debug_file.write("ATTACHMENTS:\n")
                debug_file.write("-" * 80 + "\n")
                if attachment_info:
                    for att in attachment_info:
                        debug_file.write(f"  - {att}\n")
                else:
                    debug_file.write("  (none)\n")
                debug_file.write("\n" + "=" * 80 + "\n")
                debug_file.write("END OF EMAIL DEBUG OUTPUT\n")
                debug_file.write("=" * 80 + "\n")

            print(f"DEBUG MODE: Email saved to {debug_filename}")
            return

        # Send email (normal mode)
        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)

        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)

        # Build recipient list (To + CC)
        recipients = [to_email.strip()]
        if cc_emails:
            recipients.extend([email.strip() for email in cc_emails.split(',')])

        server.send_message(msg, to_addrs=recipients)
        server.quit()

        print(f"Email notification sent for {au_name} to {to_email}" + (f" (CC: {cc_emails})" if cc_emails else ""))

    except Exception as e:
        # Don't let email failures interrupt the main processing pipeline
        print(f"Warning: Failed to send email notification for {au_name}: {e}")

################################### MAIN ENTRY #################################################
### main entry point triggered by __main__ below, handles all processing as branch statements
### and hands off to functions above
def process_tar_files(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.tar'):
                file_path = os.path.join(root, file)    #file path
                file_name = os.path.basename(file_path) #file name
                fname = os.path.splitext(file_name)     #file name without path or ext in array
                size = os.path.getsize(file_path)
                new_file_path = os.path.join(root, fname[0]) #new file path after the tar is put into a folder with the logging files
                    
                #validity checks
                if is_web_safe_filename(fname[0]):      #check filename is websafe
                    if is_right_size(file_path):        #check the file is under max_au_size
                        if run_clamav_scan(file_path):  #run the clamav scan, proceed if clear
                                baginfo_dict = {}  # Initialize in case extraction fails
                                try:    #try and parse the tarball, get the manifest and bag-info, and create manifest
                                    baginfo_dict = extract_and_convert_manifest(file_path, root)
                                except Exception as error:
                                    print(f"Error: Failed to extract manifest from {file_path}, possibly corrupted, uploading", error)

                                try:     #move the tarball into the folder with the manifest and bag-info file
                                    shutil.move(file_path, os.path.join(root, fname[0], file))         #move tarball into the AU folder
                                    shutil.move(file_path + '-clamav.txt', os.path.join(root, fname[0], 'clamav.txt'))         #move clamav.txt into the AU folder
                                except Exception as error:
                                    print("Error moving tar or clamav.txt into au folder", error)

                                try:  #try to parse bag-info.txt and create the titledb
                                    # Use baginfo_dict from extract_and_convert_manifest
                                    publisher = baginfo_dict.get('Source-Organization', '')
                                    title = baginfo_dict.get('External-Identifier', '')
                                    journal_title = baginfo_dict.get('Bag-Group-Identifier', '')

                                    #check that journal title (Bag-Group-Identifier) has data, if not, default to External-Identifer for the titledb
                                    if not journal_title:
                                        journal_title = title  #default to External-Identifer

                                    insert_into_titledb(publisher, fname[0], title, journal_title)    #publisher, fname, title, journal_title
                                except Exception as error:
                                    print("Error inserting into titledb", error)
                                    
                                try: #try and run the droid format scan, generate reports
                                    #generate the droid_report.csv file
                                    result = subprocess.run([config['DROID']['java_path'], "-Xmx1024m", "-jar", config['DROID']['droid_path'], "-R", "-A", new_file_path, "-o", new_file_path + "/droid_report.csv" ], capture_output=True, text=True)                                   
                                    #generate the droid_report.droid file, not really sure we need this... 
                                    # subprocess.run([java_path, "-Xmx1024m", "-jar", droid_path, "-R", "-A", new_file_path, "-p", new_file_path + "/droid_profile.droid" ], capture_output=True, text=True)
                                except Exception as error:
                                    print(f"Error conducting droid format scan", result, error)
                                
                                try: #try to move the file to production folder
                                    #note, ran into a bug below if the staging folder isn't created, dumps file contents in the desination root
                                    shutil.move(new_file_path, config['DEFAULT']['destination_dir'])     #move into the production folder
                                    status = "Staged"                           #update status for the log to "Staged"
                                except Exception as error:
                                    print(f"Error: Copy to production error, {file} may already exist, be uploading, or corrupted", error)
                                    status = "Error: Copy to production error, file may already exist, be uploading, or corrupted"
                        else:
                            print(f"Error: ClamAV scan failed for {file_path}, file deleted")
                            os.remove(file_path) #remove file
                            os.remove(file_path + '-clamav.txt') #remove the scan results file
                            status = "Error: ClamAV scan failed, file deleted"
                    else:
                        print(f"Error: {file_path} is either zero bytes or greater than {config['DEFAULT']['max_au_size']}, file deleted")
                        os.remove(file_path) #remove file
                        status = "Error: File is either zero bytes or greater than max size"
                else:
                    print(f"Error: The AU named {fname[0]} is not web safe, file deleted")
                    os.remove(file_path) #remove file
                    status = "Error: Package Name is not web safe, file deleted" 
                
                #update the log, logging reports user "if" conditions, not exceptions which are admin side, except for production copy (duplicate)
                try:
                    # Use baginfo_dict for consistency
                    publisher = baginfo_dict.get('Source-Organization', '')
                    title = baginfo_dict.get('External-Identifier', '')

                    log_to_csv(fname[0], publisher, title, size, status, "edu|auburn|adpn|directory|AuburnDirectoryPlugin&base_url~" + urllib.parse.quote_plus(config['DEFAULT']['staging_url']).replace(".", "%2E") + "&directory~" + fname[0]) #filename, publisher, title, size, status, au_id
                    csv_to_html(config['DEFAULT']['logfile'], config['DEFAULT']['weblog']) #convert the logfile over to an HTML file

                    ### Log the droid data to the central log ###
                    df = pd.read_csv(config['DEFAULT']['destination_dir'] + "/" + fname[0] + "/droid_report.csv")

                    # Add the new columns to add in the package data
                    df['Package_Name'] = fname[0]
                    df['Source_Organization'] = publisher
                    df['External-Identifier'] = title
                    df['Date'] = datetime.datetime.now()

                    # Check if the output file already exists
                    if os.path.exists(config['DROID']['droid_log']):
                        # Append to the existing file without writing the header
                        df.to_csv(config['DROID']['droid_log'], mode='a', index=False, header=False)
                    else:
                        # Create a new file with the header
                        df.to_csv(config['DROID']['droid_log'], index=False)

                except Exception as error:
                    print("Error inserting into logfile", error)

                # Send email notification
                try:
                    # Get Contact-Email from baginfo_dict
                    contact_email = baginfo_dict.get('Contact-Email', '')

                    # Prepare attachment paths
                    attachments = []
                    if status == "Staged":  # Only attach files if processing succeeded
                        baginfo_path = os.path.join(config['DEFAULT']['destination_dir'], fname[0], 'bag-info.txt')
                        clamav_path = os.path.join(config['DEFAULT']['destination_dir'], fname[0], 'clamav.txt')
                        droid_path = os.path.join(config['DEFAULT']['destination_dir'], fname[0], 'droid_report.csv')
                        attachments = [baginfo_path, clamav_path, droid_path]
                        send_notification_email(fname[0], contact_email, success=True, attachments=attachments)
                    else:  # Processing failed
                        send_notification_email(fname[0], contact_email, success=False, error_message=status)
                except Exception as error:
                    print(f"Warning: Email notification failed for {fname[0]}: {error}")

if __name__ == "__main__":
    #do the main processing process_tar_files
    process_tar_files(config['DEFAULT']['source_dir'])

