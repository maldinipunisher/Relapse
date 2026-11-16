// Entri payload lokal — digabungkan ke payload_map.js oleh server.py (auto-sync).
// Jangan edit payload_map.js langsung; dia ditimpa dari upstream.
payload_map.push({
    displayTitle: "nanoDNS",
    description: "DNS server payload (local ad-block / custom DNS resolver) by drakmor.",
    fileName: "nanodns.elf",
    author: "drakmor",
    projectSource: "https://github.com/drakmor/nanodns",
    binarySource: "local copy (~/Downloads/nanodns.elf)",
    version: "0.4",
    toPort: 9021
});
payload_map.push({
    displayTitle: "Relapse Installer (Self-Host)",
    description: "Installs Relapse home screen app (webview-style) — opens this Mac's server instead of the remote host.",
    fileName: "relapse-install-selfhost.elf",
    author: "earthonion (patched local)",
    projectSource: "https://github.com/earthonion/np-fake-signin",
    binarySource: "patched from relapse-install.elf (deeplinkUri -> https://maldinipunisher.github.io/Relapse/relapse-menu/, titleId RLPS10011)",
    version: "1.0-selfhost",
    toPort: 9021
});
payload_map.push({
    displayTitle: "Relapse Direct (Self-Host)",
    description: "Installs home screen app that runs the exploit directly from this Mac's server (no menu).",
    fileName: "relapse-direct-install-selfhost.elf",
    author: "earthonion (patched local)",
    projectSource: "https://github.com/earthonion/np-fake-signin",
    binarySource: "patched from relapse-direct-install.elf (deeplinkUri -> https://maldinipunisher.github.io/Relapse/wobkot/, titleId RLPS10012)",
    version: "1.0-selfhost",
    toPort: 9021
});
payload_map.push({
    displayTitle: "Relapse Installer (LAN)",
    description: "Home screen app (webview-style) — opens the local Mac server via raw IP (no DNS needed pre-jailbreak).",
    fileName: "relapse-install-lan.elf",
    author: "earthonion (patched local)",
    projectSource: "https://github.com/earthonion/np-fake-signin",
    binarySource: "patched from relapse-install.elf (deeplinkUri -> http://192.168.100.10/relapse-menu/, titleId RLPS10011)",
    version: "1.0-lan",
    toPort: 9021
});
payload_map.push({
    displayTitle: "Relapse Direct (LAN)",
    description: "Home screen app that runs the exploit directly from the local Mac server via raw IP (no DNS needed).",
    fileName: "relapse-direct-install-lan.elf",
    author: "earthonion (patched local)",
    projectSource: "https://github.com/earthonion/np-fake-signin",
    binarySource: "patched from relapse-direct-install.elf (deeplinkUri -> http://192.168.100.10/wobkot/, titleId RLPS10012)",
    version: "1.0-lan",
    toPort: 9021
});
payload_map.push({
    displayTitle: "YouTube Adblock",
    description: "Ad-blocker payload for the YouTube app. YT Adblocker v0.01.",
    fileName: "yt-adblock.elf",
    author: "maldinipunisher",
    projectSource: "",
    binarySource: "local build (/Users/macbookairm1/Data/adblock_yt/yt-adblock.elf)",
    version: "0.01",
    toPort: 9021
});
