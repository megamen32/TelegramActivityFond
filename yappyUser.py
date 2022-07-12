# .env
# ROOT_PATH_FOR_DYNACONF="config/"
# SETTINGS_FILE_FOR_DYNACONF="['settings_user.yaml']"
import asyncio
import datetime
import os
import random
import shutil
import traceback
import typing
from glob import glob
import utils
import config
from collections import namedtuple, defaultdict

from utils import ensure_directory_exists, URLsearch

ALL_USERS_PATH = 'data/users.txt'

Transaction = namedtuple('Transaction', ['amount', 'sender', 'reason', 'transaction_id'],
                         defaults=(0, 'none', 'no_reason', ''))

premium_ids=[]

Yappy_Users = []


class YappyUser: pass


All_Users_Dict: typing.Dict[str, YappyUser] = {}


class YappyUser:
    def __init__(self, username):
        username = username.lstrip(' ')
        print(f'creating user {username}')
        self.username = username
        self.done_tasks = set()
        self.skip_tasks = set()
        self.reserved_amount = 0.0
        self.photos_path = f"img/{self.username}/"
        os.makedirs(self.photos_path.rsplit('/')[0] + '/', exist_ok=True)
        self.update_photos()
        self.guilty_count = 0
        self.affiliate = None
        self.callbacks = {'first_task_complete': []}
        self.done_urls=set()
        self.level=0
        self.unlock_today = False
        self.tasks_to_next_level=1
        self.complets_to_unlock_creating=0
        self.last_login_time=datetime.datetime.now()
        self.completes_by_day=defaultdict(utils.return_zero)
        self.savedata_path = f"data/transactions/{self.username}.bin"
        os.makedirs(self.savedata_path.rsplit('/')[0] + '/', exist_ok=True)
        if config.data.exists(f'transactionHistory{self.username}'):
            self.transactionHistory = config.data.get(f'transactionHistory{self.username}',default=[])
        else:
            self.transactionHistory = []
            self.transactionHistory = config.data.set(f'transactionHistory{self.username}', self.transactionHistory)
        self.savedata_txt_path = f"data/all_transactions.bin"
        if os.path.exists(self.savedata_txt_path):
            all_transactions = self.get_all_transactions()
            if username in all_transactions:
                self.coins = float(all_transactions[username])
        if 'coins' not in vars(self):
            self.coins = float(config.settings['START_BALANCE'])
        Yappy_Users.append(self)
        All_Users_Dict[username] = self
        Save()
    def add_task_complete(self,task):
        self.done_tasks.add(task.name)
        self.done_urls=self.done_urls.union(URLsearch(task.url))
        self.completes_by_day[datetime.datetime.today().date()]+=1
        self.complets_to_unlock_creating=max(0,self.complets_to_unlock_creating-1)
        if self.complets_to_unlock_creating==0 and self.unlock_today==False:
            self.unlock_today=True

    def remove_task_complete(self,task):
        self.done_tasks.remove(task.name)
        self.completes_by_day[datetime.datetime.today().date()] -= 1
        self.done_urls = self.done_urls.difference(URLsearch(task.url))
        self.complets_to_unlock_creating = self.complets_to_unlock_creating+1
    def is_skiping_tasks(self, tasks):

        gooad_tasks = []
        wory_tasks = []
        for task in tasks:
            if self.username == task.creator: continue
            if task.name in self.done_tasks: continue
            if any([url in self.done_urls for url in URLsearch(task.url)]):continue
            if task.name not in self.skip_tasks:
                gooad_tasks.append(task)
            else:
                wory_tasks.append(task)
        if any(gooad_tasks):
            return gooad_tasks
        else:
            random.shuffle(wory_tasks)
            return wory_tasks

    def get_readable_balance(self):
        self.reserved_amount=max(0.0,self.reserved_amount)
        if self.reserved_amount>=0:
            t= f"Баланс: {self.coins:.1f}\n"
            t+=  f"Заморожено для исполнителей: {self.reserved_amount:.1f}\n"
            t+=  f"Доступно для трат: {(self.coins - self.reserved_amount):.1f}\n"
            return t
        else:
            return f"\nДоступный баланс: {self.coins - self.reserved_amount:.1f}\n"

    @staticmethod
    def get_all_transactions():
        all_transactions = config.data.get('all_transactions', {})
        return all_transactions
    @staticmethod
    def get_active_users_count():
        return len(YappyUser.get_active_users())
    @staticmethod
    def get_active_users():
        return list(filter(lambda user: (datetime.datetime.now() - user.last_login_time).total_seconds()/60/60 <= config._settings.get('active_users_hours',default=3),
                       All_Users_Dict.values()))

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
        syh = f'{u.username}  {balance} завершено:{len(done_tasks)} виновен:{u.guilty_count}'
        return syh

    def update_photos(self):
        self.photos = glob(self.photos_path + '*')

    def have_refferer(self):
        return 'affiliate' in vars(self) and self.affiliate is not None and any(self.affiliate)

    async def AddBalance(self, amount: float, sender, reason, tr_id=''):
        global all_transactions
        if self.transactionHistory is None:
            self.transactionHistory = []
        try:
            if amount > 0 and any(tr_id):
                if self.have_refferer():
                    for callback in self.callbacks['first_task_complete']:
                        callback(task_creator=sender)
        except:
            traceback.print_exc()
        save_data = reason
        if isinstance(reason, str):
            if os.path.isfile(reason):
                filename, file_extension = os.path.splitext(reason)
                saven_name = f'Номер задания {len(self.transactionHistory)}'
                saven_name += f' Получено от {sender}, сумма {amount}' if amount > 0 else f' Отправлено {sender}, сумма {-amount}'
                saven_name += f' Баланс {self.coins + amount}'
                saven_name=saven_name.replace('.',',')
                copy_path = self.photos_path + f'{saven_name}{file_extension}'
                ensure_directory_exists(copy_path)
                save_data = copy_path
                loop=asyncio.get_running_loop()
                def _local_f():
                    shutil.copy(reason, copy_path)
                    self.update_photos()

                await asyncio.wrap_future(loop.run_in_executor( None,_local_f))
            else:
                saven_name = f'Номер задания {len(self.transactionHistory)})'
                saven_name += f' Получено от {sender} за {reason}. Сумма {amount}' if amount > 0 else f' Отправлено {sender} за {reason}. Сумма {-amount}'
                saven_name += f' Баланс {self.coins + amount}'
                save_data = saven_name.replace('.', ',')
        self.coins += amount
        transaction = Transaction(amount=amount, sender=sender, reason=save_data, transaction_id=tr_id)

        self.transactionHistory.append(transaction)

        await config.data.async_set(f'transactionHistory{self.username}', self.transactionHistory)
        #all_transactions = self.get_all_transactions()
        all_transactions[self.username] = self.coins
        #await config.data.async_set('all_transactions', all_transactions)

    def GetPhotos(self):
        return self.photos

    def get_max_spend_amount(self):
        return self.coins - self.reserved_amount

    def refferal_can_set(self):
        if any(self.done_tasks): return False
        if self.affiliate is not None: return False
        return True

    def set_refferal(self, affiliate):
        if not self.refferal_can_set():
            print('ERROR ОШИБКА')
            raise ValueError(f'Уже установлен другой реферал:{self.affiliate}')
        if affiliate==self.username:
            raise ValueError(f'Нельзя указывать самого себя')
        self.affiliate = affiliate

def Save():
    global Yappy_Users, All_Users_Dict,premium_ids,all_transactions
    config.data.set('All_Users_Dict', All_Users_Dict)
    config.data.set('Yappy_Users', Yappy_Users)
    config.data.set('all_transactions', all_transactions)


async def async_Save():
    global Yappy_Users, All_Users_Dict,premium_ids,all_transactions
    await config.data.async_set('All_Users_Dict', All_Users_Dict)
    await config.data.async_set('Yappy_Users', Yappy_Users)
    await config.data.async_set('all_transactions', all_transactions)


async def async_Load():
    global Yappy_Users, All_Users_Dict,premium_ids,all_transactions
    All_Users_Dict =await config.data.async_get('All_Users_Dict', default={})
    Yappy_Users =await config.data.async_get('Yappy_Users', default=[])
    all_transactions = await config.data.async_get('all_transactions', {})
def Load():
    global Yappy_Users, All_Users_Dict,premium_ids,all_transactions
    All_Users_Dict = config.data.get('All_Users_Dict', default={})
    Yappy_Users = config.data.get('Yappy_Users', default=[])
    all_transactions =  config.data.get('all_transactions', {})

config.data_callbacks.append(Save)
config.start_callbacks.append(Load)
