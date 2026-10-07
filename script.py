import os
import sys
import json
import requests

# ----------------- CONFIGURATION -----------------
# Le webhook est récupéré de manière sécurisée depuis les variables d'environnement
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
MC_VERSION = "26.3"  # Remplacez par une version Minecraft valide (ex: 1.20.4, 1.21, 1.21.1)

API_URL = f"https://papermc.io{MC_VERSION}"
CACHE_FILE = "last_build.json"
# -------------------------------------------------

def get_last_notified_build():
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            return data.get("last_build", 0)
    except FileNotFoundError:
        return 0

def save_last_build(build_number):
    with open(CACHE_FILE, "w") as f:
        json.dump({"last_build": build_number}, f)

def fetch_paper_data():
    if not WEBHOOK_URL:
        print("Erreur : La variable d'environnement DISCORD_WEBHOOK est manquante.")
        sys.exit(1)
        
    try:
        response = requests.get(API_URL)
        if response.status_code != 200:
            print(f"Version Minecraft introuvable ou erreur API ({response.status_code})")
            return None
        
        builds = response.json().get("builds", [])
        if not builds:
            return None
            
        latest_build = builds[-1]
        
        detail_url = f"{API_URL}/builds/{latest_build}"
        detail_response = requests.get(detail_url)
        if detail_response.status_code == 200:
            return detail_response.json()
            
    except Exception as e:
        print(f"API Error : {e}")
    return None

def send_discord_webhook(build_data):
    build_num = build_data.get("build")
    version = build_data.get("version")
    
    downloads = build_data.get("downloads", {})
    jar_size_bytes = downloads.get("application", {}).get("size-bytes", 0)
    jar_size_mb = f"{jar_size_bytes / (1024 * 1024):.2f} MB" if jar_size_bytes else "N/A"

    changes = build_data.get("changes", [])
    changelog = changes[-1].get("summary", "No summary provided.") if changes else "Minor update."

    payload = {
        "embeds": [
            {
                "title": "🟢 PAPERMC Added new Build",
                "color": 15844367,
                "fields": [
                    {"name": "🆔 ID / Build", "value": f"#{build_num}", "inline": True},
                    {"name": "📦 Version", "value": version, "inline": True},
                    {"name": "📁 Jar Size", "value": jar_size_mb, "inline": True},
                    {"name": "📝 Changelog", "value": changelog, "inline": False}
                ],
                "thumbnail": {
                    "url": "https://papermc.io"
                },
                "footer": {
                    "text": "Version Installer - Automatic via GitHub"
                }
            }
        ]
    }

    res = requests.post(WEBHOOK_URL, json=payload)
    if res.status_code in:
        print(f"Discord notification sent for build #{build_num}!")
    else:
        print(f"Failed to send Discord notification: {res.status_code} - {res.text}")

def main():
    last_build = get_last_notified_build()
    build_data = fetch_paper_data()
    
    if build_data:
        current_build = build_data.get("build")
        
        if current_build > last_build:
            send_discord_webhook(build_data)
            save_last_build(current_build)
        else:
            print(f"No new build. (Last notified: #{last_build} / Current: #{current_build}).")

if __name__ == "__main__":
    main()
