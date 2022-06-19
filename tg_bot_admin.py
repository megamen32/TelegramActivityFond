import traceback

import LikeTask
from tgbot import *
def admin_user(func):
    """Декоратор первичного обработчика сообщения, отвечает за контроль доступа и логи"""
    async def user_msg_handler(message: types.Message,**kwargs):
        telegram_id = message.from_user.id
        if telegram_id in config._settings.get("admin_ids",default=["540308572"]):
            await func(message,**kwargs)
        else:
            await message.reply(f'You are not admin"')
    return user_msg_handler
@admin_user
@dp.message_handler( commands='send_all',state='*')
async def send_all(message: types.Message,**kwargs):

    text=strip_command(message.text)
    #ids:dict=tg_ids_to_yappy[message.from_user.id]
    loop=asyncio.get_running_loop()
    tasks=[]
    for teleagram_id in tg_ids_to_yappy.keys():
        try:
            tasks.append(loop.create_task(bot.send_message(teleagram_id,text),name=f'send_message_to_{teleagram_id}'))
        except:
            traceback.print_exc()
    await asyncio.wait(tasks)
@admin_user
@dp.message_handler( commands='send',state='*')
async def send(message: types.Message,**kwargs):

    username,message.text=strip_command(message.text).split(' ',1)
    telegram_id=list(tg_ids_to_yappy.keys())[list(tg_ids_to_yappy.values()).index(username)]
    await message.reply(f"Send to {username} id {telegram_id}  \n{message.text}")
    await bot.send_message(telegram_id,message.text)
@admin_user
@dp.message_handler( commands='admin_info',state='*')
async def send(message: types.Message,**kwargs):
    info=f"Всего заданий: {len(LikeTask.All_Tasks)} Активных Заданий: {len(LikeTask.Get_Undone_Tasks())} Всего пользователей: {yappyUser.Yappy_Users}"
    await message.reply(info)
    data=''
    for user in yappyUser.All_Users_Dict.values():
        try:
            syh =  get_user_info(user)
            data+=syh+'\n\n'
            if len(data)>4000:
                await message.reply(data[-4600::])
                data=''
        except:traceback.print_exc()
    if any(data):
        await message.reply(data[-4200::])


def get_user_info(user):
    u: yappyUser.YappyUser = user
    balance = u.get_readable_balance()
    done_tasks = u.done_tasks
    syh = f'{u.username}  {balance} \n'
    if u.username in LikeTask.All_Tasks:
        self_task = LikeTask.All_Tasks[u.username]
        if isinstance(self_task, list):
            syh += '\n-'.join(str(task) for task in self_task)
        else:
            syh += str(self_task)
    return syh


def is_user_register(message: types.Message):
    telegram_id=message.from_user.id
    return telegram_id in tg_ids_to_yappy.keys()
@dp.message_handler()
async def echo(message: types.Message,state:FSMContext):
    a=await state.get_state()
    data=await state.get_data()
    if is_user_register:
        await message.answer(f'Пожалуйста введите комманду чтобы начать. Например /help или /balance', reply_markup=quick_commands_kb)
    else:
        await message.answer(f'Вы еще не зарегистрированны. Пожалуйста введите ваше имя', reply_markup=quick_commands_kb)
        await send_name(message,state)
        
# Press the green button in the gutter to run the script.