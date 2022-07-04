# .env
# ROOT_PATH_FOR_DYNACONF="config/"
# SETTINGS_FILE_FOR_DYNACONF="['settings.conf']"
import datetime
import operator
import pickle
import re
import traceback
import asyncio
from collections import defaultdict
from glob import glob
from utils import flatten, URLsearch
from aiogram.utils.executor import start_webhook

import LikeTask
import config
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text,ContentTypeFilter
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
import yappyUser




# Configure logging
logging.basicConfig(level=logging.INFO)

from tg_bot_admin import *





async def save_exit(dispatcher):
    config.save()
    await config.async_save()
    if config._settings.get('is_use_WEBHOOK',False):
        await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()
async def startup(dispatcher):
    config.startup()
    await config.async_startup()
    if config._settings.get('is_use_WEBHOOK',False):

        await bot.set_webhook(WEBHOOK_URL)

    done=set()
    done_target=set()
    done_urls=set()

    good_tasks={}
    try:
        for task in flatten(LikeTask.All_Tasks.values()):
            if task.name not in done and task.url not in done_target:
                done.add(task.name)  # note it down for further iterations
                if 'done_cost' not in vars(task):
                    task.done_cost=1
                urls = URLsearch(task.url)
                if not any(urls):
                    print(str(task) + "Удалено. Нет ссылки.")
                    continue
                task.creator=task.creator.lower().replace('@','')
                done_urls=done_urls.union(urls)
                done_target.add(task.url)
                task_time=(datetime.datetime.now()-task.created_at)
                if (not task.is_active()) and task_time.days>config._settings.get('days_to_delete_complete_task',7):
                    print(str(task) + f"Удалено.  слишком старое задание. Ему уже {task_time.days} дней")
                    LikeTask.remove_task(task)
                    continue
                if task.creator in good_tasks:
                    good_tasks[task.creator] += [task]
                else:
                    good_tasks[task.creator] = [task]
    except:
        traceback.print_exc()
    LikeTask.All_Tasks=good_tasks
    new_users={}
    for id in tg_ids_to_yappy.keys():
        tg_ids_to_yappy[id]=tg_ids_to_yappy[id].lower().replace('@','')
    loop=asyncio.get_running_loop()
    tasks=[]
    for user in yappyUser.All_Users_Dict.values():
        user.username=user.username.lower().replace('@','')
        if  'guilty_count' not in vars(user):
            user.guilty_count=0
        if 'reserved_amount' not in vars(user):
            user.reserved_amount=0
        if 'skip_tasks' not in vars(user):
            user.skip_tasks=set()
        if 'affiliate' not in vars(user):
            user.affiliate=None
        if isinstance(user.done_tasks,list):
            user.done_tasks=set(user.done_tasks)
        if 'done_urls' not in vars(user):
            user.done_urls=set(map(lambda x:URLsearch(x.url)[-1],filter(None,map(lambda x: LikeTask.get_task_by_name(x),user.done_tasks))))
        if 'tasks_to_next_level' not in vars(user):
            user.tasks_to_next_level=1

        if 'level' not in vars(user) or user.tasks_to_next_level==1:
            user.level=0
            level_system.get_level(user)
            #tasks+=[ asyncio.create_task(bot.send_message(get_key(user.username,tg_ids_to_yappy),f"Поздравляем ваш уровень:{user.level}"))]
        reserved=0
        if user.username in LikeTask.All_Tasks:
            reserved=sum([task.amount-task.done_amount for task in LikeTask.All_Tasks[user.username]],0)
        user.coins=max(0.0,user.coins)
        user.reserved_amount=min(user.coins,max(0.0,reserved))
        new_users[user.username]=user
    yappyUser.All_Users_Dict=new_users
    try:
        await asyncio.wait(tasks,timeout=30)
    except:traceback.print_exc()
    if config._settings.get('print_refferals',False):
        reffers=defaultdict(lambda :1,{})
        full_info=defaultdict(lambda :[],{})
        for user in yappyUser.All_Users_Dict.values():
            if user.have_refferer():
                    reffers[user.affiliate]+=1
                    full_info[user.affiliate]+=[user]
        if not any(reffers.keys()):
            print("no_reffers")
            return
        refferes_sorted=sorted(reffers.items(),key=lambda x: x[1])
        for ref,count in refferes_sorted:
            info=", ".join(map(lambda x:f'{x.username}, done,{len(x.done_tasks)}',full_info[ref]))
            sum_done=sum(map(lambda l:len(l.done_tasks),full_info[ref]))
            print(f'{ref}, invited, {count}, invited_done count, {sum_done}, info, {info}')
    if config._settings.get('print_active', False):
        time=datetime.datetime.now()
        user_done=defaultdict(lambda :1,{})
        for user in yappyUser.All_Users_Dict.values():
            tasks=filter(None,map(LikeTask.get_task_by_name,user.done_tasks))
            for task in tasks:
                if (time-task.created_at).days<5:
                        user_done[user.username]+=1

        refferes_sorted = sorted(user_done.items(), key=lambda x: x[1])
        for ref, count in refferes_sorted:
            print(f'{ref} done: {count}')
    for user in sorted(yappyUser.All_Users_Dict.values(),key=operator.attrgetter('level')):
        print(f"{user} level: {user.level}")







if __name__ == '__main__':
    try:
        for middleware in AdminMiddleWares:
            dp.middleware.setup(middleware)
        if config._settings.get('is_use_WEBHOOK',False):
            WEBHOOK_HOST=config._settings.get('WEBHOOK_HOST','https://demiurgespace.duckdns.org/')
            WEBHOOK_PATH=config._settings.get('WEBHOOK_PATH','')
            WEBHOOK_URL=f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
            WEBAPP_HOST=config._settings.get('WEBAPP_HOST','0.0.0.0')  # or ip
            WEBAPP_PORT=int(config._settings.get('WEBAPP_PORT',8443))  # or ip
            start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            on_startup=startup,
            on_shutdown=save_exit,
            skip_updates=True,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT)
        else:
            executor.start_polling(dp, skip_updates=True,on_startup=startup,on_shutdown=save_exit)

    except:
        traceback.print_exc()


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
