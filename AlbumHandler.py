from aiogram_media_group import media_group_handler, MediaGroupFilter

@dp.message_handler(MediaGroupFilter(), content_types=ContentType.PHOTO)
@media_group_handler
async def album_handler(messages: typing.List[types.Message]):
    for message in messages:
        print(message)