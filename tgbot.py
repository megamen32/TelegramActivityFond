# .env
# ROOT_PATH_FOR_DYNACONF="config/"
# SETTINGS_FILE_FOR_DYNACONF="['settings.conf']"
import re
import time
import traceback
import asyncio
from typing import Iterable

from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified

import LikeTask
import config
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
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
class BotHelperState(StatesGroup):
    create_task=State()
    get_target=State()
    start_doing_task=State()

tg_ids_to_yappy=config.data.get('tg_ids_to_yappy',{})
# Initialize bot and dispatcher
storage = MemoryStorage()
API_TOKEN = config._settings.get('TG_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot,storage=storage)
vote_cb = CallbackData('newtask', 'action','amount')  # post:<action>:<amount>
cancel_cb = CallbackData('cancel','action')  # post:<action>:<amount>
cancel_task_cb = CallbackData('cancel_task', 'task')

button_task = KeyboardButton('Создать Задание', callback_data=vote_cb.new(action='up',amount=10))
button_like = KeyboardButton('Выполнить Задание', callback_data=vote_cb.new(action='like',amount=10))
help_kb =  ReplyKeyboardMarkup(resize_keyboard=True)
#greet_kb.add(button_task)
#greet_kb.add(button_like)

balance_task = KeyboardButton('Баланс')

history_task = KeyboardButton('История' )
name_task = KeyboardButton('Имя' )
get_task_button = KeyboardButton('Выполнить Задание' )
new_task_button = KeyboardButton('Создать Задание' )
quick_commands_kb =  ReplyKeyboardMarkup(resize_keyboard=True)
quick_commands_kb.row(balance_task, history_task)

quick_commands_kb.row(new_task_button, get_task_button)
help_kb.add(name_task)
cancel_task = KeyboardButton('отмена')
cancel_kb= ReplyKeyboardMarkup(resize_keyboard=True)

cancel_kb.add(cancel_task)
commands=[BotCommand('balance','Узнать свой баланс'),
BotCommand('history','Посмотреть историю транзацкий с баланса'),
BotCommand('like','Взять себе задание'),
BotCommand('task','Создать задание'),
BotCommand('tasks','Посмотреть свои задания'),
BotCommand('cancel','Отменить'),
BotCommand('name','поменять свой ник')
          ]
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
        like_task:LikeTask.LikeTask=None
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
        LikeTask.All_Tasks[username].remove(like_task)
        if not any(LikeTask.All_Tasks[username]):
            user.reserved_amount=0
        await query.message.reply(f'Удаляю задание {like_task.url} от {like_task.creator}',reply_markup=quick_commands_kb)

    except IndexError:
        await query.message.reply('No active tasks', reply_markup=quick_commands_kb)


@dp.callback_query_handler(state='*')
async def vote_cancel_cb_handler(query: types.CallbackQuery):
    """
        Allow user to cancel any action
        """
    await bot.answer_callback_query(query.id)
    state = dp.current_state(user=query.message.from_user.id)
    current_state=await state.get_state()
    if current_state is None:
        await query.message.reply('Отменяю.', reply_markup=types.ReplyKeyboardRemove())
        return


    logging.info('Отменяю state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await query.message.reply('Отменяю.', reply_markup=types.ReplyKeyboardRemove())

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
        await message.reply(f"Привет {tg_ids_to_yappy[message.from_user.id]} Я бот для взаимной активности в {config._settings.get('APP_NAME',default='yappy')}.", reply_markup=quick_commands_kb)
        return
    await message.reply(f"Привет. Я бот для взаимной активности в {config._settings.get('APP_NAME',default='yappy')}. Пожалуйста напиши мне свой ник в {config._settings.get('APP_NAME',default='yappy')}.",reply_markup=help_kb)
    await RegisterState.name.set()

def strip_command(str):
    return str.split(' ',1)[1]

@dp.message_handler(state=RegisterState.name)

async def send_name(message: types.Message,state:FSMContext):
    yappy_username = message.text
    if utils.any_re('[а-яА-Я]+',yappy_username):
        await message.reply('Вы написали свой ник на русском языке. Это невозможно. Напишите еще раз')
        return
    yappy_username=yappy_username.replace('@','').lower()
    if  yappy_username not in tg_ids_to_yappy.values():
        tg_ids_to_yappy[message.from_user.id] = yappy_username
        user=yappyUser.YappyUser(yappy_username)
        await message.reply(f'Отлично. теперь я знаю что вас зовут {yappy_username}.', reply_markup=quick_commands_kb)
        await state.finish()
        
    else:
        if tg_ids_to_yappy[message.from_user.id]!=yappy_username:
            await message.reply(f'Этот ник {config._settings.get("APP_NAME",default="yappy")} зарегистрирован для другого пользователя телеграма. Если это ваш Ник напишите администратуру')
        else:
            await message.reply(f'Ник уже был успешно зарегистрирован')

    config.data.set('tg_ids_to_yappy', tg_ids_to_yappy)
@dp.message_handler(commands=['name'])
@dp.message_handler(regexp='name|Имя|имя|ник')
async def _send_name(message: types.Message,state:FSMContext):
    try:
        message.text = strip_command(message.text)
    except:
        await message.reply(f'Напишите свой ник в {config._settings.get("APP_NAME",default="yappy")}')
        await RegisterState.name.set()
        return
    await send_name(message,state)
def registerded_user(func):
    """Декоратор первичного обработчика сообщения, отвечает за контроль доступа и логи"""
    async def user_msg_handler(message: types.Message,**kwargs):
        id = message.from_user.id
        if id in tg_ids_to_yappy.keys():
            username=tg_ids_to_yappy[id]
            if username not in yappyUser.All_Users_Dict.keys():
                yappyUser.YappyUser(username)
            await func(message,**kwargs)
        else:
            await message.reply(f'Пожалуйста скажите мне ваш ник {config._settings.get("APP_NAME",default="yappy")}: "Имя твой_никнейм"')
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
        while any(photos):
            media = types.MediaGroup()
            media_send = types.MediaGroup()
            for photo in photos:
                if photo in done_photos:
                    continue
                name = photo.split('.')[0].split('/')[-1]
                #name=re.match('\d(.*)$',name).group(1)
                if 'Получено' in name:
                    if len(media.media)<10:
                        media.attach_photo(open(photo,'rb'), caption=name)
                        done_photos.append(photo)
                else:
                    if len(media_send.media)<10:
                        media_send.attach_photo(open(photo,'rb'), caption=name)
                        done_photos.append(photo)
                if len(media_send.media) >= 10 and len(media.media)>10:
                    break

            if any(media.media)>0:
                await message.reply('Задания, которые ты выполнил:')
                await message.answer_media_group(media)
            if any(media_send.media)>0:
                await message.reply('Твои задания, выполненные другими людьми:')
                await message.answer_media_group(media_send)
            photos = utils.exclude(all_photos, done_photos)
            time.sleep(1)
    else:
        await message.reply('У вас еще нет истории транзакций', reply_markup=quick_commands_kb)

# You can use state '*' if you need to handle all states
@dp.message_handler( commands='cancel',state='*')
@dp.message_handler(Text(equals='отмена', ignore_case=True),state='*')
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
        task:LikeTask.LikeTask=await state.get_data('task')
        if task:
            user.done_tasks.append(task.name)
            await message.reply(f'Отменяю задание от {task.creator}', reply_markup=types.ReplyKeyboardRemove())
    logging.info('Отменяю state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Отменяю.', reply_markup=types.ReplyKeyboardRemove())
def get_key(val,my_dict):
    for key, value in my_dict.items():
         if val == value:
             return key
@dp.message_handler(state=BotHelperState.start_doing_task)
@registerded_user
async def finish_liking_invalid(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    await message.reply(f'Пожалуйста пришли фото, подтверждающее выполнение задания, или нажми отмена',reply_markup=cancel_kb)

@dp.message_handler(content_types=types.ContentTypes.PHOTO, state='*')
@registerded_user
async def finish_liking(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    try:
        task:LikeTask.LikeTask=(await state.get_data('task'))
        if task is None or (isinstance(task,list) and not(any(task))) or isinstance(task,dict) and not any(task.values()):
            await message.reply(f'У тебя нет активного задания! Получи задание написав /like')
            return
        last_photo= message.photo[-1]
        photo_path = f'img/{last_photo.file_id}.jpg'
        await last_photo.download(photo_path)

        await task.AddComplete(whom=name,reason=photo_path)
        creator_id=get_key(task.creator,tg_ids_to_yappy)
        await message.reply(f'Ты закончил задание успешно, твой баланс:{user.coins}', reply_markup=quick_commands_kb)
        await state.finish()
        try:
            if creator_id is not None:
                if 'msg_id' in vars(task):
                    await bot.send_photo(creator_id,photo=open(photo_path,'rb'),caption=f'Твое задание успешно выполнил {name} {task.done_amount} раз из {task.amount} раз',reply_to_message_id=task.msg_id)
                else:
                    await bot.send_photo(creator_id,photo=open(photo_path,'rb'),caption=f'Твое задание успешно выполнили {task.done_amount} раз из {task.amount} раз')
        except: traceback.print_exc()
        user.done_tasks.append(task.name)
    except:
        error=traceback.format_exc()
        traceback.print_exc()
        await message.reply(f'Что-то пошло не так. Ошибка: {error}')

@dp.message_handler(commands='like')
@dp.message_handler(regexp='[Вв]ыполнить [Зз]адание')
@registerded_user
async def start_liking(message: types.Message, state: FSMContext,**kwargs):

    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    a_tasks=LikeTask.Get_Undone_Tasks()
    tasks=[]
    for task in a_tasks:
        if task.creator!=name and task.name not in user.done_tasks:
            tasks.append(task)
    if not any(tasks):
        await message.reply(f'Сейчас нет ни одного задания', reply_markup=quick_commands_kb)
        return
    await message.reply(f'Сейчас активных заданий: {len(tasks)}')
    task=tasks[0]
    await state.reset_data()
    await BotHelperState.start_doing_task.set()
    await state.set_data(task)
    text=f'''Задание
{task.url}
--------
автор: {task.creator}
Чтобы завершить задание пришлите фотографию. Или нажмите отмена.'''

    await message.reply(text, reply_markup=cancel_kb)



@dp.callback_query_handler(vote_cb.filter(action='up'))
async def vote_up_cb_handler(query: types.CallbackQuery, callback_data: dict):
    name = tg_ids_to_yappy[query.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    await query.answer('Введите количество очков, которые вы потратите на это задание',ReplyKeyboardRemove())
    await CreateTaskStates.amount.set()
@dp.message_handler(regexp='Создать Задание')
@dp.message_handler(commands='task')
@registerded_user
async def vote_task_cb_handler(message: types.Message,state,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]

    text_and_data = (
        ('отмена', 'cancel'),
    )
    keyboard_markup = types.InlineKeyboardMarkup(row_width=3)
    row_btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in text_and_data)
    keyboard_markup.row(*row_btns)
    await CreateTaskStates.amount.set()
    await message.reply(f'Введите цифрами количество очков, которые вы потратите на это задание. Ваш баланс {user.coins}. Например:"{min(10,user.coins)}. Или нажмите отмена" ',reply_markup=keyboard_markup)



@dp.callback_query_handler(vote_cb.filter(action='task_description'))
async def task_descriptio_hander(query: types.CallbackQuery,  state: FSMContext,callback_data: dict):
    name = tg_ids_to_yappy[query.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    task_description=callback_data['amount']
    state.set_data({'description':task_description})
    await bot.send_message(  f'Введите цифрами количество очков, которые вы потратите на это задание. Ваш баланс {user.coins}. Например:"{min(10, user.coins)}" ')
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
            await message.reply(f'У вас всего {user.get_readable_balance()}  монет. А вы ввели {amount}. При этом уже зарезервировано {user.reserved_amount} на другие задания. Вам нужно еще {amount+user.reserved_amount-user.coins} монет. Введите число не больше {user.coins-user.reserved_amount}')
        else:
            data= await state.get_data()
            if 'description' not in data:
                await CreateTaskStates.next()
                await message.reply(f'Введено {amount} количество очков. Теперь напишите описание задания')
            else:
                await _create_task(amount,message,name,data['description'],user)

    except:
        h_b=InlineKeyboardButton('Это было описание задание',callback_data=vote_cb.new(action='task_description',amount=message.text))
        await message.reply('Введено неправильное количество очков.',reply_markup=InlineKeyboardMarkup().add(h_b))
        traceback.print_exc()

@dp.message_handler(state=CreateTaskStates.amount)
async def task_input_amount_invalid(message: types.Message, state: FSMContext,**kwargs):
    await message.reply("Я ожидал что вы сейчас введите только число очков. Если вы хотите 10 лайков, надо 10 очков. Напишите 10.\nДля отмены, напишите отмена",reply_markup=cancel_kb)



@dp.message_handler(commands='Задание')
@registerded_user
async def create_task(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    amount,url=strip_command(message.text).split(' ',1)
    await _create_task(amount, message, name, url, user)


async def _create_task(amount, message, name, url, user:yappyUser.YappyUser):
    amount = float(amount)
    if user.coins < amount+user.reserved_amount:
        await message.reply(f'Слишком мало на балансе. Твой баланс: {user.get_readable_balance()}. Надо {amount+user.reserved_amount - user.coins}')
    urls = re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', url)
    if not any(urls):
        await message.reply('Задание не было создано, не найденна ссылка. Попробуйте заново')
        return
    task = LikeTask.LikeTask(name, url=url, amount=amount, msg_id=message.message_id)
    user.reserved_amount+=amount
    keyboard_markup=types.InlineKeyboardMarkup(row_width=3)
    create_cancel_buttons(keyboard_markup,task)
    urls_text="\n".join(urls)
    await message.reply(f'Задание создано: {task.creator}\n {task.url}\nСсылки: {urls_text}',reply_markup=keyboard_markup)

def create_cancel_buttons(keyboard_markup,task:LikeTask.LikeTask):
    text_and_data=[('Отмена задания','cancel_task',task)]
    row_btns=InlineKeyboardButton('Отмена задания',callback_data=cancel_task_cb.new(task=task.name))
    keyboard_markup.add(row_btns)


@dp.message_handler(state=CreateTaskStates.task_description)
async def task_input_task_description(message: types.Message, state: FSMContext, **kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    try:
        target = message.text
        amount=(await state.get_data())['amount']
        await state.finish()
        message.text=f'/Задание {amount} {target}'
        await _create_task(amount, message, name, target, user)
    except:
        await message.reply('Введено неправильное описание')
        traceback.print_exc()



@dp.message_handler(commands='tasks',state='*')
@registerded_user
async def send_tasks(message: types.Message,**kwargs):
    name=tg_ids_to_yappy[message.from_user.id]
    try:
        tasks:Iterable[LikeTask.LikeTask]=LikeTask.All_Tasks[name]
        targets=''
        for i in range(len(tasks)):
            task=tasks[i]
            str=f'Задание {i} {"активно" if task.is_active() else "неактивно"}, описание:{task.url}, выполнено {task.done_amount} из {task.amount} раз'
            keyboard_markup=InlineKeyboardMarkup()
            create_cancel_buttons(keyboard_markup,task)
            await message.answer(str,reply_markup=keyboard_markup)
        if not any(tasks):
            await message.reply('У вас еще нет созданных заданий')
    except KeyError:
        await message.reply('У вас еще нет созданных заданий')
    except:
        traceback.print_exc()
    
    
    
