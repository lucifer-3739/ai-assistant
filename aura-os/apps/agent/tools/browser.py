import os
import webbrowser
import urllib.parse
from tools.base import registry

@registry.register(
    name="open_url",
    description="Opens a specified website URL in the user's default web browser.",
    risk_level="SAFE",
    required_permission="browser",
    verify_method=None
)
def open_url(url: str = None, **kwargs) -> str:
    target = url or kwargs.get("link") or kwargs.get("website") or kwargs.get("address")
    if not target:
        return "Error: No URL provided."
    if not target.startswith("http://") and not target.startswith("https://"):
        target = "https://" + target
    try:
        webbrowser.open(target)
        return f"Successfully opened URL: {target}"
    except Exception as e:
        return f"Failed to open URL '{target}': {e}"

@registry.register(
    name="search_web",
    description="Searches Google for the specified query and opens the search results in the browser.",
    risk_level="SAFE",
    required_permission="browser",
    verify_method=None
)
def search_web(query: str = None, **kwargs) -> str:
    q = query or kwargs.get("search_query") or kwargs.get("term") or kwargs.get("text") or kwargs.get("q")
    if not q:
        return "Error: No search query provided."
    encoded = urllib.parse.quote(str(q))
    url = f"https://www.google.com/search?q={encoded}"
    try:
        webbrowser.open(url)
        return f"Successfully executed web search for: '{q}'"
    except Exception as e:
        return f"Failed to perform search: {e}"

@registry.register(
    name="play_media",
    description="Searches and plays music, videos, or media on YouTube or Spotify.",
    risk_level="SAFE",
    required_permission="browser",
    verify_method=None
)
def play_media(query: str = None, platform: str = "youtube", **kwargs) -> str:
    q = query or kwargs.get("song") or kwargs.get("music") or kwargs.get("track") or kwargs.get("video") or kwargs.get("search")
    plat = platform or kwargs.get("service") or "youtube"
    
    if not q:
        return "Error: No media track or query provided."
        
    encoded = urllib.parse.quote(str(q))
    
    if "spotify" in str(plat).lower():
        url = f"https://open.spotify.com/search/{encoded}"
    else:
        url = f"https://www.youtube.com/results?search_query={encoded}"
        
    try:
        webbrowser.open(url)
        return f"Successfully opened {plat.capitalize()} to play: '{q}'"
    except Exception as e:
        return f"Failed to open media: {e}"
