import asyncio
import json
import logging
import os
from typing import Dict, Optional

import aiohttp

IPTV_ENDPOINTS = {
    "江苏": "http://live.epg.gitv.tv/tagNewestEpgList/JS_CUCC/1/100/0.json",
    "广东": "http://live.epg.gitv.tv:29010/tagNewestEpgList/GD_CUCC/1/100/1.json",
}

headers = {"Content-Type": "application/json;charset=UTF-8"}
logger = logging.getLogger(__name__)


async def fetch_json(url: str) -> Optional[Dict]:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                logger.debug(f"Successfully fetched data from {url}")
                return await response.json(content_type=None)
        except (
            aiohttp.ClientResponseError,
            aiohttp.ClientError,
            json.JSONDecodeError,
        ) as e:
            logger.error(f"Error fetching JSON from {url}: {e}")
            return None


async def process_channel_data(item: Dict) -> Optional[str]:
    play_url = item.get("playUrl")
    if not play_url:
        logger.warning(f"Missing playUrl in item: {item}")
        return None

    play_url += "&mac=d4:38:44:a5:72:8b"
    json_data = await fetch_json(play_url)
    if not json_data:
        logger.warning(f"Failed to fetch JSON data from play URL: {play_url}")
        return None

    channel_name = item.get("chnName")

    final_url = (
        json_data.get("u")
        if json_data.get("u")
        else json_data.get("data")[0].get("url")
    )

    logger.debug(f"Processed channel {channel_name} with URL {final_url}")
    return f"{channel_name},{final_url}\n"


async def process_endpoint(key: str, url: str) -> None:
    filepath = f"txt/iptv/中国联通/{key}.txt"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    json_data = await fetch_json(url)
    if not json_data or "data" not in json_data:
        logger.error(f"Invalid or empty data received from {url}")
        return

    tasks = [process_channel_data(item) for item in json_data["data"]]
    results = await asyncio.gather(*tasks)
    lines = [line for line in results if line]

    if lines:
        with open(filepath, "w", encoding="utf-8") as file:
            file.writelines(lines)
        logger.info(f"Data successfully saved to {filepath}.")
    else:
        logger.warning(f"No valid data to save for {key}.")


async def main():
    tasks = [process_endpoint(key, url) for key, url in IPTV_ENDPOINTS.items()]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(main())
