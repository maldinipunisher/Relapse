# Relapse — PS5 Jailbreak Host Clone (45.56.67.85)

> Target: host jailbreak PS5 "wobkot / etawen.dev" di `https://45.56.67.85`
> Tujuan project: reverse engineering exploit chain **Relapse** (FW 7.00–13.60) + infrastruktur menu/payload.
> Status legal: penelitian security-research / homebrew PS5, target publik yang memang dibuka untuk itu.

---

## Struktur Clone (`site/`)

```
site/
├── index.html                      # Redirector "etawen.dev" (daftar exploit + history localStorage)
├── relapse-menu/
│   └── index.html                  # Menu utama; probe loader @127.0.0.1:9021 (elfldr)
├── payloads/
│   ├── index.html                  # Menu payload (fetch payload_map.js, kirim via /x?uri=)
│   ├── payload_map.js              # Metadata ~45 payload (versi, author, FW, link ELF)
│   └── payloads/                   # 45 ELF payload TER-MIRROR (177 MB, semua 200 dari server)
└── wobkot/
    ├── index.html                  # Console UI exploit
    └── src/
        ├── main.js                 # Entry: deteksi PS4/PS5 dari UA
        ├── misc.js                 # BInt (64-bit arith), deteksi firmware, hex utils
        ├── userland.js             # addrof/fakeobj, mem utils, NativeFunction, syscalls table
        ├── kernel.js               # KernelView (kernel R/W via pipe), patch_proc, post_jailbreak
        ├── thread.js               # helper thread (dipakai lapse.js)
        ├── lapse.js                # Exploit FW < 6.00 [BELUM DIANALISIS]
        ├── ps4/
        │   ├── impl.js             # Impl PS4 (offsets) — server TIDAK punya src/ps4/payload.bin (404)
        │   └── payload.bin         # [TIDAK ADA DI SERVER]
        └── ps5/
            ├── impl.js             # Tabel offset per-FW: kernel, libkernel, WebKit ROP gadgets
            ├── relapse.js          # INTI EXPLOIT FW ≥ 6.00 (AIO UAF + AF_ROUTE leak + sysctl corruption)
            ├── kexp.bin            # Kernel exploit payload (binary shellcode) [BELUM DIANALISIS]
            └── elfldr.elf          # ELF loader PS5 (port 9021), FreeBSD x86-64 PIE, stripped
```

SHA-256 binary:
- `kexp.bin`  = `618f4b121cd26f2b259ade4fc3a69b3bdb631667758ae63fb9d316b4362015eb`
- `elfldr.elf` = `82f6227610172c98bad6efe68219fc93a10027035991f47eb4b75532d023407d`

## Arsitektur Chain

```
main.js
  → misc.js           (BInt util, parse UA "PlayStation 5/x.yz" — minor di-parse hex!)
  → ps5/impl.js       (offsets per FW 6.00–13.60, Proxy impl_cache dengan fallback minor)
  → ps5/relapse.js    (exploit_main → init, setup, leak_kaddrs, make_karw, cleanup)
  → userland.js       (arw: addrof/fakeobj + fake TypedArray → R/W WebKit heap)
  → kernel.js         (KernelView pipe-R/W, patch_proc rootfs+dynlib, post_jailbreak)
  → kexp.bin          (dijalankan via jitshm_create + pthread_create di WebKit; args: pipes, allproc, elfldr)
  → elfldr.elf        (loader persisten di 127.0.0.1:9021, terima ELF via /x?uri=)
```

## Temuan Analisis (per-file)

### ps5/relapse.js — inti exploit
1. **Infoleak** (`leak_kaddrs`): socket `AF_ROUTE`/`SOCK_RAW`; `route_output` tidak memvalidasi
   `sin_len` terhadap `sizeof(sockaddr_storage)` → kernel stack dibocorkan via `RTM_GET`.
   Dapat: `td` (thread), `so` (socket), `rtmsg2_ret` → **kernel base**.
2. **UAF arbitrary decrement** (`aio_uaf_arb_dec`): `aio_multi_wait` timeout → AIO MWait mutex
   di-free tapi `aio_batch+0x50` masih menunjuk (UAF). Spray `sendmsg` (0x100×, iov_base =
   target, iov[1] = `so_rcv.sb_mtx` valid) → `aio_multi_cancel` memicu decrement 1 byte.
3. **Kernel R/W via korupsi sysctl OID** (`make_karw`): korupsi `kern.smp.{cpus,maxcpus,topology}`:
   - `oid_kind` byte3 `0x80→0x7f` (CTLFLAG_WR|CTLFLAG_ANYBODY), `oid_enabled=1`
   - master cpus → tulis `oid_arg1` victim maxcpus (R/W terbatas di kernel .data)
   - master ke-2 (topology) mengontrol upper 32-bit → **arbitrary kernel R/W 64-bit**
   - pasangkan f_data dua pipe di `fdt_ofiles` → KernelView
   - restore OID ke kondisi asli setelah R/W map aktif (bersih)
4. `remove_uaf_waiter_from_aio`: bersihkan aio_waiter UAF dari aio_batch (naikkan aio_table)
   supaya `aio_multi_delete` tidak menolak (0x80020010).

### ps5/impl.js — offset table
- Per-FW: `k_sysctl___kern_smp_cpus`, `k_route_output_rtmsg2_ret` (anchor kernel base),
  `k_dynlib_status`, `k_stack_leak_td/so`, `k_aio_table`, `lk_close` (untuk syscall wrapper
  di lk_close+7), offsets struct WebKit (TypedArray mode/byteOffset, ArrayBuffer contents),
  dan ROP gadgets (POP_Rx, LEAVE_RET, MOV, PUSH...JMP).
- `impl` = Proxy dengan fallback minor (cari FW terdekat ≤ versi console).
- FW 6.00 ada sub-minor `2`; 7.xx sub `0x20`,`0x40`,`0x60`; dst.

### userland.js — WebKit R/W
- `addrof`: Leaker Proxy `super.foo` + getter 0x10000 properti + scope leak → alamat objek.
- `fakeobj` + fake container TypedArray (make_fake_container per-FW) → `arw` R/W heap.
- `mem.copy/bset` pakai `ArrayBuffer.from(addr, len)` (custom WebKit builtin? perlu verifikasi).

### kernel.js — KernelView & post-JB
- KernelView: pipe master/victim dipasangkan di level filedesc → baca/tulis kernel memory
  via pipe read/write biasa.
- `patch_proc`: fd_cdir/rdir/jdir = root vnode (full FS), dynlib start=0 end=-1 (dlsym), eboot.
- `post_jailbreak`: jitshm_create(0, sz, RWX) + mmap → copy kexp.bin → pthread_create →
  join. Args payload: [rp, wp, victim_rp, victim_wp, allproc, elfldr_addr, elfldr_size].
- SYSCORE_AUTHID = 0x4800000000000007.

### menu & infra
- `/relapse-menu/`: probe `fetch('http://127.0.0.1:9021/')` no-cors → deteksi sudah JB.
  Force http di PS5 (mixed-content). Controller nav via Gamepad API (D-pad, X=enter, O=back).
- `/payloads/`: filter payload per-FW pakai prefix `supportedFirmwares`; kirim ELF via
  `fetch('http://127.0.0.1:9021/x?uri=<server>/payloads/payloads/<file>.elf')`.
- Server: nginx/1.22.1, Cache-Control: no-store di menu. `/payloads` (no slash) 404.
- Catatan payload_map: beberapa `binarySource` menunjuk ke `soniciso1.github.io/relapse`
  dan `satanic.lol/payloads/payloads/*` (installers), bukan repo asli — perlu verifikasi hash.

---

## Testing

### server.py (test server lokal)
- `server.py` — HTTP :80 + HTTPS :443 (self-signed auto-gen ke `certs/` via openssl,
  SAN = hostname + IP LAN + 127.0.0.1). Port kustom: `python3 server.py 8080 8443`.
  - Header no-store/no-cache + CORS *; dir listing 403 (meniru nginx asli).
  - MIME: .elf/.bin = octet-stream, .js = application/javascript.
  - Jalankan sendiri via `sudo python3 server.py` (user run manual).
- **Auto-sync payload**: thread daemon refresh `payload_map.js` dari upstream
  (45.56.67.85) tiap 300 detik + download otomatis ELF yang belum ada di
  `payloads/payloads/`. Entri lokal dipisah di `site/payloads/local_payloads.js`
  (payload_map.js JANGAN diedit langsung — ditimpa saat sync). Force refresh
  manual: `GET /__sync`. Offline → fallback ke cache terakhir.
- `/` → 302 ke `/relapse-menu/` (flag `INDEX_REDIRECT_TO_MENU`, bisa dimatikan).
- Terverifikasi (port tes 8800/8443): semua endpoint 200, dir listing 403,
  nanodns.elf tersaji utuh di HTTP & HTTPS.

### Payload lokal
- `site/payloads/payloads/nanodns.elf` — terdaftar di payload_map.js
  (SHA-256 `fcfb7d47...680ef1fc5`, 132 KB, ELF x86-64 PIE stripped).
- `site/payloads/payloads/yt-adblock.elf` — terdaftar di payload_map.js
  (SHA-256 `b76b8e97...17170f25e`, 112 KB, ELF FreeBSD x86-64 PIE **not stripped**;
  sumber: `/Users/macbookairm1/Data/adblock_yt/yt-adblock.elf`).
  Keduanya terverifikasi tersaji via server.py (HTTP + HTTPS 200).

### Catatan PS5
- Halaman menu sudah auto-redirect https→http di browser PS5 (mixed-content untuk
  probe 127.0.0.1:9021), jadi HTTP cukup; HTTPS 443 tersedia jika dibutuhkan.
- elfldr di console mengambil ELF dari URI `location.host`, jadi akses PS5 harus
  langsung ke IP Mac (bukan localhost/port-forward).
- FW PS5 target ≥ 6.00 → chain relapse.js; FW < 6.00 → lapse.js (belum dianalisis).

### Self-host PKG "webview" (patch installer)
- Mekanisme installer home screen = **webview-style**: ELF installer berisi manifest JSON
  (`titleId` + `deeplinkUri` + `titleName`) yang di-install sebagai fakePKG. App dibuka →
  browser bawaan PS5 fullscreen membuka `deeplinkUri`. Confirmed via strings:
  `RLPS10001` → `http://45.56.67.85/relapse-menu/` (asli).
- `tools/patch_installers.py` — patch equal-length manifest (whitespace JSON dirapatkan
  sebagai padding, offset ELF tidak bergeser). Output:
  - `relapse-install-selfhost.elf` — titleId **RLPS10011**, deeplinkUri →
    `http://192.168.100.10/relapse-menu/` (menu Mac)
  - `relapse-direct-install-selfhost.elf` — titleId **RLPS10012**, deeplinkUri →
    `http://192.168.100.10/wobkot/` (exploit langsung)
- Keduanya terdaftar di local_payloads.js (map total 49 entri) dan verified 200.
- ⚠️ IP ter-bake (192.168.100.10). IP Mac berubah → jalankan ulang
  `python3 tools/patch_installers.py` (atau dengan argumen IP).
- Alur full self-host: install selfhost installer via payload menu → ikon home screen →
  buka webview → exploit dari Mac → elfldr → kirim payload dari menu.

## TODO / Next Steps

- [ ] Analisis `lapse.js` (exploit FW < 6.00, 35 KB) + `thread.js`
- [ ] Analisis `kexp.bin` (disasm — Ghidra/objdump) → map kernel payload & jalur exec ke elfldr
- [ ] Analisis `elfldr.elf` (FreeBSD PIE, stripped) → protokol `/x?uri=` dan port 9021
- [ ] Bedah `userland.js` penuh (bug WebKit persis yang dipakai: expm1 builtin, JIT leak)
- [ ] Bedah `kernel.js` penuh (KernelView internals, inc_karw_pipe_refcnt, find_all_proc)
- [ ] PS4 side: impl.js ada tapi payload.bin tidak di-host — cari sumber (repo upstream?)
- [ ] Mirror ELF payload dari /payloads/payloads/<file> bila diperlukan (ukuran besar)
- [ ] Bandingkan dengan repo publik: EchoStretch/kstuff-lite, PS5Dev/Byepervisor-Reborn,
      cragson/ps5-hen untuk identifikasi bug relapse versi upstream vs modifikasi host ini
- [ ] Rangkum chain ke satu dokumen arsitektur (diagram) di `notes/`

## Progress

- 2026-11-16: **Repo GitHub** — push ke https://github.com/maldinipunisher/Relapse
  (user: maldinipunisher). Deployment Pages lama (v3–v5: index.html, offsets/, src/,
  payloads/) dihapus dari repo per instruksi "timpa semua" — file tetap ada di disk lokal
  sebagai cadangan (untracked). `certs/` di-gitignore sejak awal (key TLS tidak pernah
  masuk history). Isi repo final: README.md, server.py, site/, tools/, progress.md.
  Catatan: kalau GitHub Pages repo ini masih aktif, sekarang tidak ada index.html di root
  → Pages 404; aktifkan kembali dengan meng-commit ulang file legacy bila mau restore.
- 2026-11-16: UI dibedakan dari upstream — badge "Self-Host" (hijau) + baris credit
  (earthonion, soniciso1 & PS5 scene) di /relapse-menu/ dan /payloads/. Ter-push ke GitHub.

- 2026-11-16: Initial inspect (menu, payloads, wobkot chain) selesai; semua JS + binary
  PS5 di-clone ke `site/`; analisis tahap-1 (relapse.js, impl.js, struktur) didokumentasikan di atas.
- 2026-11-16: `server.py` dibuat (HTTP:80 + HTTPS:443 self-signed auto-gen); nanodns.elf
  ditambahkan ke payload_map.js; verified di port tes 8800/8443. yt-adblock.elf PENDING
  (file belum ada di Downloads). User akan jalankan server sendiri via sudo (port 80/443).
- 2026-11-16: yt-adblock.elf ditemukan di `/Users/macbookairm1/Data/adblock_yt/`, dicopy ke
  payloads + didaftarkan; keduanya (nanodns & yt-adblock) verified 200 via HTTP/HTTPS.
  payload_map.js syntax-checked. Siap dites di PS5.
- 2026-11-16: Semua 43 ELF payload dari server (45 total termasuk 2 build lokal) di-download
  ke `site/payloads/payloads/` — 177 MB, semua HTTP 200, 0 file rusak/0-byte. Server.py
  diupdate: `/` → 302 `/relapse-menu/` (flag INDEX_REDIRECT_TO_MENU, masih bisa dikembalikan).
- 2026-11-16: Auto-sync payload ditambahkan ke server.py — payload_map.js refresh dari
  upstream tiap 5 menit + auto-download ELF baru; entri lokal (nanoDNS, yt-adblock)
  pindah ke local_payloads.js; endpoint /__sync untuk force refresh. Terverifikasi:
  47 entri map ter-serve, sync log "up-to-date (43 payload)".
- 2026-11-16: Self-host PKG webview-style dibuat — manifest JSON di relapse-install.elf &
  relapse-direct-install.elf dipatch equal-length ke IP Mac (192.168.100.10), titleId baru
  RLPS10011/10012; tools/patch_installers.py dibuat (re-runnable bila IP berubah);
  keduanya didaftarkan di local_payloads.js (49 entri) & verified 200.
- 2026-11-16: **GitHub Pages aktif lagi** — site/ di-deploy sebagai root repo
  (https://maldinipunisher.github.io/Relapse). Badge Self-Host + credit tampil live
  (verified HTTP 200, badge 2x di /relapse-menu/). Payload legacy v3-v5 tetap dihapus
  dari repo (untracked di disk); .nojekyll dikembalikan. Pages = HTTPS valid, cocok
  untuk PS5 tanpa self-signed warning; server.py lokal tetap untuk dev/testing.
- 2026-11-16: **Pages live penuh** — root `/` redirect ke `/relapse-menu/` (meta refresh +
  JS, karena Pages legacy tidak bisa server-side redirect). Verified live: root 200 (redirect),
  /relapse-menu/ 200 + badge Self-Host, /payloads/ 200, payload_map.js 200, ELF payload 206
  (range request OK). Catatan: API pages/builds/latest balik 404 terus (quirk legacy build)
  — pantau via HTTP check langsung, bukan API. 404 sebelumnya = build legacy belum selesai
  (repo ~200MB, build makan waktu beberapa menit) + cache CDN edge.
