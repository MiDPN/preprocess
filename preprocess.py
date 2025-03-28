#!/usr/bin/env python
#
#"preprocess.py - examines uploaded tar files for validity, makes a manifest"
# adds entry into titledb, and moves into production"
#
#__author__      = "Paul Gallagher"
#__copyright__   = "CC0 - openly shared into the public domain on behalf of MDPN"
#__version__     = 0.7
# Runs without any options ie python3 ./preprocess.py
# Expects the below configuration directories exist and have contents to process
# and that there is a titledb.xml file in the location specified. max_au_size sets the
# upper limit of the AU.
#
# REQUIREMENTS:
# requires pandas for html creation - pip install pandas
# also requires droid: https://tna-cdn-live-uk.s3.eu-west-2.amazonaws.com/documents/droid-binary-6.8.0-bin.zip
# droid uses java openjdk version 8 to 17, 17 tested here
# droid needs to be updated periodically(daily?), create a cron job simular to the following: java -Xmx1024m -jar /PATH/TO/droid-command-line-6.8.0.jar -d
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
import urllib 

############################## Configuration fields ################################
source_dir = "/home/sftpuser/uploads/"  #works on all subfolders
destination_dir = "/var/www/html/staging"
titledb = "/var/www/html/mdpn/titledb/titledb.xml"  #this file needs to exist
staging_url = "http://192.168.60.130/staging/"      #LOCKSS crawable URL
logfile = "/var/www/html/mdpn/log/log.csv"          #creates on first run
weblog = "/var/www/html/mdpn/log/log.html"          #updates per AU ie: as each log entry is added
max_au_size = 5000000000   #50gb

######## DROID Format Settings ########
java_path = "/usr/lib/jvm/java-17-openjdk-amd64/bin/java"
droid_path = "/home/aristotle23/droid/droid-command-line-6.8.0.jar"
droid_log = "/var/www/html/mdpn/log/droid_log.csv"
###############################################################################3###

### functions
def run_clamav_scan(file_path):
    result = subprocess.run(['clamscan', file_path], capture_output=True, text=True)
    f = open(file_path + '-clamav.txt', 'w')
    f.write(result.stdout)
    return result.returncode == 0

#has the file size definitions below 1byte to 50gb valid
def is_right_size(file_path):
    file_size = os.path.getsize(file_path)
    return file_size > 0 and file_size < max_au_size

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

        url = staging_url + fname[0]
        convert_to_html(manifest_file_path, baginfo_file_path, url, content[10].split(" ", 1)[1].strip()) #manifest_file_path, baginfo_file_path, url, title   
    return True

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
        tree = ET.parse(titledb)
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
        sub_param11.attrib["value"] = staging_url
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
        
        #merge into the main element
        parent_element[1].append(new_au) #append to the second instance of property
        ET.indent(tree, space="\t", level=0)
        tree.write(titledb, encoding='utf-8')

def is_web_safe_filename(filename):
    #check to see if a filename is websafe
    # Define a regular expression for a web-safe file name
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$'
    
    # Check if the filename matches the pattern
    if re.match(pattern, filename) and not filename.startswith(('.', '-')) and not filename.endswith(('.', '-')):
        return True
    return False

def log_to_csv(filename, publisher, title, size, status, au_id, csv_filename=logfile):
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
    df1 = df.drop("LOCKSS AU Id", axis="columns") #remove the au_id from the web interface
    
    # Convert DataFrame to HTML format with table styling
    html_content = df1.to_html(index=False, classes="table table-striped", border=0)
    
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
                                try:    #try and parse the tarball, get the manifest and bag-info, and create manifest
                                    extract_and_convert_manifest(file_path, root)
                                except Exception as error:
                                    print(f"Error: Failed to extract manifest from {file_path}, possibly corrupted, uploading", error)
                                                                
                                try:     #move the tarball into the folder with the manifest and bag-info file
                                    shutil.move(file_path, os.path.join(root, fname[0], file))         #move tarball into the AU folder
                                    shutil.move(file_path + '-clamav.txt', os.path.join(root, fname[0], 'clamav.txt'))         #move clamav.txt into the AU folder
                                except Exception as error:
                                    print("Error moving tar or clamav.txt into au folder", error)

                                try:  #try to parse bag-info.txt and create the titledb                              
                                    baginfo = os.path.join(root, fname[0], "bag-info.txt")
                                    with open(baginfo, 'r') as file:
                                            content = file.readlines() 

                                    #check that journal title (Bag-Group-Identifier) has data, if not, default to External-Identifer for the titledb
                                    journal_title = content[1].split(" ", 1)[1].strip()
                                    if not journal_title:
                                        journal_title = content[10].split(" ", 1)[1].strip() #default to External-Identifer
                                    
                                    insert_into_titledb(content[15].split(" ", 1)[1].strip(), fname[0], content[10].split(" ", 1)[1].strip(), journal_title)    #publisher, fname, title, journal_title
                                except Exception as error:
                                    print("Error inserting into titledb", error)
                                    
                                try: #try and run the droid format scan, generate reports
                                    #generate the droid_report.csv file
                                    result = subprocess.run([java_path, "-Xmx1024m", "-jar", droid_path, "-R", "-A", new_file_path, "-o", new_file_path + "/droid_report.csv" ], capture_output=True, text=True)                                   
                                    #generate the droid_report.droid file, not really sure we need this... 
                                    # subprocess.run([java_path, "-Xmx1024m", "-jar", droid_path, "-R", "-A", new_file_path, "-p", new_file_path + "/droid_profile.droid" ], capture_output=True, text=True)
                                except Exception as error:
                                    print(f"Error conducting droid format scan", result, error)
                                
                                try: #try to move the file to production folder
                                    #note, ran into a bug below if the staging folder isn't created, dumps file contents in the desination root
                                    shutil.move(new_file_path, destination_dir)     #move into the production folder
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
                        print(f"Error: {file_path} is either zero bytes or greater than {max_au_size}, file deleted")
                        os.remove(file_path) #remove file
                        status = "Error: File is either zero bytes or greater than max size"
                else:
                    print(f"Error: The AU named {fname[0]} is not web safe, file deleted")
                    os.remove(file_path) #remove file
                    status = "Error: Package Name is not web safe, file deleted" 
                
                #update the log, logging reports user "if" conditions, not exceptions which are admin side, except for production copy (duplicate)  
                try: 
                    log_to_csv(fname[0], content[15].split(" ", 1)[1].strip(), content[10].split(" ", 1)[1].strip(), size, status, "edu|auburn|adpn|directory|AuburnDirectoryPlugin&base_url~" + urllib.parse.quote_plus(staging_url).replace(".", "%2E") + "&directory~" + fname[0]) #filename, publisher, title, size, status, au_id
                    csv_to_html(logfile, weblog) #convert the logfile over to an HTML file
                    
                    ### Log the droid data to the central log ###
                    df = pd.read_csv(destination_dir + "/" + fname[0] + "/droid_report.csv")
                    
                    # Add the new columns to add in the package data
                    df['Package_Name'] = fname[0]
                    df['Source_Organization'] = content[15].split(" ", 1)[1].strip()
                    df['External-Identifier'] = content[10].split(" ", 1)[1].strip()
                    df['Date'] = datetime.datetime.now()
                    df['AU_Id'] = "edu|auburn|adpn|directory|AuburnDirectoryPlugin&base_url~" + urllib.parse.quote_plus(staging_url).replace(".", "%2E") + "&directory~" + fname[0] #add LOCKSS au_id
                    
                    # Check if the output file already exists
                    if os.path.exists(droid_log):
                        # Append to the existing file without writing the header
                        df.to_csv(droid_log, mode='a', index=False, header=False)
                    else:
                        # Create a new file with the header
                        df.to_csv(droid_log, index=False)
                    
                except Exception as error:
                    print("Error inserting into logfile", error)

if __name__ == "__main__":
    #do the main processing process_tar_files
    process_tar_files(source_dir)
