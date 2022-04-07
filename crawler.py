import re
import os
import sys
import time
import asyncio
import hashlib
import logging
import subprocess
from urllib.parse import urljoin
from dataclasses import dataclass
from optparse import OptionParser

import aiohttp
import aiofiles
import aiofiles.os
from bs4 import BeautifulSoup
from aiohttp.client_exceptions import (ClientResponseError,
                                       InvalidURL,
                                       ClientConnectorCertificateError)


ROOTPAGE = 'https://news.ycombinator.com/'
TIMEOUT = aiohttp.ClientTimeout(total=5)
MAX_CONNECTIONS = 5
MAX_RETRY = 3
MAX_WORKERS = 5
DOWNLOADS_DIR = 'downloads'
number_pattern = re.compile(r'\n(\d{1,2})\.')
name_pattern = re.compile(r'\n\d+\. (.*)')


@dataclass
class NewsItem:
    name: str = None
    link: str = None
    id: str = None
    comments_page: str = None


def get_filename(filename: str):
    h = hashlib.md5(bytes(filename, encoding='utf8'))
    return h.hexdigest()


def get_extra_links(dirname: str, links: list[str]):
    extra_links = []
    files = os.listdir('/'.join((DOWNLOADS_DIR, dirname)))
    try:
        files.remove('links.txt')
    except ValueError:
        pass
    for link in list(set(links)):
        if '.'.join((get_filename(link), 'html')) not in files:
            extra_links.append(link)
    return extra_links


async def save_file(newsdir, filename, content):
    h = hashlib.md5(bytes(filename, encoding='utf8'))
    filename = h.hexdigest()
    filename = '.'.join((filename, 'html'))
    path = '/'.join((DOWNLOADS_DIR, newsdir, filename))
    if os.path.exists(path):
        logging.debug('File %s already exists' % filename)
    async with aiofiles.open(path, 'w') as f:
        await f.write(content)
    logging.debug('File %s saved' % filename)


async def make_dirs(names: str or list[str]):
    if isinstance(names, str):
        names = [names]
    for dirname in names:
        path = '/'.join((DOWNLOADS_DIR, dirname))
        if not os.path.isdir(path):
            await aiofiles.os.makedirs(path)
            logging.debug('Directory %s created' % dirname)
        else:
            logging.debug('Directory %s already exists' % dirname)


def parse_news_list(html: str) -> list[NewsItem]:
    """
    Returns list of NewsItems.
    """
    soup = BeautifulSoup(html, features='html.parser')
    news_table = soup.find('table', 'itemlist')
    raw_news_list = news_table.find_all('tr', 'athing')
    news_list = []
    for el in raw_news_list:
        news_id = el['id']
        name = name_pattern.search(el.text).group(1)
        link = el.find('a', 'titlelink')['href']
        if not link.startswith('http'):
            logging.debug('Got internal link')
            link = urljoin(ROOTPAGE, link)
        comments_page = urljoin(ROOTPAGE, f'item?id={news_id}')
        news_list.append(
            NewsItem(
                name=name, link=link, id=news_id,
                comments_page=comments_page
            )
        )
    logging.debug('Made newslist, length: %s' % len(news_list))
    return news_list


def parse_comments_page(html: str) -> list[str]:
    """
    Return list of parsed links
    """
    result_list = []
    soup = BeautifulSoup(html, features='html.parser')
    comments = soup.find_all('span', 'commtext c00')
    for comm in comments:
        link: str = comm.find('a')
        if not link:
            continue
        link = link['href']
        if link.startswith('http') and not len(link) > 150:
            result_list.append(link)
    result_list = list(set(result_list))
    logging.debug('Parsing result list length: %s' % len(result_list))
    return result_list


async def fetch(session, page):
    html = ''
    try:
        async with session.get(page) as response:
            html = await response.text(encoding='utf-8')
    except asyncio.TimeoutError:
        logging.error('Timeout error. Cannot get %s' % page)
    except ClientResponseError:
        logging.error('Bad response. Cannot get %s.' % page)
    except InvalidURL:
        logging.error('Url invalid. Cannot get %s.' % page)
    except ClientConnectorCertificateError:
        logging.error('Certificate error. Cannot get %s.' % page)
    except UnicodeDecodeError:
        logging.error('Decode error. Cannot get %s.' % page)
    return html


async def download_page(page, client=None):
    html = ''
    logging.debug('Sheduled downloading %s...' % page[:20])
    if not client:
        client = aiohttp.ClientSession(timeout=TIMEOUT)
    async with client:
        html = await fetch(client, page)
        logging.debug('Success: %s...' % page[:20])
    if not html:
        logging.error('Got empty html')
    return html


async def register_and_create(newspiece):
    files = os.listdir('/'.join((DOWNLOADS_DIR, newspiece.id)))
    linkfile = '/'.join((DOWNLOADS_DIR, newspiece.id, 'links.txt'))
    if 'links.txt' not in files:
        buffer = (
                    newspiece.comments_page + '\n',
                    newspiece.link + '\n'
                ) if newspiece.comments_page != newspiece.link else (
                    newspiece.comments_page + '\n'
                )
        async with aiofiles.open(linkfile, 'w') as f:
            await f.writelines(buffer)

    async with aiofiles.open(linkfile, 'r') as f_r:
        links = await f_r.readlines()
    links = [link[:-1] for link in links]
    comments_page = links[0]
    logging.debug('Ask comments for %s' % newspiece.id)
    comments_html = await download_page(comments_page)
    print(comments_html[:100])
    logging.debug('Parsing comments for %s' % newspiece.id)
    links_from_comments = parse_comments_page(comments_html)
    print(links_from_comments)
    logging.info(
        'Got %s links from comments %s' % (len(links_from_comments),
                                           newspiece.id)
    )
    links_to_append = list(set(links_from_comments) - set(links))
    if links_to_append:
        logging.debug(
            'Appending %s new links into %s' % (len(links_from_comments),
                                                newspiece.id)
        )
        async with aiofiles.open(linkfile, 'a') as f_a:
            await f_a.writelines([lnk + '\n' for lnk in links_to_append])


async def worker(name, queue):
    logging.debug('%s started' % name)
    while True:
        link, folder = await queue.get()
        try:
            html = await download_page(link)
        except Exception:
            logging.exception('Cannot download from %s' % link)
        else:
            await save_file(newsdir=folder, filename=link, content=html)
        finally:
            queue.task_done()


async def cycle():
    logging.info('Getting news list...')
    main_html = await download_page(ROOTPAGE)
    news_list = parse_news_list(main_html)
    logging.info('Making dirs...')
    await make_dirs([piece.id for piece in news_list])
    logging.info('Registering incoming news...')
    registrators = [
        register_and_create(newspiece)
        for newspiece in news_list
    ]
    await asyncio.gather(*registrators, return_exceptions=True)

    queue = asyncio.Queue(maxsize=10)
    tasks = []
    for i in range(MAX_WORKERS):
        task = asyncio.create_task(
            worker(f'worker-{i}', queue)
        )
        tasks.append(task)

    news_folders = os.listdir(DOWNLOADS_DIR)
    for folder in news_folders:
        linkfile = '/'.join((DOWNLOADS_DIR, folder, 'links.txt'))
        async with aiofiles.open(linkfile, 'r') as f:
            links = await f.readlines()
            links = [link[:-1] for link in links[1:]]
        links_to_download = get_extra_links(folder, links)
        [await queue.put((link, folder)) for link in links_to_download]

    await queue.join()
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def main():
    await cycle()


def runtest():
    command = ['python', '-m', 'unittest', '-v']
    subprocess.run(command)


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-d", "--debug", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    opts, args = op.parse_args()
    logging.basicConfig(filename=opts.log,
                        level=(
                            logging.INFO if not opts.debug else logging.DEBUG
                        ),
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        runtest()
        sys.exit(0)
    logging.info('Ycrawler started with options: %s' % opts)
    try:
        start = time.time()
        asyncio.run(main())
        elapsed = round(time.time() - start, 2)
        logging.info('Completed in %s sec' % elapsed)
    except Exception as e:
        logging.exception('Unexpected error: %s' % e)
        sys.exit(1)
