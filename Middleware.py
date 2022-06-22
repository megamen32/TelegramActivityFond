import asyncio

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


        # Use Dispatcher.throttle method.
        id = message.chat.id
        if id in self.banned_users:
            await message.answer('Вы были заблокированы. Напишите администратору.')
            # Cancel current handler
            raise CancelHandler()


