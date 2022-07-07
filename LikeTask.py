import datetime
import operator
import random
import string
import traceback
import typing
from collections import defaultdict

import config
import yappyUser
from utils import flatten,URLsearch

class LikeTask:pass
All_Tasks:typing.Dict[str,LikeTask]={}
All_Tasks_History:typing.Dict[str,LikeTask]={}

_All_Tasks_by_name:typing.Dict[str,LikeTask]={}
async def save():
    await config.data.async_set('All_Tasks',All_Tasks)
    await config.data.async_set('All_Tasks_History',All_Tasks_History)
async def load():
    global All_Tasks,_All_Tasks_by_name
    All_Tasks=await config.data.async_get('All_Tasks',default={})
    All_Tasks_History=await config.data.async_get('All_Tasks_History',default={})
    All_Tasks=defaultdict(lambda :[],All_Tasks)
    for task in flatten(All_Tasks.values()):
        _All_Tasks_by_name[task.name]=task





def random_choice(k=8):
    alphabet=string.ascii_lowercase + string.digits
    return ''.join(random.choices(alphabet, k=k))
class LikeTask():
    def __init__(self,creator,url,amount,done_cost=1,name=None,msg_id=None):
        self.creator=creator
        self.name=random_choice() if name is None else name
        self.msg_id=msg_id
        self.amount=amount
        self.url=url
        self.done_amount=0
        self.created_at=datetime.datetime.now()
        self.done_history={}
        self.done_cost=done_cost
        self.reserved_done_amount=0
        _All_Tasks_by_name[self.name]=self
        if self.creator in All_Tasks.keys():
            All_Tasks[self.creator] += [self]
        else:
            All_Tasks[self.creator] = [self]


        config.data.set('All_Tasks',All_Tasks)

    def __eq__(self, other):
        if isinstance(other,LikeTask):
            return self.name==other.name
        else:
            return self.name==str(other)
    def is_active(self): return self.amount+self.reserved_done_amount > self.done_amount
    def __str__(self):return f'Задание {self.creator} {"активно" if self.is_active() else "выполнено"}, описание:{self.url}, выполнено {self.done_amount} раз из {self.amount} раз.'

    def __repr__(self):return f'Задание {self.creator} {"активно" if self.is_active() else "выполнено"}, описание:{self.url}, ' \
                              f'выполнено {self.done_amount} раз из {self.amount} раз.'

    async def AddComplete(self,whom,reason):
        self.done_amount+=1
        self.reserved_done_amount-=1
        if 'done_history' not in vars(self) or self.done_history is None:
            self.done_history= {}
        tr_id=random_choice(3)
        self.done_history[(whom,tr_id)]=reason

        await yappyUser.All_Users_Dict[whom].AddBalance(self.done_cost,self.creator,reason=reason,tr_id=tr_id)
        await yappyUser.All_Users_Dict[self.creator].AddBalance(-self.done_cost,whom,reason=reason,tr_id=tr_id)
        yappyUser.All_Users_Dict[self.creator].reserved_amount -= self.done_cost
        try:
            yappyUser.All_Users_Dict[whom].done_urls.add(URLsearch(self.url)[-1])
        except:traceback.print_exc()
        await config.data.async_set('All_Tasks', All_Tasks)
        return tr_id


def get_task_by_name(name:str) -> LikeTask:
    global _All_Tasks_by_name,_All_Tasks_by_name
    name=str(name)
    if name  in _All_Tasks_by_name:
        return _All_Tasks_by_name[name]
    try:
        return All_Tasks_History[name]
    except KeyError:pass
    except:traceback.print_exc()
    return None





def Get_Undone_Tasks(user=None) -> typing.List[LikeTask]:
    tasks=All_Tasks.values()
    undone_tasks=[]

    for user_task in flatten(tasks):
        if user_task.is_active():
            if user is None or user_task.creator!=user:
                undone_tasks.append(user_task)
    return sorted(undone_tasks, key=lambda task:(-task.done_cost,task.created_at),reverse=False)


config.start_async_callbacks.append(load)
config.data_async_callbacks.append(save)


async def add_task( task):
    if task.creator in All_Tasks:
        current_user_tasks=All_Tasks[task.creator]
        if isinstance(current_user_tasks,list):
                if task.name not in current_user_tasks:
                    All_Tasks[task.creator].append(task)
                    print(f'addning  {task}')
        else:
            All_Tasks[task.creator]=[current_user_tasks,task]
            print(f'adding second task {task}')
    else:
        All_Tasks[task.creator]=[task]
        print(f'creating first task  {task}')
    await config.data.async_set('All_Tasks',All_Tasks)
def remove_task(task:LikeTask):
    print('removing '+str(task))
    if task in All_Tasks[task.creator]:
        All_Tasks[task.creator].remove(task)
    if task.name in _All_Tasks_by_name:
        _All_Tasks_by_name.pop(task.name)
    All_Tasks_History[task.name]=task