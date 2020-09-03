#!/usr/bin/env python3
import sys, os, subprocess, time
import threading
import queue

print("""###########
# Extractor is part of https://github.com/internetwache/GitTools
#
# Developed and maintained by @gehaxelt from @internetwache
# Revrited to python by Gorlik
# 
# Use at your own risk. Usage might be illegal in certain circumstances. 
# Only for educational purposes!
###########""")


if len(sys.argv) != 3 and len(sys.argv) != 4:
    print("\033[33m[*] USAGE: extractor.sh GIT-DIR DEST-DIR [thread_number] \033[0m")
    sys.exit(1)

GITDIR = sys.argv[1]
DESTDIR = sys.argv[2]

try:
    thread_number = int(sys.argv[3])
except ValueError as err:
    sys.exit(err)

QUEUE = queue.Queue()

if os.path.exists(GITDIR+"/.git") == False:
    print("\033[31m[-] There's no .git folder \033[0m")
    sys.exit(0)

if os.path.isdir(DESTDIR) == False:
    print("\033[33m[*] Destination folder does not exist\033[0m")
    print("\033[32m[+] Creating "+DESTDIR+"\033[0m")
    os.makedirs(DESTDIR)


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

    def run(self):
        global QUEUE
        while self.run_loop:
            task = QUEUE.get()

            if(task["task_type"] == "save2file"):
                file_ = open(task["_file_path"], "w")
                subprocess.Popen(task["command"], stdout=file_, stderr=subprocess.PIPE, cwd=GITDIR, universal_newlines=True)
            elif(task["task_type"] == "traverse_commit"):
                traverse_commit(task["TARGETDIR"], task["objecthash"], task["COMMITCOUNT"], str(self.id))
            elif(task["task_type"] == "traverse_tree"):
                traverse_tree(task["tree"], task["path"], thread_id=task["thread_id"])
            else:
                sprint(task)
            QUEUE.task_done()

    def terminate(self):
        self.run_loop = False
        sprint("Thread #%d is down..." % (self.id))


def traverse_tree(tree, path, thread_id="+"):
    #Read blobs/tree information from root tree
    
    command = str('git ls-tree {0}').format(tree).split(" ")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=GITDIR, universal_newlines=True)
    for leaf in result.stdout.split("\n"):
        leaf = leaf.replace("\t"," ")
        if leaf == "":
            continue
        type = leaf.split(" ")[1]
        hash = leaf.split(" ")[2]
        name = leaf.split(hash)[1].strip()
        
        # Get the blob data
        command = str("git cat-file -e "+hash+"").split(" ")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=GITDIR, universal_newlines=True)
        if (result.returncode != 0):
            #Ignore invalid git objects (e.g. ones that are missing)
            continue
        
        if type == "blob":
            sprint("\33[32m["+thread_id+"] Found file: {0}\33[0m".format(path+"/"+name))
            command = str('git cat-file -p {0}').format(hash).split(" ")            
            QUEUE.put({"task_type":"save2file", "command":command, "_file_path":path+"/"+name })
        else:
            sprint("\33[34m["+thread_id+"] Found folder: {0}\33[0m".format(path+"/"+name))
            try:
                os.makedirs(path+"/"+name)
            except:
                pass
            #Recursively traverse sub trees
            QUEUE.put({"task_type":"traverse_tree", "tree":hash, "path":path+"/"+name, "thread_id":thread_id})

    return

def traverse_commit(base, commit, count, thread_id="+"):
    #Create folder for commit data
    sprint("\033[33m["+thread_id+"] Found commit: {0}\033[0m".format(commit))
    path="{0}/{1}-{2}".format(base, count, commit)
    try:
        os.makedirs(path)
    except:
        pass

    #Add meta information
    command = str('git cat-file -p {0}').format(commit).split(" ")
    QUEUE.put({"task_type":"save2file", "command":command, "_file_path":path+"/commit-meta.txt" })

    #Try to extract contents of root tree
    traverse_tree(commit, path, thread_id=thread_id)
    return

# Spawn worker threads
workers = []
for i in range(0, thread_number):
    t = ProcessThread(i)
    t.setDaemon(True)
    t.start()
    workers.append(t)

start_time = time.time()
#Current directory as we'll switch into others and need to restore it.
OLDDIR = os.getcwd()
TARGETDIR = DESTDIR
COMMITCOUNT=0


#If we don't have an absolute path, add the prepend the CWD
TARGETDIR = os.path.abspath(OLDDIR+"/"+TARGETDIR)

hashes=[]
#Extract all object hashes
for directory, subdirectories, files in os.walk(GITDIR+"/.git/objects"):
        for file in files:
            h = directory[-2:]+file
            hashes.append(h)

for objecthash in hashes:
    command = str("git cat-file -t "+objecthash+"").split(" ")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=GITDIR, universal_newlines=True)
    
    # Only analyse commit objects
    if "commit" in result.stdout:
        QUEUE.put({"task_type":"traverse_commit", "TARGETDIR":TARGETDIR, "objecthash":objecthash, "COMMITCOUNT":COMMITCOUNT })
        COMMITCOUNT=COMMITCOUNT+1

try:
    while QUEUE.empty() == False:
        time.sleep(0.1)
        pass
except KeyboardInterrupt:
    sprint("Przerwij !!!")
    for worker in workers:
        worker.terminate()
    sys.exit(0)

QUEUE.join()

sprint("Empty queue")
time.sleep(5)
QUEUE.join()
sprint("Realy Empty queue")

for worker in workers:
    worker.terminate()
        
end_time = time.time()
print("Time elapsed: %.1f seconds." % (end_time - start_time))