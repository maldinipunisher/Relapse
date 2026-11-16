#!/usr/bin/env python3
"""
Relapse PS5 test server — HTTP (port 80) + HTTPS (port 443, self-signed).

Menjalankan mirror situs jailbreak (site/) untuk testing di PS5.

Pemakaian:
    sudo python3 server.py          # HTTP :80  + HTTPS :443 (default)
    python3 server.py 8080 8443     # port kustom (HTTP HTTPS), tanpa root

Catatan PS5:
  - Browser PS5 menolak sertifikat self-signed di beberapa firmware; kalau halaman
    https gagal dibuka, pakai http. Halaman menu sudah otomatis memaksa http di PS5.
  - Cert self-signed di-generate otomatis ke certs/ (CN = hostname) via openssl.
  - Menu /payloads/ mengirim ELF ke loader console lewat http://127.0.0.1:9021/x?uri=...
    dan URI memakai location.host, jadi PS5 harus mengakses lewat IP Mac ini langsung.
"""

import functools
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.join(BASE_DIR, "site")
CERTS_DIR = os.path.join(BASE_DIR, "certs")
CERT_FILE = os.path.join(CERTS_DIR, "server.crt")
KEY_FILE = os.path.join(CERTS_DIR, "server.key")

DEFAULT_HTTP_PORT = 80
DEFAULT_HTTPS_PORT = 443

# Sementara: / dan /index.html di-redirect ke menu Relapse.
# Set False untuk kembali ke redirector asli (etawen.dev style).
INDEX_REDIRECT_TO_MENU = True

MENU_PATH = "/relapse-menu/"

# --- Auto-sync payload dari upstream ---------------------------------------
# payload_map.js = upstream cache + local_payloads.js (digabung saat sync).
# Payload ELF yang belum ada di payloads/payloads/ di-download otomatis.
UPSTREAM_BASE = os.environ.get("RELAPSE_UPSTREAM", "https://45.56.67.85")
PAYLOADS_DIR = os.path.join(SITE_DIR, "payloads")
PAYLOADS_BIN_DIR = os.path.join(PAYLOADS_DIR, "payloads")
UPSTREAM_MAP_URL = UPSTREAM_BASE + "/payloads/payload_map.js"
MAP_CACHE = os.path.join(PAYLOADS_DIR, "payload_map.js")
LOCAL_MAP = os.path.join(PAYLOADS_DIR, "local_payloads.js")
SYNC_TTL = 300  # detik antar-sync

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

_map_lock = threading.Lock()
_last_sync = 0.0
_sync_status = "belum pernah sync"


def _fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "relapse-sync/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
        return r.read()


def sync_payloads(force=False):
    """Refresh payload_map.js dari upstream + download ELF yang belum ada."""
    global _last_sync, _sync_status
    with _map_lock:
        if not force and time.time() - _last_sync < SYNC_TTL:
            return
        _last_sync = time.time()

    try:
        src = _fetch(UPSTREAM_MAP_URL).decode("utf-8", "replace")
    except Exception as e:
        _sync_status = f"upstream gagal: {e} (pakai cache lokal)"
        print(f"[sync] {_sync_status}", flush=True)
        return

    os.makedirs(PAYLOADS_BIN_DIR, exist_ok=True)

    # gabung: upstream + entri lokal (menu evaluasi via new Function(...),
    # payload_map.push() setelah deklarasi const tetap valid)
    merged = src
    if os.path.exists(LOCAL_MAP):
        with open(LOCAL_MAP, "r", encoding="utf-8") as f:
            merged = src + "\n" + f.read()

    tmp = MAP_CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(merged)
    os.replace(tmp, MAP_CACHE)

    # generate payloads.json (untuk deliverPayloads metode direct) dari merged map
    map_names = [n for n in re.findall(r'fileName:\s*"([^"]*)"', merged) if n]
    seen, ordered = set(), []
    for n in map_names:
        if n not in seen:
            seen.add(n)
            ordered.append(n)
    pj = os.path.join(PAYLOADS_DIR, "payloads.json")
    with open(pj + ".tmp", "w") as f:
        json.dump({"mandatory": [], "optional": ordered}, f, indent=2)
    os.replace(pj + ".tmp", pj)

    # download payload yang belum ada secara lokal
    names = {n for n in re.findall(r'fileName:\s*"([^"]*)"', src) if n}
    have = set(os.listdir(PAYLOADS_BIN_DIR))
    missing = sorted(names - have)

    ok, fail = 0, 0
    for name in missing:
        try:
            url = UPSTREAM_BASE + "/payloads/payloads/" + urllib.parse.quote(name)
            data = _fetch(url, timeout=600)
            with open(os.path.join(PAYLOADS_BIN_DIR, name), "wb") as f:
                f.write(data)
            print(f"[sync] payload baru: {name} ({len(data)} bytes)", flush=True)
            ok += 1
        except Exception as e:
            print(f"[sync] gagal download {name}: {e}", flush=True)
            fail += 1

    if missing:
        _sync_status = f"{len(missing)} payload baru ({ok} ok, {fail} gagal)"
    else:
        _sync_status = f"up-to-date ({len(names)} payload terdaftar)"
    print(f"[sync] {_sync_status}", flush=True)


def sync_loop():
    while True:
        try:
            sync_payloads()
        except Exception as e:
            print(f"[sync] error tak terduga: {e}", flush=True)
        time.sleep(SYNC_TTL)


class NoCacheHandler(SimpleHTTPRequestHandler):
    """Static handler + header no-cache agar PS5 browser tidak pakai versi lama."""

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".elf": "application/octet-stream",
        ".bin": "application/octet-stream",
        ".map": "application/json",
    }

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def list_directory(self, path):
        """Directory listing dimatikan (mengikuti nginx asli yang 403)."""
        self.send_error(403, "Directory listing forbidden")
        return None

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/__sync":
            sync_payloads(force=True)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            super().end_headers()
            self.wfile.write(f"sync status: {_sync_status}\n".encode())
            return
        if INDEX_REDIRECT_TO_MENU and path.rstrip("/") in ("", "/index.html"):
            self.send_response(302)
            self.send_header("Location", MENU_PATH)
            super().end_headers()  # includes no-cache/CORS headers
            return
        super().do_GET()

    def do_HEAD(self):
        if INDEX_REDIRECT_TO_MENU and self.path.rstrip("/") in ("", "/index.html"):
            self.send_response(302)
            self.send_header("Location", MENU_PATH)
            super().end_headers()
            return
        super().do_HEAD()


def ensure_selfsigned_cert():
    """Generate self-signed cert (SAN = hostname + IP lokal) bila belum ada."""
    os.makedirs(CERTS_DIR, exist_ok=True)
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return

    hostname = socket.gethostname()
    local_ip = get_local_ip()

    subj = f"/CN={hostname}"
    san = f"DNS:{hostname},IP:{local_ip},IP:127.0.0.1"
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", KEY_FILE, "-out", CERT_FILE,
        "-days", "825", "-subj", subj,
        "-addext", f"subjectAltName={san}",
    ]
    print(f"[*] Generating self-signed cert (CN={hostname}, SAN={san}) ...")
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        os.chmod(KEY_FILE, 0o600)
        print(f"[+] Cert  : {CERT_FILE}")
        print(f"[+] Key   : {KEY_FILE}")
    except FileNotFoundError:
        print("[!] openssl tidak ditemukan — HTTPS akan dilewati, hanya HTTP yang jalan.")
    except subprocess.CalledProcessError as e:
        print(f"[!] openssl gagal: {e.stderr.decode().strip()} — HTTPS dilewati.")


def make_server(port, handler, use_tls=False):
    class Server(ThreadingHTTPServer):
        allow_reuse_address = True

    httpd = Server(("0.0.0.0", port), handler)
    if use_tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(CERT_FILE, KEY_FILE)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    return httpd


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    http_port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_HTTP_PORT
    https_port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_HTTPS_PORT

    if http_port < 1024 and hasattr(os, "geteuid") and os.geteuid() != 0:
        print(f"[!] Port {http_port} < 1024 butuh root: sudo python3 {sys.argv[0]}")
        print("    atau port tinggi: python3 {} 8080 8443".format(sys.argv[0]))

    ensure_selfsigned_cert()

    # thread auto-sync payload (daemon: mati saat server mati)
    threading.Thread(target=sync_loop, daemon=True).start()

    handler = functools.partial(NoCacheHandler, directory=SITE_DIR)
    servers = []

    # HTTP
    try:
        servers.append(make_server(http_port, handler))
    except (PermissionError, OSError) as e:
        print(f"[!] HTTP  :{http_port} gagal: {e}")

    # HTTPS (hanya kalau cert tersedia)
    has_cert = os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)
    if has_cert:
        try:
            servers.append(make_server(https_port, handler, use_tls=True))
        except (PermissionError, OSError) as e:
            print(f"[!] HTTPS :{https_port} gagal: {e}")
    else:
        print("[!] HTTPS dilewati (cert tidak tersedia).")

    if not servers:
        print("[!] Tidak ada server yang bisa start.")
        sys.exit(1)

    ip = get_local_ip()
    scheme_note = "  (PS5: kalau https ditolak, pakai http)"
    print("=" * 60)
    print("  Relapse PS5 Test Server")
    print("=" * 60)
    print(f"  Site dir  : {SITE_DIR}")
    for s in servers:
        proto = "HTTPS" if isinstance(s.socket, ssl.SSLSocket) else "HTTP  "
        print(f"  {proto} : 0.0.0.0:{s.server_address[1]}")
    url = f"http://{ip}/" if http_port == 80 else f"http://{ip}:{http_port}/"
    surl = f"https://{ip}/" if https_port == 443 else f"https://{ip}:{https_port}/"
    print(f"  URL PS5   : {url}")
    if has_cert:
        print(f"              {surl}{scheme_note}")
    print("-" * 60)
    print("  Menu      : /relapse-menu/   Exploit: /wobkot/   Payloads: /payloads/")
    print("  Sync      : otomatis tiap %d detik; paksa manual -> /__sync" % SYNC_TTL)
    print("=" * 60)
    print("[i] PS5 harus satu subnet dengan Mac ini.")
    print("[i] Jalankan exploit dulu sampai elfldr aktif (port 9021 di console),")
    print("    lalu buka menu Payloads untuk mengirim ELF.")

    try:
        threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in servers]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n[*] Server dimatikan.")
        for s in servers:
            s.server_close()


if __name__ == "__main__":
    main()
