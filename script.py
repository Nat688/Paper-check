import os
import sys
import json
import requests

# ----------------- CONFIGURATION DU WIKI -----------------
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
PROJECT = "paper"
MC_VERSION = "26.3"  # Version Minecraft ciblée

# URL officielle v3 tirée de la documentation
API_URL = f"https://fill.papermc.io/v3/projects/{PROJECT}/versions/{MC_VERSION}/builds"
CACHE_FILE = "last_build.json"

# USER-AGENT OBLIGATOIRE (exigé par le wiki sous peine de blocage)
HEADERS = {
    "User-Agent": "Paper-Check-Bot/3.0.0 (https://github.com)"
}
# ---------------------------------------------------------

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
        response = requests.get(API_URL, headers=HEADERS)
        if response.status_code != 200:
            print(f"Erreur API ({response.status_code}) - Version introuvable.")
            return None
        
        builds = response.json()
        if not builds or len(builds) == 0:
            print("Aucun build disponible pour cette version.")
            return None
            
        # Comme demandé, on extrait le build le plus récent (le premier de la liste)
        latest_build = builds[0]
        return latest_build
            
    except Exception as e:
        print(f"Erreur lors de la requête API : {e}")
    return None

def send_discord_webhook(build_data):
    # Lecture des champs d'après la structure de l'API v3
    build_num = build_data.get("id")
    channel = build_data.get("channel", "UNKNOWN")
    
    downloads = build_data.get("downloads", {})
    server_default = downloads.get("server:default", {})
    jar_name = server_default.get("name", "N/A")
    jar_size_bytes = server_default.get("size", 0)
    jar_size_mb = f"{jar_size_bytes / (1024 * 1024):.2f} MB" if jar_size_bytes else "N/A"

    payload = {
        "embeds": [
            {
                "title": f"🟢 PAPERMC - New Build Detected",
                "color": 15844367,
                "fields": [
                    {"name": "🆔 ID / Build", "value": f"`#{build_num}`", "inline": True},
                    {"name": "📦 Version Minecraft", "value": "`26.3`", "inline": True},
                    {"name": "🏷️ Canal (Channel)", "value": channel, "inline": True},
                    {"name": "📁 JAR File", "value": jar_name, "inline": False},
                    {"name": "⚖️ Size", "value": jar_size_mb, "inline": True}
                ],
                "thumbnail": {
                    "url": "https://cdn.discordapp.com/emojis/1557495100907593898.webp?size=56"
                },
                "footer": {
                    "text": "Version Installer - Automatic via GitHub"
                }
            }
        ]
    }

    res = requests.post(WEBHOOK_URL, json=payload)
    if res.status_code < 400:
        print(f"Notification Discord envoyée pour le build #{build_num} !")
    else:
        print(f"Échec de l'envoi Discord : {res.status_code} - {res.text}")

def main():
    last_build = get_last_notified_build()
    latest_build_data = fetch_paper_data()
    
    if latest_build_data:
        current_build = latest_build_data.get("id")
        
        print(f"Dernier build sur l'API : #{current_build} | Cache actuel : #{last_build}")
        
        if current_build > last_build:
            send_discord_webhook(latest_build_data)
            save_last_build(current_build)
        else:
            print(f"Pas de nouveau build. (Dernier notifié: #{last_build} / Actuel: #{current_build}).")

if __name__ == "__main__":
    main()
