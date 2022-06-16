# .env
# ROOT_PATH_FOR_DYNACONF="config/"
# SETTINGS_FILE_FOR_DYNACONF="['settings_user.yaml']"
import os
import pickle
import shutil
from glob import glob

import config
from collections import namedtuple

ALL_USERS_PATH = 'data/users.txt'

Transaction = namedtuple('Transaction', ['amount', 'sender', 'reason'])

def ensure_directory_exists(filename):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def Save_All_Users():
    with open(ALL_USERS_PATH, 'w') as file:
        usernames=[user if isinstance(user,str) else user.username for user in Yappy_Users]
        file.writelines(usernames)
        print('all users saved')

Yappy_Users=[]
All_Users_Dict={}


class YappyUser():
    def __init__(self, username):
        self.username = username
        self.done_tasks=[]
        self.photos_path = f"img/{self.username}/"
        os.makedirs(self.photos_path.rsplit('/')[0]+'/', exist_ok=True)
        self.update_photos()
        self.savedata_path = f"data/transactions/{self.username}.bin"
        os.makedirs(self.savedata_path.rsplit('/')[0] + '/', exist_ok=True)
        if config.data.exists(f'transactionHistory{self.username}'):
            self.transactionHistory=config.data.get(f'transactionHistory{self.username}')
        else:
            self.transactionHistory = []
            self.transactionHistory = config.data.set(f'transactionHistory{self.username}',self.transactionHistory)
        self.savedata_txt_path = f"data/transactions.txt"
        if os.path.exists(self.savedata_txt_path):
            all_transactions = self.get_all_transactions()
            if username in all_transactions:
                self.coins=float(all_transactions[username])
        else:
            self.coins =float( config.settings['START_BALANCE'])
        Yappy_Users.append(self)
        All_Users_Dict[username]=self
        Save()

    def get_all_transactions(self):
        all_transactions = config.data.get('all_transactions',{})
        return all_transactions

    def update_photos(self):
        self.photos = glob(self.photos_path + '*')

    def AddBalance(self, amount: float, sender, reason):
        if self.transactionHistory is None:
            self.transactionHistory=[]
        if isinstance(reason, str):
            save_data=reason
            if os.path.isfile(reason):
                filename, file_extension = os.path.splitext(reason)
                copy_path = self.photos_path + f'{len(self.transactionHistory)}{file_extension}'
                ensure_directory_exists(copy_path)
                shutil.copy(reason, copy_path)
                save_data=copy_path
                self.update_photos()

        self.coins += amount
        transaction = Transaction(amount=amount, sender=sender, reason=reason)

        self.transactionHistory.append(transaction)

        config.data.set(f'transactionHistory{self.username}',self.transactionHistory)
        all_transactions = self.get_all_transactions()
        all_transactions[self.username]=self.coins
        config.data.set('all_transactions',all_transactions)
    def GetPhotos(self):
        return self.photos


def Save():
    config.data.set('Yappy_Users',Yappy_Users)
    config.data.set('All_Users_Dict',All_Users_Dict)
def Load():
    global Yappy_Users,All_Users_Dict
    Yappy_Users=config.data.get('Yappy_Users',default=[])
    All_Users_Dict=config.data.get('All_Users_Dict', default={})
config.data_callbacks.append(Save)
config.start_callbacks.append(Load)