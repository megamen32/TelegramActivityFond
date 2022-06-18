import asyncio
import traceback

import yandex_search
from html2image import Html2Image
from searchit import GoogleScraper, YandexScraper, BingScraper
from searchit import ScrapeRequest


import config
from utils import ensure_directory_exists
yandex = yandex_search.Yandex(api_user='deaddadend', api_key='03.412520258:7db914564474c0250c36e79d0255ced2')
scrapes=[GoogleScraper(max_results_per_page=1) , # max_results = Number of results per page
YandexScraper(max_results_per_page=1),
BingScraper(max_results_per_page=1)]
hti = Html2Image()
async def search_platform(name):
    search_quire=f"{config.settings['APP_NAME']} {name} host:{config.settings['APP_SITE']}"
    request=ScrapeRequest(search_quire,30)
    
    results=[]
    for scrape in scrapes:
        try:
            results+=await scrape.scrape(request)
        except:traceback.print_exc()
    
    for result in results:
        if config.settings['APP_SITE'] in result.url:
            s=result
            break
    
    avatar_path = f'avatar_{name}.png'
    ensure_directory_exists(avatar_path)
    hti.screenshot(url=s, save_as=avatar_path)
    return avatar_path
async def async_search(name):
    return await search_platform(name)