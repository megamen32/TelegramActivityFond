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

import level_system
import tg_bot_admin
import utils
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

import tgbot


# Configure logging
logging.basicConfig(level=logging.INFO)

from tg_bot_admin import *




save_load=False
async def save_exit(dispatcher):
    global save_load
    if not save_load:return
    await tg_bot_admin._save_data()



async def startup(dispatcher):
    global save_load
    try:
        config.startup()
        await config.async_startup()
    except:
        traceback.print_exc()
        exit(0)

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
                if 'reserved_done_amount' not in vars(task):
                    task.reserved_done_amount=0
                task.reserved_done_amount=0
                urls = URLsearch(task.url)
                if not any(urls):
                    print(str(task) + "Удалено. Нет ссылки.")
                    continue
                task.creator=task.creator.lower().replace('@','')
                done_urls=done_urls.union(urls)
                done_target.add(task.url)
                task_time=(datetime.datetime.now()-task.created_at)
                if (not task.is_active()) and task_time.days>config._settings.get('days_to_delete_complete_task',3):
                    print(str(task) + f"Удалено.  слишком старое задание. Ему уже {task_time.days} дней")
                    LikeTask.remove_task(task)
                    continue
                if task.creator in good_tasks:
                    good_tasks[task.creator] += [task]
                else:
                    good_tasks[task.creator] = [task]
    except:
        traceback.print_exc()
    sorted_tasks=sorted(flatten(good_tasks.values()), key=lambda item: item.created_at)
    new_dict={}
    for task in sorted_tasks:
        if task.creator in new_dict:
            new_dict[task.creator] += [task]
        else:
            new_dict[task.creator] = [task]
    LikeTask.All_Tasks=new_dict
    new_users={}
    for id in tg_ids_to_yappy.keys():
        tg_ids_to_yappy[id]=tg_ids_to_yappy[id].lower().replace('@','')
    loop=asyncio.get_running_loop()
    tasks=[]
    premium_ids=await config.data.async_get("premium_ids", [])
    undone_tasks = LikeTask.Get_Undone_Tasks()
    ALL_TASKS = list(LikeTask._All_Tasks_by_name.values()) + list(LikeTask.All_Tasks_History.values())
    task_sorted = sorted(ALL_TASKS, key=lambda task: task.created_at.date())
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
        if user.affiliate==user.username:
            print(f"user {user.username} установил самого себя как рефферала")
            try:
                await bot.send_photo(get_key(user.username,tg_ids_to_yappy),"http://risovach.ru/upload/2015/04/mem/hitriy-getsbi_79275296_orig_.jpg",
                                       caption="Ты указал себя в качестве реферала, и получал за это балы, но мы тебя поймали! Больше не будешь получать за это баллы")
            except:traceback.print_exc()
            user.affiliate=None
        if isinstance(user.done_tasks,list):
            user.done_tasks=set(user.done_tasks)
        if 'done_urls' not in vars(user):
            user.done_urls=set(map(lambda x:URLsearch(x.url)[-1],filter(None,map(lambda x: LikeTask.get_task_by_name(x),user.done_tasks))))
        if 'last_login_time' not in vars(user) or isinstance(user.last_login_time,int):
            user.last_login_time=datetime.datetime.now()-datetime.timedelta(days=3)
        if 'tasks_to_next_level' not in vars(user):
            user.tasks_to_next_level=1
        if 'transactionHistory' not in vars(user):
            user.transactionHistory=[]
        if 'level' not in vars(user) or user.tasks_to_next_level==1:
            user.level=0
            level_system.get_level(user)
            #tasks+=[ asyncio.create_task(bot.send_message(get_key(user.username,tg_ids_to_yappy),f"Поздравляем ваш уровень:{user.level}"))]
        level_system.get_level(user)
        if 'complets_to_unlock_creating' not in vars(user) :
            user.complets_to_unlock_creating= min(len(undone_tasks), 50)
        if 'completes_by_day' not in vars(user):
            user.completes_by_day=defaultdict(utils.return_zero)
            oldest_task=task_sorted[0].created_at.date( )
            newest_task=task_sorted[-1].created_at.date( )
            for today in utils.daterange(oldest_task,newest_task):
                user.completes_by_day[today]=len(list(filter(lambda task: task.name in user.done_tasks and task.created_at.date() == today,
                                                         ALL_TASKS)))
        if 'unlock_today' not in vars(user) :
            user.unlock_today=False
        if not user.unlock_today:
            complets_to_unlock_creating = min(len(undone_tasks), 50,max(10-user.level,user.complets_to_unlock_creating))
            if complets_to_unlock_creating>user.completes_by_day[datetime.datetime.today().date()]:
                user.complets_to_unlock_creating=complets_to_unlock_creating
        reserved=0
        if user.username in LikeTask.All_Tasks:
            reserved=sum([task.amount-task.done_amount for task in LikeTask.All_Tasks[user.username]],0)
        user.coins=max(0.0,user.coins)
        user.reserved_amount=min(user.coins,max(0.0,reserved))
        tr_history=await config.data.async_get(f'transactionHistory{user.username}', [])
        tr_sum=sum(map(operator.attrgetter('amount'),tr_history))


        for i in range(user.level):
            tr_sum+=level_system.BONUS_FOR_NEXT_LEVEL[i] if  i in level_system.BONUS_FOR_NEXT_LEVEL else 0
        if tr_sum > user.coins:
            print(f"баланс:{user.coins}!=Транзакции {tr_sum} для {user.username}")
            if tr_sum>user.coins:
                user.coins=tr_sum
        tasks_send=[]
        user.update_photos()
        for photo in user.photos:
            name = photo.rsplit('.',1)[0].split('/')[-1]
            task_numer = int(re.findall(r'\d+', name, re.I)[0])
            task_balance = float(re.findall(r'\d+', name.split('Баланс ')[-1].replace(',','.'), re.I)[0])
            tasks_send.append((task_numer,name,task_balance))
        tasks=sorted(tasks_send,key=operator.itemgetter(0),reverse=False)[-15:]
        try:
            tr_sum=0
            for i in range(1,len(tasks)):
                if tasks[i][2]-tasks[i-1][2]>-3:
                    tr_sum=tasks[i][2]

            if tr_sum > user.coins:
                print(f"баланс:{user.coins}!=По заданием {tr_sum} для {user.username}")
                user.coins=tr_sum
        except ValueError:pass
        except:traceback.print_exc()
        if user.level>=10:
            try:
                if  get_key(user.username,tg_ids_to_yappy) not in premium_ids:
                    premium_ids.add(get_key(user.username,tg_ids_to_yappy))
            except:traceback.print_exc()
        else:
            try:
                if get_key(user.username, tg_ids_to_yappy)  in premium_ids:
                    premium_ids.remove(get_key(user.username, tg_ids_to_yappy))
            except:
                traceback.print_exc()
        new_users[user.username]=user
    yappyUser.All_Users_Dict=new_users
    await config.data.async_set("premium_ids", premium_ids)
    tgbot.premium_ids=premium_ids
    save_load=True
    try:
        if any(tasks):
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
                if (time-task.created_at).days<config._settings.get('active_days',9):
                        user_done[user.username]+=1

        refferes_sorted = sorted(user_done.items(), key=lambda x: x[1])
        for ref, count in refferes_sorted:
            print(f'{ref} done: {count}')
    if config._settings.get('print_level', False):
        for user in sorted(yappyUser.All_Users_Dict.values(),key=operator.attrgetter('level')):
            print(f"{user} level: {user.level}")







if __name__ == '__main__':
    try:
        #yappyUser.YappyUser.create_table(  )
        #LikeTask.LikeTask.create_table()
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
            skip_updates=False,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT)
        else:
            executor.start_polling(dp, skip_updates=False,on_startup=startup,on_shutdown=save_exit)

    except:
        traceback.print_exc()


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
