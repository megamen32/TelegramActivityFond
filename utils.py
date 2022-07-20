import os
import re
import traceback
from datetime import timedelta

import numpy as np
from PIL import Image
def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

def return_zero():
    return 0
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
def get_concat_v(im1, im2):
    dst = Image.new('RGB', (im1.width, im1.height + im2.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (0, im1.height))
    return dst
def combine_imgs(images_list):
    from collage_maker import make_collage
    imgs = [np.array(Image.open(i))for i in images_list]
    img_merge=make_collage(images=imgs)
    name=f"img/{images_list[-1].rsplit('/',1)[-1].rsplit('.',1)[0]}_combo.jpg"
    img=Image.fromarray(img_merge)
    img=img.convert('RGB')
    img.save(open(name,'wb'))
    return name



    # If you're using an older version of Pillow, you might have to use .size[0] instead of .width
    # and later on, .size[1] instead of .height
    min_img_width = max(i.width for i in imgs)

    total_height = 0
    for i, img in enumerate(imgs):
        # If the image is larger than the minimum width, resize it
        if img.width < min_img_width:
            imgs[i] = img.resize((min_img_width, int(img.height / img.width * min_img_width)), Image.ANTIALIAS)
        total_height += imgs[i].height

    # I have picked the mode of the first image to be generic. You may have other ideas
    # Now that we know the total height of all of the resized images, we know the height of our final image
    img_merge = Image.new(imgs[0].mode, (min_img_width, total_height))
    y = 0
    for img in imgs:
        img_merge.paste(img, (0, y))

        y += img.height
    img_merge.save(images_list[-1])
    return images_list[-1]
def URLsearch(stringinput):
    # regular expression

    regularex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|(([^\s()<>]+|(([^\s()<>]+)))))+(?:(([^\s()<>]+|(([^\s()<>]+))))|[^\s`!()[]{};:'\".,<>?«»“”‘’]))"

    # finding the file_id in passed string

    urlsrc = re.findall(regularex, stringinput)

    # return the found website file_id

    return [url[0] for url in urlsrc]

def ensure_directory_exists(filename):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)


def flatten(xss):
    return [x for xs in xss for x in xs]


def get_key(val,my_dict):
    for key, value in my_dict.items():
         if val == value:
             return key
