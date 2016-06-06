#!/usr/bin/env python

"""
Student/programmer: Marley Yeong
marleyyeong@live.nl
supervisor: Marnix Medema

Usage: score a network

"""

import os
import subprocess
import sys
from encodings import gbk

global verbose
verbose = False

def frange(start, stop, step):
    """Range function with float increments"""
    
    i = start
    while i <= stop:
        yield i
        i += step
         

def remove_values_from_list(the_list, val):
   return [value for value in the_list if value != val]


def get_anchor_domains(filename):
    """Get the anchor/marker domains from a txt file.
    This text file should contain one Pfam id per line"""

    domains = []
    
    try:
        handle = open(filename, 'r')
    except IOError:
        print "You have not provided the anchor_domains.txt file."
        print "if you want to make use of the anchor domains in the DDS distance metric,\
        make a file that contains a Pfam domain on each line."
        return []
        
    raw_domains = handle.readlines()
    for line in raw_domains:
        domains.append(line.strip())
    handle.close()
    return domains
        

def get_domain_list(filename):
    """Convert the Pfam string in the .pfs files to a Pfam list"""
    handle = open(filename, 'r')
    domains_string = handle.readline().strip()
    domains = domains_string.split(" ")
    return domains


def make_domains_output_name(args):
    foldername = "domains_" + "_".join(args)
    foldername = foldername.replace("/", "_")
    return foldername.replace(" ", "_") 
 

def make_network_output_name(args):
    foldername = "networks_" + "_".join(args)
    foldername = foldername.replace("/", "_")
    return foldername.replace(" ", "_")


def get_all_features_of_type(seq_record, types):
    "Return all features of the specified types for a seq_record"
    if isinstance(types, str):
        # force into a tuple
        types = (types, )
    features = []
    for f in seq_record.features:
        if f.type in types:
            features.append(f)
    return features


def get_hmm_output_files(output_folder):
    """Finds all .domtable files in the output folder and its child folders"""
    
    hmm_table_list = []
    for dirpath, dirnames, filenames in os.walk(str(output_folder) + "/"):
        for fname in filenames:
            if fname.split(".")[-1] == "domtable":
                try:
                    if open(output_folder + "/" + fname, "r").readlines()[3][0] != "#": #if this is false, hmmscan has not found any domains in the sequence
                        hmm_table_list.append(fname)
                        if verbose == True:
                            print fname
                    else:
                        print output_folder + "/" + fname, "seems to be an empty domtable file"
                    
                except IndexError:
                    print "IndexError on file", output_folder + "/" + fname

    return hmm_table_list


def check_overlap(pfd_matrix, overlap_cutoff):
    """Check if domains overlap for a certain overlap_cutoff.
     If so, remove the domain(s) with the lower score."""
     
    row1_count = 0
    delete_list = []
    for row1 in pfd_matrix:
        row1_count += 1
        row2_count = 0
        for row2 in pfd_matrix:
            row2_count += 1
            if row1_count != row2_count and row1[-1] == row2[-1]: #check if we are not comparing the same rows, but has the same CDS
                #check if there is overlap between the domains
                if no_overlap(int(row1[3]), int(row1[4]), int(row2[3]), int(row2[4])) == False:
                    overlapping_nucleotides = overlap(int(row1[3]), int(row1[4]), int(row2[3]), int(row2[4]))
                    overlap_perc_loc1 = overlap_perc(overlapping_nucleotides, int(row1[4])-int(row1[3]))
                    overlap_perc_loc2 = overlap_perc(overlapping_nucleotides, int(row2[4])-int(row2[3]))
                    #check if the amount of overlap is significant
                    if overlap_perc_loc1 > overlap_cutoff or overlap_perc_loc2 > overlap_cutoff:
                        if float(row1[1]) > float(row2[1]): #see which has a better score
                            delete_list.append(row2)
                        elif float(row1[1]) < float(row2[1]):
                             delete_list.append(row1)

    for lst in delete_list:
        try:
            pfd_matrix.remove(lst)
        except ValueError:
            pass
    try:    
        pfd_matrix = sorted(pfd_matrix, key=lambda pfd_matrix_entry: int(pfd_matrix_entry[3]))
    except ValueError:
        print "Something went wrong during the sorting of the fourth column (ValueError)"
        print pfd_matrix
        
    domains = []
    for row in pfd_matrix:
        domains.append(row[5]) #save the pfam domains for the .pfs file

    return pfd_matrix, domains                       
                        

def write_pfs(pfs_handle, domains):
    for domain in domains:
        pfs_handle.write(domain+" ")
    pfs_handle.close()
    

def write_pfd(pfd_handle, matrix):
    for row in matrix:
        row = "\t".join(row)
        pfd_handle.write(row+"\n")
        
    pfd_handle.close() 
    

def dct_writeout(handle, dct):
    for key in dct.keys():
        handle.write(key+"\n"+dct[key]+"\n")
    handle.close()


def check_data_integrity(gbk_files):
    """Perform some integrity checks on the input gbk files."""
    duplication = False
    if gbk_files == []:
        print "No .gbk files were found"
        sys.exit()
    
    gbk_files = list(iterFlatten(gbk_files))
    for file in gbk_files:
        name = file.split("/")[-1]
        file_occ = 0
        for cfile in gbk_files:
            
            cname = cfile.split("/")[-1]
            if name == cname:
                file_occ += 1
                if file_occ > 1:
                    duplication = True
                    print "duplicated file at:", cfile 
    
    if duplication == True:
        print "There was duplication in the input files, if this is not intended remove them."
        cont = raw_input("Continue anyway? Y/N ")
        if cont.lower() == "n":
            sys.exit()
            

def hmmscan(fastafile, outputdir, name, cores):
    """Runs hmmscan"""
    #removed --noali par

    hmmscan_cmd = "hmmscan --cpu " + str(cores) + " --domtblout " + str(outputdir)\
     + "/" +str(name) + ".domtable --cut_tc Pfam-A.hmm " + str(fastafile)
    if verbose == True:
        print hmmscan_cmd
        
    subprocess.check_output(hmmscan_cmd, shell=True)
    
    
def get_domains(filename):
    handle = open(filename, 'r')
    domains = []
    for line in handle:
        if line[0] != "#":
            domains.append(filter(None, line.split(" "))[1])
            
    return domains


def no_overlap(locA1, locA2, locB1, locB2):
    """Return True if there is no overlap between two regions"""
    if locA1 < locB1 and locA2 < locB1:
        return True
    elif locA1 > locB2 and locA2 > locB2:
        return True
    else:
        return False


def overlap_perc(overlap, len_seq):
    return float(overlap) / len_seq
    

def overlap(locA1, locA2, locB1, locB2):
    """Returns the amount of overlapping nucleotides"""

    if locA1 < locB1:
        cor1 = locA1
    else:
        cor1 = locB1

    if locA2 > locB2:
        cor2 = locA2
    else:
        cor2 = locB2

    total_region = cor2 - cor1
    sum_len = (locA2 - locA1) + (locB2 - locB1)

    return sum_len - total_region

  
def calc_perc_identity(seq1, seq2, spec_domain, spec_domain_nest, domain):
    """Percent Identity = Matches/Length of aligned region (with gaps) (sequence similarity!)
    Note that only internal gaps are included in the length, not gaps at the sequence ends."""

    al_len = min([len(seq1.strip("-")), len(seq2.strip("-"))])
    matches = 0
    for pos in range(len(seq1)): #Sequences should have the same length because they come from an MSA
        try:
            if seq1[pos] == seq2[pos] and seq1[pos] != "-":  #don't count two gap signs as a match!
                matches += 1
        except IndexError:
            print "Something went wrong, most likely your alignment file contains duplicate sequences"
            print "file: ", domain, "domains: ", spec_domain, spec_domain_nest
        
            

    return float(matches) / float(al_len), al_len    


def BGC_dic_gen(filtered_matrix):
    """Generates the: { 'general_domain_name_x' : ['specific_domain_name_1',
     'specific_domain_name_2'] } part of the BGCs variable."""
    bgc_dict = {}
    for row in filtered_matrix:
        try: #Should be faster than performing if key in dictionary.keys()
            bgc_dict[row[5]]
            bgc_dict[row[5]].append(str(row[0]) + "_" + str(row[-1]) + "_" + str(row[3]) + "_" + str(row[4]))
        except KeyError: #In case of this error, this is the first occurrence of this domain in the cluster
           bgc_dict[row[5]]=[str(row[0]) + "_" + str(row[-1]) + "_" + str(row[3]) + "_" + str(row[4])]
            
    return bgc_dict

    
def save_domain_seqs(filtered_matrix, fasta_dict, domains_folder, output_folder, outputbase):
    """Write fasta sequences for the domains in the right pfam-domain file"""
    for row in filtered_matrix:
        domain = row[5]
        seq = fasta_dict[">"+str(row[-1].strip())] #access the sequence by using the header
        

        domain_file = open(output_folder + "/" + domains_folder + "/" + domain +".fasta", 'a') #append to existing file
        domain_file.write(">" + str(row[0]) + "_" + str(row[-1]) + "_" + str(row[3]) + "_" + str(row[4]) \
        + "\n" + str(seq)[int(row[3]):int(row[4])] + "\n") #only use the range of the pfam domain within the sequence
        
#===============================================================================
# 
#         if str(seq)[int(row[3]):int(row[4])] == "":
#             print seq
#             print row[3], row[4]
#             print str(row[-1].strip())
#             print outputbase
#===============================================================================
            
        domain_file.close()
        

def fasta_parser(handle):
    """Parses a fasta file, and stores it in a dictionary.
    Only works if there are no duplicate fasta headers in the fasta file"""
    
    fasta_dict = {}
    header = ""
    for line in handle:
        if line[0] == ">":
            header=line.strip()
        else:
            try:
                fasta_dict[header] += line.strip()
            except KeyError:
                fasta_dict[header] = line.strip()

    return fasta_dict


def get_domain_fastas(domain_folder, output_folder):
    """Finds the pfam domain fasta files"""
    domain_fastas = []
    dirpath_ = ""
    for dirpath, dirnames, filenames in os.walk(output_folder + "/" + domain_folder + "/"):
        for fname in filenames:
            if ".fasta" in fname and "hat2" not in fname:
                dirpath_ = dirpath[:-1] if dirpath[-1] == "/" else dirpath
                domain_fastas.append(dirpath_ + "/" + fname)
                if verbose == True:
                    print fname
                    
    return domain_fastas


def iterFlatten(root):
    """'Flattens' a matrix by collapsing the lists into one list"""
    if isinstance(root, (list, tuple)):
        for element in root:
            for e in iterFlatten(element):
                yield e
    else:
        yield root


def distout_parser(distout_file):
    """returns similarity values, for domains in the following format  { ('specific_domain_name_1',
    'specific_domain_name_2'): (sequence_identity, alignment_length), ... }"""
    
    try:
        hat2_handle = open(distout_file, 'r')
    except IOError:
        return {}
    
    domain_pairs_dict = {}    
    linecounter = 0
    seqsdict = {}
    distances = [] #will be of length numberof_seqs * (numberof_seqs-1) / 2
    numberof_seqs = 0
    for line in hat2_handle:
        linecounter += 1
        if linecounter == 2: #contains number of sequences
            numberof_seqs = int(line.replace(" ", "").strip())
            
        elif linecounter >= 4 and linecounter <= 3 + numberof_seqs:
            try:
                #seq_number = int(re.search(r' \d*\. ', str(line.split("=")[0])).group(0).replace(".", "").replace(" ", ""))
                seq_number = int(line.split("=")[0].replace(" ", "").replace(".", ""))
            except AttributeError:
                print "something went wrong during the import of distout file: ", str(distout_file)
                
            
            seqsdict[seq_number] = "".join(line.split("=")[1:]).strip()#in case the header contains an = sign

        elif linecounter > 3 + numberof_seqs:
            distances += line.strip().split(" ")

    keys=[]
    if len(distances) != (numberof_seqs * (numberof_seqs-1)) / 2.0:
        print "something went horribly wrong in importing the distance matrix"
    else:
        print "distance matrix imported correctly"
        keys = seqsdict.keys()

    keys_queue = []
    for key in keys:
        keys_queue.append(key)

    tuples = []
    for key in keys:
        keys_queue.remove(key)
        for key_queue in keys_queue:
            tuples.append((key, key_queue))
            
    for tupl in range(len(tuples)):
        ##    { ('specific_domain_name_1',
        ##    'specific_domain_name_2'): (sequence_identity, alignment_length), ... }
        #1-distance is a representation of the sequence_identity
        domain_pairs_dict[tuple(sorted([seqsdict[tuples[tupl][0]], seqsdict[tuples[tupl][1]]]))] = (1-float(distances[tupl]), 0)

    return domain_pairs_dict


def write_network_matrix(matrix, cutoff, filename, include_disc_nodes):
    networkfile = open(filename, 'w+')
    clusters = [] # will contain the names of clusters that have an edge value lower than the threshold
    networkfile.write("clustername1\tclustername2\tgroup1\tdefinition\tgroup2\tdefinition\t-log2score\traw distance\tsquared similarity\tcombined group\tshared group\n")
    for row in matrix:
        temprow = []
        #if both clusters have the same group, this group will be annotated in the last column of the network file
        for i in row:
            temprow.append(i)
        
        if float(temprow[7]) <= float(cutoff):
            clusters.append(row[0])
            clusters.append(row[1])

            if row[2] != "" and row[4] != "": #group1, group2
                temprow.append(" - ".join(sorted([str(row[2]),str(row[4])])))
            elif row[4] != "":
                temprow.append(str(row[4]))
            elif row[2] != "":
                temprow.append(str(row[2]))
            else:
                 temprow.append(str("NA"))
            
            if row[2] == row[4]:
                temprow.append(row[2])
            else:
                temprow.append("")
                
            networkfile.write("\t".join(temprow) + "\n")

            
    if include_disc_nodes == True:  
        #Add the nodes without any edges, give them an edge to themselves with a distance of 0 
        clusters = set(clusters)
        passed_clusters = []
        for row in matrix:
            if row[0] not in clusters and row[0] not in passed_clusters:
                networkfile.write("\t".join([row[0],row[0],row[2],row[3],'','',str(0),str(0),str(0),'','']) + "\n")
                passed_clusters.append(row[0])
            elif row[1] not in clusters and row[1] not in passed_clusters:
                networkfile.write("\t".join([row[1],row[1],row[4],row[5],'','',str(0),str(0),str(0),'','']) + "\n")
                passed_clusters.append(row[1])
            
    networkfile.close()
                    

def get_gbk_files(inputdir, samples, min_bgc_size, exclude_gbk_str):
    """Find .gbk files, and store the .gbk files in lists, separated by sample."""
    genbankfiles=[] #Will contain lists of gbk files
    dirpath_ = ""
    file_counter = 0
    
    print "Importing the gbk files, while skipping gbk files with", exclude_gbk_str, "in their filename"
    
    if inputdir != "" and inputdir[-1] != "/":
        inputdir += "/"
        
    for dirpath, dirnames, filenames in os.walk(inputdir):
        genbankfilelist=[]
        
        #avoid double slashes
        dirpath_ = dirpath[:-1] if dirpath[-1] == "/" else dirpath
        
        for fname in filenames:
            if fname.split(".")[-1] == "gbk" and exclude_gbk_str not in fname:
                if " " in fname:
                    print "Your GenBank files should not have spaces in their filenames. Please remove the spaces from their names, HMMscan doesn't like spaces (too many arguments)."
                    sys.exit(0)
                
                gbk_header = open(dirpath_ + "/" + fname, "r").readline().split(" ")
                gbk_header = filter(None, gbk_header) #remove the empty items from the list
                bgc_size = int(gbk_header[gbk_header.index("bp")-1])
                    
                file_counter += 1
                if bgc_size > min_bgc_size: #exclude the bgc if it's too small
                    genbankfilelist.append(dirpath_ + "/" + fname)
                    
                    if samples == False: #Then each gbk file represents a different sample
                        genbankfiles.append(genbankfilelist)
                        genbankfilelist = []
                    
                if verbose == True:
                    print fname
                    print "bgc size in bp", bgc_size
                    
        if genbankfilelist != []:
            genbankfiles.append(genbankfilelist)

    return genbankfiles


def domtable_parser(gbk, dom_file):
    """Parses the domain table output files from hmmscan"""
    
##example from domain table output:
# target name        accession   tlen query name                                    accession   qlen   E-value  score  bias   #  of  c-Evalue  i-Evalue  score  bias  from    to  from    to  from    to  acc description of target
#------------------- ---------- -----                          -------------------- ---------- ----- --------- ------ ----- --- --- --------- --------- ------ ----- ----- ----- ----- ----- ----- ----- ---- ---------------------
#Lycopene_cycl        PF05834.8    378 loc:[0:960](-):gid::pid::loc_tag:['ctg363_1'] -            320   3.1e-38  131.7   0.0   1   1   1.1e-40   1.8e-36  126.0   0.0     7   285    33   295    31   312 0.87 Lycopene cyclase protein
    
#pfd_matrix columns: gbk filename - score - gene id - first coordinate - second coordinate - pfam id - domain name -start coordinate of gene - end coordinate of gene - cds header
    
    pfd_matrix = []
    dom_handle = open(dom_file, 'r')
    for line in dom_handle:
        
        if line[0] != "#":

            splitline = filter(None, line.split(" "))
            pfd_row = []
            pfd_row.append(gbk)         #add clustername or gbk filename
            
            pfd_row.append(splitline[13]) #add the score

            header_list = splitline[3].split(":")
            try:
                pfd_row.append(header_list[header_list.index("gid")+1]) #add gene ID if known
            except ValueError:
                print "No gene ID in ", gbk
                pfd_row.append('')
                
            pfd_row.append(splitline[19])#first coordinate, env coord from
            pfd_row.append(splitline[20])#second coordinate, env coord to
            
            #===================================================================
            # loc_split = header_list[2].split("]") #second coordinate (of CDS) and the direction
            # pfd_row.append(loc_split[1]) #add direction          
            #===================================================================
            
            pfd_row.append(splitline[1]) #pfam id
            pfd_row.append(splitline[0]) #domain name
            pfd_row.append(header_list[header_list.index("loc")+1]) #start coordinate of gene
            pfd_row.append(header_list[header_list.index("loc")+2]) #end coordinate of gene
            
            pfd_row.append(splitline[3])#cds header
            pfd_matrix.append(pfd_row)


    return pfd_matrix



def hmm_table_parser(gbk, hmm_table):
##AB050629.gbk    score   yxjC    1    1167    +    PF03600    CitMHS

##example from hmm table output:
##Thiolase_N           PF00108.19 loc:[2341:3538](+):gid::pid::loc_tag:['ctg4508_7'] -
##8.2e-90  300.5   2.3   1.2e-89  300.0   2.3   1.2   1   0   0   1   1   1   1 Thiolase, N-terminal domain

    pfd_matrix = []

    handle = open(hmm_table, 'r')
    for line in handle:
        
        if line[0] != "#":
            
            splitline = filter(None, line.split(" "))
            pfd_row = []
            pfd_row.append(gbk)
            pfd_row.append(splitline[5]) #add the score

##example of header_list ['loc', '[2341', '3538](+)', 'gid', '', 'pid', '', 'loc_tag', "['ctg4508_7"]]

            header_list = splitline[2].split(":")
            pfd_row.append(header_list[header_list.index("gid")+1])
            pfd_row.append(header_list[1].replace("[", "")) #first coordinate
            loc_split = header_list[2].split("]") #second coordinate and the direction
            pfd_row.append(loc_split[0])
            pfd_row.append(loc_split[1])

            pfd_row.append(splitline[1])
            pfd_row.append(splitline[0])
            
            pfd_matrix.append(pfd_row)

    return pfd_matrix


