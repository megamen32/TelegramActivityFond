import traceback


def exclude(a, b):
    if not b: return a
    #if not isinstance(y,list):y=[y]
    new_list=[]
    for fruit in a:
        if fruit not in b:
            new_list.append(fruit)
    return new_list
def any_re(patter,str):
    try:
        find=re.match(patter,str).group()
        if find is not None:
            return any(find)
    except:traceback.print_exc()
    return False