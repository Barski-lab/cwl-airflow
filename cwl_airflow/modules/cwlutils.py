# CWL utils
# File with help functions.
import urlparse
import os
import glob
from airflow import configuration
from airflow.exceptions import AirflowConfigException

def shortname(n):
    # return n.split("#")[-1].split("/")[-1]
    return n.split("#")[-1]

def flatten(input_list):
    result = []
    for i in input_list:
        if isinstance(i,list): result.extend(flatten(i))
        else: result.append(i)
    return result

def url_shortname(inputid):
    d = urlparse.urlparse(inputid)
    if d.fragment:
        return d.fragment.split(u"/")[-1]
    else:
        return d.path.split(u"/")[-1]

def conf_get_default (section, key, default):
    try:
        return configuration.get(section, key)
    except AirflowConfigException:
        return default


def get_only_files (jobs, key, excl_key = None):
    key_filtered = []
    for item in jobs:
        key_filtered.extend(\
                            [ filename for filename in glob.iglob(item[key]+"/*") if \
                                    (not excl_key and os.path.isfile(filename)) or \
                                    (excl_key and os.path.isfile(filename) and \
                                     os.path.basename(filename) not in [os.path.basename(excl_filename) for excl_filename in glob.iglob(item[excl_key]+"/*")])\
                                    ]\
                            )                              
    return key_filtered


def set_permissions (item, dir_perm=0777, file_perm=0666, grp_own = os.getgid(), user_own=-1):
    os.chown(item, user_own, grp_own)
    if os.path.isfile(item):
        os.chmod(item, file_perm)
    else:
        os.chmod(item, dir_perm)
        for root, dirs, files in os.walk(item):
            for file in files:
                os.chmod(os.path.join(root,file), file_perm)
                os.chown(os.path.join(root,file), user_own, grp_own)
            for dir in dirs:
                os.chmod(os.path.join(root,dir), dir_perm)
                os.chown(os.path.join(root,dir), user_own, grp_own)