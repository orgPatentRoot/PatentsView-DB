#Count Null and Blank QA

#set up sql alchemy engine
import pandas as pd
import os
import configparser
import sys
sys.path.append('/project/Development')
from helpers import general_helpers
import configparser
config = configparser.ConfigParser()
config.read('/project/Development/config.ini')
host = config['DATABASE']['HOST']
username = config['DATABASE']['USERNAME']
password = config['DATABASE']['PASSWORD']
new_database = config['DATABASE']['NEW_DB']
old_database = config['DATABASE']['OLD_DB']
temporary_upload = config['DATABASE']['TEMP_UPLOAD_DB']
previous_qa_loc = config['FOLDERS']['OLD_QA_LOC']
new_qa_loc = config['FOLDERS']['OLD_QA_LOC']
latest_expected_date = config['CONSTANTS']['LATEST_DATE']

engine = general_helpers.connect_to_db(host, username, password, new_database)
data = pd.read_excel("{}/1_null_and_blank_count.xlsx".format(previous_qa_loc))
#print (data.head())

def count_null_and_blank(new_database, previous_qa_loc):
    tc = pd.read_excel('{}/1_null_and_blank_count.xlsx'.format(previous_qa_loc))
    table_col_dict = zip(tc['Table'], tc['Column'])
    results = []
    for table, col in table_col_dict:
        try:
            counts = engine.execute("select count(*) from {0}.{1} where `{2}` is null or `{2}` = '';".format(new_database, table, col))
            results.append(counts)
            print ("{0}.{1}: {2}".format(table, col, counts))
        except:
            results.append("Error: Problem with {0}.{1}".format(table, col))
            print ("Error: Problem with {0}.{1}".format(table, col) )
    return results
def increase_10_percent_desc(newdb_count, olddb_count, accept_inc):
    try:
        int(newdb_count)
        int(olddb_count)
        if newdb_count < olddb_count:
            return "Problem: Less nulls in current update than previous update."
        elif newdb_count > (olddb_count * accept_inc):
            return "Problem: Too many new nulls."
        elif olddb_count <= newdb_count <= olddb_count * accept_inc:
            return "No Problem!"
        else:
            return "Check the logic!"
    except:
        return "Problem : {}" .format(newdb_count)
def null_to_excel(newdb_results,previous_qa_loc, new_qa_loc, new_database):
    df = pd.read_excel('{}/1_null_and_blank_count.xlsx'.format(previous_qa_loc))
    df_2 = pd.DataFrame(newdb_results)
    df_2.rename(columns={0:new_database}, inplace = True)
    df_3 = pd.concat([df, df_2], axis = 1)
    df_3.drop(['Description'], inplace = True, axis = 1)
    df_3['Description'] = df_3.apply(lambda row: increase_10_percent_desc(row[df_3.columns[-1]], row[df_3.columns[-2]], 1.1), axis=1)
    df_3.to_excel('{}/1_null_and_blank_count.xlsx'.format(new_qa_loc), index = False)

null_results = count_null_and_blank(new_database, previous_qa_loc)
null_to_excel(null_results, previous_qa_loc, new_qa_loc, new_database)