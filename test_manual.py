import asyncio
import logging
import os

import requests

from crawler import parse_comments_page
from crawler import download_page


LINK = 'https://news.ycombinator.com/item?id=30943039'
PATTERN = 'https://news.ycombinator.com/item?id={}'
ids = [_id for _id in os.listdir('downloads')]


def normal(link):
    html = requests.get(link).text
    comments = parse_comments_page(html)
    print('*** Normal mode:\n')
    print('Got comments: ', len(comments))
    print(comments)
    print(' ***\n')


async def via_crawler(link):
    html = await download_page(link)
    comments = parse_comments_page(html)
    print('*** Crawler mode:\n')
    print('Got comments: ', len(comments))
    print(comments)
    print(' ***\n')

if __name__ == '__main__':
    logging.basicConfig(filename=None,
                        level=logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    # links = [PATTERN.format(_id) for _id in ids]
    # asyncio.run(asyncio.wait(
    #    [via_crawler(link) for link in links]
    #    )
    # )
    asyncio.run(via_crawler(LINK))
