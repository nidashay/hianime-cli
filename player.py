import subprocess
import shlex
from urllib.parse import urlparse


# CDN domains known to use Cloudflare anti-bot protection
CLOUDFLARE_CDN_DOMAINS = [
    "cinewave2.site",
    "streamzone1.site",
    "streamzone2.site",
    "animep2p.site",
    "mewstream.buzz",
    "aniwaves.ru",
]


def is_cloudflare_protected(url):
    """Check if URL is on a Cloudflare-protected CDN."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return any(domain in host for domain in CLOUDFLARE_CDN_DOMAINS)


class AnimePlayer:
    def __init__(self, player_cmd="mpv"):
        self.player_cmd = player_cmd

    def _is_embed_url(self, url):
        """Check if URL is an embed page (not a direct stream)."""
        embed_domains = [
            "vidnest.fun",
            "tryembed.us.cc",
            "megacloud.tv",
            "megacloud.blog",
            "megacloud.click",
            "vidhidepro.com",
            "vidhidevip.com",
            "animension.org",
            "streamani.net",
        ]
        return any(domain in url for domain in embed_domains)

    def _is_direct_stream(self, url):
        """Check if URL is a direct video stream."""
        return url.endswith((".m3u8", ".mp4", ".mkv", ".webm", ".ts"))

    def _build_mpv_cmd(self, url, title=None, referer=None, headers=None, disable_ytdl=False):
        """
        Build mpv command with proper headers for anime streaming.
        
        Args:
            url: Stream URL (m3u8, mp4, etc.)
            title: Window title
            referer: Referer header (CRITICAL for most anime hosts)
            headers: Dict of additional headers
            disable_ytdl: If True, disable yt-dlp hook (useful for embed pages)
        """
        cmd = [self.player_cmd]
        
        # Window/title settings
        cmd.extend([
            "--force-window",
            f"--title={title or 'Anime Player'}",
        ])
        
        # Disable yt-dlp for embed pages (they're not supported)
        if disable_ytdl or self._is_embed_url(url):
            cmd.append("--ytdl=no")
            print("  Note: Disabled yt-dlp for embed page (using native demuxer)")
        
        # Network/streaming optimizations
        cmd.extend([
            # Better HLS/m3u8 handling
            "--demuxer-lavf-o=protocol_whitelist=[file,crypto,data,tcp,udp,rtp,https,tls,http]",
            # Larger cache for smoother streaming
            "--cache=yes",
            "--cache-secs=60",
            "--cache-pause=yes",
            # Timeout settings
            "--network-timeout=30",
            # User agent (for initial connection)
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ])
        
        # Build http-header-fields for the stream request
        header_fields = []
        
        # Referer is CRITICAL for most anime streaming hosts
        if referer:
            header_fields.append(f"Referer: {referer}")
        
        # Add custom headers
        if headers:
            for key, value in headers.items():
                header_fields.append(f"{key}: {value}")
        
        # Add Origin based on referer if not explicitly provided
        if referer and "Origin" not in (headers or {}):
            parsed = urlparse(referer)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            header_fields.append(f"Origin: {origin}")
        
        # Apply headers if any
        if header_fields:
            # mpv expects headers as a single string with \r\n separation
            header_string = "\r\n".join(header_fields) + "\r\n"
            cmd.append(f"--http-header-fields={header_string}")
        
        # The stream URL (must be last)
        cmd.append(url)
        
        return cmd

    def play(self, url, title=None, referer=None, headers=None, embed_fallback_url=None):
        """
        Play a stream URL with mpv.

        Args:
            url: Stream URL (m3u8, mp4, etc.)
            title: Window title
            referer: Referer header (e.g., "https://hianime.ms/")
            headers: Additional headers dict (e.g., {"Cookie": "..."})
            embed_fallback_url: If provided, will open this URL in browser if mpv fails
            
        Returns:
            True if playback started successfully, False otherwise
        """
        if not url:
            print("No URL provided for playback.")
            return False

        # Check for Cloudflare-protected CDN - skip mpv, go straight to browser
        if is_cloudflare_protected(url):
            print(f"  ☁ Detected Cloudflare-protected CDN ({urlparse(url).netloc})")
            print(f"  ⚠ mpv/yt-dlp cannot bypass Cloudflare anti-bot protection")
            if embed_fallback_url:
                print(f"  ──▶ Opening embed page in browser for playback...")
                import webbrowser
                webbrowser.open(embed_fallback_url)
                print(f"  Opened: {embed_fallback_url}")
                print(f"  Use the video player on the page to watch.")
                return True
            else:
                print(f"  No embed fallback URL provided.")
                return False

        print(f"Launching player for: {title if title else url}")
        if referer:
            print(f"  Using Referer: {referer}")

        # For embed pages, we need special handling
        is_embed = self._is_embed_url(url)
        is_direct = self._is_direct_stream(url)

        if is_embed and not is_direct:
            print(f"  ⚠ Detected embed page (not a direct stream)")
            print(f"  Trying with yt-dlp disabled...")

        cmd = self._build_mpv_cmd(url, title, referer, headers)

        try:
            # Run mpv - it handles its own event loop
            result = subprocess.run(cmd)

            if result.returncode != 0:
                print(f"\nPlayer exited with code {result.returncode}")
                if is_embed:
                    print("  Embed pages usually don't work directly in mpv.")
                    print("  The video player on the embed page loads the actual stream via JavaScript.")
                print("Common issues:")
                print("  - Stream requires Referer/Origin headers")
                print("  - Stream expired or geo-blocked")
                if embed_fallback_url:
                    print(f"  ──▶ Opening embed page in browser...")
                    import webbrowser
                    webbrowser.open(embed_fallback_url)
                    return True
                print(f"  - Try opening in browser: {url}")
                return False

            return True

        except FileNotFoundError:
            print(f"Error: '{self.player_cmd}' not found. Please install mpv.")
            print("  Ubuntu/Debian: sudo apt install mpv")
            print("  Arch: sudo pacman -S mpv")
            print("  Fedora: sudo dnf install mpv")
            print("  macOS: brew install mpv")
            return False
        except KeyboardInterrupt:
            print("\nPlayback interrupted.")
            return True  # User interrupted, not an error
        except Exception as e:
            print(f"An error occurred while playing: {e}")
            if embed_fallback_url:
                print(f"  ──▶ Opening embed page in browser...")
                import webbrowser
                webbrowser.open(embed_fallback_url)
                return True
            print(f"Try opening this URL in your browser: {url}")
            return False

    def play_in_browser(self, url):
        """Open URL in default browser."""
        import webbrowser
        print(f"Opening in browser: {url}")
        webbrowser.open(url)
        return True


# Convenience function for common anime hosts
def get_headers_for_host(url):
    """Return recommended headers for known anime streaming hosts."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    
    host_configs = {
        # Embed/portal hosts
        "vidnest.fun": {"referer": "https://hianime.ms/"},
        "megacloud.tv": {"referer": "https://hianime.ms/"},
        "megacloud.blog": {"referer": "https://hianime.ms/"},
        "megacloud.click": {"referer": "https://hianime.ms/"},
        "megaplay.buzz": {"referer": "https://hianime.ms/"},
        "vidhidepro.com": {"referer": "https://hianime.ms/"},
        "vidhidevip.com": {"referer": "https://hianime.ms/"},
        "animension.org": {"referer": "https://hianime.ms/"},
        "streamani.net": {"referer": "https://hianime.ms/"},
        "vidcdn.pro": {"referer": "https://hianime.ms/"},
        "vidcdn.xyz": {"referer": "https://hianime.ms/"},
        "tryembed.us.cc": {"referer": "https://hianime.ms/"},
        
        # Actual CDN/video hosts (discovered from decrypted API)
        "cinewave2.site": {"referer": "https://aniwaves.ru/"},
        "streamzone1.site": {"referer": "https://aniwaves.ru/"},
        "streamzone2.site": {"referer": "https://aniwaves.ru/"},
        "animep2p.site": {"referer": "https://aniwaves.ru/"},
        "aniwaves.ru": {"referer": "https://aniwaves.ru/"},
    }
    
    for domain, config in host_configs.items():
        if domain in host:
            return config
    
    # Default fallback
    return {"referer": "https://hianime.ms/"}