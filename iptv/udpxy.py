import asyncio
import base64
import logging
import os
import re
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup
from pypinyin import lazy_pinyin

from iptv.base import Base
from iptv.config import IP_DIR, ISP_DICT, OUTPUT_DIR, REGION_LIST, RTP_DIR

logger = logging.getLogger(__name__)


class UDPxy(Base):
    def __init__(self):
        super().__init__()
        self.ip_dir = os.path.join(IP_DIR, "udpxy")
        self.output_dir = os.path.join(OUTPUT_DIR, "udpxy")

    def extract_mcast_from_file(self, file_path: str) -> Optional[str]:
        logging.info(f"Extracting mcast from file: {file_path}")

        try:
          with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
            rtp_match = re.search(
                r"rtp://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+)", file_content
            )
            mcast = rtp_match.group(1) if rtp_match else None

        except FileNotFoundError:
          logging.warning(f"File not found: {file_path}")
          return None

        if mcast:
            logging.info(f"Found mcast: {mcast}")
        else:
            logging.warning(f"No mcast found in file: {file_path}")
        return mcast

    def generate_search_url(self, region: str, org_name: str) -> str:
        pinyin_name = "".join(lazy_pinyin(region, errors=lambda x: x))
        search_txt = (
            f'"udpxy" && country="CN" && region="{pinyin_name}" && org="{org_name}"'
        )
        # search_txt = f'"udpxy" && country="CN" && region="{pinyin_name}" && org="{org_name}" && is_domain=true'
        encoded_search_txt = base64.b64encode(search_txt.encode("utf-8")).decode(
            "utf-8"
        )
        return f"https://fofa.info/result?qbase64={encoded_search_txt}"

    async def validate_ip(self, ip: List[str], isp, region) -> List[str]:
        if not ip:
            logging.warning("No valid IPs to validate.")
            return []

        mcast = self.extract_mcast(isp, region)
        if not mcast:
            logging.warning(f"No rtp:// URL found in {isp} {region}. Skipping...")
            return []

        validated_ip = []

        async def validate_single_ip(ip_address: str) -> bool:
            url_status = f"http://{ip_address}/status"
            url_video = f"http://{ip_address}/rtp/{mcast}"
            return await self.is_url_accessible(
                url_status
            ) and self.is_video_stream_valid(url_video)

        tasks = [validate_single_ip(ip_address) for ip_address in ip]

        for ip_address, valid in zip(ip, await asyncio.gather(*tasks)):
            if valid:
                validated_ip.append(ip_address)

        logging.info(f"Validated {len(ip)} IPs. Found {len(validated_ip)} valid IPs.")
        return validated_ip

    def extract_mcast(self, isp, region):
        isp_dir = os.path.join(RTP_DIR, isp)
        file_path = os.path.join(isp_dir, f"{region}.txt")

        return self.extract_mcast_from_file(file_path)

    async def sniff_ip(self):
        for isp in os.listdir(RTP_DIR):
            isp_dir = os.path.join(RTP_DIR, isp)
            if not os.path.isdir(isp_dir):
                continue

            if isp not in ISP_DICT:
                logging.warning(f"Unknown ISP '{isp}'. Skipping...")
                continue

            org_name = ISP_DICT[isp]

            for filename in os.listdir(isp_dir):
                if not filename.endswith(".txt"):
                    continue

                region = filename.replace(".txt", "")

                url = self.generate_search_url(region, org_name)
                content = await self.fetch_page_content(url)

                if not content:
                    logging.warning(f"Empty content for region {region}. Skipping...")
                    continue

                ip = await self.extract_ip_from_content(content)

                validated_ips = await self.validate_ip(ip, isp, region)

                self.save_ip(isp, region, validated_ips)

    async def get_valid_ip(self, isp, region):
        mcast = self.extract_mcast(isp, region)
        if not mcast:
            logging.warning(f"No rtp:// URL found in {isp} {region}. Skipping...")
            return []

        ip_file_path = os.path.join(self.ip_dir, isp, f"{region}.txt")

        if not os.path.exists(ip_file_path):
            logging.warning(f"IP file not found: {ip_file_path}. Skipping...")
            return None

        with open(ip_file_path, "r", encoding="utf-8") as f:
            valid_ips = f.read().splitlines()

        if not valid_ips:
            logging.warning(f"No valid IP found in file: {ip_file_path}.")
            return None

        invalid_ips = []
        valid_ip = None
        for ip in valid_ips:
            if await self.is_url_accessible(
                f"http://{ip}/status"
            ) and self.is_video_stream_valid(f"http://{ip}/udp/{mcast}"):
                valid_ip =  ip
                break
            else:
                invalid_ips.append(ip)

        if invalid_ips:
          with open(ip_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join([ip for ip in valid_ips if ip not in invalid_ips]))

        if valid_ip:
            return valid_ip

        logging.warning(f"No valid IP found after re-validation for {region}.")
        return None

    async def generate_playlist(self):
        for isp in os.listdir(RTP_DIR):
            isp_dir = os.path.join(RTP_DIR, isp)
            if not os.path.isdir(isp_dir):
                logging.warning(f"Directory not found: {isp_dir}. Skipping...")
                continue

            for filename in os.listdir(isp_dir):
                if not filename.endswith(".txt"):
                    continue

                region = filename.replace(".txt", "")

                ip = await self.get_valid_ip(isp, region)

                if not ip:
                    logging.warning(f"No valid IP available for {region}. Skipping...")
                    continue

                file_path = os.path.join(RTP_DIR, isp, f"{region}.txt")
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                playlists = content.replace("rtp://", f"http://{ip}/udp/")

                output_dir = os.path.join(self.output_dir, isp)
                os.makedirs(output_dir, exist_ok=True)

                output_path = os.path.join(output_dir, f"{region}.txt")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"{isp}-{region}-组播,#genre#\n")
                    f.write(playlists)

                logging.info(f"Created playlist file: {output_path}")

            self.merge_playlist(
                self.output_dir, os.path.join(self.output_dir, "全国.txt")
            )

    async def fetch_ip(self, search):
        form_data = {"saerch": search, "Submit": ""}
        # print(form_data)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Referer": "http://tonkiang.us/hoteliptv.php",
            "Cache-Control": "no-cache",
            # "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://tonkiang.us/hoteliptv.php",
                    data=form_data,
                    headers=headers,
                ) as response:
                    if response.status != 200:
                        logger.error(
                            f"Failed to fetch IPs for search '{search}', status code: {response.status}"
                        )
                        return []

                    content = await response.text()
                    soup = BeautifulSoup(content, "html.parser")
                    elements = soup.select("div.channel > a")

            ip_list = [element.text.strip() for element in elements]
            logger.info(f"Fetched IPs for search '{search}': {len(ip_list)}")
            return ip_list

        except Exception as e:
            logger.error(
                f"Exception occurred while fetching IPs for search '{search}': {e}"
            )
            return []

    async def get_rtp(self, ip):
        playlist = {}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://tonkiang.us/alllist.php?s={ip}&c=false",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
                        "Referer": "http://tonkiang.us/hoteliptv.php",
                        "Cache-Control": "no-cache",
                    },
                ) as response:
                    if response.status != 200:
                        logger.error(
                            f"Failed to get RTP for IP '{ip}', status code: {response.status}"
                        )
                        return {}

                    content = await response.text()
                    soup = BeautifulSoup(content, "html.parser")
                    elements = soup.select("div.tables")

                    for element in elements:
                        channel_elements = element.select("div.channel")
                        m3u8_elements = element.select("div.m3u8")

                        for channel, m3u8 in zip(channel_elements, m3u8_elements):
                            name = channel.text.strip()
                            url = m3u8.text.strip()

                            rtp_url = re.sub(
                                r"https?://[^/]+/(udp|rtp)/", "rtp://", url
                            )
                            playlist[name] = rtp_url

            logger.info(f"Playlist fetched for IP '{ip}': {len(playlist)}")
            return playlist

        except Exception as e:
            logger.error(f"Exception occurred while getting RTP for IP '{ip}': {e}")
            return {}

    async def init_rtp(self):
        for region in REGION_LIST:
            for isp_name, org_name in ISP_DICT.items():
                search = region[0:2] + isp_name[2:]
                ips = await self.fetch_ip(search)

                if not ips:
                    logger.warning(f"No IPs found for search '{search}'")
                    continue

                validated_ips = await self.validate_ip(ips, isp_name, region)

                self.save_ip(isp_name, region, validated_ips)

                for ip in ips:
                    playlist = await self.get_rtp(ip)
                    if playlist:
                        output_dir = os.path.join(RTP_DIR, isp_name)
                        os.makedirs(output_dir, exist_ok=True)

                        output_path = os.path.join(output_dir, f"{region}.txt")
                        with open(output_path, "w", encoding="utf-8") as f:
                            for name, url in playlist.items():
                                f.write(f"{name},{url}\n")

                        logger.info(
                            f"Playlist for region '{region}' and ISP '{isp_name}' saved to '{output_path}'"
                        )
                        break
