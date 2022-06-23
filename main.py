# .env
# ROOT_PATH_FOR_DYNACONF="config/"
# SETTINGS_FILE_FOR_DYNACONF="['settings.conf']"
import pickle
import re
import traceback
import asyncio
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
    yappyUser.Save_All_Users()
    config.save()
    if config._settings.get('is_use_WEBHOOK',False):
        await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()
async def startup(dispatcher):
    config.startup()
    if config._settings.get('is_use_WEBHOOK',False):

        await bot.set_webhook(WEBHOOK_URL)

    all_tasks_saves=glob('data/all_tasks*')
    for task_save in all_tasks_saves:

        tasks=pickle.load(open(task_save,'rb'))
        for task in tasks:
            
            LikeTask.add_task(task)
    done=set()
    done_target=set()

    good_tasks={}
    try:
        for task in flatten(LikeTask.All_Tasks.values()):
            if task.name not in done and task.url not in done_target:
                done.add(task.name)  # note it down for further iterations
                done_target.add(task.url)
                urls = URLsearch(task.url)
                if not any(urls):
                    print(str(task) + "Удалено. Нет ссылки.")
                    continue
                if task.creator in good_tasks:
                    good_tasks[task.creator] += [task]
                else:
                    good_tasks[task.creator] = [task]
    except:
        traceback.print_exc()
    LikeTask.All_Tasks=good_tasks
    new_users={}
    for user in yappyUser.All_Users_Dict.values():
        if  'guilty_count' not in vars(user):
            user.guilty_count=0
        if 'reserved_amount' not in vars(user):
            user.reserved_amount=0
        reserved=0
        if user.username in LikeTask.All_Tasks:
            reserved=sum([task.amount-task.done_amount for task in LikeTask.All_Tasks[user.username]],0)
        user.reserved_amount=min(user.coins,max(0,reserved))
        new_users[user.username]=user
    yappyUser.All_Users_Dict=new_users








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
