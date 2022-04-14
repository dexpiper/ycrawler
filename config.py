import re

import aiohttp


ROOTPAGE = 'https://news.ycombinator.com/'
TIMEOUT = aiohttp.ClientTimeout(total=5)        # total in seconds
MAX_RETRY = 3
MAX_WORKERS = 5
PERIOD = 60                                     # in seconds
DOWNLOADS_DIR = 'downloads'                     # name of dir for downloads
number_pattern = re.compile(r'\n(\d{1,2})\.')
name_pattern = re.compile(r'\n\d+\. (.*)')
