# .env
# ROOT_PATH_FOR_DYNACONF="config/"
# SETTINGS_FILE_FOR_DYNACONF="['settings.conf']"
import pickle
import re
import traceback
import asyncio
from glob import glob

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
    for user in yappyUser.All_Users_Dict.values():
        if 'reserved_amount' not in vars(user):
            user.reserved_amount=0
    all_tasks_saves=glob('data/all_tasks*')
    for task_save in all_tasks_saves:

        tasks=pickle.load(open(task_save,'rb'))
        for task in tasks:
            
            LikeTask.add_task(task)
    done=set()
    
    good_tasks={}
    for user_tasks in LikeTask.All_Tasks.values():
        if isinstance(user_tasks,list):
            for task in user_tasks:
                if task.name not in done:
                    done.add(task.name)  # note it down for further iterations
                    good_tasks[task.creator]=task
        else:
            if user_tasks.name not in done:
                done.add(user_tasks.name)  # note it down for further iterations
                good_tasks[user_tasks.creator]=user_tasks
    LikeTask.All_Tasks=good_tasks
    
    for task in LikeTask.Get_Undone_Tasks():
        urls = re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', task.url)
        if not any(urls):
            print(str(task)+"Удалено. Нет ссылки.")
            LikeTask.remove_task(task)

if __name__ == '__main__':
    try:
        if config._settings.get('is_use_WEBHOOK',False):
            WEBHOOK_HOST=config._settings.get('WEBHOOK_HOST','https://demiurgespace.duckdns.org/')
            WEBHOOK_PATH=config._settings.get('WEBHOOK_HOST','')
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
