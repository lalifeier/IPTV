import logging
import os
import re
import time
from hashlib import md5
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from iptv.config import OUTPUT_DIR

logger = logging.getLogger(__name__)

IPTV_URL = "https://proxy.lalifeier.eu.org/https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u"
M3U_DIR = "m3u"
TXT_DIR = "txt"
SALT = os.getenv("SALT", "")
PROXY_URL = os.getenv("PROXY_URL", "")


def read_file_content(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""

def write_to_file(file_path, content):
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
    except Exception as e:
        print(f"Error writing to file {file_path}: {e}")


def extract_ids(url):
    match = re.search(r"/([^/]+)/([^/]+)\.[^/]+$", url)
    return match.groups() if match else (None, None)


def get_sign_url(url):
    if PROXY_URL:
        url = url.replace("https://127.0.0.1:8080", PROXY_URL)

    channel_id, video_id = extract_ids(url)
    if not channel_id or not video_id:
        raise ValueError("Invalid URL format")

    timestamp = str(int(time.time()))
    key = md5(f"{channel_id}{video_id}{timestamp}{SALT}".encode("utf-8")).hexdigest()

    parsed_url = urlparse(url)
    query = dict(parse_qsl(parsed_url.query))
    query.update({"t": timestamp, "key": key})

    return urlunparse(parsed_url._replace(query=urlencode(query)))


def txt_to_m3u(content):
    result = ""
    genre = ""

    for line in content.split("\n"):
        line = line.strip()
        if "," not in line:
            continue

        channel_name, channel_url = line.split(",", 1)
        if channel_url == "#genre#":
            genre = channel_name
        else:
            if "127.0.0.1:8080" in channel_url:
                channel_url = get_sign_url(channel_url)

            result += (
                f'#EXTINF:-1 tvg-logo="https://proxy.lalifeier.eu.org/https://raw.githubusercontent.com/linitfor/epg/main/logo/{channel_name}.png" '
                f'group-title="{genre}",{channel_name}\n{channel_url}\n'
            )

    return result


def m3u_to_txt(m3u_content):
    lines = m3u_content.strip().split("\n")[1:]
    output_dict = {}
    group_name = ""

    url_pattern = re.compile(r'\b(?:http|https|rtmp)://[^\s]+', re.IGNORECASE)

    for line in lines:
        if line.startswith("#EXTINF"):
            if(len(line.split('group-title="')) > 1):
              group_name = line.split('group-title="')[1].split('"')[0]
            channel_name = line.split(",")[-1]
        elif url_pattern.match(line):
            channel_link = line
            output_dict.setdefault(group_name, []).append(f"{channel_name},{channel_link}")

    output_lines = [f"{group},#genre#\n" + "\n".join(links) for group, links in output_dict.items()]
    return "\n".join(output_lines)


def main():
    os.makedirs(M3U_DIR, exist_ok=True)
    os.makedirs(TXT_DIR, exist_ok=True)

    update_local_iptv_txt()

    # iptv_response = requests.get(IPTV_URL)
    # m3u_content = iptv_response.text

    # write_to_file(os.path.join(M3U_DIR, "ipv6.m3u"), m3u_content)

    # m3u_content = read_file_content(os.path.join(M3U_DIR, "ipv6.m3u"))

    live_m3u_content = '#EXTM3U\n'

    for channel in ['douyu', 'huya', 'yy', 'douyin', 'bilibili', 'afreecatv', 'pandatv', 'flextv', 'twitch']:
        try:
            M3U_URL = f"{PROXY_URL}/{channel}/index.m3u?_={int(time.time() * 1000)}"
            if channel in ['afreecatv', 'pandatv', 'twitch'] and not PROXY_URL:
                continue

            if not PROXY_URL:
                M3U_URL = f"https://proxy.lalifeier.eu.org/https://raw.githubusercontent.com/lalifeier/IPTV/main/m3u/{channel}.m3u"

            m3u_content = requests.get(M3U_URL).text
            channel_id = urlparse(M3U_URL).path.split('/')[1]

            if channel not in ['afreecatv', 'pandatv', 'flextv', 'twitch']:
              write_to_file(os.path.join(M3U_DIR, channel_id + '.m3u'), m3u_content)
              logger.info(f"Successfully downloaded and saved M3U file for channel {channel_id}")

            live_m3u_content += '\n'.join(m3u_content.split('\n')[1:]) + '\n'

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download M3U file for channel {channel_id}: {e}")
        except Exception as e:
            logger.error(f"An error occurred while processing M3U file for channel {channel_id}: {e}")

    write_to_file(os.path.join(M3U_DIR, 'Live.m3u'), live_m3u_content)
    logger.info("Successfully merged and saved Live.m3u file")

    generate_youtube_txt()

    playlists = {
        "Hot": file_to_m3u("Hot.txt"),
        "CCTV": file_to_m3u("CCTV.txt"),
        "CNTV": file_to_m3u("CNTV.txt"),
        "Shuzi": file_to_m3u("Shuzi.txt"),
        "NewTV": file_to_m3u("NewTV.txt"),
        "iHOT": file_to_m3u("iHOT.txt"),
        # "SITV": file_to_m3u("SITV.txt"),
        "Movie": file_to_m3u("Movie.txt"),
        "Sport": file_to_m3u("Sport.txt"),
        "MiGu": file_to_m3u("MiGu.txt"),
        "Maiduidui": file_to_m3u("maiduidui.txt"),
        "lunbo.txt": file_to_m3u("lunbo.txt"),
        "HK": file_to_m3u("hk.txt"),
        "TW": file_to_m3u("tw.txt"),
        "YouTube": file_to_m3u("YouTube.txt"),
        "YouTube2": file_to_m3u("YouTube2.txt"),
        "Local": file_to_m3u("Local.txt"),
        "LiveChina": file_to_m3u("LiveChina.txt"),
        "Panda": file_to_m3u("Panda.txt"),
        "Documentary": file_to_m3u("Documentary.txt"),
        "Chunwan": file_to_m3u("Chunwan.txt"),
        "fm": file_to_m3u("fm.txt"),
        "Animated": file_to_m3u("Animated.txt"),
        "About": file_to_m3u("About.txt"),
    }

    iptv_m3u = "".join(playlists.values()) + '\n'
    # update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # update_m3u = txt_to_m3u(f"更新时间,#genre#\n{update_time},\n")

    live_m3u = '\n'.join(live_m3u_content.split('\n')[1:]) + '\n'

    write_m3u_to_file(os.path.join(M3U_DIR, "IPTV.m3u"), iptv_m3u + live_m3u)

    iptv_txt = m3u_to_txt(read_file_content(os.path.join(M3U_DIR, "IPTV.m3u")))
    write_to_file(os.path.join(TXT_DIR, "IPTV.txt"), iptv_txt)


def file_to_m3u(file_name):
    file_path = os.path.join(TXT_DIR, file_name)
    content = read_file_content(file_path)
    return txt_to_m3u(content)


def write_m3u_to_file(file_path, content):
    header = (
        '#EXTM3U x-tvg-url="https://proxy.lalifeier.eu.org/https://raw.githubusercontent.com/lalifeier/IPTV/main/e.xml"\n'
    )
    write_to_file(file_path, header + content.strip())

def update_local_iptv_txt():
    logging.info("Starting to update local IPTV txt files.")

    # try:
    #     # Fetch and convert IPTV M3U content to TXT format
    #     iptv_response = requests.get(IPTV_URL)
    #     iptv_response.raise_for_status()
    #     iptv_m3u_content = iptv_response.text
    #     iptv_txt_content = m3u_to_txt(iptv_m3u_content)
    #     logging.info("Successfully fetched and converted IPTV content.")
    # except requests.exceptions.RequestException as e:
    #     logging.error(f"Error fetching IPTV content: {e}")
    #     return

    def update_line(channel_name, current_url, suffix, suffix_type):
        province = suffix[1:3]
        isp = suffix[3:5]
        file_name = os.path.join(OUTPUT_DIR, suffix_type, f"中国{isp}", f"{province}.txt")
        try:
            udpxy_content = read_file_content(file_name)
        except FileNotFoundError:
            logging.error(f"File not found: {file_name}")
            return None

        pattern = re.compile(rf"^{re.escape(channel_name)},(http[^\s]+)", re.MULTILINE)
        match = pattern.search(udpxy_content)
        if match:
            new_url = match.group(1)
            logging.info(f"Updating URL for {channel_name}: {new_url}")
            return f"{channel_name},{new_url}${province}{isp}{suffix[-2:]}\n"
        return None

    for file_name in os.listdir(OUTPUT_DIR):
        if file_name.endswith('.txt') and file_name not in ['IPTV.txt']:
            file_path = os.path.join(OUTPUT_DIR, file_name)
            logging.info(f"Processing file: {file_name}")

            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                logging.info(f"Successfully read {file_name}.")
            except OSError as e:
                logging.error(f"Error reading file {file_name}: {e}")
                continue

            updated_lines = []
            for line in lines:
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    channel_name, current_url = parts
                    updated_line = None

                    if current_url.endswith('酒店'):
                        suffix_match = re.search(r'\$(.+)酒店$', current_url)
                        if suffix_match:
                            updated_line = update_line(channel_name, current_url, suffix_match.group(0), "hotel")

                    elif current_url.endswith('组播'):
                        suffix_match = re.search(r'\$(.+)组播$', current_url)
                        if suffix_match:
                            updated_line = update_line(channel_name, current_url, suffix_match.group(0), "udpxy")

                    # elif file_name in ['CCTV.txt', 'CNTV.txt', 'Shuzi.txt', 'NewTV.txt']:
                    #     pattern = re.compile(rf"^{re.escape(channel_name)},(http[^\s]+)", re.MULTILINE)
                    #     match = pattern.search(iptv_txt_content)
                    #     if match:
                    #         new_url = match.group(1)
                    #         logging.info(f"Updating URL for {channel_name}: {new_url}")
                    #         updated_line = f"{channel_name},{new_url}\n"

                    if updated_line:
                        line = updated_line

                updated_lines.append(line)

            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.writelines(updated_lines)
                logging.info(f"Successfully updated {file_name}.")
            except OSError as e:
                logging.error(f"Error writing to file {file_name}: {e}")

    logging.info("Finished updating all files.")

def generate_youtube_txt():
    try:
        logging.info("Fetching README.md from GitHub...")
        response = requests.get("https://proxy.lalifeier.eu.org/https://raw.githubusercontent.com/ChiSheng9/iptv/refs/heads/master/README.md")
        response.raise_for_status()
        logging.info("README.md fetched successfully.")

        content = response.text

        # logging.info("Replacing text pattern...")
        # pattern = r'(TV\d+),(.+)'
        # replacement = r'\2,https://raw.githubusercontent.com/ChiSheng9/iptv/master/\1.m3u8'
        # text = re.sub(pattern, replacement, content)
        # logging.info("Text pattern replaced successfully.")

        # text = text.replace('  ', '')
        lines = content.splitlines()
        output_lines = []
        for line in lines:
            line = line.strip()
            if line:
                match = re.match(r"(TV\d+),(.*)", line)
                if match:
                    channel_id = match.group(1)
                    channel_name = match.group(2)
                    new_line = f"{channel_name},https://raw.githubusercontent.com/ChiSheng9/iptv/master/{channel_id}.m3u8"
                    output_lines.append(new_line)

        text = "\n".join(output_lines)

        text = """
YouTube「代理」,#genre#
""" + text

        logging.info("Writing to Youtube.txt...")
        write_to_file(os.path.join(TXT_DIR, "YouTube2.txt"), text)
        logging.info("Youtube.txt written successfully.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching README.md: {e}")
    except Exception as e:
        logging.error(f"Error generating Youtube.txt: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    main()
