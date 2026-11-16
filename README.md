# Relapse — PS5 Self-Host

Self-host server untuk exploit chain Relapse (PS5 FW 7.00–13.60) + payload manager.
Educational purposes / personal use only. Gunakan pada console milik sendiri.

## Isi

| Path | Keterangan |
|---|---|
| `server.py` | Server self-host: HTTP :80 + HTTPS :443 (self-signed otomatis), auto-sync payload dari upstream tiap 5 menit, `/__sync` force refresh |
| `site/` | Mirror situs Relapse — menu, exploit chain `wobkot` (FW ≥ 6: relapse.js / AIO UAF; FW < 6: lapse.js), 45 payload ELF |
| `site/payloads/local_payloads.js` | Entri payload lokal (nanoDNS, yt-adblock, installer self-host) |
| `tools/patch_installers.py` | Patch manifest installer → webview home screen menunjuk ke server sendiri |
| `progress.md` | Catatan reverse engineering & progress |

## Pemakaian

```bash
sudo python3 server.py            # HTTP 80 + HTTPS 443
# di PS5: http://<ip-mac>/        # auto-redirect ke /relapse-menu/
```

1. Jailbreak: menu → Jailbreak (chain wobkot) → elfldr aktif di console (:9021)
2. Payloads: menu → pilih payload → ELF dikirim ke loader console
3. Self-host permanen: kirim `Relapse Installer (Self-Host)` → ikon home screen
   membuka webview ke server Mac ini. Untuk offline penuh: Y2JB installer
   (jailbreak via splash cache app YouTube, FW 10–13.60).

## Catatan

- Entri `payload_map.js` di-refresh otomatis dari upstream; entri lokal di
  `local_payloads.js` — jangan edit `payload_map.js` langsung.
- IP ter-bake di installer self-host; IP berubah → `python3 tools/patch_installers.py`.
- `certs/` di-gitignore (key TLS).
