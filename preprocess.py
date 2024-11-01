#!/usr/bin/env python
#
#"preprocess.py - examines uploaded tar files for validity, makes a manifest"
# adds entry into titledb, and moves into production"
#
#__author__      = "Paul Gallagher"
#__copyright__   = "CC0 - openly shared into the public domain on behalf of MDPN"
#__version__     = 0.4
# Runs without any options ie python3 ./preprocess.py
# Expects the below configuration directories exist and have contents to process
# and that there is a titledb.xml file in the location specified. max_au_size sets the
# upper limit of the AU.
#########################################################

import os
import subprocess
import tarfile
import shutil
import xml.etree.ElementTree as ET

############################## Configuration fields ################################
source_dir = "/home/sftpuser/uploads/"  #works on all subfolders
destination_dir = "/var/www/html/staging"
titledb = "/var/www/html/mdpn/titledb/titledb.xml"
staging_url = "http://192.168.60.130/staging/" #LOCKSS crawable URL
max_au_size = 5000000000   #50gb
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
        tar.extract(member, path=extract_to)
        baginfo_file_path = os.path.join(extract_to, fname[0], 'bag-info.txt')
        
        #extract the manifest file
        member = tar.getmember(fname[0] + '/manifest-sha256.txt')
        tar.extract(member, path=extract_to)
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
    html_content = f"<html><head><title>{title} - LOCKSS Manifest Page</title></head><body><h1><a href='{url}'>{title}</a></h1><a href='bag-info.txt'><h3>bag-info.txt</h3></a><pre>{baginfo}</pre><h3>manifest-sha256.txt</h3><pre>{content}</pre>"       
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
                
                #validity checks
                if is_right_size(file_path):
                    if run_clamav_scan(file_path):
                            try:    #try and parse the tarball, get the manifest and bag-info, and create manifest
                                extract_and_convert_manifest(file_path, root)
                            except Exception as error:
                                print(f"Error: Failed to extract manifest from {file_path}", error)
                                                             
                            try:     #move the tarball into the folder with the manifest and bag-info file
                                shutil.move(file_path, os.path.join(root, fname[0], file))         #move tarball into the AU folder
                                shutil.move(file_path + '-clamav.txt', os.path.join(root, fname[0], 'clamav.txt'))         #move clamav.txt into the AU folder
                            except Exception as error:
                                print("Error moving tar or clamav.txt into au folder" + error)

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
                            
                            try: #try to move the file to production folder
                                #note, ran into a bug below if the staging folder isn't created, dumps file contents in the desination root
                                 au_folder = os.path.join(root, fname[0])
                                 shutil.move(au_folder, destination_dir) #move into the production folder
                            except Exception as error:
                                print(f"Copy to production error, {file} already exists?", error)
                    else:
                        print(f"Error: ClamAV scan failed for {file_path}")
                        os.remove(file_path) #get that stuff out of here!
                else:
                    print(f"Error: {file_path} is either zero bytes or greater than {max_au_size}")

if __name__ == "__main__":
    #do the main processing process_tar_files
    process_tar_files(source_dir)
