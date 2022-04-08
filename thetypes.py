import asyncio
from dataclasses import dataclass


@dataclass
class NewsItem:
    name: str = None
    link: str = None
    id: str = None
    comments_page: str = None


class Counter:
    """
    Simple async counter
    """
    def __init__(self):
        self.total_downloads = 0
        self.total_saved_files = 0
        self.lock = asyncio.Lock()

    async def incr_download(self):
        async with self.lock:
            self.total_downloads += 1

    async def incr_files(self):
        async with self.lock:
            self.total_saved_files += 1

    async def zero(self):
        async with self.lock:
            self.total_downloads = 0
            self.total_saved_files = 0
