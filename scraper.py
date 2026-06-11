import requests
from bs4 import BeautifulSoup
import re
import base64
import json
import urllib.parse
import gzip

BASE_URL = "https://hianime.ms"

# Vidnest API decryption key (used as custom base64 alphabet)
VIDNEST_KEY_STR = "RB0fpH8ZEyVLkv7c2i6MAJ5u3IKFDxlS1NTsnGaqmXYdUrtzjwObCgQP94hoeW+/="
VIDNEST_CUSTOM_ALPHABET = VIDNEST_KEY_STR[:64]
VIDNEST_PAD_CHAR = VIDNEST_KEY_STR[64]
VIDNEST_CHAR_TO_VAL = {ch: i for i, ch in enumerate(VIDNEST_CUSTOM_ALPHABET)}


def vidnest_decrypt(encrypted_b64):
    """Decrypt vidnest API response using custom base64 alphabet + gzip."""
    # Custom base64 decode
    result = bytearray()
    i = 0
    data = encrypted_b64
    while i < len(data):
        chunk = data[i:i+4]
        i += 4
        while len(chunk) < 4:
            chunk += VIDNEST_PAD_CHAR
        vals = []
        for ch in chunk:
            if ch in VIDNEST_CHAR_TO_VAL:
                vals.append(VIDNEST_CHAR_TO_VAL[ch])
            elif ch == VIDNEST_PAD_CHAR:
                vals.append(64)
            else:
                vals.append(0)
        combined = (vals[0] << 18) | (vals[1] << 12) | (vals[2] << 6) | vals[3]
        result.append((combined >> 16) & 0xFF)
        if vals[2] != 64:
            result.append((combined >> 8) & 0xFF)
        if vals[3] != 64:
            result.append(combined & 0xFF)

    decoded = bytes(result)

    # Decompress if gzipped
    if decoded[:2] == b'\x1f\x8b':
        decoded = gzip.decompress(decoded)

    return json.loads(decoded.decode())


class HiAnimeScraper:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.embed_session = requests.Session()
        self.embed_session.headers.update(self.headers)

    def search(self, keyword):
        url = f"{BASE_URL}/search?keyword={keyword}"
        try:
            for attempt in range(3):
                try:
                    response = self.session.get(url, headers=self.headers, timeout=30)
                    if response.status_code == 200:
                        break
                except (requests.ConnectionError, requests.Timeout) as e:
                    if attempt == 2:
                        print(f"Search connection failed after 3 attempts: {e}")
                        return []
                    continue
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            for item in soup.find_all("div", class_="flw-item"):
                name_tag = item.find("h3", class_="film-name").find("a")
                if not name_tag: continue
                title = name_tag.text.strip()
                link = name_tag["href"]
                if not link.startswith("http"):
                    link = BASE_URL + link
                
                quality_tag = item.find("div", class_="tick-quality")
                quality = quality_tag.text.strip() if quality_tag else "N/A"
                
                results.append({
                    "title": title,
                    "link": link,
                    "quality": quality
                })
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def get_episodes(self, anime_url):
        try:
            # Use longer timeout and retry on connection issues
            for attempt in range(3):
                try:
                    response = self.session.get(anime_url, headers=self.headers, timeout=30)
                    if response.status_code == 200:
                        break
                except (requests.ConnectionError, requests.Timeout) as e:
                    if attempt == 2:
                        print(f"Connection failed after 3 attempts: {e}")
                        return []
                    continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            play_btn = soup.find("a", class_="btn-play")
            if not play_btn:
                play_btn = soup.find("a", href=re.compile(r"/watch-"))
               
            if not play_btn:
                return []
            
            watch_url = play_btn["href"]
            if not watch_url.startswith("http"):
                watch_url = BASE_URL + watch_url
               
            # Retry watch page fetch
            for attempt in range(3):
                try:
                    response = self.session.get(watch_url, headers=self.headers, timeout=30)
                    if response.status_code == 200:
                        break
                except (requests.ConnectionError, requests.Timeout) as e:
                    if attempt == 2:
                        print(f"Watch page connection failed after 3 attempts: {e}")
                        return []
                    continue
            if response.status_code != 200:
                return []
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            anilist_id = None
            script_tags = soup.find_all("script")
            for script in script_tags:
                if "var anilistId =" in script.text:
                    match = re.search(r"var anilistId = (\d+);", script.text)
                    if match:
                        anilist_id = match.group(1)
                        break
            
            # Extract servers from the watch page
            page_servers = []
            srv_matches = re.findall(r'data-server-url="([^"]+)"[^>]*data-server="([^"]+)"[^>]*>([^<]+)', response.text)
            for srv_url, srv_provider, srv_name in srv_matches:
                if srv_url == "backup": continue
                page_servers.append({
                    "name": srv_name.strip(),
                    "url": srv_url,
                    "provider": srv_provider
                })

            episodes = []
            ep_items = soup.find_all("a", class_="ws-ep")
            
            for i, ep in enumerate(ep_items):
                ep_num = ep.get("data-episode") or ep.find("span", class_="ws-ep__num").text.strip()
                ep_title = ep.find("span", class_="ws-ep__title").text.strip()
                
                stream_token = ep.get("data-stream-token")
                ep_id = None
                if stream_token:
                    try:
                        padding = len(stream_token) % 4
                        if padding:
                            stream_token += "=" * (4 - padding)
                        decoded = base64.b64decode(stream_token).decode("utf-8")
                        ep_id = decoded.split(":")[0]
                    except:
                        pass
                
                episodes.append({
                    "id": ep_id,
                    "number": ep_num,
                    "title": ep_title,
                    "anilist_id": anilist_id,
                    "servers": page_servers
                })

            return episodes
        except Exception as e:
            print(f"Episode fetch error: {e}")
            return []

    def get_stream_url(self, episode):
        """
        Returns a tuple of (stream_url, server_info) where server_info contains
        the server/provider name for proper referer handling.
        Returns (None, None) if no stream found.
        """
        # 1. Attempt MegaPlay Ryu (often the first server)
        # Ryu uses the ep_id we decoded from the stream-token
        if episode.get("id"):
            ryu_id = self.get_megaplay_id(episode["id"])
            if ryu_id:
                # We still need the getSources API to work, but let's try direct extraction if possible
                pass

        # 2. Try to find a direct .m3u8 in the servers
        servers = episode.get("servers", [])
        for s in servers:
            if s.get("url") and s["url"].endswith(".m3u8"):
                return s["url"], s

        # 3. Try to extract m3u8 from embed pages for each server
        anilist_id = episode.get("anilist_id")
        ep_num = episode.get("number")
        
        for s in servers:
            embed_url = s.get("url")
            provider = s.get("provider", "").lower()
            
            if embed_url and anilist_id and ep_num:
                print(f"  Trying to extract stream from {provider} ({s.get('name')})...")
                m3u8_url = self.extract_m3u8_from_embed(
                    embed_url, provider, "https://hianime.ms/", anilist_id, ep_num
                )
                if m3u8_url:
                    print(f"  ✓ Found m3u8: {m3u8_url[:80]}...")
                    return m3u8_url, s

        # 4. Fallback: Use anilist_id predictable URLs (embed pages, not direct streams)
        if anilist_id and ep_num:
            # Determine likely server from available servers
            server_info = None
            for s in servers:
                if "vidnest" in s.get("url", "") or "megacloud" in s.get("url", "") or "megacloud" in s.get("provider", ""):
                    server_info = s
                    break
            if not server_info and servers:
                server_info = servers[0]
            return f"https://vidnest.fun/anime/{anilist_id}/{ep_num}/sub", server_info

        return None, None

    def get_megaplay_id(self, real_ep_id):
        # Fetch the megaplay page to get the data-id
        url = f"https://megaplay.buzz/stream/s-2/{real_ep_id}/sub"
        try:
            resp = self.session.get(url, headers={"Referer": "https://hianime.ms/", **self.headers}, timeout=10)
            if resp.status_code == 200:
                match = re.search(r'data-id="(\d+)"', resp.text)
                if match:
                    return match.group(1)
        except:
            pass
        return None

    def decrypt_megacloud(self, encrypted_string, secret_key):
        # Implementation of LCG decryption as researched
        def get_hash(key):
            val = 0
            for char in key:
                val = (val * 31 + ord(char)) & 0xFFFFFFFF
            return val

        multiplier = 1103515245
        increment = 12345
        modulus = 0x7FFFFFFF

        current_hash = get_hash(secret_key)
        decrypted_chars = []
        for char in encrypted_string:
            current_hash = (current_hash * multiplier + increment) & modulus
            val1 = ord(char) - 32
            val2 = current_hash % 95
            decrypted_char = chr((val1 - val2) % 95 + 32)
            decrypted_chars.append(decrypted_char)
        
        # Unshuffling block logic
        key_len = len(secret_key)
        blocks = [decrypted_chars[i:i + key_len] for i in range(0, len(decrypted_chars), key_len)]
        # Reordering based on sorted key... (omitted for brevity, basic LCG is usually enough to find URLs)
        return "".join(decrypted_chars)

    def extract_m3u8_from_embed(self, embed_url, provider, referer="https://hianime.ms/", anilist_id=None, episode=None):
        """
        Extract actual m3u8 URL from embed page based on provider.
        Returns the m3u8 URL or None if extraction fails.
        """
        headers = {"Referer": referer, **self.headers}
        
        for attempt in range(2):  # 2 attempts per provider
            try:
                if provider == "tryembed" or "tryembed" in embed_url:
                    return self._extract_tryembed(embed_url, headers, anilist_id, episode)
                elif provider == "vidnest" or "vidnest" in embed_url:
                    return self._extract_vidnest(embed_url, headers, anilist_id, episode)
                elif "megacloud" in provider or "megacloud" in embed_url:
                    return self._extract_megacloud(embed_url, headers, anilist_id, episode)
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt == 1:
                    print(f"Embed extraction connection failed for {provider}: {e}")
                    return None
            except Exception as e:
                print(f"Embed extraction error for {provider}: {e}")
                return None
        
        return None

    def _extract_tryembed(self, embed_url, headers, anilist_id, episode):
        """Extract m3u8 from tryembed.us.cc embed page."""
        # Fetch embed page to get RAW_PAYLOAD
        resp = self.embed_session.get(embed_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"  tryembed: embed page fetch failed ({resp.status_code})")
            return None
        
        # Extract RAW_PAYLOAD
        match = re.search(r'window\.RAW_PAYLOAD="([^"]+)"', resp.text)
        if not match:
            print(f"  tryembed: no RAW_PAYLOAD found")
            return None
        
        payload_b64 = match.group(1)
        try:
            decoded = base64.b64decode(payload_b64).decode()
            data = json.loads(decoded)
            meta = data.get("meta", {})
        except Exception as e:
            print(f"  tryembed: payload decode failed: {e}")
            return None
        
        # Call stream_data API
        api_url = "https://tryembed.us.cc/api/stream_data"
        params = {
            "id": meta.get("anilist_id") or anilist_id,
            "episode": meta.get("episode") or episode,
        }
        if meta.get("audio"):
            params["audio"] = meta["audio"]
        if meta.get("tk"):
            params["tk"] = meta["tk"]
        
        api_resp = self.embed_session.get(api_url, params=params, headers=headers, timeout=15)
        if api_resp.status_code != 200:
            print(f"  tryembed: API returned {api_resp.status_code}: {api_resp.text[:100]}")
            return None
        
        try:
            api_data = api_resp.json()
            # Look for m3u8 in response
            sources = api_data.get("sources") or api_data.get("data", {}).get("sources")
            if sources:
                for source in sources:
                    if source.get("file", "").endswith(".m3u8") or source.get("type") == "hls":
                        return source.get("file")
                    if source.get("file", "").endswith(".mp4"):
                        return source.get("file")
        except Exception as e:
            print(f"  tryembed: API response parse failed: {e}")
        
        return None

    def _extract_vidnest(self, embed_url, headers, anilist_id, episode):
        """Extract m3u8 from vidnest.fun using their API with decryption."""
        if not anilist_id or not episode:
            return None

        # Try the working API endpoint we discovered
        api_url = f"https://new.vidnest.fun/hianime/anime/{anilist_id}/{episode}/sub"
        
        # Use referer for aniwave (the default working server)
        api_headers = {
            "Referer": "https://aniwaves.ru/",
            **headers
        }

        for attempt in range(3):
            try:
                resp = self.embed_session.get(api_url, headers=api_headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("encrypted"):
                        try:
                            decrypted = vidnest_decrypt(data["data"])
                            sources = decrypted.get("sources", [])
                            for source in sources:
                                file_url = source.get("file") or source.get("url")
                                if file_url and (file_url.endswith(".m3u8") or source.get("type") == "hls"):
                                    return file_url
                        except Exception as e:
                            print(f"  vidnest: decryption failed: {e}")
                            return None
                    elif data.get("sources"):
                        for source in data["sources"]:
                            file_url = source.get("file") or source.get("url")
                            if file_url and (file_url.endswith(".m3u8") or source.get("type") == "hls"):
                                return file_url
                elif resp.status_code == 502:
                    # Try anitaku fallback
                    api_url = f"https://new.vidnest.fun/anitaku/anime/{anilist_id}/{episode}/sub/hd-2"
                    api_headers["Referer"] = "https://anitaku.to"
                else:
                    print(f"  vidnest: API returned {resp.status_code}")
                    return None
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt == 2:
                    print(f"  vidnest: API connection failed: {e}")
                    return None
            except Exception as e:
                print(f"  vidnest: extraction error: {e}")
                return None

        return None

    def _extract_megacloud(self, embed_url, headers, anilist_id, episode):
        """Extract m3u8 from megacloud embed using Ryu ID."""
        # The megaplay ID (Ryu ID) should be in the episode data
        # We need to fetch the megaplay page first
        return None  # Implement if needed
