#!/usr/bin/env python3
"""
Etrah — Publication automatique des articles planifiés
Appelé par GitHub Actions chaque jour à 9h
"""

import json, subprocess, sys
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).parent.parent.parent  # racine du repo
QUEUE    = ROOT / "queue.json"
TODAY    = datetime.now().strftime("%Y-%m-%d")
GENERER  = ROOT / "generer.py"

def main():
    if not QUEUE.exists():
        print("queue.json introuvable — rien à faire.")
        return

    articles = json.loads(QUEUE.read_text(encoding="utf-8"))
    to_publish = [a for a in articles if a.get("date") == TODAY and a.get("status") == "pending"]

    if not to_publish:
        print(f"Aucun article prévu pour le {TODAY}.")
        return

    for article in to_publish:
        title = article["title"]
        print(f"\n✦ Publication : {title}")

        result = subprocess.run(
            [sys.executable, str(GENERER), title],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"ERREUR : {result.stderr}")
            article["status"] = "error"
        else:
            print(f"✓ Article publié : {title}")
            article["status"] = "done"

    QUEUE.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n✦ queue.json mis à jour.")

if __name__ == "__main__":
    main()
