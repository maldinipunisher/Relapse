// Entri payload lokal — digabungkan ke payload_map.js oleh server.py (auto-sync).
// Jangan edit payload_map.js langsung; dia ditimpa dari upstream.
payload_map.push({
    displayTitle: "nanoDNS",
    description: "DNS server payload (local ad-block / custom DNS resolver).",
    fileName: "nanodns.elf",
    author: "local",
    projectSource: "",
    binarySource: "local build (~/Downloads/nanodns.elf)",
    version: "1.0",
    toPort: 9021
});
payload_map.push({
    displayTitle: "Relapse Installer (Self-Host)",
    description: "Installs Relapse home screen app (webview-style) — opens this Mac's server instead of the remote host.",
    fileName: "relapse-install-selfhost.elf",
    author: "earthonion (patched local)",
    projectSource: "https://github.com/earthonion/np-fake-signin",
    binarySource: "patched from relapse-install.elf (deeplinkUri -> http://192.168.100.10/relapse-menu/, titleId RLPS10011)",
    version: "1.0-selfhost",
    toPort: 9021
});
payload_map.push({
    displayTitle: "Relapse Direct (Self-Host)",
    description: "Installs home screen app that runs the exploit directly from this Mac's server (no menu).",
    fileName: "relapse-direct-install-selfhost.elf",
    author: "earthonion (patched local)",
    projectSource: "https://github.com/earthonion/np-fake-signin",
    binarySource: "patched from relapse-direct-install.elf (deeplinkUri -> http://192.168.100.10/wobkot/, titleId RLPS10012)",
    version: "1.0-selfhost",
    toPort: 9021
});
payload_map.push({
    displayTitle: "YouTube Adblock",
    description: "Ad-blocker payload for the YouTube app (local build from ~/Data/adblock_yt).",
    fileName: "yt-adblock.elf",
    author: "local",
    projectSource: "",
    binarySource: "local build (/Users/macbookairm1/Data/adblock_yt/yt-adblock.elf)",
    version: "1.0",
    toPort: 9021
});
