import os.path
import subprocess
import traceback

paths=["OzoneActivity","TelegramActivityFond","TelegramActivityFondDevelop","vkactivity","instaactivity"]
filename="update_and_run.sh"
root=os.path.pardir
full_path=[f'{root}/{path}/{filename}' for path in paths]
try:
    for result in map(os.system,full_path):
        print(result)
except:traceback.print_exc()