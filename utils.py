import os
import re
import traceback


def exclude(a, b):
    if not b: return a
    #if not isinstance(y,list):y=[y]
    new_list=[]
    for fruit in a:
        if fruit not in b:
            new_list.append(fruit)
    return new_list
def any_re(patter,stri):
    try:
        find=re.match(patter,stri)
        if find is not None:
            return any(find.group())
    except:traceback.print_exc()
    return False

def ensure_directory_exists(filename):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
