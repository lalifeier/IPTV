import asyncio
import base64
import json
import logging
import os
import random
import re
from typing import List

import aiohttp
from pypinyin import lazy_pinyin

from iptv.base import Base
from iptv.config import IP_DIR, ISP_DICT, OUTPUT_DIR, REGION_LIST

logger = logging.getLogger(__name__)


def is_province(region):
    return region in REGION_LIST


def clean_name(name):
    # 清洗名称的函数，根据需要自行添加清洗规则
    name = name.replace("中央", "CCTV")
    name = name.replace("高清", "")
    name = name.replace("超清", "")
    name = name.replace("HD", "")
    name = name.replace("标清", "")
    name = name.replace("超高", "")
    name = name.replace("频道", "")
    name = name.replace("-", "")
    name = name.replace(" ", "")
    name = name.replace("PLUS", "+")
    name = name.replace("＋", "+")
    name = name.replace("(", "")
    name = name.replace(")", "")
    name = name.replace("（", "")
    name = name.replace("）", "")
    name = name.replace("L", "")
    name = name.replace("CMIPTV", "")
    name = name.replace("cctv", "CCTV")
    name = re.sub(r"CCTV(\d+)台", r"CCTV\1", name)
    name = name.replace("CCTV1综合", "CCTV1")
    name = name.replace("CCTV2财经", "CCTV2")
    name = name.replace("CCTV3综艺", "CCTV3")
    name = name.replace("CCTV4国际", "CCTV4")
    name = name.replace("CCTV4中文国际", "CCTV4")
    name = name.replace("CCTV4欧洲", "CCTV4")
    name = name.replace("CCTV5体育", "CCTV5")
    name = name.replace("CCTV5+体育", "CCTV5+")
    name = name.replace("CCTV6电影", "CCTV6")
    name = name.replace("CCTV7军事", "CCTV7")
    name = name.replace("CCTV7军农", "CCTV7")
    name = name.replace("CCTV7农业", "CCTV7")
    name = name.replace("CCTV7国防军事", "CCTV7")
    name = name.replace("CCTV8电视剧", "CCTV8")
    name = name.replace("CCTV8纪录", "CCTV9")
    name = name.replace("CCTV9记录", "CCTV9")
    name = name.replace("CCTV9纪录", "CCTV9")
    name = name.replace("CCTV10科教", "CCTV10")
    name = name.replace("CCTV11戏曲", "CCTV11")
    name = name.replace("CCTV12社会与法", "CCTV12")
    name = name.replace("CCTV13新闻", "CCTV13")
    name = name.replace("CCTV新闻", "CCTV13")
    name = name.replace("CCTV14少儿", "CCTV14")
    name = name.replace("央视14少儿", "CCTV14")
    name = name.replace("CCTV少儿超", "CCTV14")
    name = name.replace("CCTV15音乐", "CCTV15")
    name = name.replace("CCTV音乐", "CCTV15")
    name = name.replace("CCTV16奥林匹克", "CCTV16")
    name = name.replace("CCTV17农业农村", "CCTV17")
    name = name.replace("CCTV17军农", "CCTV17")
    name = name.replace("CCTV17农业", "CCTV17")
    name = name.replace("CCTV5+体育赛视", "CCTV5+")
    name = name.replace("CCTV5+赛视", "CCTV5+")
    name = name.replace("CCTV5+体育赛事", "CCTV5+")
    name = name.replace("CCTV5+赛事", "CCTV5+")
    name = name.replace("CCTV5+体育", "CCTV5+")
    name = name.replace("CCTV5赛事", "CCTV5+")
    name = name.replace("凤凰中文台", "凤凰中文")
    name = name.replace("凤凰资讯台", "凤凰资讯")
    name = name.replace("CCTV4K测试）", "CCTV4")
    name = name.replace("CCTV164K", "CCTV16")
    name = name.replace("上海东方卫视", "上海卫视")
    name = name.replace("东方卫视", "上海卫视")
    name = name.replace("内蒙卫视", "内蒙古卫视")
    name = name.replace("福建东南卫视", "东南卫视")
    name = name.replace("广东南方卫视", "南方卫视")
    name = name.replace("金鹰卡通卫视", "金鹰卡通")
    name = name.replace("湖南金鹰卡通", "金鹰卡通")
    name = name.replace("炫动卡通", "哈哈炫动")
    name = name.replace("卡酷卡通", "卡酷少儿")
    name = name.replace("卡酷动画", "卡酷少儿")
    name = name.replace("BRTVKAKU少儿", "卡酷少儿")
    name = name.replace("优曼卡通", "优漫卡通")
    name = name.replace("优曼卡通", "优漫卡通")
    name = name.replace("嘉佳卡通", "佳嘉卡通")
    name = name.replace("世界地理", "地理世界")
    name = name.replace("CCTV世界地理", "地理世界")
    name = name.replace("BTV北京卫视", "北京卫视")
    name = name.replace("BTV冬奥纪实", "冬奥纪实")
    name = name.replace("东奥纪实", "冬奥纪实")
    name = name.replace("卫视台", "卫视")
    name = name.replace("湖南电视台", "湖南卫视")
    name = name.replace("2金鹰卡通", "金鹰卡通")
    name = name.replace("湖南教育台", "湖南教育")
    name = name.replace("湖南金鹰纪实", "金鹰纪实")
    name = name.replace("少儿科教", "少儿")
    name = name.replace("影视剧", "影视")
    return name


class Hotel(Base):
    def __init__(self):
        super().__init__()
        self.ip_dir = os.path.join(IP_DIR, "hotel")
        self.output_dir = os.path.join(OUTPUT_DIR, "hotel")

    def generate_search_url(self, region, isp_name, org_name):
        pinyin_name = "".join(lazy_pinyin(region, errors=lambda x: x))
        if is_province(region):
            search_txt = f'"iptv/live/zh_cn.js" && country="CN" && region="{pinyin_name}" && org="{org_name}"'
        elif not is_province(region):
            search_txt = f'"iptv/live/zh_cn.js" && country="CN" && city="{pinyin_name}" && org="{org_name}"'
        else:
            return None

        bytes_string = search_txt.encode("utf-8")
        encoded_search_txt = base64.b64encode(bytes_string).decode("utf-8")
        return f"https://fofa.info/result?qbase64={encoded_search_txt}"

    async def validate_ip(self, ip: List[str]) -> List[str]:
        if not ip:
            logging.warning("No valid IPs to validate.")
            return []

        validated_ip = []

        tasks = [
            self.is_url_accessible(f"http://{ip_address}/iptv/live/1000.json?key=txiptv")
            for ip_address in ip
        ]

        for ip_address, valid in zip(ip, await asyncio.gather(*tasks)):
            if valid:
                validated_ip.append(ip_address)

        logging.info(f"Validated {len(ip)} IPs. Found {len(validated_ip)} valid IPs.")
        return validated_ip

    async def sniff_ip(self):
        for region in REGION_LIST:
            for isp_name, org_name in ISP_DICT.items():
                url = self.generate_search_url(region, isp_name, org_name)
                content = await self.fetch_page_content(url)

                if not content:
                    logging.warning(f"Empty content for region {region}. Skipping...")
                    continue

                ip = await self.extract_ip_from_content(content)

                # ip_ports = set()
                # for ip_port in ip:
                #     ip_address, port = ip_port.split(":")
                #     for i in range(1, 256):  # 第四位从1到255
                #         ip_ports.add(f"{ip_address.rsplit('.', 1)[0]}.{i}:{port}")

                validated_ips = await self.validate_ip(ip)

                self.save_ip(isp_name, region, validated_ips)

    async def _generate_playlist(self, ips) -> str:
        if not ips:
          return ""

        ip_playlists = {}

        async with aiohttp.ClientSession() as session:
            for ip in ips:
                url = f"http://{ip}/iptv/live/1000.json?key=txiptv"
                try:
                    async with session.get(url, timeout=3) as response:
                        if response.status == 200:
                            json_data = await response.json()
                            programs = []

                            for item in json_data.get("data", []):
                                if isinstance(item, dict):
                                    name = item.get("name", "")
                                    chid = str(item.get("chid")).zfill(4)
                                    srcid = item.get("srcid")
                                    if name and chid and srcid:
                                        name = clean_name(name)
                                        m3u8_url = f"http://{ip}/tsfile/live/{chid}_{srcid}.m3u8"
                                        programs.append((name, m3u8_url))

                            ip_playlists[ip] = programs
                            logging.info(f"Processed {len(programs)} programs from IP {ip}")

                except aiohttp.ClientError as e:
                    logging.error(f"Failed to fetch data from {url}. Error: {e}")
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse JSON from {url}. Error: {e}")
                except Exception as e:
                    logging.error(f"Unexpected error occurred for URL {url}. Error: {e}")

        if not ip_playlists:
            return ""

        async def check_random_urls(urls):
            for url in urls:
                if self.is_video_stream_valid(url):
                    return True
            return False

        best_ip = None
        best_count = 0

        for ip, programs in ip_playlists.items():
            sampled_urls = [url for _, url in random.sample(programs, min(len(programs), 3))]

            if await check_random_urls(sampled_urls):
                if len(programs) > best_count:
                    best_ip = ip
                    best_count = len(programs)

        if best_ip:
            best_playlist = "\n".join(f"{name},{url}" for name, url in ip_playlists[best_ip])
            return best_playlist

        return ""

    async def generate_playlist(self):
        # if os.path.exists(self.output_dir):
        #   shutil.rmtree(self.output_dir)

        os.makedirs(self.output_dir, exist_ok=True)
        for region in REGION_LIST:
            for isp_name, org_name in ISP_DICT.items():
                ip = self.get_ip(isp_name, region)

                if not ip:
                    logging.warning(f"No IP available for {region}. Skipping...")
                    continue

                playlists = await self._generate_playlist(ip)

                if not playlists:
                  continue

                output_dir = os.path.join(self.output_dir, isp_name)
                os.makedirs(output_dir, exist_ok=True)

                output_path = os.path.join(output_dir, f"{region}.txt")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"{isp_name}-{region}-酒店,#genre#\n")

                    f.write(playlists)

                logging.info(f"Created playlist file: {output_path}")

        self.merge_playlist(self.output_dir, os.path.join(self.output_dir, "全国.txt"))
