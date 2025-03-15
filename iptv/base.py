import logging
import os
import re
from typing import List, Optional

import aiohttp
import cv2
from bs4 import BeautifulSoup

from iptv.config import IP_DIR, OUTPUT_DIR
from iptv.playwright import get_playwright


class Base:
    def __init__(self):
        self.ip_dir = IP_DIR
        self.output_dir = OUTPUT_DIR

    def sniff_ip(self):
        pass

    def generate_playlist(self):
        pass

    def save_ip(self, isp: str, region: str, ip: List[str]):
        if not ip:
            logging.warning(f"No validated IPs to save for {region}.")
            return

        output_dir = os.path.join(self.ip_dir, isp)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{region}.txt")

        existing_ips = set()
        if os.path.exists(output_path):
            with open(output_path, "r", encoding="utf-8") as file:
                existing_ips = set(file.read().splitlines())

        all_ips = sorted(existing_ips.union(ip))
        with open(output_path, "w", encoding="utf-8") as file:
            file.write("\n".join(all_ips))
        logging.info(f"Saved IPs to: {output_path}")

    def get_ip(self, isp: str, region: str) -> list:
        ip_file_path = os.path.join(self.ip_dir, isp, f"{region}.txt")

        if not os.path.exists(ip_file_path):
            logging.warning(f"IP file not found: {ip_file_path}. Skipping...")
            return []

        with open(ip_file_path, "r", encoding="utf-8") as f:
            ip = f.read().splitlines()

        return ip

    async def fetch_page_content(self, url: str) -> Optional[str]:
        logging.info(f"Fetching content from {url}")
        playwright = await get_playwright()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_init_script("Object.defineProperties(navigator, {webdriver:{get:()=>false}});")
        page = await context.new_page()

        try:
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")

            # await  page.locator('//span[@class="hsxa-host"]/a').first.wait_for()

            content = await page.content()
            logging.info(f"Finished fetching content from {url}")
            return content
        except Exception as e:
            logging.error(f"Error fetching page content from {url}: {e}")
            return None
        finally:
            await browser.close()

    async def extract_ip_from_content(self, content: str) -> List[str]:
        soup = BeautifulSoup(content, 'html.parser')
        elements = soup.select('span.hsxa-host > a')
        values = [element.text for element in elements]

        def remove_protocol(url: str) -> str:
          return re.sub(r'^https?://', '', url)

        values = set(remove_protocol(element.get('href', '')) for element in elements)
        return list(values)

    async def is_url_accessible(self, url: str) -> bool:
        async with aiohttp.ClientSession() as session:
            try:
                logging.info(f"Checking accessibility for URL: {url}")
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        logging.info(f"URL {url} is accessible. Status code: {response.status}")
                        return True
                    else:
                        logging.warning(f"URL {url} is not accessible. Status code: {response.status}")
                        return False
            except Exception as e:
                logging.error(f"Error while checking URL {url}: {e}")
                return False

    def is_video_stream_valid(self, url: str) -> bool:
        logging.info(f"Checking video URL: {url}")

        try:
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if width > 0 and height > 0:
                    logging.info(f"Valid video stream found (width={width}, height={height}) at {url}")
                    return True
                else:
                    logging.info(f"Invalid video stream (width={width}, height={height}) at {url}")
            else:
                logging.info(f"Failed to open video stream at {url}")
            return False
        except cv2.error as e:
            logging.error(f"Error checking video stream {url}: {e}")
            return False
        finally:
            cap.release()

    def merge_playlist(self, output_dir: str, merged_file_path: str):
        try:
            with open(merged_file_path, "w", encoding="utf-8") as outfile:
                for subdir in os.listdir(output_dir):
                    subdir_path = os.path.join(output_dir, subdir)
                    if not os.path.isdir(subdir_path):
                        continue
                    logging.info(f"Processing directory: {subdir_path}")
                    for filename in os.listdir(subdir_path):
                        file_path = os.path.join(subdir_path, filename)
                        if os.path.isfile(file_path):
                            logging.info(f"Reading file: {file_path}")
                            with open(file_path, "r", encoding="utf-8") as infile:
                                outfile.write(infile.read() + "\n")
            logging.info(f"All files merged into {merged_file_path}")
        except Exception as e:
            logging.error(f"Error merging files: {e}")
