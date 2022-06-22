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


def URLsearch(stringinput):
    # regular expression

    regularex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|(([^\s()<>]+|(([^\s()<>]+)))))+(?:(([^\s()<>]+|(([^\s()<>]+))))|[^\s`!()[]{};:'\".,<>?«»“”‘’]))"

    # finding the url in passed string

    urlsrc = re.findall(regularex, stringinput)

    # return the found website url

    return [url[0] for url in urlsrc]

def ensure_directory_exists(filename):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)


def flatten(xss):
    return [x for xs in xss for x in xs]
