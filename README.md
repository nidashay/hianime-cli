# 🎬 HiAnime CLI Player

<div align="center">

![HiAnime CLI](https://img.shields.io/badge/HiAnime-CLI%20Player-pink?style=for-the-badge&logo=anime&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white)
![MPV](https://img.shields.io/badge/MPV-Player-orange?style=for-the-badge&logo=mpv&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

*A beautiful terminal-based anime player that streams directly from HiAnime with real .m3u8 extraction, Cloudflare bypass, and seamless browser fallback.*

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Smart Search** | Search any anime with fuzzy matching |
| 📺 **Episode Browser** | Browse all episodes with titles |
| 🌐 **Dual Audio** | Choose **Dub (English)** or **Sub (Japanese)** at startup |
| 🔓 **Real Stream Extraction** | Decrypts vidnest API to get actual `.m3u8` URLs |
| ☁️ **Cloudflare Detection** | Auto-detects protected CDNs (`cinewave2`, `streamzone`, `mewstream`) |
| 🌐 **Seamless Fallback** | Opens embed page in browser when MPV can't play |
| 🔄 **Retry Logic** | 3-attempt exponential backoff for flaky connections |
| 🎯 **Proper Headers** | Referer/Origin injection for all known anime hosts |

---

## 🚀 Quick Start

```bash
# Clone & setup
git clone https://github.com/nidashay/hianime-cli
cd hianime-cli

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run!
python main.py
```

---

## 📖 Usage Guide

### 1. Select Language
```
? Select language: (Use arrow keys)
  » Dub (English)
    Sub (Japanese)
```
Choose **Dub** for English audio, **Sub** for Japanese with subtitles.

### 2. Search Anime
```
? Search for an anime (or 'q' to quit): Solo Leveling
```

### 3. Pick Series
```
? Select an anime: (Use arrow keys)
  » Solo Leveling Season 2 -Arise from the Shadow- (N/A)
    Solo Leveling (N/A)
```

### 4. Choose Episode
```
? Select an episode: (Use arrow keys)
  » Ep 1: I'm used to it
    Ep 2: ...
    Ep 3: ...
    Back to search
```

### 5. Watch! 🎬

**If MPV can play directly:**
```
✓ Direct stream detected - playing with mpv
Launching player for: Solo Leveling - Ep 1: I'm used to it
```

**If Cloudflare-protected (auto browser fallback):**
```
☁ Detected Cloudflare-protected CDN (cdn.mewstream.buzz)
⚠ mpv/yt-dlp cannot bypass Cloudflare anti-bot protection
──▶ Opening embed page in browser for playback...
Opened: https://vidnest.fun/anime/176496/1/dub
Use the video player on the page to watch.
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      HiAnime CLI Player                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐  │
│  │  Search  │───▶│ Episodes │───▶│  Stream Extraction   │  │
│  │  (retry) │    │  (retry) │    │  ┌────────────────┐  │  │
│  └──────────┘    └──────────┘    │  │ Vidnest API    │  │  │
│                                  │  │ + Decryption   │  │  │
│                                  │  └────────────────┘  │  │
│                                  └──────────┬────────────┘  │
│                                             │               │
│                    ┌────────────────────────┴────────┐      │
│                    ▼                                 ▼      │
│         ┌─────────────────┐              ┌────────────────┐  │
│         │   Direct .m3u8  │              │  Cloudflare CDN │  │
│         │   ▶ MPV + Headers│              │   ▶ Browser    │  │
│         └─────────────────┘              └────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Technical Details

### Stream Extraction Pipeline

1. **Fetch Watch Page** → Extract `anilistId` + server list
2. **Filter by Language** → Keep only `/dub` or `/sub` servers
3. **Try Each Server**:
   - **vidnest** → Call `new.vidnest.fun/hianime/anime/{id}/{ep}/sub`
   - **tryembed** → Extract `RAW_PAYLOAD` → Call `/api/stream_data`
   - **megacloud** → Uses Ryu ID from megaplay.buzz
4. **Decrypt Response** → Custom base64 alphabet + gzip decompression
5. **Return .m3u8** → Real CDN URL with proper Referer

### Vidnest Decryption

```python
# Custom base64 alphabet (64 chars) + padding char
KEY_STR = "RB0fpH8ZEyVLkv7c2i6MAJ5u3IKFDxlS1NTsnGaqmXYdUrtzjwObCgQP94hoeW+/="

# Decrypt → gzip decompress → JSON parse
sources = decrypted["sources"]  # [{file: "https://cdn.xxx/master.m3u8", ...}]
```

### Supported Hosts

| Type | Hosts | Referer |
|------|-------|---------|
| **Embed Portals** | vidnest.fun, tryembed.us.cc, megacloud.* | hianime.ms |
| **CDN (Cloudflare)** | cinewave2.site, streamzone*.site, mewstream.buzz | aniwaves.ru |
| **Direct** | Any `.m3u8`/`.mp4` | Auto-detected |

---

## 📁 Project Structure

```
hianime-cli/
├── main.py          # CLI entry point, search/episode flow, language selection
├── scraper.py       # HiAnime scraping + vidnest API + decryption
├── player.py        # MPV wrapper, Cloudflare detection, browser fallback
├── requirements.txt # Dependencies
├── .gitignore       # Excludes venv, __pycache__, IDE files
└── README.md        # This file
```

---

## 📋 Requirements

- **Python 3.10+**
- **MPV** (system package)

| OS | Install MPV |
|----|-------------|
| Ubuntu/Debian | `sudo apt install mpv` |
| Arch Linux | `sudo pacman -S mpv` |
| Fedora | `sudo dnf install mpv` |
| macOS | `brew install mpv` |
| Windows | `winget install mpv` |

### Python Dependencies

```txt
requests>=2.31.0
beautifulsoup4>=4.12.0
questionary>=2.0.1
```

---

## 🎌 Screenshots

<div align="center">

**Language Selection**
```
? Select language: (Use arrow keys)
  » Dub (English)
    Sub (Japanese)
```

**Search & Select**
```
? Search for an anime (or 'q' to quit): Spy x Family
? Select an anime: (Use arrow keys)
  » SPY×FAMILY (HD)
    SPY×FAMILY Season 2 (HD)
```

**Episode Browser**
```
? Select an episode: (Use arrow keys)
  » Ep 1: Operation Strix
    Ep 2: Secure a Wife
    Ep 3: Prepare for the Interview
    Back to search
```

**Stream Extraction & Playback**
```
Trying to extract stream from vidnest (Volt)...
  ✓ Found m3u8: https://cdn.mewstream.buzz/anime/xxx/master.m3u8
Using server: Volt
Stream URL: https://cdn.mewstream.buzz/anime/xxx/master.m3u8
Referer: https://aniwaves.ru/
✓ Direct stream detected - playing with mpv
  ☁ Detected Cloudflare-protected CDN (cdn.mewstream.buzz)
  ──▶ Opening embed page in browser for playback...
  Opened: https://vidnest.fun/anime/12345/1/dub
```

</div>

---

## ⚠️ Known Limitations

| Limitation | Workaround |
|------------|------------|
| Cloudflare CDNs block MPV/yt-dlp | Auto-opens embed page in browser |
| tryembed API returns 403 sometimes | Falls back to vidnest |
| Subtitles not shown in MPV for embed pages | Use browser player (has sub menu) |
| Requires internet connection | N/A |

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Ideas for Contributions
- [ ] Episode auto-advance (next/prev)
- [ ] Subtitle track selection in MPV
- [ ] Quality selector (1080p/720p/480p)
- [ ] Download option (yt-dlp)
- [ ] History/favorites (local JSON)
- [ ] AniList/MyAnimeList integration
- [ ] TUI with textual/rich

---

## 📜 License

MIT License - feel free to use, modify, distribute.

---

## ⚖️ Disclaimer

> **This tool is for educational purposes only.**
> 
> Streaming copyrighted content may violate terms of service of the source website. Please support official releases when possible. The author is not responsible for any misuse.

---

## 🙏 Credits

- **HiAnime** - Source website
- **vidnest.fun** - Video hosting (API reverse-engineered)
- **MPV** - Best media player ever
- **yt-dlp** - For inspiration on extractor patterns
- **Questionary** - Beautiful CLI prompts

---

<div align="center">

**Made with 💖 by [nidashay](https://github.com/nidashay)**

*Happy watching! 🍿✨*

</div>