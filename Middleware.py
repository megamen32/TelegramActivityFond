import asyncio
import traceback

from aiogram import Bot, Dispatcher, executor, types

from aiogram.dispatcher import DEFAULT_RATE_LIMIT
from aiogram.dispatcher.handler import CancelHandler, current_handler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils.exceptions import Throttled

import config






class BanMiddleware(BaseMiddleware):
    """
    Simple middleware
    """

    def __init__(self):
        self.__banned_users=config.data.get('banned_users',default=[])

        super(BanMiddleware, self).__init__()

    @property
    def banned_users(self):
        if self.__banned_users is None:
            self.__banned_users=[]
        return self.__banned_users
    @banned_users.setter
    def banned_users(self,value):
        self.__banned_users=value
        config.data.set('banned_users',self.__banned_users)

    async def on_process_message(self, message: types.Message, data: dict):
        """
        This handler is called when dispatcher receives a message

        :param message:
        """
        # Get current handler
        handler = current_handler.get()

        # Get dispatcher from context
        dispatcher = Dispatcher.get_current()
        # If handler was configured, get rate limit and key from handler
        if not any(message.photo):
            try:
                await dispatcher.throttle(key='request', rate=0.5, user_id=message.from_user.id,chat_id=message.chat.id)
            except Throttled:
                #await message.answer_photo(photo='https://u.livelib.ru/reader/amazing_olw/o/mip7mpvd/o-o.jpeg',caption='Слишком много запросов от тебя. Подожди немного и повтори.')
                await message.answer('Слишком много запросов от тебя. Подожди немного и повтори.')
                raise CancelHandler()
        # Use Dispatcher.throttle method.
        id = message.chat.id

        if id in self.banned_users:
            await message.answer('Вы были заблокированы. Напишите в t.me/ShareActivity.')
            # Cancel current handler
            raise CancelHandler()


