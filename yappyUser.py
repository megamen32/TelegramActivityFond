# .env
# ROOT_PATH_FOR_DYNACONF="config/"
# SETTINGS_FILE_FOR_DYNACONF="['settings_user.yaml']"
import os
import random
import shutil
import typing
from glob import glob

import config
from collections import namedtuple

from utils import ensure_directory_exists

ALL_USERS_PATH = 'data/users.txt'

Transaction = namedtuple('Transaction', ['amount', 'sender', 'reason','transaction_id'],defaults=(0,'none','no_reason',''))

def Save_All_Users():
    with open(ALL_USERS_PATH, 'w') as file:
        usernames=[user if isinstance(user,str) else user.username for user in Yappy_Users]
        file.writelines("\n".join(usernames))
        print('all users saved')

Yappy_Users=[]
class YappyUser():pass
All_Users_Dict:typing.Dict[str,YappyUser]={}


class YappyUser():
    def __init__(self, username):
        username=username.lstrip(' ')
        print(f'creating user {username}')
        self.username = username
        self.done_tasks=set()
        self.skip_tasks=set()
        self.reserved_amount=0.0
        self.photos_path = f"img/{self.username}/"
        os.makedirs(self.photos_path.rsplit('/')[0]+'/', exist_ok=True)
        self.update_photos()
        self.guilty_count=0
        self.affiliate=None
        self.callbacks={'first_task_complete':[]}
        self.savedata_path = f"data/transactions/{self.username}.bin"
        os.makedirs(self.savedata_path.rsplit('/')[0] + '/', exist_ok=True)
        if config.data.exists(f'transactionHistory{self.username}'):
            self.transactionHistory=config.data.get(f'transactionHistory{self.username}')
        else:
            self.transactionHistory = []
            self.transactionHistory = config.data.set(f'transactionHistory{self.username}',self.transactionHistory)
        self.savedata_txt_path = f"data/all_transactions.bin"
        if os.path.exists(self.savedata_txt_path):
            all_transactions = self.get_all_transactions()
            if username in all_transactions:
                self.coins=float(all_transactions[username])
        if 'coins' not in vars(self):
                self.coins =float( config.settings['START_BALANCE'])
        Yappy_Users.append(self)
        All_Users_Dict[username]=self
        Save()
    def is_skiping_tasks(self,tasks):

        gooad_tasks=[]
        wory_tasks=[]
        for task in tasks:
            if self.username==task.creator:continue
            if task.name in self.done_tasks:continue
            if task.name not in self.skip_tasks:
                gooad_tasks.append(task)
            else:
                wory_tasks.append(task)
        if any(gooad_tasks): return gooad_tasks
        else:
            random.shuffle(wory_tasks)
            return wory_tasks
    def get_readable_balance(self):return f"\n_____\n\nОбщий баланс: {self.coins}\nЗаморожено для исполнителей: {self.reserved_amount}\nДоступный баланс: {self.coins-self.reserved_amount}"
    @staticmethod
    def get_all_transactions():
        all_transactions = config.data.get('all_transactions',{})
        return all_transactions
    @property
    def tasks_to_skip(self):
        return self.skip_tasks.union(self.done_tasks)
    def __str__(u):
        balance = u.get_readable_balance()
        done_tasks = u.done_tasks
        syh = f'{u.username}  {balance} '
        return syh
    def __repr__(u):
        balance = u.get_readable_balance()
        done_tasks = u.done_tasks
        syh = f'{u.username}  {balance}'
        return syh
    def update_photos(self):
        self.photos = glob(self.photos_path + '*')
    def have_refferer(self):return 'affiliate'in vars(self)and self.affiliate is not None and any(self.affiliate)
    def AddBalance(self, amount: float, sender, reason,tr_id=''):
        if self.transactionHistory is None:
            self.transactionHistory=[]

        if amount>0:
            if self.have_refferer():
                for callback in self.callbacks['first_task_complete']:
                    callback(task_creator=sender)
        save_data=reason
        if isinstance(reason, str):
            if os.path.isfile(reason):
                filename, file_extension = os.path.splitext(reason)
                saven_name=f'Номер задания {len(self.transactionHistory)}'
                saven_name+=f' Получено от {sender}, сумма {amount}' if amount>0 else f' Отправлено {sender}, сумма {-amount}'
                saven_name+=f' Баланс {self.coins+amount}'
                copy_path = self.photos_path + f'{saven_name}{file_extension}'
                ensure_directory_exists(copy_path)
                shutil.copy(reason, copy_path)
                save_data=copy_path
                self.update_photos()

        self.coins += amount
        transaction = Transaction(amount=amount, sender=sender, reason=save_data,transaction_id=tr_id)

        self.transactionHistory.append(transaction)

        config.data.set(f'transactionHistory{self.username}',self.transactionHistory)
        all_transactions = self.get_all_transactions()
        all_transactions[self.username]=self.coins
        config.data.set('all_transactions',all_transactions)
    def GetPhotos(self):
        return self.photos

    def get_max_spend_amount(self):
        return self.coins-self.reserved_amount
    def refferal_can_set(self):
        if any(self.done_tasks):return False
        if self.affiliate is not None:return False
        return True
    def set_refferal(self,affiliate):
        if not self.refferal_can_set():
            print('ERROR ОШИБКА')
            raise ValueError(f'Уже установлен другой реферал:{self.affiliate}')
        self.affiliate=affiliate

def Save():
    config.data.set('Yappy_Users',Yappy_Users)
    config.data.set('All_Users_Dict',All_Users_Dict)
def Load():
    global Yappy_Users,All_Users_Dict
    Yappy_Users=config.data.get('Yappy_Users',default=[])
    All_Users_Dict=config.data.get('All_Users_Dict', default={})
config.data_callbacks.append(Save)
config.start_callbacks.append(Load)