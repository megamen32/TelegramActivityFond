# .env
# ROOT_PATH_FOR_DYNACONF="config/"
# SETTINGS_FILE_FOR_DYNACONF="['settings.conf']"
import datetime
import operator
import os.path
import random
import re
import time
import traceback
import asyncio
import typing
import urllib
from functools import partial

import aiogram.utils.deep_linking
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.webhook import SendMessage
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified, MessageToDeleteNotFound, Throttled


import LikeTask
import config
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import  RedisStorage2
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, \
    ReplyKeyboardRemove, BotCommand, BotCommandScopeDefault, ContentType

#import find_user
import level_system
import utils
import yappyUser


from utils import get_key


class CreateTaskStates(StatesGroup):
    amount=State()
    task_description=State()
class LikeTaskStates(StatesGroup):
    confirm=State()
class BotHelperState(StatesGroup):
    create_task=State()
    get_target=State()
    start_doing_task=State()
    doing_task=State()
class AdminHelperState(StatesGroup):
    admin_cancel_task=State()

tg_ids_to_yappy=config.data.get('tg_ids_to_yappy',{})
# Initialize bot and dispatcher
if config._settings.get('is_use_Redis',False):
    storage = RedisStorage2()

else:
    storage = MemoryStorage()
API_TOKEN = config._settings.get('TG_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot,storage=storage)
new_task_cb = CallbackData('newtask', 'action', 'amount')  # post:<action>:<amount>
cancel_cb = CallbackData('cancel','action')  # post:<action>:<amount>
like_cb = CallbackData('confirm','photo_path')  # post:<action>:<amount>
cancel_task_cb = CallbackData('cancel_task', 'task')
cancel_task_cb_admin = CallbackData('cancel_task_a', 'task')
change_photo_cb = CallbackData('change_photo', 'photo_path')
more_info_cb= CallbackData('more_info','photo')
next_task_cb=CallbackData('next_task','task')
buy_cb = CallbackData('b_c_t', 'amount')
button_task = KeyboardButton('Создать задание', callback_data=new_task_cb.new(action='up', amount=10))
button_like = KeyboardButton('Выполнить задание', callback_data=new_task_cb.new(action='like', amount=10))
help_kb =  ReplyKeyboardMarkup(resize_keyboard=True)
#greet_kb.add(button_task)
#greet_kb.add(button_like)

balance_task = KeyboardButton('Баланс')

history_task = KeyboardButton('Мои задания' )
name_task = KeyboardButton('Имя' )
get_task_button = KeyboardButton('Выполнить задание' )
new_task_button = KeyboardButton('Создать задание' )
quick_commands_kb =  ReplyKeyboardMarkup(resize_keyboard=True)
quick_commands_kb.row(balance_task, history_task)
quick_commands_kb.row(new_task_button, get_task_button)
cancel_task = KeyboardButton('Отмена')
accept_kb =  ReplyKeyboardMarkup(resize_keyboard=True)
accept_kb.row(KeyboardButton("Подтвердить"),cancel_task)
help_kb.add(name_task)
cancel_kb= ReplyKeyboardMarkup(resize_keyboard=True)

cancel_kb.add(cancel_task)
normal_commands=[BotCommand('balance','Баланс'),
BotCommand('tasks','Мои задания'),
BotCommand('task','Создать задание'),
BotCommand('like','Выполнить задание'),
BotCommand('history','История'),
BotCommand('name','Изменить никнейм'),
BotCommand('rules','Правила'),
BotCommand('invite','Получить реферальную ссылку'),
BotCommand('pass','Установить пароль')
          ]
commands=normal_commands+[BotCommand('cancel','Отменить')]
admin_commands=commands+[BotCommand('edit_tasks','[username] Изменить задание'),BotCommand('add_balance','{username} {1} Изменить баланс'),BotCommand('info','{username} Инфа о пользователе'),BotCommand('admin_info','Инфа для админа')]
dispute_cb=CallbackData('dispute', 'task','tid',
                                          'username')
dispute_admin_cb=CallbackData('dispute_admin', 'task','tid'
                                          ,'username','guilty')
async def async_Save():
    global premium_ids
    if 'premium_ids' in vars():
        await config.data.async_set('premium_ids', premium_ids)

async def Load():
    global premium_ids
    premium_ids =await config.data.async_get('premium_ids', default=[])


config.data_async_callbacks.append(async_Save)
config.start_async_callbacks.append(Load)

@dp.callback_query_handler(dispute_cb.filter(),state='*')
async def callback_dispute(query: types.CallbackQuery,state:FSMContext,callback_data:dict):
    message = query.message
    name = tg_ids_to_yappy[message.chat.id]
    user = yappyUser.All_Users_Dict[name]
    data=callback_data
    await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, reply_markup=None)
    await query.answer("Отправлено модераторам.")
    guilty_username=data['username']

    
    try:

        while 'task' in data:
            data=data['task']

        task:LikeTask.LikeTask=LikeTask.get_task_by_name(data)
        guilty_user:yappyUser.YappyUser=yappyUser.All_Users_Dict[guilty_username]

        photo_path=None
        try:
            if 'tid' in callback_data:
                tr_id = callback_data['tid']
                photo_path=task.done_history[(guilty_username,tr_id)]
        except:traceback.print_exc()

        if photo_path is None and 'done_history' not in vars(task):
            for transaction in reversed(guilty_user.transactionHistory):
                tr: yappyUser.Transaction=transaction
                if tr.sender==name:
                    photo_path=tr.reason
                    break



        admin_ids=config._settings.get('admin_ids',['540308572','65326877'])
        loop=asyncio.get_running_loop()


        msg_ids={}
        photo = lambda :open(photo_path, 'rb') if os.path.exists(photo_path) else photo_path
        for admin in admin_ids:
            guilty_button=InlineKeyboardButton("Виновен",callback_data=dispute_admin_cb.new(task=task.name,tid=tr_id,username=guilty_username,guilty=True))
            not_guilty_button=InlineKeyboardButton("Не виновен",callback_data=dispute_admin_cb.new(task=task.name,tid=tr_id,username=guilty_username,guilty=False))
            admin_kb=InlineKeyboardMarkup()
            admin_kb.row(guilty_button,not_guilty_button)

            caption = f'Автор: {name} | Испол: {guilty_username}\n' \
                      f'Виновен {guilty_user.guilty_count} раз\n\n' \
                      f'{task}'
            msg=await bot.send_photo(admin, photo=photo(), caption=caption, reply_markup=admin_kb)
            msg_ids[admin]=msg.message_id
            await storage.update_data(user=tr_id,data={'admin_buttons':msg_ids})
        guilty_id= get_key(guilty_username, tg_ids_to_yappy)
        await bot.send_photo(guilty_id,photo=photo(),caption=f'Твоё выполнение "{task.url}" оспорил {name}. Это не значит, что очки обязательно снимут. После проверки тебе придёт оповещение.')
        await query.answer('Информация успешно отправлена модераторам.')
        
        guilty_user=yappyUser.All_Users_Dict[guilty_username]
        


    except:traceback.print_exc()


@dp.callback_query_handler(dispute_admin_cb.filter(),state='*')
async def callback_dispute(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    message = query.message
    data = callback_data

    guilty_username = data['username']
    is_guilty=(data['guilty'])

    try:
        while 'task' in data:
            data = data['task']

        task: LikeTask.LikeTask = LikeTask.get_task_by_name(data)
        guilty_user: yappyUser.YappyUser = yappyUser.All_Users_Dict[guilty_username]
        tr_id = None
        photo_path=None
        try:
            tr_id = callback_data['tid']
            photo_path = task.done_history[(guilty_username, tr_id)]
        except:
            traceback.print_exc()
        to_remove = await storage.get_data(user=tr_id)
        if task.name not in guilty_user.done_tasks or 'admin_buttons' not in to_remove:
            await message.reply("Другой модератор уже все рассмотрел")
            return
        if 'admin_buttons' in to_remove:
            msg_ids = to_remove['admin_buttons']
            for msg in msg_ids.keys():
                try:
                    await bot.edit_message_reply_markup(msg, msg_ids[msg], reply_markup=None)
                    text=f'{task.creator} оспорил задание, которые выполнил {guilty_username} виновен {guilty_user.guilty_count} раз, задание: {task}, Решение вынесено {tg_ids_to_yappy[query.from_user.id]} : {"Виновен" if "True" in is_guilty else "Не виновен"}'
                    await bot.edit_message_caption(caption=text,message_id= msg_ids[msg],chat_id=msg, reply_markup=None)

                except MessageNotModified:pass
            await storage.reset_data(user=tr_id)

        if photo_path is None:
            for transaction in reversed(guilty_user.transactionHistory):
                tr: yappyUser.Transaction = transaction
                if tr.sender == task.creator and tr.transaction_id==tr_id:
                    photo_path = tr.reason
                    break
        admin_ids = config._settings.get('admin_ids', ['540308572', '65326877'])

        task_creator = yappyUser.All_Users_Dict[task.creator]
        photo = lambda : open(photo_path, 'rb') if os.path.exists(photo_path) else photo_path
        if 'True' in is_guilty:
            await query.message.reply('Отправляем очки: Виновен')
            #Удаляем у пользователей и у задания транзакцию
            for transaction in reversed(guilty_user.transactionHistory):
                tr: yappyUser.Transaction = transaction
                if tr.sender == task.creator and tr.transaction_id==tr_id:
                    guilty_user.transactionHistory.remove(transaction)
                    break
            for transaction in reversed(task_creator.transactionHistory):
                tr: yappyUser.Transaction = transaction
                if tr.sender == guilty_username and tr.transaction_id==tr_id:
                    task_creator.transactionHistory.remove(transaction)
                    break
            if (guilty_username,tr_id) in task.done_history:
                task.done_history.pop((guilty_username,tr_id))
            guilty_user.skip_tasks.add(task.name)
            guilty_user.remove_task_complete(task)
            await guilty_user.AddBalance(-task.done_cost, 'ActivityBot', f'Неправильно сделал задание {task_creator.username}')
            task_creator.reserved_amount-=task.done_cost
            await task_creator.AddBalance(task.done_cost, 'ActivityBot', f'Неправильно выполнили задание. {guilty_username}')
            guilty_user.guilty_count += 1
            task.done_amount -= 1
            await bot.send_photo(get_key(guilty_username, tg_ids_to_yappy), photo=photo(), caption=f"Оспаривание твоего выполнения задания '{task.url}' от {task.creator} рассмотрено.\n\nОчки сняты.")
            await bot.send_photo(get_key(task.creator, tg_ids_to_yappy), photo=photo(), caption=f"Твоё оспаривание выполнения '{task.url}' от {guilty_username} рассмотрено.\n\nОчки возвращены.", reply_to_message_id=task.msg_id)
        else:
            await query.message.reply('Отправляем очки: Не виновен')

            await bot.send_photo(get_key(guilty_username, tg_ids_to_yappy), photo=photo(), caption=
            f"Оспаривание выполнения задания: '{task.url}' от {task.creator} закрыто в твою пользу.")
            await bot.send_photo(get_key(task.creator, tg_ids_to_yappy), photo=photo(), caption=
            f"Твоё оспаривание выполнения '{task.url}'  от {guilty_username} рассмотрено.\n\nЗаявка отклонена.",
                                 reply_to_message_id=task.msg_id)

    except:
            traceback.print_exc()
@dp.message_handler(Text('Подтвердить',ignore_case=True),state=[BotHelperState.doing_task,BotHelperState.start_doing_task])
@dp.message_handler(commands='confirm',state=[BotHelperState.doing_task,BotHelperState.start_doing_task])
async def message_like_confirm(message: types.Message,state:FSMContext):
    await process_finish_liking(message, state=state)

@dp.callback_query_handler(text='confirm',state='*')
async def callback_like_confirm(query: types.CallbackQuery,state:FSMContext):
    message=query.message
    name=tg_ids_to_yappy[message.chat.id]
    try:
        await query.message.answer("Подтверждено!",reply_markup=quick_commands_kb)
        await query.message.edit_text("Подтверждено!",reply_markup=None)
    except:traceback.print_exc()
    await process_finish_liking(message,state=state)

async def process_finish_liking(message,state):
    name = tg_ids_to_yappy[message.chat.id]
    user:yappyUser.YappyUser = yappyUser.All_Users_Dict[name]
    try:
        state_data = await state.get_data()

        if 'task' in state_data:
            task = state_data['task']
        else:
            task = state_data
        while isinstance(task, dict) and 'task' in task:
            task = task['task']
        task = LikeTask.get_task_by_name(task)
        if task is None:
            await message.reply(
                f'Это задание было закончено или удалено. Сейчас автоматически откроется следующее. Кстати держи 1 бал')
            message.chat.id = message.chat.id
            await user.AddBalance(1, 'ActivityBot', f'За сломанное задание')
            await start_liking(message, state=state)
            return
        photo_path = None

        l_msg=await message.answer(
        f'Задание Выполняется!\n\n'
        f'{user.get_readable_balance()}', reply_markup=quick_commands_kb
                                   )

        state_data=await storage.get_data(chat=message.chat.id,user='task_doing')
        await storage.reset_data(chat=message.chat.id,user='task_doing')
        if 'photos_path' in state_data:
            all_photos = state_data['photos_path']
            files=list(filter(os.path.exists,all_photos))
            async def download(url):
                #file=await bot.get_file(url)
                #path=f"img/{file.file_path.rsplit('/', 1)[-1]}"
                path=await bot.download_file_by_id(url,destination_dir="img/")
                return path.name

            tasks=[await download(url) for url in utils.exclude(all_photos,files)]
            all_photos=files+tasks

            if len(all_photos) > 1:
                photo_path = utils.combine_imgs(all_photos)
            else:
                photo_path = all_photos[0]
        if photo_path is None:
            await message.reply(
                f'Очень странно, но фотография не была найдена на сервере. Пришлите еще раз. Доступные данные "{state_data}"')
            return
        keys = filter(lambda path: path[0] == name, task.done_history.keys())

        for username, tr_id in keys:
            if username == name or task.done_history[(username, tr_id)] == photo_path:
                await message.reply("Вы уже выполняли это задание. Это странный баг, но такое случается.")
                await state.finish()
                user.add_task_complete(task)
                return

        transaction_id = await task.AddComplete(whom=name, reason=photo_path)
        creator_id = get_key(task.creator, tg_ids_to_yappy)

        await message.answer_photo(photo=open(photo_path, 'rb'), caption=
        f'Задание завершено!\n\n'
        f'{user.get_readable_balance()}', reply_markup=quick_commands_kb
                                   )
        if 'l_msg' in vars():
            await l_msg.delete()
        state_data=await state.get_data()
        if 'msg_ids' in state_data:
            for msg_id in state_data['msg_ids']:
                # if msg_id != message.message_id:
                try:
                    await bot.delete_message(message.chat.id, message_id=msg_id)
                except MessageToDeleteNotFound:
                    pass
        await state.finish()
        try:
            if creator_id is not None:
                reply_to_message_id = task.msg_id if 'msg_id' in vars(task) else None

                dispute_button = InlineKeyboardButton("Оспорить",
                                                      callback_data=dispute_cb.new(task=task.name, tid=transaction_id,

                                                                                   username=name))
                dispute_keboard = InlineKeyboardMarkup()
                dispute_keboard.add(dispute_button)
                photo = open(photo_path, 'rb') if os.path.exists(photo_path) else photo_path
                await bot.send_photo(
                    creator_id, photo=photo,
                    caption=f'Твоё задание выполнил/а: {name}!\n\nУже сделано {task.done_amount} раз из {task.amount}',
                    reply_to_message_id=reply_to_message_id, reply_markup=dispute_keboard
                )

        except:
            traceback.print_exc()
        user.add_task_complete(task)
        new_level=level_system.get_level(user)
        if new_level:
            bonus=level_system.BONUS_FOR_NEXT_LEVEL[user.level]
            await bot.send_photo(chat_id=message.chat.id,photo=r'https://media.istockphoto.com/vectors/simple-flat-pixel-art-illustration-of-cartoon-golden-inscription-up-vector-id1335529268?k=20&m=1335529268&s=612x612&w=0&h=DCGXjxQxXPDxgNoyRq7gC9-H0Yis6gloaMl-uag9760=',caption=f"Поздравляем тебя с новым {user.level} уровнем!\n\n"
                                f"Награда в размере {bonus} очков начислена!")
            await user.AddBalance(bonus, 'ActivityBot', f'Уровень {user.level}')

    except:
        error = traceback.format_exc()
        traceback.print_exc()

        if task is not None:
            user.skip_tasks.add(str(task.name))
        await message.answer(
            f'Задание не удалось выполнить. Нажми /task для получения следующего.\n\nНе пугайся, перешли это сообщение @{config._settings.get("log_username", "careviolan")} и получи балл.\n\nЛоги ошибки:\n{error[:4000]}')
        await state.finish()
@dp.callback_query_handler(change_photo_cb.filter(),state='*')
async def callback_like_change(query: types.CallbackQuery,state: FSMContext,callback_data:dict,**kwargs):

    data=await storage.get_data(chat=query.message.chat.id,user='task_doing')
    kb = None
    try:
        texts=list(map(lambda x: x['text'], query.message.reply_markup.inline_keyboard[0]))
        if any(['Подтвердить' in text for text in texts]):
            kb=InlineKeyboardMarkup()
            Confirm_buton = InlineKeyboardButton(f"Подтвердить", callback_data='confirm')
            kb.add(Confirm_buton)
    except:traceback.print_exc()
    msg=await query.message.edit_text('Скриншот удалён.\n\nПришли другой, если требуется.',reply_markup=kb)
    photo_path=data['photo_path']
    data['photos_path'].remove(photo_path)
    if 'msg_ids' in data:
        data['msg_ids']+=[msg.message_id]
    else:
        data['msg_ids']=[msg.message_id]

    await storage.update_data(chat=query.message.chat.id,user=data['task'],data=data)
@dp.callback_query_handler(cancel_task_cb_admin.filter(),state='*')
async def vote_cancel_cb_admin_handler(query: types.CallbackQuery,state:FSMContext,callback_data:dict):

    await bot.answer_callback_query(query.id)
    await query.message.reply('Введите причину отмены:')
    await state.set_data(callback_data)
    await AdminHelperState.admin_cancel_task.set()

@dp.message_handler(state=AdminHelperState.admin_cancel_task)
async def vote_cancel_admin_handler(message:types.Message,state:FSMContext,**kwargs):

    callback_data = await state.get_data()
    await state.finish()
    taskname = callback_data['task']
    reason=message.text
    try:
        like_task: LikeTask.LikeTask = LikeTask.get_task_by_name(taskname)
        username = like_task.creator
        await bot.send_message(get_key(username, tg_ids_to_yappy), f'Задание {like_task.url} было отменено по причине: "{reason}"')
        await task_remove_handler(message, callback_data)
    except:
        traceback.print_exc()

@dp.callback_query_handler(cancel_task_cb.filter(),state='*')
async def vote_cancel_cb_handler(query: types.CallbackQuery,callback_data:dict):
    """
        Allow user to cancel any action
        """
    await bot.answer_callback_query(query.id)
    await task_remove_handler(query.message, callback_data,query=query)



async def task_remove_handler(message: types.Message, callback_data: dict,query=None):
    """
        Allow user to cancel any action
        """

    taskname=callback_data['task']
    try:
        like_task:LikeTask.LikeTask=LikeTask.get_task_by_name(taskname)
        username = like_task.creator
        user = yappyUser.All_Users_Dict[username]
        user.reserved_amount-=(like_task.amount-like_task.done_amount)*like_task.done_cost
        LikeTask.remove_task(like_task)
        if not any(LikeTask.All_Tasks[username]):
            user.reserved_amount=0
        if query is None:
            await message.reply(f'Удаляю задание {like_task.url} от {like_task.creator}.',reply_markup=quick_commands_kb)
        else:
            await message.edit_text(f'Удаляю задание {like_task.url} от {like_task.creator}.',reply_markup=None)

    except IndexError:
        await message.reply('Нет заданий', reply_markup=quick_commands_kb)


@dp.callback_query_handler(text='cancel',state='*')
async def tasl_remove_cb_handler(query: types.CallbackQuery,state:FSMContext,**kwargs):
    """
        Allow user to cancel any action
        """
    await bot.answer_callback_query(query.id)

    await cancel_handler(query.message,state=state)

@dp.errors_handler(exception=MessageNotModified)  # for skipping this exception
async def message_not_modified_handler(update, error):
    return True
class RegisterState(StatesGroup):
    name=State()
    refferal=State()
    password=State()
class SettingsState(StatesGroup):
    password=State()
@dp.message_handler(commands=['start', 'help'],state='*')
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    if str(message.chat.id) not in config._settings.get('admin_ids',['540308572','65326877']):
        await bot.set_my_commands(commands,scope=BotCommandScopeDefault())
    else:
        await bot.set_my_commands(admin_commands,scope=BotCommandScopeDefault())
    try:
        args = message.get_args()
        payload = aiogram.utils.deep_linking.decode_payload(args)
        if payload in tg_ids_to_yappy.values():
            await storage.update_data(chat=message.chat.id,data={'ref':payload})
    except:traceback.print_exc()
    if message.chat.id in tg_ids_to_yappy.keys():
        await message.reply(f"*{tg_ids_to_yappy[message.chat.id]}*, снова привет!\n\n*Новые задания* уже в ленте!", reply_markup=quick_commands_kb, parse_mode= "Markdown")
        return

    await message.reply(f"Привет! Я – *Бот взаимной активности* в {config._settings.get('APP_NAME',default='Yappy')}. Напиши свой "
                        f"никнейм:",reply_markup=ReplyKeyboardRemove(), parse_mode= "Markdown")

    await RegisterState.name.set()

def strip_command(stri):
    return stri.split(' ',1)[1]

@dp.message_handler(commands=['rules'])
async def get_rules(message: types.Message,**kwargs):
    def_rules='''
Продолжая использование Бота, ты подтверждаешь согласие с Правилами:


1. Максимальное количество действий в одном задании — 3 (три).

Лайк, подписка, коммент (ссылка на ролик);
Подписка (ссылка на аккаунт) и т.п.

Задания, нарушающие или обходящие Правила, удаляются.


2. Если скриншот/ы не доказывают полное выполнение условий — спор будет закрыт в пользу автора задания.

Гайды:
https://telegra.ph/Primery-vypolneniya-zadanij-v-Yappy-07-09
https://telegra.ph/Kak-vypolnyat-zadaniya-v-OzonActivityBot-07-12


3. Удалять комментарии, снимать лайки или отписываться после выполнения задания запрещено.
Штраф – 25 очков и блокировка при повторном нарушении.

4. Ссылки на любые другие соцсети, ресурсы или приложения запрещены.

При частых или злостных нарушениях — Пользователь может быть заблокирован.


Бот Yappy: @YappyActivityBot
Бот Ozon: @OzonActivityBot
Бот VK: @VKActivity_bot
Бот Instagram: @InstagramActivityBot
Бот Rutube: @RutubeActivityBot

Чат: @ShareActivity


@ActivityBots
'''
    rules_text=config._settings.get('rules',def_rules)
    await message.reply(rules_text)
@dp.message_handler(commands='invite')
@dp.message_handler(Text('Пригласить',ignore_case=True))
async def start_refferal(message: types.Message,state:FSMContext):
    username = tg_ids_to_yappy[message.chat.id]
    link=await aiogram.utils.deep_linking.get_start_link(username,encode=True)
    await message.reply(link)
@dp.message_handler(commands='refferal')
async def start_refferal(message: types.Message,state:FSMContext):
    username = tg_ids_to_yappy[message.chat.id]
    user: yappyUser.YappyUser = yappyUser.All_Users_Dict[username]
    if user.refferal_can_set():
        data=await storage.get_data(chat=message.chat.id)
        if 'ref' in data:
            message.text=data['ref']
            await send_refferal(message,state)
        else:
            await RegisterState.refferal.set()
            await message.reply('Напиши никнейм того, кто тебя пригласил. Если тебя никто не приглашал, нажми /cancel')
    else:
        await message.reply('Уже нельзя установить того, кто тебя пригласил.')
def refferal_task_complete(username,**kwargs):
    user:yappyUser.YappyUser=yappyUser.All_Users_Dict[username]
    if user.have_refferer():
        if 'task_creator' in kwargs and kwargs['task_creator']==user.affiliate:return
        firsts_tasks = []
        for task_name in user.done_tasks:
            task=LikeTask.get_task_by_name(task_name)
            if task is not None and task.creator != user.affiliate:
                firsts_tasks.append(task)
        loop = asyncio.get_running_loop()
        if not any(firsts_tasks):
            refferal=user.affiliate
            refferal_user=yappyUser.All_Users_Dict[refferal]
            refferer_init_bouns = config._settings.get('refferer_init_bonus', default=2)



            loop.create_task( refferal_user.AddBalance(refferer_init_bouns, 'ActivityBot', f'За приглашение {username}'))
            loop.create_task( bot.send_message(get_key(refferal, tg_ids_to_yappy),
                                   f'Спасибо за то, что пригласил/а {username}!\n\nТебе добавлено:{refferer_init_bouns} очков.'))
        else:
            refferal = user.affiliate
            refferal_user = yappyUser.All_Users_Dict[refferal]
            refferer_init_bouns = config._settings.get('refferer_complete_bonus', default=0.1)


            loop.create_task( refferal_user.AddBalance(refferer_init_bouns, 'ActivityBot', f'За выполнение {username} заданий'))

            loop = asyncio.get_running_loop()
            #loop.create_task(bot.send_message(get_key(refferal, tg_ids_to_yappy),
             #                                 f'Спасибо за то, что пригласил/а {username}!\n\nТебе добавлено:{refferer_init_bouns} очков.'))


@dp.message_handler(state=RegisterState.refferal)
async def send_refferal(message: types.Message,state:FSMContext):

    refferer = message.text
    if refferer.startswith('/'):
        if  refferer in [c.command for c in normal_commands]:
            await message.reply('Напиши *никнейм* того, кто тебя пригласил, чтобы продолжить.',parse_mode="Markdown")
            return
        elif refferer.startswith('/cancel') :
            await get_rules(message)
            await cancel_handler(message,state=state)
            return
    if '/' in refferer:
            await message.reply('Напиши *никнейм*, а не ссылку, того, кто тебя пригласил, чтобы продолжить.',parse_mode="Markdown")
            return
    refferer=refferer.replace('@','').lower()
    if refferer not in yappyUser.All_Users_Dict:
        await message.reply(f'Пользователь с ником {refferer} не найден.', parse_mode="Markdown")
        return
    try:
        username=tg_ids_to_yappy[message.chat.id]
        user:yappyUser.YappyUser=yappyUser.All_Users_Dict[username]
        if refferer!=username:
            user.set_refferal(refferer)
            await message.reply(f'Мы сказали спасибо {refferer}')
            await bot.send_message(get_key(refferer, tg_ids_to_yappy), f'Спасибо за то, что пригласил/а {username}!\n\nКогда пользователь выполнит первое задание, ты получишь бонус за приглашение!')
        else:
            await message.answer_photo("http://risovach.ru/upload/2015/04/mem/hitriy-getsbi_79275296_orig_.jpg",caption="нельзя указать самого себя в реферальной программе. Напишите /refferal")
    except:
        traceback.print_exc()
        await message.reply('Не удалось установить никнейм того, кто вас пригласил. Если хотите попробовать еще раз нажмите /refferal')

    await state.finish()
    await get_rules(message)

@dp.message_handler(state=RegisterState.name)
async def send_name(message: types.Message,state:FSMContext):
    try:
        args = message.get_args()
        payload = aiogram.utils.deep_linking.decode_payload(args)
        if payload in tg_ids_to_yappy.values():
            await storage.update_data(chat=message.chat.id,data={'ref':payload})
    except TypeError:pass
    except:traceback.print_exc()
    yappy_username = message.text
    if yappy_username.startswith('/') or yappy_username in map(operator.attrgetter('description'),commands) or '/' in yappy_username:
        if  yappy_username in [c.command for c in normal_commands]:
            await message.reply('Напиши свой *никнейм*, чтобы продолжить.',parse_mode="Markdown")
            return
        elif yappy_username.startswith('/cancel') :
            await cancel_handler(message,state=state)
            return
        else:
            await message.reply('Напиши свой *никнейм*, чтобы продолжить.',parse_mode="Markdown")
            return

    yappy_username=yappy_username.replace('@','').lower()
    try:
        old_username = tg_ids_to_yappy[message.chat.id]
        if old_username == yappy_username:
            await state.finish()
            return await message.reply(f'Ты написал такой же никнейм {yappy_username}, какой и был указан раньше.')
    except:traceback.print_exc()
    try:
        if yappy_username not in yappyUser.All_Users_Dict:
                user = await create_user(yappy_username)


        if yappyUser.All_Users_Dict[yappy_username].has_password():

            return await send_password(message, state=state, yappy_username=yappy_username)
        else:
            if yappy_username in tg_ids_to_yappy.values():

                return await message.reply(f'Этот никнейм {config._settings.get("APP_NAME", default="yappy")} уже зарегистрирован. Если он твой – установи пароль на старом телеграмме через комманду /pass и попробуй снова. Тебя спросят пароль. Бот будет отправлять сообщения последнему залогиненому устройству!')


            tg_ids_to_yappy[message.chat.id] = yappy_username
            user=yappyUser.All_Users_Dict[yappy_username]
            await message.reply(f'Отлично! Спасибо за регистрацию, {yappy_username}.')


            if user.refferal_can_set():
                await start_refferal(message,state)
            else:
                await state.finish()
                await get_rules(message)


    except:
        traceback.print_exc()
        await message.answer(f'Пользователь с ником {yappy_username} не найден!')

    await config.data.async_set('tg_ids_to_yappy', tg_ids_to_yappy)


async def create_user(yappy_username):
    user = yappyUser.YappyUser(yappy_username)
    active_users, average_task_comlete_count, inflation, prev_day_tasks, task_complete_count, tasks_count = await get_inflation(
        user
    )
    user.complets_to_unlock_creating = average_task_comlete_count
    user.callbacks['first_task_complete'] += [partial(refferal_task_complete, username=yappy_username)]
    return user


@dp.message_handler(commands=['name'])
@dp.message_handler(regexp='Никнейм')
async def _send_name(message: types.Message,state:FSMContext):
    try:
        message.text = strip_command(message.text)
    except:
        await message.reply(f'Напиши свой никнейм в {config._settings.get("APP_NAME",default="Yappy")}.')
        await RegisterState.name.set()
        return
    await send_name(message,state)
async def get_inflation(user):
    all_tasks = LikeTask.Get_Undone_Tasks()
    all_tasks=user.is_skiping_tasks(all_tasks)
    active_users = 1 + yappyUser.YappyUser.get_active_users_count()
    today_tasks = list(
        filter(lambda task: task.created_at.date()==datetime.datetime.today().date() and not task.is_active(),
               filter(None, utils.flatten(LikeTask.All_Tasks.values())+list(LikeTask.All_Tasks_History.values()))))
    task_complete_count = 1 + len(today_tasks)
    tasks_count = len(all_tasks) + 1
    # volume=sum(map(lambda task:(task.amount-task.done_amount)*task.done_cost,all_tasks))
    inflation = 1 - task_complete_count / tasks_count
    prev_day_tasks=utils.exclude(all_tasks,today_tasks)
    prev_day_tasks=user.is_skiping_tasks(prev_day_tasks)
    if inflation>0.5:
        average_task_comlete_count = int(((tasks_count - len(prev_day_tasks))/ active_users) + (len(prev_day_tasks)/(max(1,user.level))))
        average_task_comlete_count = min(average_task_comlete_count, 50,tasks_count)
    else:
        average_task_comlete_count=0
    return active_users, average_task_comlete_count, inflation, prev_day_tasks, task_complete_count, tasks_count
def registerded_user(func):
    """Декоратор первичного обработчика сообщения, отвечает за контроль доступа и логи"""
    async def user_msg_handler(message: types.Message,**kwargs):
        telegram_id = message.chat.id

        if telegram_id in tg_ids_to_yappy.keys():
            username=tg_ids_to_yappy[telegram_id]
            if username not in yappyUser.All_Users_Dict.keys():
                try:
                    user=create_user(username)
                except:
                    await message.reply(f"Ошибка,нажми /name и напиши свой никнейм ещё раз.\n\nинформация для разработчика {traceback.format_exc()}")
                    traceback.print_exc()
            try:
                time1 = time.time()
                try:
                    if message.text and message.text.startswith('/cancel'):
                        return await cancel_handler(message,**kwargs)
                except:traceback.print_exc()
                await func(message, **kwargs)
                time2 = time.time()
                ms = (time2 - time1) * 1000.0
                if ms>10000:
                    print('%s function took %0.3f ms' % (func.__name__, ms))

                user=yappyUser.All_Users_Dict[username]
                if   ( datetime.datetime.today().date() > user.last_login_time.date()):
                    user.unlock_today = False
                    active_users, average_task_comlete_count, inflation, prev_day_tasks, task_complete_count, tasks_count = await get_inflation(
                        user)
                    today_complete = user.completes_by_day[datetime.datetime.today().date()]
                    tasks_complete = "\n".join(
                        map(lambda tuple: f"{tuple[0]}, сделано {tuple[1]} заданий",
                            list(sorted(user.completes_by_day.items(), key=lambda tuple: tuple[0],reverse=True))[-7:-2]))
                    if average_task_comlete_count> today_complete:
                        user.complets_to_unlock_creating=average_task_comlete_count-today_complete
                    await message.answer_photo('http://risovach.ru/upload/2013/03/mem/fraj_13021855_orig_.jpg',caption=f"Добро пожаловать!  В последний раз виделись {(user.last_login_time)}.История%\n {tasks_complete}. Чтобы создать задание, решите еще {user.complets_to_unlock_creating} заданий")
                    user.last_login_time = datetime.datetime.now()

            except:
                traceback.print_exc()
                await message.reply(f'Мне жаль, что-то пошло не так: {traceback.format_exc()[-3000:]}')
        else:
            await message.reply(f"Привет! Я – *Бот взаимной активности* в {config._settings.get('APP_NAME',default='yappy')}.\n\nНапиши "
                                f"свой никнейм:",reply_markup=ReplyKeyboardRemove(), parse_mode= "Markdown")
            await RegisterState.name.set()
    return user_msg_handler
@dp.message_handler(commands=['balance'])
@dp.message_handler(regexp='Баланс')
@registerded_user
async def send_balance(message: types.Message,**kwargs):
    name=tg_ids_to_yappy[message.chat.id]
    user:yappyUser.YappyUser=yappyUser.All_Users_Dict[name]
    balance=user.coins
    await send_balance_(message, user)
    if 'telegram_username' not in vars(user):
        user.telegram_username=message.from_user.username

async def send_password(message: types.Message,state:FSMContext,yappy_username:str,**kwargs):

    await RegisterState.password.set()
    await state.update_data(name=yappy_username)
    return await message.answer(f'Введи пароль для *{yappy_username}*от трёх символов.', parse_mode= "Markdown")
def can_cancel(func):
    async def cancel_def_handler(messsage:types.Message,**kwargs):
        if messsage.text and messsage.text.startswith('/cancel'):
            return await cancel_handler(messsage,**kwargs)
        await func(messsage,**kwargs)
    return cancel_def_handler
@dp.message_handler(regexp='.{3,}',state=RegisterState.password)
@can_cancel
async def input_password(message: types.Message, state:FSMContext,**kwargs):


    try:
        data = await state.get_data()
        name = data['name']
        user=yappyUser.All_Users_Dict[name]
        if not user.has_password():
            await state.finish()
            return await message.answer('Установи пароль, нажав /pass!')
        else:
            if not user.same_passord(message.text):
                if str(message.chat.id) in  config._settings.get('admin_ids', ['540308572', '65326877']):
                    await message.reply(f"Пароль: '{user.password}'")
                return await message.answer('Пароль не совпадает.')
            else:

                tg_ids_to_yappy[message.chat.id]=name
                await state.finish()
                return await message.answer(f'Привет, {name}')
    except:
        traceback.print_exc()
        return await message.answer('Ошибка установки пароля.')


@dp.message_handler(commands=['pass'])
@dp.message_handler(regexp='Пароль')
@registerded_user
async def send_settings_password(message: types.Message,**kwargs):


    await SettingsState.password.set()
    return await message.answer('Напишите пароль от трех символов')

@dp.message_handler(regexp='.{3,}',state=SettingsState.password)
@registerded_user
async def input_settings_password(message: types.Message, state:FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.chat.id]
    user: yappyUser.YappyUser = yappyUser.All_Users_Dict[name]
    await state.finish()
    if 'password' not in vars(user):
        await message.answer('Пароль впервые установлен')
    else:
        await message.answer('Пароль успешно изменен')
    password=message.text.strip()
    if password.startswith('/') and ' ' in password: password=strip_command(password)
    user.password=password
@dp.message_handler(state=[RegisterState.password,SettingsState.password])
@registerded_user
async def input_settings_password_invalid(message: types.Message, state:FSMContext,**kwargs):
    await message.answer("Введите пароль от трех символов")

async def send_balance_(message, user):
    tasks_complete = "\n".join(
        map(lambda tuple: f"{tuple[0]}, сделано {tuple[1]} заданий", reversed(list(sorted(user.completes_by_day.items(),key=lambda tuple:tuple[0],reverse=False))[-7:-2])))
    await message.reply(f'*{user.username}*, *{user.level}* уровень\n\n'
                        f'До повышения *{user.tasks_to_next_level}* заданий\n\_\_\_\_\n\n*{user.get_readable_balance()}*\nЧтобы создать новое – осталось выполнить* {user.complets_to_unlock_creating} *заданий.\n\nВсего выполнено* {len(user.done_tasks)} *заданий\nСегодня: *{user.completes_by_day[datetime.datetime.today().date()]}* | Вчера: *{user.completes_by_day[(datetime.datetime.today() - datetime.timedelta(days=1)).date()]}* \n{tasks_complete}',
                        reply_markup=quick_commands_kb, parse_mode="Markdown")


@dp.message_handler(commands=['history'])
@dp.message_handler(regexp='История')
@dp.message_handler(regexp='/history\d+')
@registerded_user
async def send_photos(message: types.Message,**kwargs):
    name=tg_ids_to_yappy[message.chat.id]
    await send_history(message, name)


async def send_history(message, username):

    try:
        await dp.throttle(key='history', rate=2, user_id=message.from_user.id, chat_id=message.chat.id)
    except Throttled:
        return await message.answer_photo(photo='http://risovach.ru/upload/2014/09/mem/moe-lico_60802046_orig_.jpeg',
                                   caption='Слишком много запросов от тебя. Подожди немного и повтори.')
    user: yappyUser.YappyUser = yappyUser.All_Users_Dict[username]
    await asyncio.get_running_loop().run_in_executor(None, user.update_photos)
    photos = set(list(map(operator.attrgetter('reason'), user.transactionHistory))).union(user.photos)
    page = 0
    try:
        page = int(re.findall(r'\d+',message.text)[-1])
    except IndexError:pass
    except ValueError:
        pass
    except:
        traceback.print_exc()
    # Good bots should send chat actions...
    if any(photos):
        # await types.ChatActions.upload_photo()

        done_photos = []
        all_photos = photos
        tasks_send = []
        tasks_recived = []
        for photo in all_photos:
            try:
                name = photo.rsplit('.', 1)[0].split('/')[-1]
                task_numer = int(re.findall(r' \d+', name, re.I)[0])
                tasks_send.append((task_numer, photo,name))
            except:
                task_numer += 1
                tasks_send.append((task_numer, photo,name))

        tasks_send = sorted(tasks_send, key=lambda tuple: tuple[0],reverse=True)

        page_len = 5
        num=0
        for i in range(page*page_len, page_len*(page+1)):
            try:
                numz, photo,task_name = tasks_send[i]
                name_ =num
                task_numer=task_name[:20]
                num+=1
                buttin_more = InlineKeyboardButton(text='Подробнее', callback_data=more_info_cb.new(photo=num))
                kb = InlineKeyboardMarkup()
                kb.add(buttin_more)
                try:
                    if page==0 :
                        msg = await message.answer(f'{i}){task_name}', reply_markup=kb)
                    else:
                        data = await storage.get_data(chat=message.chat.id, user=num)


                        message_id=data['mid']
                        msg = await bot.edit_message_text(f'{i}){task_name}', chat_id=message.chat.id,
                                                      message_id=message_id, reply_markup=kb)
                except:
                    traceback.print_exc()
                    msg = await message.answer(f'{i}){task_name}', reply_markup=kb)
                await storage.update_data(chat=message.chat.id, user=num, data={'photo': photo, 'user': name,"mid":msg.message_id})
            except:
                traceback.print_exc()
        next_page=f'/history{page+1}'
        try:
            if "/info" in message.text:
                next_page=f"/info{page+1}@{username}"

            max_page = int(len(tasks_send) / page_len)
            if page+1<=max_page:
                try:
                    old_data=  await storage.get_data(chat=message.chat.id, user=-1)
                    error=True
                    if 'mid' in old_data and page!=0:
                        error=False
                        msg = await bot.edit_message_text(
                            f"Страница {page} | Всего страниц {max_page} \nДля переходя на следующую напишите: {next_page}",chat_id=message.chat.id,message_id=old_data['mid'])
                except:error=True
                if error:
                    msg = await message.answer(
                        f"Страница {page} | Всего страниц {max_page} \nДля переходя на следующую напишите: {next_page}")
                    await storage.update_data(chat=message.chat.id, user=-1, data={"mid":msg.message_id})
        except:traceback.print_exc()

@dp.callback_query_handler(more_info_cb.filter(), state='*')
async def more_info_handler(query: types.CallbackQuery, state: FSMContext,callback_data:dict, **kwargs):

    photo_short=callback_data['photo']
    data=await storage.get_data(chat=query.message.chat.id,user=photo_short)
    photo=data['photo']
    username=data['user']
    if 'photo' in vars():
        name = photo.split('.')[0].split('/')[-1]
        await query.message.answer_photo(open(photo,'rb+'),caption=name)
    else:
        await query.message.answer(photo_short)

# You can use state '*' if you need to handle all states
@dp.message_handler( commands='cancel',state='*')
@dp.message_handler(Text(equals='Отмена', ignore_case=True),state='*')
async def cancel_handler(message: types.Message, state: FSMContext,**kwargs):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()

    sended = 'Отменено.'
    try:
        if current_state == BotHelperState.start_doing_task.state:
            name = tg_ids_to_yappy[message.chat.id]
            user:yappyUser.YappyUser = yappyUser.All_Users_Dict[name]


            task=await state.get_data('task')

            while isinstance(task,dict) and 'task' in task:
                task=task['task']
            task: LikeTask.LikeTask=LikeTask.get_task_by_name(task)
            if task:
                user.skip_tasks.add(str(task.name))
                sended=f'Задание от {task.creator} отменено.'
                task.reserved_done_amount -= 1
    except:
        traceback.print_exc()
    if current_state is not None:
        await state.finish()
    await message.reply(sended, reply_markup=quick_commands_kb)
    logging.info('Отменено. state %r', current_state)
    # Cancel state and inform user about it

    # And remove keyboard (just in case)


lock=asyncio.Lock()


async def handler_throttled(message: types.Message, **kwargs):
    msg=await message.answer("Подождите немного!")
    await asyncio.sleep(random.uniform(1.1,1.5))
    await finish_liking(message,**kwargs)
    await msg.delete()
@dp.message_handler(content_types=types.ContentTypes.PHOTO, state='*')
@registerded_user
@dp.throttled(handler_throttled,rate=1)
async def finish_liking(message: types.Message, state: FSMContext,**kwargs):
    #global lock
    name = tg_ids_to_yappy[message.chat.id]
    timers=[(time.time(),'before_all')]
    msg = None
    _t = None



    try:


        async def _local_f():
            step = 2
            state_data = await storage.get_data(chat=message.chat.id, user='task_doing')
            #await asyncio.sleep(1)
            #if 'photos_path' not in state_data :
            #if "photos_path" not in state_data or not any(state_data["photos_path"]):
            msg= await message.reply(
            f'Загружаю фотографии {len(state_data["photos_path"])+1 if "photos_path" in state_data else 1} шт', reply_markup=accept_kb)
                #async def delete():
                    #await asyncio.sleep(2)
                    #await msg.delete()
                #asyncio.get_running_loop().create_task(delete())


        _t = asyncio.get_running_loop().create_task(_local_f())

        task_name = await state.get_data()
        while (isinstance(task_name, dict)) and 'task' in task_name:
            task_name = task_name['task']
    except:traceback.print_exc()
    try:

        task:LikeTask.LikeTask=LikeTask.get_task_by_name(str(task_name))
        if task is None :
            await state.finish()
            await message.reply(f'У тебя нет активного задания! Чтобы его получить, нажми /like')
            return


        last_photo= message.photo.pop()
        photo_path= last_photo.file_id

        timers.append((time.time(), 'before_throttle'))

        state_data = await storage.get_data(chat=message.chat.id,user='task_doing')
        if 'photos_path' in state_data:
            paths = state_data['photos_path']
            paths.append(photo_path)
        else:
            paths = [photo_path]

        dict_state = {'task': task.name, 'photo_path': photo_path, 'photos_path': paths}
        timers.append((time.time(), 'before_updare_state'))
        await storage.update_data(chat=message.chat.id, user='task_doing',data=dict_state)
        timers.append((time.time(), 'after_updare_state'))
        Edit_buton=InlineKeyboardButton("Удалить",callback_data=change_photo_cb.new(photo_path=task_name))
        keyboard_for_answer=InlineKeyboardMarkup()
        keyboard_for_answer.add(Edit_buton)

        timers.append((time.time(), 'before_reply'))
        trxt = '*Внимательно проверь скриншоты* и нажми Подвердить или /confirm.\n\nВ случае ошибки – нажми удалить под неверным скриншотом.'

        if msg:
            await msg.delete()
        if _t:
            await _t
        #if config._settings.get("is_use_WEBHOOK", False):
            #return SendMessage(message.chat.id,trxt, reply_markup=keyboard_for_answer, parse_mode="Markdown").reply(message)

        msg=await message.reply(trxt, reply_markup=keyboard_for_answer, parse_mode="Markdown")
        timers.append((time.time(), 'after_reply'))


        new_data=await state.get_data()
        if 'msg_ids' in new_data:
            msg_ids=new_data['msg_ids']
            msg_ids.append(msg.message_id)
        else:
            msg_ids=[msg.message_id]
        new_data['msg_ids']=msg_ids
        await state.update_data(new_data)
        timers.append((time.time(), 'finish'))
        def dif_ms(timer_new,timer_old):return (timer_new-timer_old)*1000
        if dif_ms(timers[-1][0],timers[0][0])>10000:
            for i in range(1,len(timers)):
                t2,name=timers[i]
                t1 = timers[i - 1][0]
                t=dif_ms(t2, t1)
                print(f"{name} took {t} ms, total {dif_ms(t2,timers[0][0])}")
    except:
        error=traceback.format_exc()
        traceback.print_exc()
        await message.reply(f'Что-то пошло не так. Ошибка: {error}')


@dp.message_handler(commands='like')
@dp.message_handler(regexp='[Вв]ыполнить [Зз]адание')
@registerded_user
@dp.async_task
async def start_liking(message: types.Message, state: FSMContext,**kwargs):
    global premium_ids
    name = tg_ids_to_yappy[message.chat.id]
    user:yappyUser.YappyUser=yappyUser.All_Users_Dict[name]
    a_tasks=LikeTask.Get_Undone_Tasks(name)

    _tasks=user.is_skiping_tasks(a_tasks)
    tasks=[]
    for task in _tasks:
        keys = list(filter(lambda x:x[0]==name,task.done_history.keys()))
        error=any(keys)

        if error:continue
        tasks.append(task)
    if not any(tasks):
        await message.reply(f'Все задания выполнены. *Создавай новые!*', reply_markup=quick_commands_kb, parse_mode= "Markdown")
        return
    await message.reply(f'Сейчас активных заданий: *{len(tasks)}*', parse_mode= "Markdown",reply_markup=quick_commands_kb)
    task=tasks[0]
    await state.reset_data()
    await BotHelperState.start_doing_task.set()
    await state.set_data({'task':str(task.name)})
    next_task_kb, text = await task_to_tg(message, premium_ids, state, task, tasks)
    if config._settings.get("is_use_WEBHOOK",False):
        return SendMessage(message.chat.id,text,reply_markup=next_task_kb)
    await message.reply(text, reply_markup=next_task_kb)


async def task_to_tg(message, premium_ids, state, task, tasks):
    text = await get_task_readable(task)
    next_task_kb = InlineKeyboardMarkup()
    cancel_task_bt = InlineKeyboardButton("Отмена", callback_data="cancel")
    next_task_kb.row(cancel_task_bt)
    if message.chat.id in premium_ids:

        if len(tasks) > 1:

            next_task = task
            step = 5
            while next_task.creator == task.creator and step > 0:
                next_task = random.choice(tasks)
                step -= 1
            next_task_bt = InlineKeyboardButton("Другое", callback_data=next_task_cb.new(task=next_task.name))
            data = {}
            data['tasks'] = list(map(operator.attrgetter('name'), tasks))
            data['task'] = task.name
            task.reserved_done_amount+=1
            await state.update_data(data)
            next_task_kb.row(next_task_bt)
    return next_task_kb, text


async def get_task_readable(task):
    text = f'''Задание:
{task.url}

Автор: {task.creator}
_____

Пришли скриншот/ы выполнения, чтобы завершить задание.
'''
    return text


@dp.callback_query_handler(next_task_cb.filter(),state=BotHelperState.start_doing_task)
async def next_task_cb_handler(query: types.CallbackQuery, state:FSMContext,callback_data: dict):
    taskname=callback_data['task']
    message_id=query.message.message_id
    message=query.message
    await bot.answer_callback_query(query.id)
    task=LikeTask.get_task_by_name(taskname)
    state_data=await state.get_data()
    try:
        await state.update_data({'task': str(task.name)})
        tasks = list(filter(None, map(LikeTask.get_task_by_name, state_data['tasks'])))
        next_task_kb, text = await task_to_tg(message, premium_ids, state, task, tasks)

        await bot.edit_message_text(text=text,chat_id=message.chat.id,message_id=message_id,reply_markup=next_task_kb)
    except MessageNotModified:pass
    except:
        error=traceback.format_exc()
        traceback.print_exc()
        await query.message.reply(f"не удалось взять следующее задание")
@dp.callback_query_handler(new_task_cb.filter(action='up'))
async def input_task_amount_cb_handler(query: types.CallbackQuery, callback_data: dict):
    name = tg_ids_to_yappy[query.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    await query.answer('Введи количество очков, которое ты потратишь на задание. Оно равно количеству человек, которым будет '
                       f'предложено его выполнить.\n\n {user.get_readable_balance()}\n\nЕсли передумал/а — нажми Отмена.'
                       )
    await CreateTaskStates.amount.set()
@dp.callback_query_handler(buy_cb.filter())
async def vote_buy_handler(query: types.CallbackQuery,state,callback_data:dict,**kwargs):

    user:yappyUser.YappyUser=yappyUser.All_Users_Dict[tg_ids_to_yappy[query.from_user.id]]

    amount=float(callback_data['amount'])
    if user.get_max_spend_amount()<amount:
        await query.answer('Недостаточный баланс')
        return
    await user.AddBalance(-amount,'ActivityBot','Купил пропуск')
    user.complets_to_unlock_creating=0
    user.unlock_today=True
    user.last_login_time=datetime.datetime.now()
    await query.answer('Готово')
    query.message.chat.id=query.from_user.id
    await vote_task_cb_handler(message=query.message,state=state)

@dp.message_handler(regexp='Создать задание')
@dp.message_handler(commands='task')
@registerded_user
async def vote_task_cb_handler(message: types.Message,state,**kwargs):
    global premium_ids
    name = tg_ids_to_yappy[message.chat.id]
    user:yappyUser.YappyUser=yappyUser.All_Users_Dict[name]

    if user.complets_to_unlock_creating>0:

        kb=InlineKeyboardMarkup()
        if user.get_max_spend_amount()>user.complets_to_unlock_creating:
            bt=InlineKeyboardButton(f"Купить Пропуск за {user.complets_to_unlock_creating} баллов",callback_data=buy_cb.new(amount=user.complets_to_unlock_creating))
            kb.add(bt)


        await message.answer(f'Чтобы создавать свои, тебе осталось выполнить ещё {user.complets_to_unlock_creating} заданий.',reply_markup=kb)

        return

    text_and_data = (
        ('Отмена', 'cancel'),
    )
    keyboard_markup = types.InlineKeyboardMarkup(row_width=3)
    row_btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in text_and_data)
    keyboard_markup.row(*row_btns)
    keyboard_digit=ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=True)
    digits=(types.KeyboardButton(str(i))  for i in range(1,int(user.get_max_spend_amount())+1))
    keyboard_digit.add(*digits)
    await CreateTaskStates.amount.set()
    await message.reply(f'*Введи количество очков*, которое ты потратишь на задание. Оно равно *количеству человек*, которым будет предложено его выполнить.\n\nТвой баланс: *{user.get_max_spend_amount()}*', parse_mode= "Markdown", reply_markup=keyboard_digit)
    await message.reply('Если передумал/а — нажми *Отмена*.', parse_mode= "Markdown", reply_markup=keyboard_markup)



@dp.callback_query_handler(new_task_cb.filter(action='task_description'))
async def task_descriptio_hander(query: types.CallbackQuery,  state: FSMContext,callback_data: dict):
    name = tg_ids_to_yappy[query.from_user.id]
    user:yappyUser.YappyUser=yappyUser.All_Users_Dict[name]
    task_description=callback_data['amount']
    await state.set_data({'description':task_description})
    await bot.send_message(query.from_user.id,'*Введи количество очков*, которое ты потратишь на задание. Оно равно количеству '
                                              'человек, '
                              f'которым будет предложено его выполнить.\n\n: *{user.get_readable_balance()}*',
                           parse_mode= "Markdown")
    await CreateTaskStates.amount.set()

@dp.callback_query_handler(new_task_cb.filter(action='like'))
async def vote_like_cb_handler(query: types.CallbackQuery, callback_data: dict):
    name = tg_ids_to_yappy[query.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    await BotHelperState.get_target.set()



@dp.message_handler(state=CreateTaskStates.amount,regexp='^ ?[0-9]+ ?[0-9]* ?$')
async def task_input_amount(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.chat.id]
    user=yappyUser.All_Users_Dict[name]
    try:
        two_digits=re.findall('\d+ +\d+', message.text)
        if any(two_digits):
            amount,cost_amount=two_digits[0].split(' ',1)
            amount=float(amount)
            cost_amount=float(cost_amount)
        else:
            cost_amount=1.0
            amount =float( message.text )
        await state.update_data({'amount':amount,'cost_amount':cost_amount})

        if user.coins<amount*cost_amount+user.reserved_amount:
            await message.reply(f'Недостаточно очков. Доступный баланс: *{user.get_readable_balance()}*\n\n'
                                f'Попробуй ещё раз или нажми */cancel*.', parse_mode= "Markdown")
        else:
            data= await state.get_data()
            if 'description' not in data:
                await CreateTaskStates.next()
                special_rules=  f'– Максимальное количество действий в одном задании – *3 (три)*.\n\n'\
                                    f'Лайк + коммент + подписка (ссылка на ролик);'\
                                    f'\nЛайк + просмотр до конца (ссылка на ролик) и т.п.'
                special_rules=config._settings.get('special_rules',default=special_rules)
                await message.reply(f'Ты потратишь {amount} очков.\n\n'
                                    f'Теперь напиши описание задания.\n\n'
                                    f'– В тексте *обязательно* должна быть ссылка на аккаунт или пост;\n{special_rules}'
                                    
                                    f'\n\n– Любые приписки к заданию, кроме действий, *повышают вероятность* его *пропуска* пользователями. Оспаривания по ним не рассматриваются.'
                                    f'\n\nНарушение Правил приведёт к снятию очков, отмене задания или блокировке.'
                                    , parse_mode= "Markdown",reply_markup=ReplyKeyboardRemove())
            else:
                await _create_task(amount,message,name,data['description'],user,cost_amount)

    except:
        h_b=InlineKeyboardButton('Возможно, это было описание задания', callback_data=new_task_cb.new(action='task_description', amount=message.text))
        await message.reply('Введено неправильное количество очков.',reply_markup=InlineKeyboardMarkup().add(h_b))
        traceback.print_exc()

@dp.message_handler(state=CreateTaskStates.amount)
async def task_input_amount_invalid(message: types.Message, state: FSMContext,**kwargs):
    await message.reply("Напиши число и повтори попытку.",reply_markup=cancel_kb)



@dp.message_handler(commands='Задание')
@registerded_user
async def create_task(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.chat.id]
    user=yappyUser.All_Users_Dict[name]
    try:
        amount,cost_amount,url=strip_command(message.text).split(' ',2)
        amount=float(amount)
        cost_amount=float(cost_amount)
    except ValueError:
        amount,url=strip_command(message.text).split(' ',1)
        cost_amount=1
    await _create_task(amount, message, name, url, user,cost_amount)


async def _create_task(amount, message, name, description, user:yappyUser.YappyUser,cost_amount=1.0):

    try:
        amount = float(amount)
        cost_amount = float(cost_amount)
        if description.startswith('/'):
            if description in [c.command for c in normal_commands]:
                await message.reply('Напиши *описание задание* или нажми /cancel', parse_mode="Markdown")
                return False
            elif description.startswith('/cancel'):
                await get_rules(message)
                return True
        if user.coins < amount*cost_amount+user.reserved_amount:
            await message.reply(f'Недостаточно очков. Твой баланс: *{user.get_readable_balance()}*', parse_mode= "Markdown")
            return True
        urls = utils.URLsearch(description)
        if not any(urls):
            await message.reply('В тексте задания нет ссылки. Добавь её и попробуй ещё раз.\n\n'
                                'Для отмены – нажми /cancel')
            return False
        wrong_desk=re.findall("(?:последни(?:е|х|м)|ролик(?:ов|ах)|\d+ видео)",description,re.I)

        if any(wrong_desk) or len(urls)>1:
            await message.reply(f'Одно задание – одно действие.\nТебе вынесено предупреждение за попытку нарушения правил. Но за попытку не ругают ^_^.')
            return False
        task = LikeTask.LikeTask(name, url=description, amount=amount, msg_id=message.message_id,done_cost=cost_amount)
        user.reserved_amount+=amount*cost_amount
        keyboard_markup=types.InlineKeyboardMarkup(row_width=3)
        create_cancel_buttons(keyboard_markup,task)
        urls_text="\n".join(urls)
        await message.reply(f'Задание успешно создано!\n\nАвтор: {task.creator}\nОписание задания: {task.url}',reply_markup=keyboard_markup)

        return True
    except:
        traceback.print_exc()
        await message.reply(f'Задание не создано. Попробуй еще раз',
                            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")

        return False

def create_cancel_buttons(keyboard_markup,task:LikeTask.LikeTask,admin=False):
    text_and_data=[('Отменить задание','cancel_task',task)]
    cb=cancel_task_cb if not admin else cancel_task_cb_admin
    row_btns=InlineKeyboardButton('Отменить задание',callback_data=cb.new(task=task.name))
    keyboard_markup.add(row_btns)


@dp.message_handler(state=CreateTaskStates.task_description)
async def task_input_task_description(message: types.Message, state: FSMContext, **kwargs):
    name = tg_ids_to_yappy[message.chat.id]
    user=yappyUser.All_Users_Dict[name]
    try:
        target = message.text
        data=(await state.get_data())
        amount=data['amount']
        if 'cost_amount' in data:
            cost_amount=data['cost_amount']
        else:
            cost_amount=1
        message.text=f'/Задание {amount} {cost_amount} {target}'
        res=await _create_task(amount, message, name, target, user,cost_amount)
        if res:

            await state.finish()
    except:
        await message.reply('Введено неправильное описание.')
        traceback.print_exc()



@dp.message_handler(commands='tasks',state='*')
@dp.message_handler(Text(equals='Мои Задания', ignore_case=True),state='*')
@registerded_user
async def send_tasks(message: types.Message,**kwargs):
    name=tg_ids_to_yappy[message.chat.id]
    try:
        tasks:typing.List[LikeTask.LikeTask]=LikeTask.All_Tasks[name]
        targets=''
        for i in range(len(tasks)):
            task=tasks[i]
            stri=f'Задание {i} {"активно" if task.is_active() else "завершено"}, описание: {task.url}, выполнено {task.done_amount} раз из {task.amount} раз.'
            keyboard_markup=InlineKeyboardMarkup()
            create_cancel_buttons(keyboard_markup,task)
            await message.answer(stri,reply_markup=keyboard_markup)
        if not any(tasks):
            await message.reply('У тебя пока нет созданных заданий.')
    except KeyError:
        await message.reply('У тебя пока нет созданных заданий.')
    except:
        traceback.print_exc()
    
    
    
