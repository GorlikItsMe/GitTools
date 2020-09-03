import sys, os, subprocess




print("""###########
# Extractor is part of https://github.com/internetwache/GitTools
#
# Developed and maintained by @gehaxelt from @internetwache
#
# Use at your own risk. Usage might be illegal in certain circumstances. 
# Only for educational purposes!
###########""")


if len(sys.argv) != 3:
    print("\033[33m[*] USAGE: extractor.sh GIT-DIR DEST-DIR \033[0m")
    sys.exit(1)

GITDIR = sys.argv[1]
DESTDIR = sys.argv[2]

if os.path.exists(GITDIR+"/.git") == False:
    print("\033[31m[-] There's no .git folder \033[0m")
    sys.exit(0)


if os.path.isdir(DESTDIR) == False:
    print("\033[33m[*] Destination folder does not exist\033[0m")
    print("\033[32m[+] Creating "+DESTDIR+"\033[0m")
    os.makedirs(DESTDIR)


def traverse_tree(tree, path):
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
        #print(type, hash, name)
        
        # Get the blob data
        command = str("git cat-file -e "+hash+"").split(" ")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=GITDIR, universal_newlines=True)
        if (result.returncode != 0):
            #Ignore invalid git objects (e.g. ones that are missing)
            continue
        
        if type == "blob":
            print("\33[32m[+] Found file: {0}\33[0m".format(path+"/"+name))
            command = str('git cat-file -p {0}').format(hash).split(" ")            
            file_ = open(path+"/"+name, "w")
            result = subprocess.Popen(command, stdout=file_, stderr=subprocess.PIPE, cwd=GITDIR, universal_newlines=True)
        else:
            print("\33[34m[+] Found folder: {0}\33[0m".format(path+"/"+name))
            try:
                os.makedirs(path+"/"+name)
            except:
                pass
            #Recursively traverse sub trees
            traverse_tree(hash, path+"/"+name)
    return

def traverse_commit(base, commit, count):
    #Create folder for commit data
    print("\033[33m[+] Found commit: {0}\033[0m".format(commit))
    path="{0}/{1}-{2}".format(base, count, commit)
    try:
        os.makedirs(path)
    except:
        pass

    #Add meta information
    command = str('git cat-file -p {0}').format(commit).split(" ")
    file_ = open(path+"/commit-meta.txt", "w")
    result = subprocess.Popen(command, stdout=file_, stderr=subprocess.PIPE, cwd=GITDIR, universal_newlines=True)

    #Try to extract contents of root tree
    traverse_tree(commit, path)
    return


#Current directory as we'll switch into others and need to restore it.
OLDDIR = os.getcwd()
TARGETDIR = DESTDIR
COMMITCOUNT=0


#If we don't have an absolute path, add the prepend the CWD
TARGETDIR = os.path.abspath(OLDDIR+"/"+TARGETDIR)

#Extract all object hashes
hashes = []
for directory, subdirectories, files in os.walk(GITDIR+"/.git/objects"):
        for file in files:
            h = directory[-2:]+file
            hashes.append(h)

for objecthash in hashes:
    command = str("git cat-file -t "+objecthash+"").split(" ")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=GITDIR, universal_newlines=True)
    
    # Only analyse commit objects
    if "commit" in result.stdout:
        traverse_commit(TARGETDIR, objecthash, COMMITCOUNT)
        COMMITCOUNT=COMMITCOUNT+1
