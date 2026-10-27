#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dong bo nguon SuperOK (da ma hoa .enc) -> input.m3u ca nhan cua Akendu.

Luong chay:
  1. Tai playlist.enc (thu worker Cloudflare truoc, du phong qua repo ENC1
     bang token nhung san trong app Super OK nhu app dang lam).
  2. Giai ma: file = Base64( IV[16] || AES-256-CBC/PKCS5 ), key = SHA-256(token).
     Token luu dang XOR-HEX giong het cach app Super OK luu trong APK.
  3. Loc theo dung luat Akendu da sua tay trong input.m3u hien tai:
     - Bo toan bo cac nhom trong BLOCK_GROUPS.
     - Bo 5 kenh Vinh Long goc cua nguon (da thay bang block ca nhan o tren cung).
  4. Chen block ca nhan "Vinh Long" (PERSONAL_BLOCK) len dau, giu nguyen
     thu tu + toan bo dong #KODIPROP/#EXTVLCOPT cua cac kenh con lai.
  5. Chi ghi de input.m3u khi noi dung thay doi.

Chay tay:  python sync.py            (ghi vao input.m3u cung thu muc)
           OUTPUT=khac.m3u python sync.py
Can: pip install pycryptodome
"""

import base64
import hashlib
import os
import re
import sys
import urllib.request
import urllib.error

from Crypto.Cipher import AES

# --- Khoa giai ma (luu dang ma hoa XOR giong trong APK Super OK) ---
_TOKEN_HEX = "6d3e633c6838623f6e396b3b6c6a696f3f623c6e3b6b3e6d396338683f6f3b6a623e693c6c396b3f633b68386e3c6d3f6a3e69396f38623b6b3c6e3f6d3e6839"
_token = bytes(b ^ 0x5A for b in bytes.fromhex(_TOKEN_HEX)).decode("utf-8")
_KEY = hashlib.sha256(_token.encode("utf-8")).digest()

# --- Token GitHub app Super OK dung de doc repo ENC1 (chi dung khi worker loi) ---
_PAT_HEX = "3c332b043d0a1a372d6a11361f30173a020110143d380f3f326e1d0b2a332f2f1c316a0911143230"
_PAT = bytes(b ^ 0x5B for b in bytes.fromhex(_PAT_HEX)).decode("utf-8")

WORKER_URL = "https://tv.ngoibut-cachmang.workers.dev/playlist.enc"
ENC1_URL = "https://api.github.com/repos/shoshjvn/ENC1/contents/playlist.enc"

# --- Luat loc cua Akendu (sua o day khi doi y) ---
BLOCK_GROUPS = {
    "🌟VIP SPORTS🌟",
    "Other",
    "🇸🇬 Mediacorp",
    "Cricket",
    "Football",
    "👌 UPDATE",
}
# 5 kenh Vinh Long goc cua nguon: bo di vi da co ban ca nhan ben duoi
DROP_TVG_IDS = {"vinhlong1hd", "vinhlong2hd", "vinhlong3hd", "vinhlong4hd", "vinhlong5hd", "update_info"}

# Thu tu nhom trong input.m3u cua Akendu (khac thu tu nguon o 2 cho:
# VIP MOVIE keo len sau SCTV, Nghe nhac day xuong cuoi).
# Trong tung nhom thi giu nguyen thu tu cua nguon.
# Nhom moi chua co trong danh sach nay se tu xep xuong cuoi.
GROUP_ORDER = [
    "🌟VTV & VTVCab🌟",
    "🌟VTV Go🌟",
    "🌟HTV🌟",
    "🌟SCTV🌟",
    "🌟VIP MOVIE🌟",
    "🌟Địa Phương🌟",
    "🌟Hoạt Hình🌟",
    "🌟Kênh Quốc Tế🌟",
    "Sự Kiện TV360",
    "🇻🇳 TV360 EVENTS",
    "Sự Kiện VTVPrime",
    "🎵 Nghe nhạc",
]

# --- Block ca nhan cua Akendu: 5 kenh Vinh Long (giu nguyen 100% nhu input.m3u hien tai) ---
PERSONAL_BLOCK = """#EXTINF:-1 tvg-id="vinhlong1hd" group-title="🌟Vĩnh Long🌟" tvg-logo="https://raw.githubusercontent.com/huyhq92/dataonly/main/pic/THVL1.webp",Vĩnh Long 1
#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K) (SMART-TV; LINUX; Tizen 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36
#KODIPROP:inputstream.adaptive.manifest_type=hls
https://freem3u.xyz/api/live/play.m3u8?vid=25
#EXTINF:-1 tvg-id="vinhlong2hd" group-title="🌟Vĩnh Long🌟" tvg-logo="https://raw.githubusercontent.com/huyhq92/dataonly/main/pic/THVL2.webp",Vĩnh Long 2
#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K) (SMART-TV; LINUX; Tizen 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36
#KODIPROP:inputstream.adaptive.manifest_type=hls
https://freem3u.xyz/api/live/play.m3u8?vid=26
#EXTINF:-1 tvg-id="vinhlong3hd" group-title="🌟Vĩnh Long🌟" tvg-logo="https://raw.githubusercontent.com/huyhq92/dataonly/main/pic/THVL3.webp",Vĩnh Long 3
#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K) (SMART-TV; LINUX; Tizen 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36
#KODIPROP:inputstream.adaptive.manifest_type=hls
https://freem3u.xyz/api/live/play.m3u8?vid=219
#EXTINF:-1 tvg-id="vinhlong4hd" group-title="🌟Vĩnh Long🌟" tvg-logo="https://raw.githubusercontent.com/huyhq92/dataonly/main/pic/THVL4.webp",Vĩnh Long 4
#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K) (SMART-TV; LINUX; Tizen 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36
#KODIPROP:inputstream.adaptive.manifest_type=hls
https://freem3u.xyz/api/live/play.m3u8?vid=220
#EXTINF:-1 tvg-id="vinhlong5hd" group-title="🌟Vĩnh Long🌟" tvg-logo="https://raw.githubusercontent.com/huyhq92/dataonly/main/pic/THVL5.webp",Vĩnh Long 5
#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K) (SMART-TV; LINUX; Tizen 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36
#KODIPROP:inputstream.adaptive.manifest_type=hls
https://freem3u.xyz/api/live/play.m3u8?vid=91"""

DEFAULT_HEADER = '#EXTM3U url-tvg="https://lichphatsong.io.vn/epgc.xml"'


def fetch_enc():
    """Thu worker truoc, du phong ENC1. Tra ve bytes cua file .enc."""
    errors = []
    # 1) Worker (khong can dang nhap)
    try:
        req = urllib.request.Request(WORKER_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if data and b"#EXTM3U" not in data[:20]:
            print(f"Worker OK: {len(data)} bytes")
            return data
        errors.append("worker tra ve du lieu la")
    except Exception as e:
        errors.append(f"worker: {e}")
    # 2) ENC1 qua token cua app
    try:
        req = urllib.request.Request(
            ENC1_URL,
            headers={
                "Authorization": f"token {_PAT}",
                "User-Agent": "SuperOK",
                "Accept": "application/vnd.github.raw+json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        print(f"ENC1 OK: {len(data)} bytes")
        return data
    except Exception as e:
        errors.append(f"enc1: {e}")
    raise RuntimeError("Khong tai duoc playlist.enc | " + " ; ".join(errors))


def decrypt(data: bytes) -> str:
    raw = base64.b64decode(data.strip())
    pt = AES.new(_KEY, AES.MODE_CBC, raw[:16]).decrypt(raw[16:])
    pad = pt[-1]
    if 1 <= pad <= 16 and pt[-pad:] == bytes([pad]) * pad:
        pt = pt[:-pad]
    return pt.decode("utf-8")


def parse_entries(text: str):
    """Tra ve (header, [entry]) - moi entry la list cac dong goc, giu nguyen van."""
    header = DEFAULT_HEADER
    entries = []
    cur = None
    for line in text.splitlines():
        if line.startswith("#EXTM3U"):
            header = line.strip()
        elif line.startswith("#EXTINF"):
            cur = [line]
            entries.append(cur)
        elif cur is not None:
            cur.append(line)
            if line.strip().startswith("http"):
                cur = None
    # Bo entry hong (khong co URL)
    return header, [e for e in entries if any(l.strip().startswith("http") for l in e)]


def entry_group(extinf: str) -> str:
    m = re.search(r'group-title="([^"]*)"', extinf)
    return m.group(1) if m else ""


def entry_tvg(extinf: str) -> str:
    m = re.search(r'tvg-id="([^"]*)"', extinf)
    return m.group(1) if m else ""


def build(text: str) -> str:
    header, entries = parse_entries(text)
    kept, dropped = [], 0
    for e in entries:
        if entry_group(e[0]) in BLOCK_GROUPS or entry_tvg(e[0]) in DROP_TVG_IDS:
            dropped += 1
            continue
        kept.append(e)
    rank = {g: i for i, g in enumerate(GROUP_ORDER)}
    kept.sort(key=lambda e: rank.get(entry_group(e[0]), len(rank)))  # sort on dinh: giu thu tu nguon trong nhom
    out = [header]
    out.extend(PERSONAL_BLOCK.splitlines())
    for e in kept:
        out.extend(e)
    print(f"Nguon: {len(entries)} kenh -> bo {dropped}, giu {len(kept)} + 5 ca nhan = {len(kept) + 5} kenh")
    return "\n".join(out) + "\n"


def main():
    dst = os.environ.get("OUTPUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "input.m3u"))
    text = decrypt(fetch_enc())
    if not text.startswith("#EXTM3U"):
        print("Giai ma khong ra M3U - dung lai, khong ghi de file cu.")
        return 1
    result = build(text)
    old = None
    if os.path.exists(dst):
        with open(dst, encoding="utf-8") as f:
            old = f.read()
    if old == result:
        print("input.m3u chua thay doi - khong can cap nhat.")
        return 0
    with open(dst, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"Da cap nhat {dst}: {len(result)} ky tu, {result.count('#EXTINF')} kenh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
