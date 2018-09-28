import re,csv,os,MySQLdb
from collections import Counter
import sys
sys.path.append('{}/{}'.format(os.getcwd(), 'Development'))
from helpers import general_helpers
import multiprocessing
from collections import defaultdict
from itertools import islice


def dict_setup(working_directory, persistent_files):
    """
    Function to setup dictionaries that will be used later
    
    Input:
        working_directory(str): the path of the working directory
        persistent_files(str): the path of where 'ipc_technology.csv' lives
    
    Output:
        ipc_to_field(dict): a dictionary of {ipc:field}
        cpc_to_ipc(dict): a dictionary of {cpc:ipc}
    
    """
    ###### IPC to WIPO lookup ######

    # input ipc_technology data from local, which contains IPC technology class definitions
    ipc_technology = csv.reader(open(persistent_files+'\\ipc_technology.csv','rb'))
    # skip the header when parsing the data
    next(ipc_technology, None)

    # create a dictionary mapping IPC code to field number
    # key: IPC_code
    # value: Sector_en
    ipc_to_field = {}
    for row in ipc_technology:
        ipc_to_field[row[7].replace("%","").replace(' ','')] = row[0]


    ###### CPC to IPC mapping ######

    # input ipc_concordance data from local
    ipc_concordance = open(working_directory + "\\" + "ipc_concordance.txt").read().split("\n")

    # create a dictionary mapping CPC to IPC
    # key: IPC_code: first column
    # value: CPC_code: second column
    cpc_to_ipc = {}
    for row in ipc_concordance:
        row = row.split("\t\t")
        # keep only rows that do not have null value in the dataset
        if len(row) > 1 and row[1] != "CPCONLY":
            cpc_to_ipc[row[0]] = row[1]

    return ipc_to_field, cpc_to_ipc


# In[4]:

def get_data(db_con):
    """
    Function to connect the database
    
    Input:
        db_con : database connection
    
    Output:
        pat_to_subgroup(list): a list of tuples with [(patent_id, subgroup_id)]
    
    """
    

    #get a list of patent ids and cpc subgroup ids from the database
    data  = db_con.execute('select distinct patent_id,subgroup_id from cpc_current where category="inventional" order by patent_id asc,sequence asc')
    pat_to_subgroup = [(item['patent_id'], item['subgroup_id']) for item in data] #[patent_id, subgroup_id]
    
    return pat_to_subgroup




def write_cpc2ipc(working_directory, pat_to_subgroup, cpc_to_ipc, ipc_to_field, output):
    """
    Function to write file WIPO_Cats_assigned_CPC2IPC
    
    Input:
        working_directory(str): the path of the working directory
        pat_to_subgroup(list): output of function get_data
        cpc_to_ipc(dict): output of function dict_setup
        ipc_to_field(dict): output of function dict_setup
    
    Output:
        pats(dict): a dictionary of {patent_id:cpc_id}
    
    """
    #Initiate a pats dict here
    # key: patent_id
    # value: corresponding wipo
    pats = {}
    #os.mkdir(working_directory + "\\WIPO_output\\")
    outp= csv.writer(file('{0}/{1}'.format(working_directory,output),'wb'),delimiter = '\t')
    cpc_to_ipc_set = set(cpc_to_ipc.keys()) #to make the lookup faster
    ipc_to_field_set = set(ipc_to_field.keys())
    #outp.writerow(['patent_id','cpc','wipo_cat'])
    counter = 0
    for item in pat_to_subgroup: #[patent_id, subgroup_id]
        counter +=1
        if counter%10000==0:
            print(counter)
        #check if subgroup_id is in the cpc_to_ipc dictionary
        #if yes, and to a new variable -- ipcconcord
        if item[1] in cpc_to_ipc_set:
            ipcconcord = cpc_to_ipc[item[1]]
        #if it's not in the dict cpc_to_ipc
        else:
            #make 'ipcconcord' equal to the cpc subgroup_id
            ipcconcord = item[1]    


        #get the patant id and cpc id of each entry   
        patent_id = item[0]
        cpc_id = item[1]
        #get the section id and group id
        section = ipcconcord[:4]
        group = ipcconcord.split("/")[0]


        #check if section is in the ipc_to_field dictionary
        #if yes, assign the field to a new variable -- wipo
        if section in ipc_to_field_set:
             wipo = ipc_to_field[section]
        #if not, look for group instead of section
        elif group in ipc_to_field_set:
            wipo = ipc_to_field[group]
        #otherwise, skip the entry
        else:
            pass

        #write the patent number, cpc_subgroup_id and wipo classification to the 'WIPO_Cats_assigned_CPC2IPC.csv' file
        outp.writerow([patent_id,cpc_id,wipo])
 



def write_wipo_assigned(working_directory, output, pats):
    """
    Function to write file WIPO_Cats_assigned
        For each patent_id, the top three wipo are listed (ties allowed)
    
    Input:
        working_directory(str): the path of the working directory
        pats: output of function write_cpc2ipc
    
    """
    #have this go over the full output file from before and grab the patent_id and cpc list

    outp= csv.writer(file('{0}/{1}'.format(working_directory,output),'wb'),delimiter = '\t')

    for k,v in pats.items():
        cpc_count_list = sorted(Counter(v).items(),key=lambda x:-x[1])

        #get the top three counter
        counter_list = []
        for cpc in cpc_count_list:
            counter_list.append(cpc[1])
        # a list of top three frequencies that are sorted in descending order
        end_point = max(len(set(counter_list)), 3)
        top_three_counter = sorted(list(set(counter_list)), reverse=True)[0:end_point]


        #keep only the cpc's with appearance that is in top 3 list
        return_cpc_list = [] # a listo f cpc's with top three appearance -- ties exist
        for cpc in cpc_count_list:
            if cpc[1] in top_three_counter:
                return_cpc_list.append(cpc[0])

        for e, cpc in enumerate(return_cpc_list):
            #print([k,return_cpc_list[i],i])
            outp.writerow([k,cpc,e])


def dict_chunks(data, size):
    it = iter(data)
    for i in xrange(0, len(data), size):
        yield {k:data[k] for k in islice(it, size)}


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('Development/config.ini')

    location_of_cpc_ipc_file = '{}/{}'.format(config['FOLDERS']['WORKING_FOLDER'], 'cpc_input')
    wipo_output = '{}/{}'.format(config['FOLDERS']['WORKING_FOLDER'], 'wipo_output')
    if not os.path.exists(wipo_output):
        os.makedir(wipo_output)
    persistent_files = config['FOLDERS']['PERSISTENT_FILES']

    #dictionary setup 
    print("dict setup")
    ipc_to_field, cpc_to_ipc = dict_setup(location_of_cpc_ipc_file, persistent_files)

    
    #connect database
    db_con = general_helpers.connect_to_db(config['DATABASE']['HOST'], config['DATABASE']['USERNAME'], config['DATABASE']['PASSWORD'], config['DATABASE']['NEW_DB'])
    print("getting data")
    pat_to_subgroup = get_data(db_con)
    #TODO: check that this works with new data
    print(len(pat_to_subgroup))

    chunks_of_patent = general_helpers.chunks(pat_to_subgroup, (len(pat_to_subgroup)/7)+1)

    outfiles = ['wipo_cats_assigned_cpc2ipc_{}'.format(item) for item in ['a', 'b', 'c', 'd', 'e', 'f', 'g']]
    working_directories = [wipo_output for _ in infiles]
    cpc_to_ipcs = [cpc_to_ipc for _ in infiles]
    ipc_to_fields = [ipc_to_field for _ in infiles]

    input_data = zip(working_directories, chunks_of_patent, cpc_to_ipcs, ipc_to_fields, outfiles)#

    desired_processes = 7 # ussually num cpu - 1
    jobs = []
    for f in input_data:
        jobs.append(multiprocessing.Process(target = write_cpc2ipc, args=(f)))

    for segment in chunks(jobs, desired_processes):
        for job in segment:
            job.start()

    print('making dictionary')
    patent_input= csv.reader(file('{0}/WIPO_output/WIPO_Cats_assigned_CPC2IPC.csv'.format(working_directory),'rb'),delimiter = '\t')
    pats = defaultdict(lambda: [])
    for row in patent_input:
        pats[row[0]].append(row[2])
    print(len(pats))
    print("Made dictionary")


    data_chunks = list(dict_chunks(pats, (len(pats)/7) + 1))
    working_directories = [working_directory for _ in data_chunks]
    outfiles = ['patent_cpc_v2_{}'.format(item) for item in ['a', 'b', 'c', 'd', 'e', 'f', 'g']]
    print("chunked")
    print len(data_chunks)
    input_data = zip(working_directories, outfiles, data_chunks)
    print("starting")
    desired_processes = 7 # ussually num cpu - 1
    jobs = []
    for f in input_data:
        jobs.append(multiprocessing.Process(target = write_wipo_assigned, args=(f)))
    print("appended")
    for segment in chunks(jobs, desired_processes):
        print(segment)
        for job in segment:
            job.start()
