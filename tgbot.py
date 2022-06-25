# .env
# ROOT_PATH_FOR_DYNACONF="config/"
# SETTINGS_FILE_FOR_DYNACONF="['settings.conf']"
import re
import time
import traceback
import asyncio
import typing
from typing import Iterable

from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified

import LikeTask
import config
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import  RedisStorage2
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text,ContentTypeFilter
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, \
    ReplyKeyboardRemove, BotCommand, BotCommandScopeDefault, InputFile
from aiogram.utils import executor

#import find_user
import utils
import yappyUser


class CreateTaskStates(StatesGroup):
    amount=State()
    task_description=State()
class LikeTaskStates(StatesGroup):
    confirm=State()
class BotHelperState(StatesGroup):
    create_task=State()
    get_target=State()
    start_doing_task=State()

tg_ids_to_yappy=config.data.get('tg_ids_to_yappy',{})
# Initialize bot and dispatcher
if config._settings.get('is_use_Redis',False):
    storage = RedisStorage2()

else:
    storage = MemoryStorage()
API_TOKEN = config._settings.get('TG_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot,storage=storage)
vote_cb = CallbackData('newtask', 'action','amount')  # post:<action>:<amount>
cancel_cb = CallbackData('cancel','action')  # post:<action>:<amount>
like_cb = CallbackData('confirm','photo_path')  # post:<action>:<amount>
cancel_task_cb = CallbackData('cancel_task', 'task')
change_photo_cb = CallbackData('change_photo', 'photo_path')
more_info_cb= CallbackData('more_info','photo')
button_task = KeyboardButton('Создать задание', callback_data=vote_cb.new(action='up',amount=10))
button_like = KeyboardButton('Выполнить задание', callback_data=vote_cb.new(action='like',amount=10))
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
help_kb.add(name_task)
cancel_task = KeyboardButton('Отмена')
cancel_kb= ReplyKeyboardMarkup(resize_keyboard=True)

cancel_kb.add(cancel_task)
normal_commands=[BotCommand('balance','На главную'),
BotCommand('tasks','Мои задания'),
BotCommand('task','Создать задание'),
BotCommand('like','Выполнить задание'),
BotCommand('history','История'),
BotCommand('name','Изменить никнейм')
          ]
commands=normal_commands+[BotCommand('cancel','Отменить')]
dispute_cb=CallbackData('dispute', 'task','tid',
                                          'username')
dispute_admin_cb=CallbackData('dispute_admin', 'task'
                                          ,'username','guilty')
@dp.callback_query_handler(dispute_cb.filter())
async def callback_dispute(query: types.CallbackQuery,state:FSMContext,callback_data:dict):
    message = query.message
    name = tg_ids_to_yappy[message.chat.id]
    user = yappyUser.All_Users_Dict[name]
    data=callback_data
    
   
    guilty_username=data['username']

    
    try:

        while 'task' in data:
            data=data['task']

        task:LikeTask.LikeTask=LikeTask.get_task_by_name(data)
        guilty_user:yappyUser.YappyUser=yappyUser.All_Users_Dict[guilty_username]


        if 'done_history' not in vars(task):
            for transaction in reversed(guilty_user.transactionHistory):
                tr: yappyUser.Transaction=transaction
                if tr.sender==name:
                    photo_path=tr.reason
                    break
        elif 'tid' in callback_data:
            tr_id = callback_data['tid']
            photo_path=task.done_history[(guilty_username,tr_id)]



        admin_ids=config._settings.get('admin_ids',['540308572','65326877'])
        loop=asyncio.get_running_loop()
        await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, reply_markup=None)
        msg_ids={}
        for admin in admin_ids:
            guilty_button=InlineKeyboardButton("Виновен",callback_data=dispute_admin_cb.new(task=task.name,username=guilty_username,guilty=True))
            not_guilty_button=InlineKeyboardButton("Не виновен",callback_data=dispute_admin_cb.new(task=task.name,username=guilty_username,guilty=False))
            admin_kb=InlineKeyboardMarkup()
            admin_kb.row(guilty_button,not_guilty_button)

            msg=await bot.send_photo(admin,photo=open(photo_path,'rb'),caption=f'{name} оспорил задание, которые выполнил {guilty_username} виновен {guilty_user.guilty_count} раз, задание: {task}',reply_markup=admin_kb)
            msg_ids[admin]=msg.message_id
        for admin in admin_ids:
            await storage.update_data(user=admin,data={'admin_buttons':msg_ids})
        guilty_id=get_key(guilty_username,tg_ids_to_yappy)
        await bot.send_photo(guilty_id,photo=open(photo_path,'rb'),caption=f'Твоё выполнение "{task.url}" оспорил {name}. Это не значит что обязательно очки снимут. После проверки вам напишут решение')
        await query.message.reply('Информация успешно отправлена Модерации')
        
        guilty_user=yappyUser.All_Users_Dict[guilty_username]
        if 'guilty_count' not in vars(guilty_user):
            guilty_user.guilty_count=0

        guilty_user.guilty_count += 1
        
        assert yappyUser.All_Users_Dict[guilty_username]==guilty_user

    except:traceback.print_exc()


@dp.callback_query_handler(dispute_admin_cb.filter())
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
        to_remove=await storage.get_data(user=query.from_user.id)
        msg_ids=to_remove['admin_buttons']

#        await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, reply_markup=None)
        if task.name not in guilty_user.done_tasks:
            await message.reply("Другой модератор уже все рассмотрел")
            return
        for msg in msg_ids.keys():
            try:
                await bot.edit_message_reply_markup(msg, msg_ids[msg], reply_markup=None)
                text=f'{task.creator} оспорил задание, которые выполнил {guilty_username} виновен {guilty_user.guilty_count} раз, задание: {task}, Решение вынесенно {tg_ids_to_yappy[query.from_user.id]} : {"Виновен" if "True" in is_guilty else "Невиновен"}'
                await bot.edit_message_caption(caption=text,message_id= msg_ids[msg],chat_id=msg, reply_markup=None)
            except MessageNotModified:pass
        for transaction in reversed(guilty_user.transactionHistory):
            tr: yappyUser.Transaction = transaction
            if tr.sender == task.creator:
                photo_path = tr.reason
                break
        admin_ids = config._settings.get('admin_ids', ['540308572', '65326877'])

        task_creator = yappyUser.All_Users_Dict[task.creator]
        if 'True' in is_guilty:
            await query.message.reply('Отправляем очки: Виновен')
            for transaction in reversed(guilty_user.transactionHistory):
                tr: yappyUser.Transaction = transaction
                if tr.sender == task.creator:
                    guilty_user.transactionHistory.remove(transaction)
                    break
            for transaction in reversed(task_creator.transactionHistory):
                tr: yappyUser.Transaction = transaction
                if tr.sender == guilty_username:
                    task_creator.transactionHistory.remove(transaction)
                    break
            guilty_user.done_tasks.remove(task.name)
            guilty_user.coins-=1
            guilty_user.guilty_count -= 1
            task_creator.reserved_amount-=1
            task_creator.coins+=1
            task.done_amount -= 1
            await bot.send_photo(get_key(guilty_username,tg_ids_to_yappy),photo=open(photo_path,'rb'),caption=f"Оспаривание твоего выполнения задания '{task.url}' от {task.creator} рассмотрено. Очки сняты.")
            await bot.send_photo(get_key(task.creator,tg_ids_to_yappy),photo=open(photo_path,'rb'),caption=f"Твое оспаривание '{task.url}' на действие от {guilty_username} рассмотрено. Очки возвращены.",reply_to_message_id=task.msg_id)
        else:
            await query.message.reply('Отправляем очки: Невиновен')
            await bot.send_photo(get_key(guilty_username, tg_ids_to_yappy),photo=open(photo_path,'rb'),caption=
                                   f"Оспаривание твоего выполнения задания '{task.url}' от {task.creator} рассмотрено в твою пользу.")
            await bot.send_photo(get_key(task.creator, tg_ids_to_yappy),photo=open(photo_path,'rb'),caption=
                                   f"Твое оспаривание '{task.url}' на действие от {guilty_username} рассмотрено.Заявка отклонена. Скорее всего, задание нарушает правила, слишком много действий, которые нельзя доказать за один скриншот.",
                                   reply_to_message_id=task.msg_id)

    except:
            traceback.print_exc()

@dp.callback_query_handler(text='confirm',state='*')
async def callback_like_confirm(query: types.CallbackQuery,state:FSMContext):
    message=query.message
    name=tg_ids_to_yappy[message.chat.id]
    user=yappyUser.All_Users_Dict[name]
    msg_id_to_edit=query.message.message_id

    try:
     
        #photo_path=data['photo_path']
        state_data=await storage.get_data(chat=message.chat.id)
        #state=await storage.get_state(chat=message.chat.id)
        #state_data=(await state.get_data())
        if 'task' in state_data:
            task=state_data['task']
        else:
            task=state_data
        while isinstance(task,dict) and 'task' in task:
            task=task['task']
        task=LikeTask.get_task_by_name(task)
        photo_path=state_data['photo_path']
        all_photos=state_data['photos_path']
        if len(all_photos)>1:
            photo_path=utils.combine_imgs(all_photos)
        transaction_id=await task.AddComplete(whom=name, reason=photo_path)
        creator_id=get_key(task.creator,tg_ids_to_yappy)

        await message.answer(
            f'Задание завершено!\n\n'
            f'Твой баланс: *{user.coins}*',reply_markup=quick_commands_kb,parse_mode="Markdown"
            )
        if 'msg_ids' in state_data:
            for msg_id in state_data['msg_ids']:
                #if msg_id != message.message_id:
                await bot.delete_message(message.chat.id,message_id=msg_id)
        await state.finish()
        try:
            if creator_id is not None:
                reply_to_message_id=task.msg_id if 'msg_id' in vars(task) else None

                dispute_button=InlineKeyboardButton("Оспорить",callback_data=dispute_cb.new(task=task.name,tid=transaction_id,
                                                                                          
                                                                                              username=name))
                dispute_keboard=InlineKeyboardMarkup()
                dispute_keboard.add(dispute_button)
                await bot.send_photo(
                    creator_id,photo=open(photo_path,'rb'),
                    caption=f'Твоё задание выполнил/а: {name}!\n\nУже сделано {task.done_amount} раз из {task.amount}',
                    reply_to_message_id=reply_to_message_id,reply_markup=dispute_keboard
                    )

        except: traceback.print_exc()
        user.done_tasks.append(task.name)
        msg_id_to_edit=query.inline_message_id
        message_id=query.message.message_id
        chat_id=query.message.chat.id
        #await bot.edit_message_reply_markup(inline_message_id=msg_id_to_edit, reply_markup=None)
#        await bot.edit_message_reply_markup(message_id=message_id,chat_id=chat_id, reply_markup=None)
    except:
        error=traceback.format_exc()
        traceback.print_exc()
        await message.answer(f'У вас нет активного задания')

@dp.callback_query_handler(change_photo_cb.filter(),state='*')
async def callback_like_change(query: types.CallbackQuery,state: FSMContext,callback_data:dict,**kwargs):
    data=await state.get_data()
    await query.message.edit_text('Пришли новую фотографию.')
    data['photos_path'].remove(callback_data['photo_path'])

    await state.set_data(data)
@dp.callback_query_handler(cancel_task_cb.filter())
async def vote_cancel_cb_handler(query: types.CallbackQuery,callback_data:dict):
    """
        Allow user to cancel any action
        """
    await bot.answer_callback_query(query.id)
    username=tg_ids_to_yappy[query.from_user.id]
    user=yappyUser.All_Users_Dict[username]
    taskname=callback_data['task']
    try:
        like_task=None
        for task in LikeTask.All_Tasks.values():
            if isinstance(task,list):
                for t in task:
                    if str(t.name)==taskname:
                        like_task=t
                        break
            elif task.name==taskname:
                like_task=task
                break
        if like_task is None:
            like_task=LikeTask.All_Tasks[username][-1]
        user.reserved_amount-=like_task.amount-like_task.done_amount
        LikeTask.remove_task(like_task)
        if not any(LikeTask.All_Tasks[username]):
            user.reserved_amount=0
        await query.message.reply(f'Отменяю задание {like_task.url} от {like_task.creator}.',reply_markup=quick_commands_kb)

    except IndexError:
        await query.message.reply('No active tasks', reply_markup=quick_commands_kb)


@dp.callback_query_handler(text='cancel',state='*')
async def vote_cancel_cb_handler(query: types.CallbackQuery):
    """
        Allow user to cancel any action
        """
    await bot.answer_callback_query(query.id)
    state = dp.current_state(chat=query.message.chat.id)
    current_state=await state.get_state()
    if current_state is None:
        await query.message.reply('Нечего отменять.', reply_markup=types.ReplyKeyboardRemove())
        return


    logging.info('Отменено. state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await query.message.reply(f'Отменено', reply_markup=types.ReplyKeyboardRemove())

@dp.errors_handler(exception=MessageNotModified)  # for skipping this exception
async def message_not_modified_handler(update, error):
    return True
class RegisterState(StatesGroup):
    name=State()
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await bot.set_my_commands(commands,scope=BotCommandScopeDefault())
    if message.from_user.id in tg_ids_to_yappy.keys():
        await message.reply(f"*{tg_ids_to_yappy[message.from_user.id]}*, снова привет!\n\n*Новые задания* уже в ленте!", reply_markup=quick_commands_kb, parse_mode= "Markdown")
        return
    await message.reply(f"Привет! Я – *Бот взаимной активности* в {config._settings.get('APP_NAME',default='Yappy')}. Напиши свой "
                        f"никнейм:",reply_markup=ReplyKeyboardRemove(), parse_mode= "Markdown")
    await RegisterState.name.set()

def strip_command(stri):
    return stri.split(' ',1)[1]

@dp.message_handler(state=RegisterState.name)

async def send_name(message: types.Message,state:FSMContext):
    yappy_username = message.text
    if utils.any_re('[а-яА-Я]+',yappy_username):
        await message.reply('Никнейм можно написать *только на английском*. Попробуй ещё раз.', parse_mode= "Markdown")
        return
    if yappy_username.startswith('/'):
        if  yappy_username in [c.command for c in normal_commands]:
            await message.reply('Напиши свой *никнейм*, чтобы продолжить.',parse_mode="Markdown")
            return
        elif yappy_username.startswith('/cancel') :
            await cancel_handler(message,state)
            return
        else:
            await message.reply('Напиши свой *никнейм*, чтобы продолжить.',parse_mode="Markdown")
            return
    yappy_username=yappy_username.replace('@','').lower()
    if  yappy_username not in tg_ids_to_yappy.values():
        tg_ids_to_yappy[message.from_user.id] = yappy_username
        if yappy_username not in yappyUser.All_Users_Dict:
            user=yappyUser.YappyUser(yappy_username)
        await message.reply(f'Отлично! Привет, {yappy_username}.', reply_markup=quick_commands_kb)
        await state.finish()
        
    else:
        if message.from_user.id not in tg_ids_to_yappy or tg_ids_to_yappy[message.from_user.id]!=yappy_username:
            await message.reply(f'Этот никнейм {config._settings.get("APP_NAME",default="yappy")} уже зарегистрирован. Если он твой – напиши администратору.')
        else:
            await message.reply(f'Ты {yappy_username} написал такой же никнейм как был указан раньше. ')
            await state.finish()

    config.data.set('tg_ids_to_yappy', tg_ids_to_yappy)
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
def registerded_user(func):
    """Декоратор первичного обработчика сообщения, отвечает за контроль доступа и логи"""
    async def user_msg_handler(message: types.Message,**kwargs):
        telegram_id = message.from_user.id
        if telegram_id in tg_ids_to_yappy.keys():
            username=tg_ids_to_yappy[telegram_id]
            if username not in yappyUser.All_Users_Dict.keys():
                try:
                    yappyUser.YappyUser(username)
                except:
                    await message.reply(f"Что -то не так с вашим логином, напишите другой, нажмите на /name. \nинформация для разработчика {traceback.format_exc()}")
                    traceback.print_exc()
            await func(message,**kwargs)
        else:
            await message.reply(f"Привет! Я – *Бот взаимной активности* в {config._settings.get('APP_NAME',default='yappy')}.\n\nНапиши "
                                f"свой никнейм:",reply_markup=ReplyKeyboardRemove(), parse_mode= "Markdown")
            await RegisterState.name.set()
    return user_msg_handler
@dp.message_handler(commands=['balance'])
@dp.message_handler(regexp='Баланс')
@registerded_user
async def send_balance(message: types.Message,**kwargs):
    name=tg_ids_to_yappy[message.from_user.id]
    user:yappyUser.YappyUser=yappyUser.All_Users_Dict[name]
    balance=user.coins
    await message.reply(f'{user.username} {user.get_readable_balance()}', reply_markup=quick_commands_kb)
@dp.message_handler(commands=['history'])
@dp.message_handler(regexp='История')
@registerded_user
async def send_photos(message: types.Message,**kwargs):
    name=tg_ids_to_yappy[message.from_user.id]
    photos=yappyUser.All_Users_Dict[name].GetPhotos()
    # Good bots should send chat actions...
    if any(photos):
        await types.ChatActions.upload_photo()

        done_photos=[]
        all_photos=photos
        tasks_send=[]
        tasks_recived=[]
        for photo in all_photos:
            name = photo.split('.')[0].split('/')[-1]
            task_numer = int(re.findall(r'\d+', name, re.I)[0])
            if 'Получено' in name:
                tasks_send.append((task_numer,name))
            else:
                tasks_recived.append((task_numer,name))
        tasks_send=sorted(tasks_send,key=lambda tuple:task_numer)
        tasks_recived=sorted(tasks_recived,key=lambda task_numer:task_numer)
        for i in range(len(tasks_send)):
            num,name=tasks_send[i]
            buttin_more=InlineKeyboardButton(text='Подробнее',callback_data=more_info_cb.new(photo=name[:20]))
            kb=InlineKeyboardMarkup()
            kb.add(buttin_more)
            await message.answer(f'--{i}){name}',reply_markup=kb)
        for i in range(len(tasks_recived)):
            num,name= tasks_recived[i]
            buttin_more=InlineKeyboardButton(text='Подробнее',callback_data=more_info_cb.new(photo=name[:20]))
            kb=InlineKeyboardMarkup()
            kb.add(buttin_more)
            await message.answer(f'{i}){name}',reply_markup=kb)


@dp.callback_query_handler(more_info_cb.filter(), state='*')
@registerded_user
async def more_info_handler(query: types.CallbackQuery, state: FSMContext,callback_data:dict, **kwargs):
    message=query.message
    name = tg_ids_to_yappy[query.from_user.id]
    photos = yappyUser.All_Users_Dict[name].GetPhotos()

    photo_short=callback_data['photo']
    res=''
    for p in photos:
        if photo_short in p:
            photo=p
            break
    name = photo.split('.')[0].split('/')[-1]
    await query.message.answer_photo(open(photo,'rb+'),caption=name)

# You can use state '*' if you need to handle all states
@dp.message_handler( commands='cancel',state='*')
@dp.message_handler(Text(equals='Отмена', ignore_case=True),state='*')
@registerded_user
async def cancel_handler(message: types.Message, state: FSMContext,**kwargs):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return
    if current_state == BotHelperState.start_doing_task.state:
        name = tg_ids_to_yappy[message.from_user.id]
        user = yappyUser.All_Users_Dict[name]
        try:
            task:LikeTask.LikeTask=LikeTask.get_task_by_name((await state.get_data('task'))['task'])
            
            while isinstance(task,dict) and 'task' in task:
                task=task['task']
            if task:
                user.done_tasks.append(task.name)
                sended=await message.reply(f'Отменяю задание от {task.creator}.', reply_markup=quick_commands_kb)
            else:
                await message.reply('Отменено.', reply_markup=quick_commands_kb)
        except:
            await message.reply('Отменено.', reply_markup=quick_commands_kb)
            traceback.print_exc()
    logging.info('Отменено. state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)

def get_key(val,my_dict):
    for key, value in my_dict.items():
         if val == value:
             return key
@dp.message_handler(state=BotHelperState.start_doing_task)
@registerded_user
async def finish_liking_invalid(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    await message.reply(f'*Пришли скриншот*, подтверждающий выполнение задания, или нажми Отмена.',reply_markup=cancel_kb, parse_mode= "Markdown")


@dp.message_handler(content_types=types.ContentTypes.PHOTO, state='*')
@registerded_user
async def finish_liking(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    try:
        task_name=await state.get_data('task')
        while (isinstance(task_name,dict)) and 'task' in task_name:
            task_name=task_name['task']
        task:LikeTask.LikeTask=LikeTask.get_task_by_name((task_name))
        if task is None or (isinstance(task,list) and not(any(task))) or isinstance(task,dict) and not any(task.values()):
            await message.reply(f'У тебя нет активного задания! Чтобы его получить, нажми /like')
            return
        done_files=set()

        last_photo= message.photo[-1]
        photo_path = f'img/{last_photo.file_unique_id}.jpg'
        await last_photo.download(photo_path)
        state_data=await state.get_data()
        if 'photos_path' in state_data:
            paths=state_data['photos_path']
            paths.append(photo_path)
        else:
            paths=[photo_path]
        dict_state={'task':task.name,'photo_path':photo_path,'photos_path':paths}

        await state.update_data(dict_state)
        Confirm_buton=InlineKeyboardButton("Подтвердить",callback_data= 'confirm')
        Edit_buton=InlineKeyboardButton("Изменить",callback_data=change_photo_cb.new(photo_path=photo_path))
        keyboard_for_answer=InlineKeyboardMarkup()
        keyboard_for_answer.row(Edit_buton,Confirm_buton)
        msg=await message.reply('Проверь скриншот и нажми Подтвердить или Изменить.',reply_markup=keyboard_for_answer)
        new_data=await state.get_data()
        if 'msg_ids' in new_data:
            msg_ids=new_data['msg_ids']
            msg_ids.append(msg.message_id)
        else:
            msg_ids=[msg.message_id]
        new_data['msg_ids']=msg_ids
        await state.update_data(new_data)
    except:
        error=traceback.format_exc()
        traceback.print_exc()
        await message.reply(f'Что-то пошло не так. Ошибка: {error}')
        

@dp.message_handler(commands='like')
@dp.message_handler(regexp='[Вв]ыполнить [Зз]адание')
@registerded_user
async def start_liking(message: types.Message, state: FSMContext,**kwargs):

    name = tg_ids_to_yappy[message.from_user.id]
    user:yappyUser.YappyUser=yappyUser.All_Users_Dict[name]
    a_tasks=LikeTask.Get_Undone_Tasks()
    tasks=[]
    done_tasks=[LikeTask.get_task_by_name(t) for t in user.done_tasks ]
    done_urls = []
    for t in done_tasks:
        if t is not None:
            try:
                done_urls.append(utils.URLsearch(t.url)[-1])
            except:pass
    for task in a_tasks:
        if task.creator!=name and task.name not in user.done_tasks:
            try:
                urls= utils.URLsearch(task.url)[-1]
                if urls in done_urls:
                    continue
                tasks.append(task)
            except:
                traceback.print_exc()
                print("Error with: "+str(task))
    if not any(tasks):
        await message.reply(f'Все задания выполнены. *Создавай новые!*', reply_markup=quick_commands_kb, parse_mode= "Markdown")
        return
    await message.reply(f'Сейчас активных заданий: *{len(tasks)}*', parse_mode= "Markdown")
    task=tasks[0]
    await state.reset_data()
    await BotHelperState.start_doing_task.set()
    await state.set_data({'task':task.name})
    text=f'''Задание:
{task.url}

Автор: {task.creator}
_____

Чтобы завершить задание — пришли скриншот или нажми Отмена.'''

    await message.reply(text, reply_markup=cancel_kb)



@dp.callback_query_handler(vote_cb.filter(action='up'))
async def vote_up_cb_handler(query: types.CallbackQuery, callback_data: dict):
    name = tg_ids_to_yappy[query.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    await query.answer('*Введи количество очков*, которое ты потратишь на задание. Оно равно *количеству человек*, которым будет '
                       f'предложено его выполнить.\n\nТвой баланс: *{user.get_readable_balance()}*\n\nЕсли передумал/а — нажми *Отмена*.'
                       )
    await CreateTaskStates.amount.set()
@dp.message_handler(regexp='Создать задание')
@dp.message_handler(commands='task')
@registerded_user
async def vote_task_cb_handler(message: types.Message,state,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user:yappyUser.YappyUser=yappyUser.All_Users_Dict[name]

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



@dp.callback_query_handler(vote_cb.filter(action='task_description'))
async def task_descriptio_hander(query: types.CallbackQuery,  state: FSMContext,callback_data: dict):
    name = tg_ids_to_yappy[query.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    task_description=callback_data['amount']
    await state.set_data({'description':task_description})
    await bot.send_message(query.from_user.id,'*Введи количество очков*, которое ты потратишь на задание. Оно равно количеству '
                                              'человек, '
                              f'которым будет предложено его выполнить.\n\nТвой баланс: *{user.coins-user.reserved_amount}*',
                           parse_mode= "Markdown")
    await CreateTaskStates.amount.set()

@dp.callback_query_handler(vote_cb.filter(action='like'))
async def vote_like_cb_handler(query: types.CallbackQuery, callback_data: dict):
    name = tg_ids_to_yappy[query.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    await BotHelperState.get_target.set()



@dp.message_handler(state=CreateTaskStates.amount,regexp='^ ?[0-9]+ ?$')
async def task_input_amount(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    try:
        amount =float( message.text )
        await state.set_data({'amount':amount})

        if user.coins<amount+user.reserved_amount:
            await message.reply(f'Недостатчно очков. Доступный баланс: *{user.get_readable_balance()}*\n\n'
                                f'Попробуй ещё раз или нажми */cancel*.', parse_mode= "Markdown")
        else:
            data= await state.get_data()
            if 'description' not in data:
                await CreateTaskStates.next()
                await message.reply(f'Ты потратишь {amount} очков.\n\nТеперь напиши описание задания. *В тексте '
                                    f'ОБЯЗАТЕЛЬНО* должна '
                                    f'быть ссылка на аккаунт или пост!\n\n*Не пиши много действий в одном задании*, '
                                    f'так ты повысишь шансы его корректного выполнения! Пример: “Лайк + Подписка на '
                                    f'ролик (ссылка)”, “Коммент (ссылка)”. '
                                    , parse_mode= "Markdown")
            else:
                await _create_task(amount,message,name,data['description'],user)

    except:
        h_b=InlineKeyboardButton('Это было описание задания.',callback_data=vote_cb.new(action='task_description',amount=message.text))
        await message.reply('Введено неправильное количество очков!',reply_markup=InlineKeyboardMarkup().add(h_b))
        traceback.print_exc()

@dp.message_handler(state=CreateTaskStates.amount)
async def task_input_amount_invalid(message: types.Message, state: FSMContext,**kwargs):
    await message.reply("Напиши число и повтори попытку!",reply_markup=cancel_kb)



@dp.message_handler(commands='Задание')
@registerded_user
async def create_task(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    amount,url=strip_command(message.text).split(' ',1)
    await _create_task(amount, message, name, url, user)


async def _create_task(amount, message, name, description, user:yappyUser.YappyUser):
    amount = float(amount)
    if user.coins < amount+user.reserved_amount:
        await message.reply(f'Недостаточно очков. Твой баланс: *{user.get_readable_balance()}*', parse_mode= "Markdown")
        return True
    urls = utils.URLsearch(description)
    if not any(urls):
        await message.reply('В задании нет ссылки. Добавь её и попробуй ещё раз.')
        return False
    wrong_desk=re.findall("(?:последни(?:е|х|м)|ролик(?:ов|ах)| \d+ видео)",description,re.I)

    if any(wrong_desk) or len(urls)>1:
        await message.reply(f'Один ролик - одно задание. А Вы написали {wrong_desk}... Вам вынесено предупреждение за попытку нарушение правил. Но за попытку не ругают^_^.')
        return False
    task = LikeTask.LikeTask(name, url=description, amount=amount, msg_id=message.message_id)
    user.reserved_amount+=amount
    keyboard_markup=types.InlineKeyboardMarkup(row_width=3)
    create_cancel_buttons(keyboard_markup,task)
    urls_text="\n".join(urls)
    await message.reply(f'Задание успешно создано! Автор:{task.creator}\n {task.url}\nЗадание: {urls_text}',reply_markup=keyboard_markup)
    return True

def create_cancel_buttons(keyboard_markup,task:LikeTask.LikeTask):
    text_and_data=[('Отменить задание','cancel_task',task)]
    row_btns=InlineKeyboardButton('Отменить задание',callback_data=cancel_task_cb.new(task=task.name))
    keyboard_markup.add(row_btns)


@dp.message_handler(state=CreateTaskStates.task_description)
async def task_input_task_description(message: types.Message, state: FSMContext, **kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    try:
        target = message.text
        amount=(await state.get_data())['amount']
        message.text=f'/Задание {amount} {target}'
        res=await _create_task(amount, message, name, target, user)
        if res:
            await state.finish()
    except:
        await message.reply('Введено неправильное описание.')
        traceback.print_exc()



@dp.message_handler(commands='tasks',state='*')
@dp.message_handler(Text(equals='Мои Задания', ignore_case=True),state='*')
@registerded_user
async def send_tasks(message: types.Message,**kwargs):
    name=tg_ids_to_yappy[message.from_user.id]
    try:
        tasks:typing.List[LikeTask.LikeTask]=LikeTask.All_Tasks[name]
        targets=''
        for i in range(len(tasks)):
            task=tasks[i]
            stri=f'Задание {i} {"активно" if task.is_active() else "неактивно"}, описание: {task.url}, выполнено {task.done_amount} раз из {task.amount} раз.'
            keyboard_markup=InlineKeyboardMarkup()
            create_cancel_buttons(keyboard_markup,task)
            await message.answer(stri,reply_markup=keyboard_markup)
        if not any(tasks):
            await message.reply('У тебя пока нет созданных заданий.')
    except KeyError:
        await message.reply('У тебя пока нет созданных заданий.')
    except:
        traceback.print_exc()
    
    
    
