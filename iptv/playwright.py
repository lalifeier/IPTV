import logging

from playwright.async_api import Playwright, async_playwright

logger = logging.getLogger(__name__)

playwright: Playwright = None

async def get_playwright():
    global playwright
    if playwright is None:
        try:
            playwright = await async_playwright().start()
        except Exception as e:
            logging.error(f"Error starting Playwright: {e}")
            raise
    return playwright
