import os
import sys
import json
import time
from datetime import datetime

import requests

# ----------------- CONFIGURATION -----------------
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
DRY_RUN = os.environ.get("DRY_RUN") == "1"        # prints the embed instead of sending it
PROJECT = "paper"
MC_VERSION_FALLBACK = "26.3"                       # used if auto-detection fails
MC_VERSION_FORCED = os.environ.get("MC_VERSION")   # forces a specific version if set

API_BASE = "https://fill.papermc.io/v3/projects"
CACHE_FILE = "last_build.json"
HEADERS = {"User-Agent": "Paper-Check-Bot/3.1.0 (+https://github.com/TON_PSEUDO/Paper-check)"}
# -------------------------------------------------


def http_get_json(url, retries=3):
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"Attempt {attempt}/{retries} ({url}): {e}")
            time.sleep(2 * attempt)
    return None


def version_key(v):
    try:
        return tuple(int(p) for p in v.split("."))
    except ValueError:
        return (0,)


def detect_mc_version():
    """Latest stable MC version (no -pre/-rc) known to the API, else fallback."""
    if MC_VERSION_FORCED:
        return MC_VERSION_FORCED
    data = http_get_json(f"{API_BASE}/{PROJECT}")
    try:
        versions = data["versions"]
        if isinstance(versions, dict):  # grouped: {"26.3": ["26.3.1", ...]}
            versions = [v for group in versions.values() for v in group]
        stable = [v for v in versions if all(p.isdigit() for p in v.split("."))]
        if stable:
            return max(stable, key=version_key)
    except (TypeError, KeyError, AttributeError):
        pass
    print(f"Auto-detection failed, using {MC_VERSION_FALLBACK}.")
    return MC_VERSION_FALLBACK


def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d.get("version"), d.get("last_build", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return None, 0


def save_cache(version, build):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"version": version, "last_build": build}, f, indent=2)
        f.write("\n")


def fetch_latest_build(mc_version):
    builds = http_get_json(f"{API_BASE}/{PROJECT}/versions/{mc_version}/builds")
    if not builds:
        print(f"No builds found for {mc_version}.")
        return None
    return max(builds, key=lambda b: b.get("id", 0))  # does not rely on API ordering


def build_embed(b, mc_version):
    dl = b.get("downloads", {}).get("server:default", {})
    size = dl.get("size")
    size_txt = f"{size / (1024 * 1024):.2f} MB" if size else "N/A"
    sha = dl.get("checksums", {}).get("sha256")

    fields = [
        {"name": "🆔 Build", "value": f"`#{b['id']}`", "inline": True},
        {"name": "📦 Version Minecraft", "value": f"`{mc_version}`", "inline": True},
        {"name": "🏷️ Channel", "value": b.get("channel", "UNKNOWN"), "inline": True},
        {"name": "📁 JAR File", "value": dl.get("name", "N/A"), "inline": False},
        {"name": "⚖️ Size", "value": size_txt, "inline": True},
    ]
    if sha:
        fields.append({"name": "🔒 SHA-256", "value": f"`{sha}`", "inline": False})

    commits = b.get("commits") or []
    if commits:
        lines = [f"• {c.get('message', '').splitlines()[0][:100]}" for c in commits[:5]]
        if len(commits) > 5:
            lines.append(f"… +{len(commits) - 5} more")
        fields.append({"name": "📝 Changes", "value": "\n".join(lines)[:1000], "inline": False})

    embed = {
        "title": "🟢 PAPERMC - New Build Detected",
        "url": "https://papermc.io/downloads/paper",
        "color": 15844367,
        "fields": fields,
        "footer": {"text": "Version Installer - Automatic via GitHub"},
    }
    if dl.get("url"):
        embed["fields"].append({"name": "⬇️ Download", "value": f"[{dl.get('name', 'JAR')}]({dl['url']})", "inline": False})
    if b.get("time"):
        try:
            embed["timestamp"] = datetime.fromisoformat(b["time"].replace("Z", "+00:00")).isoformat()
        except ValueError:
            pass
    return embed


def send_discord(embed):
    """True only if Discord accepted the message."""
    if DRY_RUN:
        print(json.dumps(embed, indent=2, ensure_ascii=False))
        return True
    for _ in range(3):
        try:
            res = requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=15)
        except requests.RequestException as e:
            print(f"Discord network error : {e}")
            time.sleep(2)
            continue
        if res.status_code == 429:
            time.sleep(float(res.json().get("retry_after", 2)))
            continue
        if res.status_code < 400:
            return True
        print(f"Discord failure : {res.status_code} - {res.text}")
        return False
    return False


def main():
    if not WEBHOOK_URL and not DRY_RUN:
        print("Error: DISCORD_WEBHOOK is missing.")
        sys.exit(1)

    mc_version = detect_mc_version()
    latest = fetch_latest_build(mc_version)
    if not latest:
        sys.exit(1)  # job turns red instead of failing silently

    cached_version, cached_build = load_cache()
    # If the MC version changes (e.g. 26.3 -> 26.4), build numbers restart from zero
    # (an old cache file without a version key is treated as matching)
    if cached_version not in (None, mc_version):
        cached_build = 0

    current = latest["id"]
    print(f"MC {mc_version} | API: #{current} | Cache: #{cached_build}")

    if current <= cached_build:
        print("No new build.")
        return

    if send_discord(build_embed(latest, mc_version)):
        if not DRY_RUN:
            save_cache(mc_version, current)  # only after a successful send
        print(f"Notification sent for #{current}.")
    else:
        print("Send failed, cache not updated: will retry on the next run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
