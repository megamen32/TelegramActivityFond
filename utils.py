def exclude(a, b):
    if not b: return a
    #if not isinstance(y,list):y=[y]
    new_list=[]
    for fruit in a:
        if fruit not in b:
            new_list.append(fruit)
    return new_list
