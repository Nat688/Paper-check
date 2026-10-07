import os
import sys
import json
import requests

# ----------------- CONFIGURATION -----------------
# GitHub va injecter le Webhook ici de manière sécurisée
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
MC_VERSION = "26.3"  # Modifie la version selon tes besoins (ex: 1.21.1)

API_URL = f"https://papermc.io{MC_VERSION}"
CACHE_FILE = "last_build.json"
# -------------------------------------------------

if not WEBHOOK_URL:
    print("Erreur : Le secret DISCORD_WEBHOOK n'est pas configuré sur GitHub.")
    sys.exit(1)

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
    try:
        response = requests.get(API_URL)
        if response.status_code != 200:
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
        print(f"Erreur API : {e}")
    return None

def send_discord_webhook(build_data):
    build_num = build_data.get("build")
    version = build_data.get("version")
    
    downloads = build_data.get("downloads", {})
    jar_size_bytes = downloads.get("application", {}).get("size-bytes", 0)
    jar_size_mb = f"{jar_size_bytes / (1024 * 1024):.2f} MB" if jar_size_bytes else "N/A"

    changes = build_data.get("changes", [])
    changelog = changes[-1].get("summary", "Aucun résumé fourni.") if changes else "Mise à jour mineure."

    payload = {
        "embeds": [
            {
                "title": "🟢 PAPERMC Added new Build",
                "color": 15844367,
                "fields": [
                    {"name": "🆔 ID / Build", "value": f"#{build_num}", "inline": True},
                    {"name": "📦 Version", "value": version, "inline": True},
                    {"name": "📁 Jar Size", "value": jar_size_mb, "inline": True},
                    {"name": "📝 Changelog", "value": changelog, "inline": True}
                ],
                "thumbnail": {
                    "url": "https://papermc.io"
                },
                "footer": {
                    "text": "Version Installer - Automatique via GitHub"
                }
            }
        ]
    }

    requests.post(WEBHOOK_URL, json=payload)
    print(f"Notification Discord envoyée pour le build #{build_num} !")

def main():
    last_build = get_last_notified_build()
    build_data = fetch_paper_data()
    
    if build_data:
        current_build = build_data.get("build")
        
        if current_build > last_build:
            send_discord_webhook(build_data)
            save_last_build(current_build)
        else:
            print(f"Pas de nouveau build (Dernier notifié : #{last_build} / Actuel : #{current_build}).")

if __name__ == "__main__":
    main()
