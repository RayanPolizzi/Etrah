#!/usr/bin/env python3
"""
Etrah — Publication automatique des articles planifiés
Appelé par GitHub Actions chaque jour (1 article par semaine selon les dates de queue.json).

- Publie au maximum 1 article par exécution (rattrape un article en retard).
- En cas d'échec, l'article reste en attente et est retenté le lendemain (3 essais maximum),
  puis passe en "error". L'exécution échoue alors (croix rouge + e-mail GitHub) pour vous prévenir.
"""

import json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT     = Path(__file__).parent.parent.parent  # racine du repo
QUEUE    = ROOT / "queue.json"
TODAY    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
GENERER  = ROOT / "generer.py"
MAX_TRIES = 3

def out(key, value):
    """Transmet une valeur aux étapes suivantes du workflow."""
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")

def main():
    if not QUEUE.exists():
        print("queue.json introuvable — rien à faire.")
        return 0

    articles = json.loads(QUEUE.read_text(encoding="utf-8"))
    due = sorted((a for a in articles if a.get("status") == "pending" and a.get("date", "9999") <= TODAY),
                 key=lambda a: a["date"])
    if not due:
        nxt = min((a["date"] for a in articles if a.get("status") == "pending"), default="aucun")
        print(f"Aucun article prévu pour le {TODAY}. Prochain article : {nxt}.")
        out("published", "0")
        return 0

    article = due[0]
    title = article["title"]
    print(f"\n✦ Publication : {title}")
    result = subprocess.run([sys.executable, str(GENERER), title], capture_output=True, text=True)
    print(result.stdout)

    if result.returncode == 0:
        article["status"] = "done"
        article["published"] = TODAY
        article.pop("tries", None)
        article.pop("last_error", None)
        code = 0
        out("published", "1")
        out("message", f"Article publié : {title}")
        print(f"✓ Article publié : {title}")
    else:
        err = (result.stderr or result.stdout).strip().splitlines()
        article["tries"] = article.get("tries", 0) + 1
        article["last_error"] = (err[-1] if err else "erreur inconnue")[:300]
        if article["tries"] >= MAX_TRIES:
            article["status"] = "error"
        print(f"ERREUR (essai {article['tries']}/{MAX_TRIES}) :\n{result.stderr}")
        code = 1
        out("published", "0")
        out("message", f"Échec de génération ({article['tries']}/{MAX_TRIES}) : {title}")

    QUEUE.write_text(json.dumps(articles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n✦ queue.json mis à jour.")
    return code

if __name__ == "__main__":
    sys.exit(main())
