# .env
# ROOT_PATH_FOR_DYNACONF="config/"
# SETTINGS_FILE_FOR_DYNACONF="['settings.conf']"
import re
import traceback
import asyncio

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
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
import yappyUser

tg_ids_to_yappy=config.data.get('tg_ids_to_yappy',{})
# Initialize bot and dispatcher
storage = MemoryStorage()
API_TOKEN = config._settings.get('TG_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot,storage=storage)
vote_cb = CallbackData('newtask', 'action','amount')  # post:<action>:<amount>


button_task = KeyboardButton('Создать Задание', callback_data=vote_cb.new(action='up',amount=10))
button_like = KeyboardButton('Выполнить Задание', callback_data=vote_cb.new(action='like',amount=10))
greet_kb =  InlineKeyboardMarkup(resize_keyboard=True)
#greet_kb.add(button_task)
#greet_kb.add(button_like)

balance_task = KeyboardButton('Баланс')
history_task = KeyboardButton('История' )
name_task = KeyboardButton('Имя' )
get_task_button = KeyboardButton('Выполнить Задание' )
new_task_button = KeyboardButton('Создать Задание' )
help_kb =  ReplyKeyboardMarkup(resize_keyboard=True)
help_kb.row(balance_task,history_task)

help_kb.row(new_task_button,get_task_button)
help_kb.add(name_task)
greet_kb=help_kb

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
    if message.from_user.id in tg_ids_to_yappy.keys():
        await message.reply(f"Привет {tg_ids_to_yappy[message.from_user.id]} Я бот для взаимной активности в яппи.")
        return
    await message.reply("Привет. Я бот для взаимной активности в яппи. Пожалуйста напиши мне свой ник в яппи.\n/name твой_ник",reply_markup=help_kb)
    await RegisterState.name.set()

def strip_command(str):
    return str.split(' ',1)[1]

@dp.message_handler(state=RegisterState.name)

async def send_name(message: types.Message,state:FSMContext):
    yappy_username = message.text
    if  yappy_username not in tg_ids_to_yappy.values():
        tg_ids_to_yappy[message.from_user.id] = yappy_username
        user=yappyUser.YappyUser(yappy_username)
        await message.reply(f'Отлично. теперь я знаю что вас зовут {yappy_username}.',reply_markup=help_kb)
        await state.finish()
    else:
        if tg_ids_to_yappy[message.from_user.id]!=yappy_username:
            tg_ids_to_yappy[message.from_user.id] = yappy_username
            await message.reply(f'Этот ник яппи зарегистрирован для другого пользователя телеграма. Если это ваш Ник напишите администратуру')
        else:
            await message.reply(f'Ник уже был успешно зарегистрирован')

    config.data.set('tg_ids_to_yappy', tg_ids_to_yappy)
@dp.message_handler(commands=['name'])
@dp.message_handler(regexp='name|Имя|имя|ник')
async def _send_name(message: types.Message,state:FSMContext):
    try:
        message.text = strip_command(message.text)
    except:
        await message.reply('Напишите свой ник в яппи')
        await RegisterState.name.set()
        return
    await send_name(message,state)
def registerded_user(func):
    """Декоратор первичного обработчика сообщения, отвечает за контроль доступа и логи"""
    async def user_msg_handler(message: types.Message,**kwargs):
        id = message.from_user.id
        if id in tg_ids_to_yappy.keys():
            await func(message,**kwargs)
        else:
            await message.reply(f'Пожалуйста скажите мне ваш ник яппи: /name никнейм')
    return user_msg_handler
@dp.message_handler(commands=['balance'])
@dp.message_handler(regexp='Баланс')
@registerded_user
async def send_balance(message: types.Message,**kwargs):
    name=tg_ids_to_yappy[message.from_user.id]
    balance=yappyUser.All_Users_Dict[name].coins
    await message.reply(f'Ваш баланс: {balance} монет',reply_markup=greet_kb)
@dp.message_handler(commands=['history'])
@dp.message_handler(regexp='История')
@registerded_user
async def send_photos(message: types.Message,**kwargs):
    name=tg_ids_to_yappy[message.from_user.id]
    photos=yappyUser.All_Users_Dict[name].GetPhotos()
    # Good bots should send chat actions...
    if any(photos):
        await types.ChatActions.upload_photo()
        media = types.MediaGroup()
        media_send = types.MediaGroup()

        for photo in photos[-10::]:
            name = photo.split('.')[0].split('/')[-1]
            name=re.match('\d(.*)$',name).group(1)
            if 'gain' in name:
                media.attach_photo(open(photo,'rb'), caption=name.replace('gain','Полученно'))
            else:
                media_send.attach_photo(open(photo,'rb'), caption=name.replace('send','Отправлено'))

        if any(media.media)>0:
            await message.answer_media_group(media)
        if any(media_send.media)>0:
            await message.answer_media_group(media_send)
    else:
        await message.reply('there is na history yet',reply_markup=greet_kb)

# You can use state '*' if you need to handle all states
@dp.message_handler( commands='cancel')
@dp.message_handler(Text(equals='отмена', ignore_case=True))
@registerded_user
async def cancel_handler(message: types.Message, state: FSMContext,**kwargs):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Отменяю state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Отменяю.', reply_markup=types.ReplyKeyboardRemove())
def get_key(val,my_dict):
    for key, value in my_dict.items():
         if val == value:
             return key
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
        await message.reply(f'Ты закончил задние успешно, твой баланс:{user.coins}',reply_markup=greet_kb)
        await state.finish()
        if 'msg_id' in vars(task):
            await bot.send_photo(creator_id,photo=open(photo_path,'rb'),caption=f'Твое задание успешно выполнили {task.done_amount} раз из {task.amount} раз',reply_to_message_id=task.msg_id)
        else:
            await bot.send_photo(creator_id,photo=open(photo_path,'rb'),caption=f'Твое задание успешно выполнили {task.done_amount} раз из {task.amount} раз')
        user.done_tasks.append(task.name)
    except:
        error=traceback.format_exc()
        traceback.print_exc()
        await message.reply(f'Что-то пошло не так. Ошибка: {error}')
class CreateTaskStates(StatesGroup):
    amount=State()
    target=State()
class BotHelperState(StatesGroup):
    create_task=State()
    get_target=State()
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
        await message.reply(f'Сейчас нет ни одного задания',reply_markup=greet_kb)
        return
    await message.reply(f'Сейчас активных заданий: {len(tasks)}')
    task=tasks[0]
    await state.reset_data()
    await state.set_data(task)

    await message.reply(f'Ваше задание от {task.creator}\n\t\t\t\t\t\t\t\tЦель:\n {task.url}',reply_markup=greet_kb)
@dp.callback_query_handler(vote_cb.filter(action='up'))
async def vote_up_cb_handler(query: types.CallbackQuery, callback_data: dict):
    name = tg_ids_to_yappy[query.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    await CreateTaskStates.amount.set()
    await query.answer('Введите количество очков, которые вы потратите на это задание')
@dp.message_handler(regexp='Создать Задание')
async def vote_up_cb_handler(message: types.Message,state,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    await CreateTaskStates.amount.set()

    await message.reply(f'Введите цифрами количество очков, которые вы потратите на это задание. Ваш баланс {user.coins}. Например:"{min(10,user.coins)}" ')


@dp.callback_query_handler(vote_cb.filter(action='like'))
async def vote_like_cb_handler(query: types.CallbackQuery, callback_data: dict):
    name = tg_ids_to_yappy[query.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    await BotHelperState.get_target.set()



@dp.message_handler(state=CreateTaskStates.amount)
async def task_input_amount(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    try:
        amount =float( message.text )
        await CreateTaskStates.next()
        await state.set_data(amount)
        if user.coins<amount:
            await message.reply(f'У вас всего {user.coins}  монет. А вы ввели {amount} Вам нужно еще {amount-user.coins} монет. Введите число не больше {user.coins}')
        else:
            await message.reply(f'Введенно {amount} количество очков. Теперь напишите описание задания')

    except:
        await message.reply('Введенно неправильное количество очков')
        traceback.print_exc()




@dp.message_handler(commands='Задание')
@registerded_user
async def create_task(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    amount,url=strip_command(message.text).split(' ',1)
    await _create_task(amount, message, name, url, user)


async def _create_task(amount, message, name, url, user):
    amount = float(amount)
    if user.coins < amount:
        await message.reply(f'Слишком мало на балансе. Твой баланс: {user.coins} монет. Надо {amount - user.coins}')
    task = LikeTask.LikeTask(name, url=url, amount=amount, msg_id=message.message_id)
    await message.reply(f'Задание создано: {task.creator}\n {task.url}')


@dp.message_handler(state=CreateTaskStates.target)
async def task_input_target(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    try:
        target = message.text
        amount=await state.get_data('amount')
        await state.finish()
        message.text=f'/Задание {amount} {target}'
        await _create_task(amount, message, name, target, user)
    except:
        await message.reply('Введенно неправильноеописание')
        traceback.print_exc()

@dp.message_handler()
async def echo(message: types.Message):
    await message.answer('Я не понял что надо делать',reply_markup=help_kb)
# Press the green button in the gutter to run the script.