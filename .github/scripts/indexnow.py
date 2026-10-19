#!/usr/bin/env python3
"""Signale à IndexNow (Bing, Yandex, Seznam, Naver…) les pages HTML modifiées dans le dernier commit."""
import json, subprocess, sys, urllib.request
HOST = "www.site-mariage.com"
KEY = "5cd93df97c4fd0d9f48b8d6dbab04c67"
SKIP = {"studio.html", "generateur-articles.html", "formulaire-maries.html", "404.html"}
base = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
files = subprocess.run(["git", "diff", "--name-only", "--diff-filter=AM", base, "HEAD"],
                       capture_output=True, text=True).stdout.split()
urls = [f"https://{HOST}/" if f == "index.html" else f"https://{HOST}/{f}"
        for f in files if f.endswith(".html") and "/" not in f and f not in SKIP]
# Ajoute aussi les pages du sitemap modifiées aujourd'hui (rattrapage)
import re, datetime
today = datetime.date.today().isoformat()
try:
    sm = open("sitemap.xml", encoding="utf-8").read()
    for loc, mod in re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", sm):
        if mod >= today and loc not in urls:
            urls.append(loc)
except FileNotFoundError:
    pass
if not urls:
    print("IndexNow : aucune page à signaler."); sys.exit(0)
body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow : {r.status} pour {len(urls)} URL(s)", *urls, sep="\n  ")
except Exception as e:
    print(f"IndexNow : échec ({e}) — sans gravité, la publication continue.")
