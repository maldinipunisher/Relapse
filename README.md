educational purposes only
## Struktur

- `index.html`, `offsets/`, `src/`, `payloads/`, `payloads.json` — GitHub Pages exploit host (deployment lama, v3–v5)
- `site/` — mirror lengkap situs Relapse (menu, wobkot exploit chain, 45 payload ELF) untuk self-host
- `server.py` — server self-host (HTTP 80 + HTTPS 443 self-signed, auto-sync payload dari upstream tiap 5 menit)
- `tools/patch_installers.py` — patch manifest installer agar webview home screen menunjuk ke server sendiri
- `progress.md` — catatan reverse engineering & progress

## Pemakaian self-host

```
sudo python3 server.py          # lalu di PS5: http://<ip-mac>/
```
