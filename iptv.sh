#!/bin/sh

# Directory for m3u files
M3U_DIR=m3u

# Create m3u directory if it doesn't exist
mkdir -p "$M3U_DIR"

rm "$M3U_DIR/ipv6.m3u"
wget https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u -O "$M3U_DIR/ipv6.m3u"

# 央视源
rm "$M3U_DIR/CCTV.m3u"
wget https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u -O "$M3U_DIR/CCTV.m3u"
sed -i -n '/央视频道/,+1p' "$M3U_DIR/CCTV.m3u"
sed -i '1i #EXTM3U' "$M3U_DIR/CCTV.m3u"
sed -i '/^\s*$/d' "$M3U_DIR/CCTV.m3u"

# 卫视源
rm "$M3U_DIR/CNTV.m3u"
for keyword in "卫视频道" "数字频道"; do
  wget https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u -O "$M3U_DIR/temp.m3u"
  sed -i -n "/$keyword/,+1p" "$M3U_DIR/temp.m3u"
  cat "$M3U_DIR/temp.m3u" >> "$M3U_DIR/CNTV.m3u"
  rm -f "$M3U_DIR/temp.m3u"
done
sed -i '1i #EXTM3U' "$M3U_DIR/CNTV.m3u"
sed -i '/^\s*$/d' "$M3U_DIR/CNTV.m3u"

# 整合源
rm "$M3U_DIR/IPTV.m3u"
cat "$M3U_DIR/CCTV.m3u" "$M3U_DIR/CNTV.m3u" > "$M3U_DIR/IPTV.m3u"
sed -i '/#EXTM3U/d' "$M3U_DIR/IPTV.m3u"
sed -i '1i #EXTM3U' "$M3U_DIR/IPTV.m3u"
sed -i '/^\s*$/d' "$M3U_DIR/IPTV.m3u"

# 节目源
# rm EPG.xml
# wget https://epg.112114.xyz/pp.xml -O EPG.xml