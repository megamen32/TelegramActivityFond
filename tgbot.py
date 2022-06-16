# .env
# ROOT_PATH_FOR_DYNACONF="config/"
# SETTINGS_FILE_FOR_DYNACONF="['settings.conf']"
import re
import traceback
import asyncio
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

tg_ids_to_yappy=config.data.get('tg_ids_to_yappy',{})
# Initialize bot and dispatcher
storage = MemoryStorage()
API_TOKEN = config._settings.get('TG_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot,storage=storage)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.reply("Привет. Я бот для взаимной активности в яппи. Пожалуйста напиши мне свой ник в яппи.\n/name твой_ник")

def strip_command(str):
    return str.split(' ',1)[1]
@dp.message_handler(commands=['name'])
async def send_name(message: types.Message):
    yappy_username = strip_command(message.text)




    if  yappy_username not in tg_ids_to_yappy.values():
        tg_ids_to_yappy[message.from_user.id] = yappy_username
        user=yappyUser.YappyUser(yappy_username)
        await message.reply(f'Отлично. теперь я знаю что вас зовут {yappy_username}.')
    else:
        if tg_ids_to_yappy[message.from_user.id]!=yappy_username:
            tg_ids_to_yappy[message.from_user.id] = yappy_username
            await message.reply(f'Этот ник яппи зарегистрирован для другого пользователя телеграма. Если это ваш Ник напишите администратуру')
        else:
            await message.reply(f'Ник уже был успешно зарегистрирован')

    config.data.set('tg_ids_to_yappy', tg_ids_to_yappy)
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
@dp.message_handler(commands=['balance'])
@registerded_user
async def send_balance(message: types.Message,**kwargs):
    name=tg_ids_to_yappy[message.from_user.id]
    balance=yappyUser.All_Users_Dict[name].coins
    await message.reply(f'Ваш баланс: {balance} монет')
@dp.message_handler(commands=['history'])
@dp.message_handler(commands=['history'])
@registerded_user
async def send_photos(message: types.Message):
    name=tg_ids_to_yappy[message.from_user.id]
    photos=yappyUser.All_Users_Dict[name].GetPhotos()
    # Good bots should send chat actions...

    await types.ChatActions.upload_photo()
    media = types.MediaGroup()
    for photo in photos:
        media.attach_photo(photo)
    await message.answer_media_group(media)

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
        await message.reply(f'Ты закончил задние успешно, твой баланс:{user.coins}')
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
@dp.message_handler(commands='like')
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
        await message.reply(f'Сейчас нет ни одного задания')
        return
    await message.reply(f'Сейчас активных заданий: {len(tasks)}')
    task=tasks[0]
    await state.reset_data()
    await state.set_data(task)
    await message.reply(f'Ваше задание от {task.creator}\n Цель:"\n\t\t{task.url}"')


@dp.message_handler(commands='Задание')
@registerded_user
async def start_liking(message: types.Message, state: FSMContext,**kwargs):
    name = tg_ids_to_yappy[message.from_user.id]
    user=yappyUser.All_Users_Dict[name]
    amount,url=strip_command(message.text).split(' ',1)
    amount=float(amount)
    if user.coins < amount:
        await message.reply(f'Слишком мало на балансе. Твой баланс: {user.coins} монет. Надо {amount-user.coins}')
    task=LikeTask.LikeTask(name,url=url,amount=amount,msg_id=message.message_id)
    await message.reply(f'Задание создано: {task.creator}\n {task.url}')

@dp.message_handler()
async def echo(message: types.Message):

    await message.answer(message.text)
# Press the green button in the gutter to run the script.