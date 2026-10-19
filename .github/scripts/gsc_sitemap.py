#!/usr/bin/env python3
"""Resoumet le sitemap à Google Search Console (API officielle) après chaque publication.
Nécessite le secret GitHub GSC_SERVICE_ACCOUNT (JSON d'un compte de service ajouté comme
propriétaire dans Search Console). Sans ce secret, le script s'arrête sans erreur."""
import json, os, sys, urllib.parse
raw = os.environ.get("GSC_SERVICE_ACCOUNT", "").strip()
if not raw:
    print("Search Console : secret GSC_SERVICE_ACCOUNT absent — étape ignorée."); sys.exit(0)
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
site = os.environ.get("GSC_SITE", "sc-domain:site-mariage.com")
sitemap = "https://www.site-mariage.com/sitemap.xml"
creds = service_account.Credentials.from_service_account_info(
    json.loads(raw), scopes=["https://www.googleapis.com/auth/webmasters"])
s = AuthorizedSession(creds)
url = ("https://www.googleapis.com/webmasters/v3/sites/" + urllib.parse.quote(site, safe="")
       + "/sitemaps/" + urllib.parse.quote(sitemap, safe=""))
r = s.put(url, timeout=30)
if r.status_code in (200, 204):
    print(f"Search Console : sitemap soumis pour {site}")
else:
    print(f"Search Console : échec {r.status_code} — {r.text[:300]}")
    sys.exit(0)
