import asyncio

from html2image import Html2Image
from googlesearch import search
import config

hti = Html2Image()
def search(name):
    s = next(search(f"{config.settings['APP_NAME']} {name} site:{config.settings['APP_SITE']}", num_results=1))
    avatar_path = f'img/avatar_{name}.png'
    hti.screenshot(url=s, save_as=avatar_path)
    return avatar_path
async def async_search(name):
    return await asyncio.get_event_loop().run_in_executor(None,search,name)