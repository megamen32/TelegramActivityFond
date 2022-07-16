import asyncio
import re
import traceback

from aiogram.types import InlineQueryResultArticle, InputTextMessageContent

import config
import yappyUser
from tgbot import *
import  Middleware
from utils import flatten, get_key, exclude

ban_middleware=Middleware.BanMiddleware()
AdminMiddleWares=[ban_middleware]
def admin_user(func):
    """Декоратор первичного обработчика сообщения, отвечает за контроль доступа и логи"""
    async def user_msg_handler(message: types.Message,**kwargs):
        telegram_id = message.from_user.id
        if str(telegram_id) in   config._settings.get('admin_ids', ['540308572', '65326877']):

            await func(message,**kwargs)
        else:
            await message.reply(f'You are not admin"')
    return user_msg_handler
@admin_user
@dp.message_handler( commands='run',state='*')
async def run_command(message: types.Message,**kwargs):
    try:
        run_command=strip_command(message.text)
        await message.answer(run_command)
        result=eval(run_command)
        await message.answer(result)
    except:
        await message.answer(traceback.format_exc()[-3000:])
@admin_user
@dp.message_handler( commands='set_user',state='*')
async def set_user(message: types.Message,**kwargs):
    try:
        username,command=strip_command(message.text).split('.',1)
        user=yappyUser.All_Users_Dict[username]
        run_command = f"user.{command}"
        await message.answer(run_command)
        result=exec(run_command,vars())
        #await message.answer(result)
    except:
        await message.answer(traceback.format_exc()[-3000:])
@admin_user
@dp.message_handler( commands='send_all',state='*')
async def send_all(message: types.Message,**kwargs):

    text=strip_command(message.text)
    #ids:dict=tg_ids_to_yappy[message.from_user.id]
    loop=asyncio.get_running_loop()
    tasks=[]
    for teleagram_id in tg_ids_to_yappy.keys():
        try:
            tasks.append((bot.send_message(teleagram_id,text)))
        except:
            traceback.print_exc()
    await asyncio.wait(tasks,timeout=config._settings.get('sending_messages_timeout',default=300))
@admin_user
@dp.message_handler( commands='send_offline',state='*')
@dp.message_handler( commands='info_offline',state='*')
async def send_offline(message: types.Message,**kwargs):

    text=''
    day=7
    try:
        text = strip_command(message.text)
    except:pass
    try:

        day=int(re.findall(r'\d+',message.text)[-1])
    except:pass
    #ids:dict=tg_ids_to_yappy[message.from_user.id]
    loop=asyncio.get_running_loop()
    tasks=[]
    usernames=[]
    for teleagram_id,username in tg_ids_to_yappy.items():
        try:
            if username not in yappyUser.All_Users_Dict:continue
            user:yappyUser.YappyUser=yappyUser.All_Users_Dict[username]
            if (datetime.datetime.now()-user.last_login_time).days>day:
                if 'send' in message.text:
                    tasks.append((bot.send_message(teleagram_id,text)))
                usernames.append(user)
        except:
            traceback.print_exc()
    usernames.sort(key=lambda usr:len(usr.done_tasks),reverse=True)

    text = "\n".join(map(lambda u: f"{u.username}, @{getattr(u,'telegram_username','')}, {len(u.done_tasks)}, {u.last_login_time}, {datetime.datetime.now()-u.last_login_time}.", usernames))
    await message.reply(text[0:4000])
    if 'send' in message.text:
        await asyncio.wait(tasks,timeout=config._settings.get('sending_messages_timeout',default=300))
@dp.inline_handler(state='*')
async def inline_handler(query: types.InlineQuery):
    try:
        # Получение ссылок пользователя с опциональной фильтрацией (None, если текста нет)
        switch_text = 'Не админ '
        if str(query.from_user.id) not in  config._settings.get('admin_ids', ['540308572', '65326877']) :
            return await query.answer(
                [], cache_time=60, is_personal=False,
                switch_pm_parameter="add", switch_pm_text=switch_text)
        cur_query = (query.query.lower() or '')
        empty = re.findall(r'\w:[^;]*$', cur_query)
        for t in empty:
            cur_query=cur_query.replace(t,'')
        switch_text = 'users '
        try:
            is_sending = re.findall(r's:([^;]*);', cur_query)
            for msg in is_sending:
                cur_query=cur_query.replace(f"s:{msg};",'')
            is_sending = re.findall(r'f:([^;]*);', cur_query)
        except:
            is_sending=[]
        if len(cur_query) == 0:
            result=list(yappyUser.All_Users_Dict.values())[-50:]
            results = await convert_to_inline(result)
            switch_text = f' users {len(yappyUser.All_Users_Dict.values())}'
            return await query.answer(
                results, cache_time=60, is_personal=False,
                switch_pm_parameter="add", switch_pm_text=switch_text)
        else:
            telegram=cur_query.startswith('@')
            if telegram:
                cur_query=cur_query.strip('@')
                cur_query = cur_query.lstrip(' ').rstrip(' ')
                result=list((filter(lambda user: hasattr(user,'telegram_username') and (getattr(user,'telegram_username',
                                                                                               '')) is not None and cur_query in (
                getattr(user,
                                                                                                                               'telegram_username','') or ' ' ).lower() ,yappyUser.All_Users_Dict.values()))) or []
            else:
                all_users = yappyUser.All_Users_Dict.values()
                filters = re.findall(r'f:[^;]*;', cur_query)

                for fil in filters:
                    cur_query=cur_query.replace(fil,"")
                    fil=fil.lstrip('f:').rstrip(';')

                    all_users=list(filter(lambda u: eval(f"{fil}"),all_users))
                cur_query = cur_query.lstrip(' ').rstrip(' ')
                result= list(filter(lambda user: cur_query in user.username, all_users))[-50:]

            loop=asyncio.get_running_loop()
            for msg in is_sending:
                for user in result:
                    try:
                        loop.create_task(bot.send_message(get_key(user.username,tg_ids_to_yappy),msg,parse_mode='Markdown'))
                    except:
                        traceback.print_exc()
            results = await convert_to_inline(list(result)[-50:],telegram=telegram)
            switch_text = f' users {len(results)}'
            return await query.answer(
                results, cache_time=60, is_personal=False,
                switch_pm_parameter="add", switch_pm_text=switch_text)
    except:
        traceback.print_exc()
        result = list(yappyUser.All_Users_Dict.values())[-50:]
        results = await convert_to_inline(result)
        return await query.answer(
            results, cache_time=60, is_personal=False,
            switch_pm_parameter="add", switch_pm_text=traceback.format_exc()[-300:])


async def convert_to_inline(result,telegram=False):
    results = [InlineQueryResultArticle(id=str(item.username),
                                        title=f"{str(item.username)} уровень:{item.level} ник:@{getattr(item,'telegram_username','')  }",

                                        description=f"Выполнено:{len(item.done_tasks)}|{item.get_readable_balance()}",
                                        input_message_content=InputTextMessageContent(
                                            message_text=f"/info {item.username}" if not telegram else getattr(item,'telegram_username',item.username) ,
                                            parse_mode="HTML"
                                        ))
               for item in result]

    return results



@admin_user
@dp.message_handler( commands='info',state='*')
@dp.message_handler( regexp=r'/info\d+',state='*')
async def info(message: types.Message,**kwargs):
    try:
        if '@' in message.text:
            username=message.text.split('@',1)[-1]
        else:
            username=strip_command(message.text)
        #digits_txt=re.findall(r'\d+',message.text)
        username=username.split(' ',1)[0]
        #digits=0
        #if any(digits_txt):
            #digits=int(digits_txt[0])

        await send_balance_(message, yappyUser.All_Users_Dict[username])
        #message.text = f'/history {digits}'
        await send_history(message, username)
    except:
        await message.answer(traceback.format_exc()[-3000:])
    #message.chat.id=get_key(username,tg_ids_to_yappy)

@admin_user
@dp.message_handler( commands='add_balance',state='*')
async def add_balance(message: types.Message,**kwargs):
    try:
        username,message.text=strip_command(message.text).split(' ',1)
        digits=float(re.fullmatch(r'-?\d+',message.text).group())
        user= yappyUser.All_Users_Dict[username]
        await user.AddBalance(digits, 'ActivityBot', f'От модерации')
        await  message.reply(f'sended to {username} {digits} \n{yappyUser.All_Users_Dict[username]}')
    except:
        await message.reply(traceback.format_exc())
        traceback.print_exc()
@admin_user
@dp.message_handler( commands='premium',state='*')
@dp.message_handler( commands='unpremium',state='*')
async def add_premium_user(message: types.Message,command,**kwargs):
    try:
        premium_ids=await config.data.async_get("premium_ids",set())
        username = strip_command(message.text)
        tg_id = get_key(username, tg_ids_to_yappy)
        if 'un' in command.command:
            premium_ids.remove(tg_id)
        else:
            premium_ids.add(tg_id)
        await config.data.async_set("premium_ids",premium_ids)
        premiums=list(filter(None,map(lambda x:tg_ids_to_yappy[x],filter(None,premium_ids))))
        txts=", ".join(premiums)
        await  message.reply(f'succes add/remove.  premiums:  {premiums} ')
    except:
        await  message.reply(f'no user found to premium {traceback.format_exc()}  ')

@admin_user
@dp.message_handler( commands='ban',state='*')
async def add_banned_user(message: types.Message,**kwargs):
    try:
        username=strip_command(message.text)
        tg_id=get_key(username,tg_ids_to_yappy)
        banned = " ,".join(map(str, [tg_ids_to_yappy[u] for u in ban_middleware.banned_users]))
        if tg_id:
            if tg_id in ban_middleware.banned_users:
                await  message.reply(f'was banned already. All banned: {banned}')
                return
            ban_middleware.banned_users+=[tg_id]


            await  message.reply(f'banned to {username} id:{tg_id}  \n{yappyUser.All_Users_Dict[username]}\nbanned:{banned}')
        else: await  message.reply(f'no user found to ban {username}  ')

    except:
        await message.reply(traceback.format_exc())
        traceback.print_exc()
@admin_user
@dp.message_handler( commands='unban',state='*')
async def remove_banned_user(message: types.Message,**kwargs):
    try:
        username=strip_command(message.text)
        tg_id=get_key(username,tg_ids_to_yappy)
        banned = " ,".join(map(str, [tg_ids_to_yappy[u] for u in ban_middleware.banned_users]))
        if tg_id in ban_middleware.banned_users:
            ban_middleware.banned_users.remove(tg_id)
            ban_middleware.banned_users=ban_middleware.banned_users
            await  message.reply(f'unbanned to {username} id:{tg_id}  \n{yappyUser.All_Users_Dict[username]}\nbanned:{banned}')
        else:
            await  message.reply(f'user {username} id:{tg_id}  not banned\n banned:{banned}')
    except:
        await message.reply(traceback.format_exc())
        traceback.print_exc()
@admin_user
@dp.message_handler( commands='send',state='*')
async def send(message: types.Message,**kwargs):
    try:
        username,message.text=strip_command(message.text).split(' ',1)
        telegram_id=list(tg_ids_to_yappy.keys())[list(tg_ids_to_yappy.values()).index(username)]
        await message.reply(f"Send to {username} id {telegram_id}  \n{message.text}")
        await bot.send_message(telegram_id,message.text)
    except:
        await message.reply(traceback.format_exc())
@admin_user
@dp.message_handler( commands='admin_info',state='*')
async def send(message: types.Message,**kwargs):
    info=f"Всего заданий: {len(LikeTask.All_Tasks)} Активных Заданий: {len(LikeTask.Get_Undone_Tasks())} Всего пользователей: {len(yappyUser.Yappy_Users)}"
    await message.reply(info)
    user=yappyUser.All_Users_Dict[tg_ids_to_yappy[message.chat.id]]
    active_users, average_task_comlete_count, inflation, prev_day_tasks, task_complete_count, tasks_count = await get_inflation(
        user)
    msg=f"Инфляция {inflation}= сегодня выполненно:{task_complete_count-1}/ активных {tasks_count-1}  \nСегодняшних заданий {tasks_count-1 -prev_day_tasks} | Активных пользователей {active_users-1} | заданий за прошлые дни: {(prev_day_tasks)} |  \n Заданий на юзера : {tasks_count-prev_day_tasks}/{active_users}-{prev_day_tasks}/{user.level}={average_task_comlete_count}"
    await message.answer(msg)
    return
    data=''
    for user in yappyUser.All_Users_Dict.values():
        try:
            syh =  get_user_info(user)
            data+=syh+'\n\n'
            if len(data)>2000:
                await message.reply(data[-3000::])
                data=''
        except:traceback.print_exc()
    if any(data):
        await message.reply(data[-4000::])





@dp.message_handler( commands='edit_tasks',state='*')
@dp.message_handler( commands='edit_tasks_all',state='*')
@admin_user
async def get_all_tasksr(message: types.Message,state:FSMContext,command,**kwargs):
    is_all=False
    try: is_all= '_all' in message.text
    except: pass
    try:
        if is_all:
            tasks=flatten(LikeTask.All_Tasks.values())
        else:
            try:
                username=strip_command(message.text)
                tasks=LikeTask.All_Tasks[username]
            except:
                tasks=LikeTask.Get_Undone_Tasks()


        for i in range(len(tasks)):
            task = tasks[i]
            stri = f'Задание {i} от {task.creator}, созданно:{task.created_at}, {"активно" if task.is_active() else "выполнено"}, описание: {task.url}, выполнено {task.done_amount} раз из {task.amount} раз.'
            keyboard_markup = InlineKeyboardMarkup()
            create_cancel_buttons(keyboard_markup, task,admin=True)
            await message.answer(stri, reply_markup=keyboard_markup)
        if not any(tasks):
            await message.reply('У тебя пока нет созданных заданий.')
    except KeyError:
        await message.reply('У тебя пока нет созданных заданий.')

    except:
        traceback.print_exc()



def get_user_info(user):
    u: yappyUser.YappyUser = user
    balance = u.get_readable_balance()
    done_tasks = u.done_tasks
    syh = f'{u.username}  {balance} \n Выполненно заданий:{len(u.done_tasks)} Всего заданий:{len(LikeTask.All_Tasks[u.username]) if u.username in LikeTask.All_Tasks else 0}'
    if u.username in LikeTask.All_Tasks:
        self_task = LikeTask.All_Tasks[u.username]
        if isinstance(self_task, list):
            syh += '\n-'.join(str(task) for task in filter(lambda x: x.is_active(),self_task))
        else:
            syh += str(self_task)
    return syh


def is_user_register(message: types.Message):
    telegram_id=message.from_user.id
    return telegram_id in tg_ids_to_yappy.keys()

@dp.message_handler(state='*')
async def echo(message: types.Message,state:FSMContext):
    a=await state.get_state()
    data=await state.get_data()
    if is_user_register(message):
        state_ = await state.get_state()
        if(state_ ==BotHelperState.start_doing_task.state or state_==BotHelperState.doing_task.state):
            if 'task' in data:

                task=LikeTask.get_task_by_name(data['task'])
                if task is not None:
                    text=await get_task_readable(task)
                    text=f"У тебя не выполнено: {text}"
                    next_task_kb = InlineKeyboardMarkup()
                    cancel_task_bt = InlineKeyboardButton("Отмена", callback_data="cancel")
                    storage_data=await storage.get_data(chat=message.chat.id,user='task_doing')
                    if 'photos_path' in storage_data :
                        Confirm_buton = InlineKeyboardButton(f"Подтвердить", callback_data='confirm')
                        next_task_kb.row(cancel_task_bt,Confirm_buton)
                    else:
                        next_task_kb.row(cancel_task_bt)
                    await message.reply(text,reply_markup=next_task_kb)
                    return

            await message.reply(
            f'*Пришли до трёх (3) скриншотов*, подтверждающих выполнение задания, или нажми Отмена.',
            reply_markup=cancel_kb, parse_mode="Markdown")
        else:
            await message.answer(f'Пожалуйста, введите команду, чтобы начать. Например /task или /balance', reply_markup=quick_commands_kb)

    else:
        await message.answer(f'Ты еще не зарегистрирован/а. Пожалуйста, введи свой никнейм: ', reply_markup=quick_commands_kb)
        await RegisterState.name.set()
        await send_name(message,state)
        
# Press the green button in the gutter to run the script.