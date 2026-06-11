import questionary
import webbrowser
import sys
from scraper import HiAnimeScraper
from player import AnimePlayer, get_headers_for_host


# Language preference
PREFER_DUB = True  # Set to False for subbed

def is_embed_url(url):
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


def is_direct_stream(url):
    """Check if URL is a direct video stream (m3u8, mp4, etc.)."""
    return url.endswith((".m3u8", ".mp4", ".mkv", ".webm", ".ts"))


def select_language():
    """Prompt user to select dub or sub preference."""
    try:
        choice = questionary.select(
            "Select language:",
            choices=["Dub (English)", "Sub (Japanese)"]
        ).ask()
        return choice == "Dub (English)"
    except Exception:
        # Fallback for non-TTY
        try:
            response = input("Language (Dub/Sub) [Dub]: ").strip().lower()
            return response not in ('s', 'sub', 'japanese')
        except Exception:
            return True


def confirm(prompt, default=True):
    """Simple confirmation prompt that works without questionary TTY issues."""
    try:
        return questionary.confirm(prompt, default=default).ask()
    except Exception:
        # Fallback for non-TTY environments
        try:
            response = input(f"{prompt} (y/N): ").strip().lower()
            return response in ('y', 'yes') if default else response not in ('n', 'no')
        except Exception:
            return default


def filter_servers_for_language(servers, prefer_dub):
    """Filter servers to only include preferred language (dub/sub)."""
    filtered = []
    for s in servers:
        url = s.get("url", "").lower()
        if prefer_dub and "dub" in url:
            filtered.append(s)
        elif not prefer_dub and "sub" in url:
            filtered.append(s)
    return filtered if filtered else servers  # fallback to all if none match


def main():
    scraper = HiAnimeScraper()
    player = AnimePlayer()
    
    # Ask language preference once at startup
    prefer_dub = select_language()
    lang_str = "Dub" if prefer_dub else "Sub"
    print(f"Language preference: {lang_str}")

    print("Welcome to HiAnime CLI Player!")

    while True:
        query = questionary.text("Search for an anime (or 'q' to quit):").ask()
        if not query or query.lower() == 'q':
            break

        results = scraper.search(query)
        if not results:
            print("No results found.")
            continue

        choices = [f"{r['title']} ({r.get('quality', 'N/A')})" for r in results]
        selected_title = questionary.select(
            "Select an anime:",
            choices=choices
        ).ask()

        if not selected_title:
            continue

        selected_anime = results[choices.index(selected_title)]
        print(f"Fetching episodes for {selected_anime['title']}...")

        episodes = scraper.get_episodes(selected_anime['link'])
        if not episodes:
            print("No episodes found or failed to fetch.")
            continue

        ep_choices = [f"Ep {e['number']}: {e['title']}" for e in episodes]
        ep_choices.append("Back to search")

        selected_ep_str = questionary.select(
            "Select an episode:",
            choices=ep_choices
        ).ask()

        if not selected_ep_str or selected_ep_str == "Back to search":
            continue

        selected_ep = episodes[ep_choices.index(selected_ep_str)]
        
        # Filter servers for preferred language before getting stream
        selected_ep["servers"] = filter_servers_for_language(selected_ep.get("servers", []), prefer_dub)
        
        stream_url, server_info = scraper.get_stream_url(selected_ep)

        if stream_url:
            # Determine referer from the STREAM URL host (not embed URL)
            # get_headers_for_host handles both embed portals AND CDN hosts
            host_config = get_headers_for_host(stream_url)
            referer = host_config.get("referer", "https://hianime.ms/")

            print(f"Using server: {server_info.get('name', 'Unknown') if server_info else 'Auto-detected'}")
            print(f"Stream URL: {stream_url[:80]}..." if len(stream_url) > 80 else f"Stream URL: {stream_url}")
            print(f"Referer: {referer}")

            # Check if we got a direct stream or an embed page
            if is_direct_stream(stream_url):
                print("✓ Direct stream detected - playing with mpv")
                # Pass the embed URL as fallback for Cloudflare-protected CDNs
                embed_fallback = server_info.get("url") if server_info else None
                player.play(
                    stream_url,
                    title=f"{selected_anime['title']} - {selected_ep_str}",
                    referer=referer,
                    embed_fallback_url=embed_fallback
                )
            elif is_embed_url(stream_url):
                print("⚠ Embed page detected (not a direct stream)")
                print("  Attempting to play with mpv (may not work for embed pages)...")
                
                # Try playing embed URL with mpv
                result = player.play(
                    stream_url,
                    title=f"{selected_anime['title']} - {selected_ep_str}",
                    referer=referer
                )
                
                # If mpv fails (which it will for embed pages), auto-offer browser
                if result is False:
                    print("\n  ──▶ Opening embed page in browser for playback...")
                    webbrowser.open(stream_url)
                    print(f"  Opened: {stream_url}")
                    print("  Use the video player on the page to watch.")
            else:
                # Unknown URL type, try mpv anyway
                embed_fallback = server_info.get("url") if server_info else None
                player.play(
                    stream_url,
                    title=f"{selected_anime['title']} - {selected_ep_str}",
                    referer=referer,
                    embed_fallback_url=embed_fallback
                )
        else:
            print("Could not find a streamable URL for this episode.")


if __name__ == "__main__":
    main()