import os
import sys
import json
import requests

# ----------------- CONFIGURATION -----------------
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
PROJECT = "paper"
MC_VERSION = "26.3"

# VÉRIFIEZ BIEN CETTE LIGNE : elle doit être exactement comme ceci
API_URL = f"https://papermc.io{PROJECT}/versions/{MC_VERSION}/builds"
CACHE_FILE = "last_build.json"

HEADERS = {
    "User-Agent": "Paper-Check-Bot/2.0.0 (https://github.com)"
}
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
        response = requests.get(API_URL, headers=HEADERS)
        if response.status_code != 200:
            print(f"Version Minecraft introuvable ou erreur API ({response.status_code})")
            return None
        
        builds = response.json()
        if not builds:
            print("Aucun build trouvé pour cette version.")
            return None
            
        # MODIFICATION ICI : On ne filtre plus par "STABLE" pour pouvoir capter
        # les builds Beta/Alpha de la version de développement 26.3
        return builds
            
    except Exception as e:
        print(f"API Error : {e}")
    return None

def send_discord_webhook(build_data):
    # build_data correspond maintenant au dictionnaire du build individuel le plus récent
    build_num = build_data.get("id")
    
    downloads = build_data.get("downloads", {})
    server_download = downloads.get("server:default", {})
    jar_name = server_download.get("name", "N/A")
    jar_size_bytes = server_download.get("size", 0)
    jar_size_mb = f"{jar_size_bytes / (1024 * 1024):.2f} MB" if jar_size_bytes else "N/A"

    changelog = "Consultez les détails sur le site officiel de PaperMC."

    payload = {
        "embeds": [
            {
                "title": f"🟡 PAPERMC Added new Build (Dev/Beta)",
                "color": 15844367,
                "fields": [
                    {"name": "🆔 ID / Build", "value": f"#{build_num}", "inline": True},
                    {"name": "📦 Version Minecraft", "value": MC_VERSION, "inline": True},
                    {"name": "📁 Nom du Fichier", "value": jar_name, "inline": False},
                    {"name": "⚖️ Taille Jar", "value": jar_size_mb, "inline": True},
                    {"name": "📝 Notes", "value": changelog, "inline": False}
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
    if res.status_code < 400:
        print(f"Discord notification sent for stable build #{build_num}!")
    else:
        print(f"Failed to send Discord notification: {res.status_code} - {res.text}")

def main():
    last_build = get_last_notified_build()
    builds_list = fetch_paper_data()
    
    # builds_list est une liste reçue de l'API v3
    if builds_list and len(builds_list) > 0:
        # On extrait le build le plus récent qui est le TOUT PREMIER de la liste (index 0)
        latest_build_data = builds_list[0]
        current_build = latest_build_data.get("id")
        
        print(f"Dernier build détecté sur l'API : #{current_build} | Cache actuel : #{last_build}")
        
        if current_build > last_build:
            send_discord_webhook(latest_build_data)
            save_last_build(current_build)
        else:
            print(f"No new build. (Last notified: #{last_build} / Current: #{current_build}).")

if __name__ == "__main__":
    main()
