#!/usr/bin/env python3
"""
Patch installer Relapse (relapse-install.elf / relapse-direct-install.elf)
agar deeplinkUri-nya menunjuk ke server self-host, bukan 45.56.67.85.

Mekanisme: installer meng-install fakePKG di home screen PS5 yang berisi
manifest JSON (titleId + deeplinkUri). Saat app dibuka, browser bawaan PS5
(fullscreen "webview") membuka deeplinkUri. Patch dilakukan equal-length
(whitespace JSON dirapatkan, sisanya dijadikan padding) supaya offset &
panjang payload lain di ELF tidak bergeser.

Pemakaian:
    python3 tools/patch_installers.py            # pakai IP LAN otomatis
    python3 tools/patch_installers.py 10.0.0.5   # pakai IP spesifik

Hasil: site/payloads/payloads/relapse-install-selfhost.elf (menu relapse)
       site/payloads/payloads/relapse-direct-install-selfhost.elf (exploit langsung)
"""

import os
import re
import socket
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAYLOAD_DIR = os.path.join(HERE, "..", "site", "payloads", "payloads")

TARGETS = [
    {
        "src": "relapse-install.elf",
        "old_uri": "http://45.56.67.85/relapse-menu/",
        "old_tid": "RLPS10001",
        "new_tid": "RLPS10011",
        "path": "/relapse-menu/",  # halaman menu (jailbreak + payloads)
    },
    {
        "src": "relapse-direct-install.elf",
        "old_uri": "http://45.56.67.85/relapse/",
        "old_tid": "RLPS10002",
        "new_tid": "RLPS10012",
        "path": "/wobkot/",  # halaman exploit langsung
    },
]

# Base URL self-host. Default: GitHub Pages (HTTPS valid, tidak butuh Mac online).
# Override: python3 patch_installers.py [base_url_atau_IP]
#   contoh: python3 patch_installers.py 192.168.100.10          → IP lokal (port 80)
#           python3 patch_installers.py https://foo.github.io/X → base URL lain
DEFAULT_BASE = "https://maldinipunisher.github.io/Relapse"


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def patch(fname, old_uri, new_uri, old_tid, new_tid):
    data = open(fname, "rb").read()
    m = re.search(rb'\{\n    "titleId": "[^"]+".*?\n\}\n', data, re.S)
    if not m:
        raise SystemExit(f"[-] manifest tidak ditemukan di {fname}")

    manifest = m.group(0)
    new_text = manifest.decode().replace(old_uri, new_uri).replace(old_tid, new_tid)
    new_text = re.sub(r'\n {2,}"', '\n"', new_text)  # rapikan indentasi JSON
    diff = len(manifest) - len(new_text)
    if diff < 0:
        raise SystemExit(
            f"[-] {fname}: manifest baru lebih panjang {diff} byte — "
            f"URI/IP terlalu panjang untuk dipatch equal-length."
        )
    new_text = new_text[:-3] + "\n" + " " * diff + "}\n"
    assert len(new_text) == len(manifest)

    out = fname.replace(".elf", "-selfhost.elf")
    open(out, "wb").write(data.replace(manifest, new_text.encode()))
    print(f"[+] {os.path.basename(fname)} -> {os.path.basename(out)}")
    print(f"    {new_uri}  (titleId {new_tid})")


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg:
        # argumen: IP (→ http://ip:80) atau URL lengkap (https://...)
        base = f"http://{arg}" if re.match(r'^[\d.]+$', arg) else arg.rstrip("/")
    else:
        base = DEFAULT_BASE
    print(f"[*] Self-host base: {base}")
    for t in TARGETS:
        src = os.path.join(PAYLOAD_DIR, t["src"])
        if not os.path.exists(src):
            print(f"[!] skip {t['src']} (tidak ada)")
            continue
        patch(
            src,
            t["old_uri"],
            base + t["path"],
            t["old_tid"],
            t["new_tid"],
        )
    print("[i] URI ter-bake ke base ini. Base berubah → jalankan ulang script ini.")


if __name__ == "__main__":
    main()
