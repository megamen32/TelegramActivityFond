from aiogram.types import InlineKeyboardButton

import LikeTask
from tgbot import *
from tgbot import cancel_task_cb, cancel_task_cb_admin
premium_cb=CallbackData('personal','is_cancel','task')

@dp.message_handler(commands='personal', state='*')
@dp.message_handler(Text(equals='Личные Задания', ignore_case=True), state='*')
@registerded_user
async def send_premium_tasks(message: types.Message, **kwargs):
    name = tg_ids_to_yappy[message.chat.id]
    try:
        LikeTask.PersonalTask.update_filters()
        tasks: typing.List[LikeTask.LikeTask] = LikeTask.GetPersonalTasks(name)

        targets = ''
        for i in range(len(tasks)):
            task = tasks[i]
            stri = f'Задание {i} описание: {task.url} Награда: {task.done_cost} от {task.creator}'
            keyboard_markup = InlineKeyboardMarkup()
            cb = premium_cb
            row_btns2 = InlineKeyboardButton('Отменить задание', callback_data=cb.new(is_cancel=True,task=task.name))
            row_btns = InlineKeyboardButton('Выполнить', callback_data=cb.new(is_cancel=False,task=task.name))
            keyboard_markup.add(row_btns,row_btns2)
            await message.answer(stri, reply_markup=keyboard_markup)
        if not any(tasks):
            await message.reply('У тебя пока нет заданий.')
    except KeyError:
        await message.reply('У тебя пока нет заданий.')
    except:
        traceback.print_exc()
@dp.callback_query_handler(premium_cb.filter(is_cancel='True'),state='*')
async def vote_cancel_premium_cb_handler(query: types.CallbackQuery,callback_data:dict):
    """
        Allow user to cancel any action
        """
    await bot.answer_callback_query(query.id)
    user=yappyUser.All_Users_Dict[tg_ids_to_yappy[query.from_user.id]]
    user.skip_tasks.add(callback_data['task'])
    return await query.message.edit_text('Удалил',reply_markup=None)
@dp.callback_query_handler(premium_cb.filter(),state='*')
async def vote_do_premium_cb_handler(query: types.CallbackQuery,state:FSMContext,callback_data:dict):


    name = tg_ids_to_yappy[query.from_user.id]
    user: yappyUser.YappyUser = yappyUser.All_Users_Dict[name]
    task=LikeTask.get_task_by_name(callback_data['task'])



    await state.reset_data()
    await BotHelperState.start_doing_task.set()
    await state.set_data({'task': str(task.name)})
    task.reserved_done_amount += 1
    text= await get_task_readable(task)
    return await query.message.answer(text,reply_markup=cancel_kb)
@dp.message_handler(regexp='Создать личное задание')
@dp.message_handler(commands='taskfor')
@registerded_user
async def create_personal_task_handler(message: types.Message,state,**kwargs):
    global premium_ids
    name = tg_ids_to_yappy[message.chat.id]
    user:yappyUser.YappyUser=yappyUser.All_Users_Dict[name]
    reciver='None'
    try:
        reciver=strip_command(message.text)
    except:pass

    reciver=await help_no_user(message,reciver)
    if reciver not in yappyUser.All_Users_Dict.keys():
        return await message.answer('Такой пользователь не найден')
    if reciver == name:
        return await message.answer("Нельзя создавать задания себе-же")
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
    await state.update_data(data={'reciver':reciver})
    await message.reply(f'*Введи количество очков*, которое ты потратишь на задание.\n\nТвой баланс: *{user.get_max_spend_amount()}*', parse_mode= "Markdown", reply_markup=keyboard_digit)
    await message.reply('Если передумал/а — нажми *Отмена*.', parse_mode= "Markdown", reply_markup=keyboard_markup)
