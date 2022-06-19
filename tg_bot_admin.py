import LikeTask
from tgbot import *
def admin_user(func):
    """Декоратор первичного обработчика сообщения, отвечает за контроль доступа и логи"""
    async def user_msg_handler(message: types.Message,**kwargs):
        id = message.from_user.id
        if id in config._settings.get("admin_ids",default=["540308572"]):
            await func(message,**kwargs)
        else:
            await message.reply(f'You are not admin"')
    return user_msg_handler
@admin_user
@dp.message_handler( commands='send_all',state='*')
async def send_all(message: types.Message,**kwargs):

    text=strip_command(message.text)
    #ids:dict=tg_ids_to_yappy[message.from_user.id]
    for id in tg_ids_to_yappy.keys():
        
        await bot.send_message(id,text)
@admin_user
@dp.message_handler( commands='send',state='*')
async def send(message: types.Message,**kwargs):

    username,message.text=strip_command(message.text).split(' ',1)
    id=list(tg_ids_to_yappy.keys())[list(tg_ids_to_yappy.values()).index(username)]
    await message.reply(f"Send to {username} id {id}  \n{message.text}")
    await bot.send_message(id,message.text)
@admin_user
@dp.message_handler( commands='admin_info',state='*')
async def send(message: types.Message,**kwargs):
    data=''
    for user in yappyUser.All_Users_Dict.values():
        u:yappyUser.YappyUser=user
        balance=u.get_readable_balance()
        done_tasks=u.done_tasks
        
        syh=f'{u.username}  {balance} '

        if u.username in LikeTask.All_Tasks:
            self_task=LikeTask.All_Tasks[u.username]
            syh+='\n'.join([str(task) for task in self_task])
        data+=syh+'\n'
    await message.reply(data[-4600::])
        
@dp.message_handler()
async def echo(message: types.Message,state:FSMContext):
    a=await state.get_state()
    data=await state.get_data()
    await message.answer(f'Я не понял что надо делать. Состояние:{a}, данные {data}', reply_markup=quick_commands_kb)
# Press the green button in the gutter to run the script.