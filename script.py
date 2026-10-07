import os
import sys
import json
import requests

# ----------------- CONFIGURATION -----------------
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
PROJECT = "paper"
MC_VERSION = "26.3"  # Utilisez un format de version Minecraft standard

# Nouvelle URL API v3 d'après votre documentation
API_URL = f"https://papermc.io{PROJECT}/versions/{MC_VERSION}/builds"
CACHE_FILE = "last_build.json"

# CONDITION OBLIGATOIRE : Un User-Agent personnalisé sous peine de blocage API
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
    # Adaptation à la nouvelle structure des propriétés (id, download, etc.)
    build_num = build_data.get("id")
    
    # Extraction des informations de téléchargement du serveur par défaut
    server_download = build_data.get("downloads", {}).get("server:default", {})
    jar_name = server_download.get("name", "N/A")
    jar_size_bytes = server_download.get("size", 0)
    jar_size_mb = f"{jar_size_bytes / (1024 * 1024):.2f} MB" if jar_size_bytes else "N/A"

    # La structure v3 ne renvoie plus toujours le changelog complet de la même façon,
    # On extrait un résumé ou on met une valeur par défaut propre.
    changelog = "Consultez les détails sur le site officiel de PaperMC."

    payload = {
        "embeds": [
            {
                "title": "🟡 PAPERMC Added new Build (Dev/Beta)",
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
    build_data = fetch_paper_data()
    
    if build_data:
        current_build = build_data.get("id")
        
        if current_build > last_build:
            send_discord_webhook(build_data)
            save_last_build(current_build)
        else:
            print(f"No new build. (Last notified: #{last_build} / Current: #{current_build}).")

if __name__ == "__main__":
    main()
