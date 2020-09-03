#!/usr/bin/env python3

import argparse, sys
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import os, re
import requests
import subprocess
import threading, time
import queue
import itertools

QUEUE = queue.Queue()
DOWNLOADED = []
BASEURL = ""
BASEDIR = ""
GITDIR = ""
BASEGITDIR = ""

thread_number = 10
checked_urls_num = itertools.count()
# Safe print()
mylock = threading.Lock()
def sprint(*a, **b):
    with mylock:
        print(*a, **b)

#
# Processor
#
class ProcessThread(threading.Thread):
    def __init__(self, id):
        threading.Thread.__init__(self)
        self.id = id
        self.run_loop = True

    # ...
    def run(self):
        global QUEUE
        while self.run_loop:
            task = QUEUE.get()
            download_item(task, QUEUE, self.id)

            next(checked_urls_num)
            QUEUE.task_done()


    def terminate(self):
        self.run_loop = False
        sprint("Thread #%d is down..." % (self.id))


        
def main():
    global QUEUE
    global DOWNLOADED
    global BASEURL
    global BASEDIR
    global GITDIR
    global BASEGITDIR
    global thread_number
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
    parser.add_argument('-u', '--url', help='input url')
    parser.add_argument('-d', '--dest', help='destination dir')
    parser.add_argument('-t', '--threads', default=10, help='threads')
    args = parser.parse_args()

    
    if args.url == None or args.dest == None:
        parser.print_usage()
        return

    try:
        thread_number = int(args.threads)
    except ValueError as err:
        sys.exit(err)


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
    
    print("Starting with Settings:")
    print("\033[35mUrl:\033[0m "+args.url)
    print("\033[35mDestination Dir:\033[0m "+args.dest)
    print("\033[35mThreads:\033[0m "+str(args.threads))
    print("")
    start_download()


def start_download():
    #Add initial/static git files
    global QUEUE
    global DOWNLOADED
    global BASEURL
    global BASEDIR
    global GITDIR
    global BASEGITDIR
    global checked_urls_num
    
    QUEUE.put('HEAD')
    QUEUE.put('objects/info/packs')
    QUEUE.put('description')
    QUEUE.put('config')
    QUEUE.put('COMMIT_EDITMSG')
    QUEUE.put('index')
    QUEUE.put('packed-refs')
    QUEUE.put('refs/heads/master')
    QUEUE.put('refs/remotes/origin/HEAD')
    QUEUE.put('refs/stash')
    QUEUE.put('logs/HEAD')
    QUEUE.put('logs/refs/heads/master')
    QUEUE.put('logs/refs/remotes/origin/HEAD')
    QUEUE.put('info/refs')
    QUEUE.put('info/exclude')
    QUEUE.put('/refs/wip/index/refs/heads/master')
    QUEUE.put('/refs/wip/wtree/refs/heads/master')
    QUEUE.put('FETCH_HEAD') #
    QUEUE.put('ORIG_HEAD') #

    # Spawn worker threads
    workers = []
    for i in range(0, thread_number):
        t = ProcessThread(i)
        t.setDaemon(True)
        t.start()
        workers.append(t)

    # count time
    start_time = time.time()

    # Wait for queue to get empty

    try:
        while QUEUE.empty() == False:
            time.sleep(0.1)
            pass
    except KeyboardInterrupt:
        sprint("Przerwij !!!")
        for worker in workers:
            worker.terminate()
        sys.exit(0)
        return

    QUEUE.join()

    sprint("Puste queue")
    time.sleep(5)
    QUEUE.join()
    sprint("serio Puste queue")

    for worker in workers:
        worker.terminate()

    # Print some info
    end_time = time.time()
    checked_urls_num = int(next(checked_urls_num))

    print("Time elapsed: %.1f seconds." % (end_time - start_time))
    print("checked_urls_num: %d" % (checked_urls_num))
    print("Bye-bye!")



def download_item(objname, QUEUE, thread_id):
    #global QUEUE
    global DOWNLOADED
    global BASEURL
    global BASEDIR
    global GITDIR
    global BASEGITDIR


    url= BASEURL+objname

    #Check if file has already been downloaded
    if objname in DOWNLOADED:
        return None
    
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
        
        sprint("\033[31m[-] Thread #"+str(thread_id)+"\t Done:"+str(len(DOWNLOADED))+"\t Left:"+str(QUEUE.qsize())+"\t Downloaded: "+objname+"\033[0m")
        return None
    sprint("\033[32m[+] Thread #"+str(thread_id)+"\t Done:"+str(len(DOWNLOADED))+"\t Left:"+str(QUEUE.qsize())+"\t Downloaded: "+objname+"\033[0m")

    #Check if we have an object hash
    if re.search(r'/[a-f0-9]{2}/[a-f0-9]{38}', objname):
        #Switch into $BASEDIR and save current working directory
        # unnesesssary >  cwd=BASEDIR in subprocess.run

        #Restore hash from $objectname
        hhash = objname.replace("/","").replace("objects","")
        command = str("git cat-file -t "+hhash+"").split(" ")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=BASEDIR, universal_newlines=True, encoding="utf-8")
        #sprint("r1 {0} {1} {2} {3}".format(objname, result.returncode, result.stdout, result.stderr)) # debug
        if (result.returncode != 0):
            #Delete invalid file
            try:
                os.remove(target)
            except:
                pass
            return None

        #Parse output of git cat-file -p $hash. Use strings for blobs
        if "blob" not in str(result.stdout):
            command = str("git cat-file -p "+hhash+"").split(" ")
            result2 = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=BASEDIR, universal_newlines=True, encoding="utf-8")
        else:
            command = str("git cat-file -p "+hhash+" | strings -a").split(" ")
            result2 = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=BASEDIR, universal_newlines=True, encoding="utf-8")
        #sprint("CRASH R2 {0} {1}".format(command, objname))
        #result2 = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=BASEDIR, encoding="utf-8")
        #sprint("r2 {0} {1} {2} {3}".format(objname, result2.returncode, result2.stdout, result2.stderr)) # debug

        matches = re.finditer(r"([a-f0-9]{40})", result2.stdout, re.MULTILINE)
        for match in matches:
            QUEUE.put("objects/"+match.group()[0:2]+"/"+match.group()[2:]+"")
        # end if

    #Parse file for other objects
    matches = re.finditer(r"([a-f0-9]{40})", r.text, re.MULTILINE)
    for match in matches:
        QUEUE.put("objects/"+match.group()[0:2]+"/"+match.group()[2:]+"")

    #Parse file for packs
    matches = re.finditer(r"(pack\-[a-f0-9]{40})", r.text, re.MULTILINE)
    for match in matches:
        QUEUE.put("objects/pack/"+match.group()+".pack")
        QUEUE.put("objects/pack/"+match.group()+".idx")

    return None

if __name__ == '__main__':
    main()
