import argparse
import asyncio
import logging

from iptv.hotel import Hotel
from iptv.udpxy import UDPxy

logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="IP fetching and playlist generation script")
    parser.add_argument("--ip", action="store_true", help="Fetch valid IPs")
    parser.add_argument("--playlist", action="store_true", help="Generate playlists from valid IPs")
    parser.add_argument("--rtp", action="store_true", help="Init rtp")
    parser.add_argument("--type", choices=["hotel", "udpxy"], required=True, help="Type of IP to process")
    args = parser.parse_args()

    if args.rtp:
        await UDPxy().init_rtp()
        return

    if args.ip:
        if args.type == "hotel":
            await Hotel().sniff_ip()
        elif args.type == "udpxy":
            await UDPxy().sniff_ip()
    elif args.playlist:
        if args.type == "hotel":
            await Hotel().generate_playlist()
        elif args.type == "udpxy":
            await UDPxy().generate_playlist()
    else:
        logging.error("You must specify an action: --ip or --playlist.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    asyncio.run(main())
