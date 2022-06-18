import datetime
import traceback
import typing
import uuid

import config
import yappyUser
from utils import exclude

All_Tasks={}


def save():
    config.data.set('All_Tasks',All_Tasks)
def load():
    global All_Tasks
    All_Tasks=config.data.get('All_Tasks',default={})
class LikeTask():
    def __init__(self,creator,url,amount,name=None,msg_id=None):
        self.creator=creator
        self.name=uuid.uuid4() if name is None else name
        self.msg_id=msg_id
        self.amount=amount
        self.url=url
        self.done_amount=0
        self.created_at=datetime.datetime.now()

        if config.data.exists(f'all_tasks{self.creator}'):
            all_tasks=config.data.get(f'all_tasks{self.creator}',[])
            all_tasks.append(self)
        else:
            all_tasks=[self]

        config.data.set(f'all_tasks{self.creator}',all_tasks)
        if self.creator in All_Tasks.keys():
            All_Tasks[self.creator]+=[self]
        else:
            All_Tasks[self.creator]=[self]

        config.data.set('All_Tasks',All_Tasks)
    def __eq__(self, other):
        if isinstance(other,LikeTask):
            return self.name==other.name
        else:
            return self.name==str(other)
    def is_active(self): return self.amount>self.done_amount
    def __str__(task):return f'Задание {"активно" if task.is_active() else "неактивно"}, описание:{task.url}, выполнено {task.done_amount} из {task.amount} раз'

    def __repr__(task):return f'Задание {"активно" if task.is_active() else "неактивно"}, описание:{task.url}, ' \
                              f'выполнено {ta/sk.done_amount} из {task.amount} раз'

    async def AddComplete(self,whom,reason):
        self.done_amount+=1
        all_tasks = config.data.get(f'all_tasks{self.creator}',[])
        bad=[]
        for i in range(len(all_tasks)):
            if all_tasks[i].name==self.name and all_tasks[i].done_amount<self.done_amount:
                bad.append(all_tasks[i])

        all_tasks= exclude(all_tasks, bad)
        all_tasks.append(self)

        config.data.set(f'all_tasks{self.creator}',all_tasks)
        for tasks in All_Tasks.values():
            if isinstance(tasks,list):
                for task in tasks:
                    if self.creator == task.creator:
                         All_Tasks[task.creator] = all_tasks

            if isinstance(tasks,LikeTask) and self.creator == tasks.creator:
                All_Tasks[tasks.creator] = all_tasks

        yappyUser.All_Users_Dict[whom].AddBalance(1,self.creator,reason=reason)
        yappyUser.All_Users_Dict[self.creator].AddBalance(-1,whom,reason=reason)
        yappyUser.All_Users_Dict[self.creator].reserved_amount -= 1

        config.data.set('All_Tasks', All_Tasks)
def get_task_by_name(name:str)->LikeTask:
    tasks=All_Tasks.values()
    for user_tasks in tasks:
        if isinstance(user_tasks,list):
            for task in user_tasks:
                if task.name==name:
                    return task
        if isinstance(user_tasks,LikeTask):
            if task.name == name:
                return task
def remove_task(task:LikeTask):
    tasks = All_Tasks.values()
    for user_tasks in tasks:
        if isinstance(user_tasks,list):
            if task in user_tasks:
                All_Tasks[task.creator].remove(task)
        if isinstance(user_tasks,LikeTask):
            if task == user_tasks:
                All_Tasks.pop(task)

def Get_Undone_Tasks()->typing.List[LikeTask]:
    tasks=All_Tasks.values()
    undone_taksks=[]

    for user_tasks in tasks:
        if isinstance(user_tasks,list):
            for task in user_tasks:
                check_task(task, undone_taksks)
        if isinstance(user_tasks,LikeTask):
            check_task(user_tasks,undone_taksks)
    sotred=sorted(undone_taksks,key=lambda task:task.created_at,reverse=False)
    return sotred


def check_task(task, undone_taksks):
    try:
        if task.done_amount < task.amount:
            undone_taksks.append(task)
    except:
        traceback.print_exc()


config.start_callbacks.append(load)
config.data_callbacks.append(save)