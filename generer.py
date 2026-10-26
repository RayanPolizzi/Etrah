#!/usr/bin/env python3
"""
Etrah — Générateur automatique d'articles
Usage : python generer.py "Titre de l'article"
        python generer.py  (mode interactif)

Requires : pip install anthropic
"""

import sys, os, json, re, html, hashlib
from datetime import datetime
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
SITE_URL  = "https://www.site-mariage.com"
TODAY     = datetime.now().strftime("%Y-%m-%d")
MONTH_FR  = {
    "01":"Janvier","02":"Février","03":"Mars","04":"Avril",
    "05":"Mai","06":"Juin","07":"Juillet","08":"Août",
    "09":"Septembre","10":"Octobre","11":"Novembre","12":"Décembre"
}
DATE_FR = f"{MONTH_FR[datetime.now().strftime('%m')]} {datetime.now().strftime('%Y')}"

HERO_IMAGES = [
    "https://images.unsplash.com/photo-1606800052052-a08af7148866?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522673607200-164d1b6ce486?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1537633552985-df8429e8048b?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1469371670807-013ccf25f16a?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1519741497674-611481863552?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1465495976277-4387d4b0b4c6?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1491895200222-0fc4a4c35e18?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1519225421980-715cb0215aed?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1502635385003-ee1e6a1a742d?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1656104717095-9d062b0d4e8d?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1780901049024-8e504f6024a8?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1621801306185-8c0ccf9c8eb8?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1632610992723-82d7c212f6d7?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1769374072486-a6c0511b7dee?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1515934751635-c81c6bc9a2d8?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1622398925373-3f91b1e275f5?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1561593367-66c79c2294e6?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1632528011905-54e2464961f4?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1721176487015-5408ae0e9bc2?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1509316554658-04f9287cdb78?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522058171200-e61f77c7353d?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1520854221256-17451cc331bf?w=1400&q=85&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1544592732-83bbbfc46783?w=1400&q=85&auto=format&fit=crop",
]
RECENT_AVOID = 5  # n'autorise pas une image déjà utilisée par les N derniers articles publiés

MODEL = os.environ.get("ETRAH_MODEL", "claude-sonnet-5-5")
MAX_TOKENS = 8000
MAX_ATTEMPTS = 3          # nouvelles tentatives si l'article ne passe pas le contrôle qualité
MIN_WORDS = 750           # longueur minimale du contenu (hors titres)
MIN_INTERNAL_LINKS = 3    # liens internes minimum dans le corps de l'article

# ── HELPERS ───────────────────────────────────────────────────────────────────
def slugify(t):
    s = t.lower()
    for a, b in [("àáâãä","a"),("èéêë","e"),("ìíîï","i"),("òóôõö","o"),("ùúûü","u"),("ç","c"),("ñ","n")]:
        for c in a: s = s.replace(c, b)
    s = re.sub(r"[^a-z0-9\s-]","",s)
    return re.sub(r"-+","-",re.sub(r"\s+","-",s.strip()))

ALLOWED_LINKS = {"/#offres", "/#contact", "/#faq", "magazine.html"}

def parse_inline(t):
    t = html.escape(t, quote=False)
    def link(m):
        txt, url = m.group(1), m.group(2).strip()
        if url in ALLOWED_LINKS:
            return f'<a href="{url}">{txt}</a>'
        return txt
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*([^*]+)\*",     r"<em>\1</em>", t)
    return t

def url_ok(url):
    """True si l'image répond (ou si le réseau est indisponible : on ne bloque pas pour ça)."""
    import urllib.request, urllib.error
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 Etrah"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status < 400
    except urllib.error.HTTPError as e:
        return e.code < 400
    except Exception:
        return True

def recently_used_heroes(n=RECENT_AVOID):
    """ID (sans paramètres) des images de couverture déjà utilisées par les n derniers articles publiés."""
    try:
        q = json.loads((BASE_DIR / "queue.json").read_text(encoding="utf-8"))
    except Exception:
        return set()
    done = sorted(
        (a for a in q if a.get("status") == "done" and a.get("published")),
        key=lambda a: a["published"], reverse=True,
    )[:n]
    used = set()
    for a in done:
        slug = slugify(a["title"]) + ".html"
        f = BASE_DIR / slug
        if not f.exists():
            continue
        m = re.search(r'og:image" content="https://images\.unsplash\.com/photo-([a-f0-9-]+)\?', f.read_text(encoding="utf-8"))
        if m:
            used.add(m.group(1))
    return used

def pick_hero(slug):
    """Image de couverture : exclut d'abord celles des derniers articles publiés pour éviter
    les répétitions rapprochées, puis choisit selon le slug parmi ce qui reste ; passe à la
    suivante si l'image ne répond plus."""
    avoid = recently_used_heroes()
    pool = [u for u in HERO_IMAGES if u.split("photo-")[1].split("?")[0] not in avoid] or HERO_IMAGES
    idx = int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(pool)
    for k in range(len(pool)):
        url = pool[(idx + k) % len(pool)]
        if url_ok(url):
            return url
        print(f"   ⚠ image indisponible, suivante : {url}")
    return pool[idx]

# ── GÉNÉRATION DU CONTENU VIA CLAUDE ─────────────────────────────────────────
SYSTEM = (
    "Tu es rédacteur expert pour Etrah, agence française de sites de mariage sur-mesure (500€, "
    "livraison 10-14 jours, basé à Nice). Style : élégant, direct, orienté couples français, "
    "concret et utile. SEO naturel. Tu n'inventes JAMAIS de chiffres, de sondages, d'études, "
    "de pourcentages ni de témoignages de couples : uniquement des conseils pratiques vérifiables."
)

PROMPT = """Génère un article de blog complet et SEO-optimisé pour le titre : "{title}"

Public : couples français qui planifient leur mariage.
Longueur : 1000-1300 mots de contenu réel.
Structure : introduction percutante + 5-7 sections variées + conclusion orientée action + FAQ.

Règles SEO (obligatoires) :
- Choisis UN mot-clé principal (la requête qu'un couple taperait sur Google pour ce sujet) et donne-le dans "keyword".
- Le mot-clé principal apparaît dans la meta description, dans la 1re phrase de l'intro et dans au moins un H2.
- Utilise naturellement 3 à 5 variantes et termes associés (champ sémantique), sans bourrage.
- H2 clairs et descriptifs ; au moins deux H2 formulés comme une question que se posent les couples.
- Meta description entre 130 et 155 caractères, incitative, avec le mot-clé.
- Paragraphes courts (2 à 4 phrases), phrases simples, réponse directe à la question dès le début de chaque section.
- Section "faq" en fin d'article : 3 questions précises (différentes des H2) avec des réponses de 2-3 phrases.

Réponds UNIQUEMENT avec un JSON valide, structure exacte :

{{
  "slug": "slug-sans-accents-avec-tirets",
  "keyword": "mot-clé principal",
  "category": "Catégorie · Sous-catégorie",
  "meta_description": "Description SEO de 130 à 155 caractères",
  "read_time": "X min de lecture",
  "hero_alt": "Description courte de l'image idéale pour cet article",
  "intro": "2-3 phrases d'accroche percutantes en italique",
  "sections": [
    {{"type":"text",  "h2":"Titre section", "paragraphs":["Para 1 avec **gras** possible.","Para 2..."]}},
    {{"type":"tip",   "text":"Conseil pratique concret en une ou deux phrases."}},
    {{"type":"list",  "h2":"Titre liste", "items":["**Item 1** — explication","**Item 2** — explication"]}},
    {{"type":"text",  "h2":"Autre section", "paragraphs":["..."]}},
    {{"type":"text",  "h2":"Conclusion ou section finale", "paragraphs":["..."]}},
    {{"type":"faq",   "items":[{{"q":"Question précise ?","a":"Réponse en 2-3 phrases."}}]}}
  ],
  "excerpt": "1-2 phrases pour la miniature sur la page d'accueil."
}}

Maillage interne (obligatoire) :
- Insère 4 à 6 liens internes DANS les paragraphes ou les listes, au format [texte d'ancre descriptif](url).
- Au moins 3 liens vers des articles existants (liste ci-dessous, écris le nom de fichier exact, ex. quand-creer-site-mariage.html),
  répartis dans l'article (pas tous dans la même section), plus 1 lien vers /#offres (offre et prix) ou /#contact.
- URLs autorisées UNIQUEMENT : celles de la liste ci-dessous, plus /#offres et /#contact.
- Ancres naturelles, descriptives et variées, qui contiennent les mots-clés de l'article cible (jamais "cliquez ici", "cet article"),
  une seule fois par URL.

Articles existants du magazine :
{existing}

Règles strictes :
- Aucun chiffre, pourcentage, sondage, étude ou témoignage inventé. Pas de citations de couples.
- Ne pas traiter un sujet déjà couvert par un article existant : apporte un angle différent.
- Mentionner Etrah dans 1 section max, naturellement
- Slug en français sans accents ni caractères spéciaux
- Chaque section "text" : au moins 2 paragraphes"""

def parse_json(raw):
    """Extrait l'objet JSON de la réponse, même entouré de texte ou de ```."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("aucun JSON dans la réponse")
    return json.loads(raw[start:end + 1])

def section_texts(data):
    """Tout le texte rédactionnel de l'article (pour compter mots et liens)."""
    out = [data.get("intro", "")]
    for s in data.get("sections", []):
        out += s.get("paragraphs", []) + s.get("items", []) if s.get("type") != "faq" else []
        if s.get("type") == "tip":
            out.append(s.get("text", ""))
        if s.get("type") == "faq":
            out += [f'{i.get("q","")} {i.get("a","")}' for i in s.get("items", []) if isinstance(i, dict)]
    return [t for t in out if isinstance(t, str)]

def internal_links(data):
    """Liens internes valides (ceux qui seront réellement publiés)."""
    found = []
    for t in section_texts(data):
        for url in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", t):
            if url.strip() in ALLOWED_LINKS:
                found.append(url.strip())
    return found

def check_quality(data, title):
    """Contrôle SEO avant publication. Renvoie la liste des problèmes (vide = OK)."""
    problems = []
    secs = data.get("sections", [])
    words_n = len(re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", " ".join(section_texts(data))).split())
    if words_n < MIN_WORDS:
        problems.append(f"article trop court ({words_n} mots, minimum {MIN_WORDS})")
    h2 = [s.get("h2", "") for s in secs if s.get("h2")]
    if len(h2) < 4:
        problems.append(f"pas assez de sections H2 ({len(h2)}, minimum 4)")
    md = data.get("meta_description", "")
    if not 110 <= len(md) <= 160:
        problems.append(f"meta description de {len(md)} caractères (attendu 130-155)")
    links = internal_links(data)
    art_links = {l for l in links if l.endswith(".html") and l != "magazine.html"}
    if len(set(links)) < MIN_INTERNAL_LINKS or len(art_links) < 2:
        problems.append(f"maillage insuffisant : {len(set(links))} lien(s) interne(s) valide(s) dont "
                        f"{len(art_links)} vers des articles (minimum {MIN_INTERNAL_LINKS} dont 2 articles) — "
                        "utilise exactement les noms de fichiers de la liste")
    if not any(s.get("type") == "faq" and len(s.get("items", [])) >= 3 for s in secs):
        problems.append("section FAQ absente ou incomplète (3 questions)")
    return problems

def generate(title, client, existing_txt=""):
    """Génère l'article, vérifie sa qualité et relance (max MAX_ATTEMPTS) en expliquant les défauts."""
    messages = [{"role": "user", "content": PROMPT.format(title=title, existing=existing_txt)}]
    last_problems = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        msg = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, system=SYSTEM, messages=messages)
        raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        if getattr(msg, "stop_reason", "") == "max_tokens":
            last_problems = ["réponse coupée (trop longue)"]
        else:
            try:
                data = parse_json(raw)
                last_problems = check_quality(data, title)
                if not last_problems:
                    print(f"   ✓ contrôle qualité OK (tentative {attempt})")
                    return data
            except Exception as e:
                last_problems = [f"JSON invalide : {e}"]
        print(f"   ⚠ tentative {attempt} refusée : " + " ; ".join(last_problems))
        messages = messages[:1] + [
            {"role": "assistant", "content": raw or "{}"},
            {"role": "user", "content": "L'article ne respecte pas les règles : " + " ; ".join(last_problems)
             + ". Corrige ces points et renvoie l'article COMPLET, uniquement en JSON valide."}]
    raise RuntimeError("contrôle qualité non passé après %d tentatives : %s" % (MAX_ATTEMPTS, " ; ".join(last_problems)))

# ── CONSTRUCTION HTML ─────────────────────────────────────────────────────────
def section_html(s):
    t = s.get("type","text")
    h2 = s.get("h2","")
    out = f'<h2>{html.escape(h2)}</h2>\n' if h2 else ""

    if t == "text":
        for p in s.get("paragraphs",[]):
            out += f"<p>{parse_inline(p)}</p>\n"
    elif t == "stat":
        n = html.escape(s.get("number",""))
        d = html.escape(s.get("description",""))
        out += f'<div class="stat"><div class="stat-n">{n}</div><div class="stat-t">{d}</div></div>\n'
    elif t == "quote":
        tx = html.escape(s.get("text",""))
        au = html.escape(s.get("author",""))
        out += f'<div class="quote"><p>{tx}</p>' + (f'<cite>— {au}</cite>' if au else "") + "</div>\n"
    elif t == "tip":
        out += f'<div class="quote"><p>{parse_inline(s.get("text",""))}</p></div>\n'
    elif t == "list":
        lis = "\n".join(f"<li>{parse_inline(i)}</li>" for i in s.get("items",[]))
        out += f"<ul>\n{lis}\n</ul>\n"
    elif t == "faq":
        out = '<h2>Questions fréquentes</h2>\n'
        for i in s.get("items", []):
            if isinstance(i, dict) and i.get("q") and i.get("a"):
                out += f'<h3>{html.escape(i["q"])}</h3>\n<p>{parse_inline(i["a"])}</p>\n'
    return out

def strip_md(t):
    """Texte brut sans markdown (pour les données structurées)."""
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    return re.sub(r"\*+([^*]+)\*+", r"\1", t)

def json_ld(title, data, page_url, hero_url, date_iso):
    """Données structurées : Article + fil d'Ariane + FAQ."""
    graph = [
        {"@type": "Article", "headline": title, "description": data.get("meta_description", ""),
         "url": page_url, "mainEntityOfPage": page_url, "datePublished": date_iso, "dateModified": date_iso,
         "author": {"@type": "Person", "name": "Rayan Polizzi", "url": f"{SITE_URL}/"},
         "publisher": {"@type": "Organization", "name": "Etrah", "url": f"{SITE_URL}/",
                       "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/favicon.svg"}},
         "inLanguage": "fr-FR", "image": hero_url,
         **({"keywords": data["keyword"]} if data.get("keyword") else {})},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Accueil", "item": f"{SITE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "Magazine", "item": f"{SITE_URL}/magazine.html"},
            {"@type": "ListItem", "position": 3, "name": title, "item": page_url}]},
    ]
    faq = [i for s in data.get("sections", []) if s.get("type") == "faq"
           for i in s.get("items", []) if isinstance(i, dict) and i.get("q") and i.get("a")]
    if faq:
        graph.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": i["q"], "acceptedAnswer": {"@type": "Answer", "text": strip_md(i["a"])}}
            for i in faq]})
    # échappe "</" pour qu'aucun texte ne puisse fermer la balise <script>
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")

ARTICLE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title_tag}</title>
<meta name="description" content="{meta_desc}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta property="og:title" content="{title_esc}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:type" content="article">
<meta property="og:image" content="{hero_url}">
<meta property="og:image:alt" content="{hero_alt}">
<meta name="twitter:card" content="summary_large_image">
<meta property="article:published_time" content="{date_iso}T09:00:00+02:00">
<meta property="article:modified_time" content="{date_iso}T09:00:00+02:00">
<meta property="article:author" content="Rayan Polizzi">
<meta name="author" content="Rayan Polizzi">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="Etrah">
<link rel="canonical" href="{page_url}">
<meta property="og:url" content="{page_url}">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600&family=Josefin+Sans:wght@100;200;300&family=Pinyon+Script&display=swap"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600&family=Josefin+Sans:wght@100;200;300&family=Pinyon+Script&display=swap" media="print" onload="this.media='all'"><noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600&family=Josefin+Sans:wght@100;200;300&family=Pinyon+Script&display=swap"></noscript>
<script type="application/ld+json">
{json_ld}
</script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--ink:#1a1612;--ink2:#2d2620;--ink3:#3a2e24;--cream:#f5f0e8;--cream2:#ede8dc;--gold:#7f6218;--gold2:#d4aa40;--white:#fdfaf5}}
html{{scroll-behavior:smooth;-webkit-font-smoothing:antialiased}}
body{{background:var(--white);color:var(--ink);font-family:'Cormorant Garamond',serif;overflow-x:hidden}}
#pb{{position:fixed;top:0;left:0;height:2px;background:var(--gold);z-index:9999;width:0%;transition:width .1s}}
nav{{position:fixed;top:0;left:0;right:0;z-index:500;padding:20px 52px;display:flex;align-items:center;justify-content:space-between;background:rgba(253,250,245,.96);backdrop-filter:blur(20px);border-bottom:1px solid rgba(184,146,42,.12)}}
.logo{{font-family:'Pinyon Script',cursive;font-size:34px;color:var(--ink);text-decoration:none;line-height:1}}
.back{{font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:8px;letter-spacing:5px;text-transform:uppercase;color:var(--ink3);text-decoration:none;transition:color .3s}}
.back:hover{{color:var(--gold)}}
.hero{{position:relative;height:520px;overflow:hidden}}
.hero img{{width:100%;height:100%;object-fit:cover;filter:brightness(.78)}}
.hero::after{{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(26,22,18,.05) 0%,rgba(26,22,18,.72) 100%)}}
.hc{{position:absolute;bottom:60px;left:50%;transform:translateX(-50%);width:100%;max-width:820px;padding:0 40px;z-index:1;text-align:center}}
.hcat{{font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:8px;letter-spacing:8px;text-transform:uppercase;color:var(--gold2);margin-bottom:18px;display:block}}
.htitle{{font-style:italic;font-weight:300;font-size:clamp(26px,4.5vw,54px);color:var(--white);line-height:1.1}}
.wrap{{max-width:740px;margin:0 auto;padding:64px 40px 0}}
.meta{{display:flex;align-items:center;gap:20px;margin-bottom:48px;padding-bottom:22px;border-bottom:1px solid rgba(184,146,42,.15)}}
.mdate{{font-family:'Josefin Sans',sans-serif;font-weight:100;font-size:8px;letter-spacing:4px;text-transform:uppercase;color:var(--ink3)}}
.mtime{{font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:8px;letter-spacing:4px;text-transform:uppercase;color:var(--gold)}}
.msep{{width:1px;height:14px;background:rgba(184,146,42,.3)}}
.intro{{font-size:20px;color:var(--ink2);line-height:1.9;margin-bottom:44px;font-style:italic;border-left:2px solid var(--gold);padding-left:24px}}
.toc{{background:rgba(184,146,42,.04);border:1px solid rgba(184,146,42,.15);padding:24px 28px;margin-bottom:44px}}
.toc-lbl{{font-family:'Josefin Sans',sans-serif;font-weight:300;font-size:8px;letter-spacing:6px;text-transform:uppercase;color:var(--gold);margin-bottom:14px}}
.toc ol{{list-style:none;display:flex;flex-direction:column;gap:8px}}
.toc a{{font-style:italic;font-size:17px;color:var(--ink2);text-decoration:none;transition:color .25s}}
.toc a:hover{{color:var(--gold)}}
.body h2{{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:30px;color:var(--ink);margin:52px 0 18px;line-height:1.2}}
.body p{{font-size:18px;color:var(--ink2);line-height:1.95;margin-bottom:24px}}
.body strong{{font-weight:600;color:var(--ink)}}
.body em{{font-style:italic;color:var(--ink3)}}
.body ul{{list-style:none;margin:0 0 28px;padding:0}}
.body ul li{{font-size:17px;color:var(--ink2);line-height:1.85;padding:10px 0 10px 24px;position:relative;border-bottom:1px solid rgba(184,146,42,.07)}}
.body ul li:last-child{{border-bottom:none}}
.body h3{{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:22px;color:var(--ink);margin:30px 0 10px;line-height:1.3}}
.body a{{color:var(--gold);text-decoration:underline;text-underline-offset:3px}}
.crumbs{{font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:9px;letter-spacing:3px;text-transform:uppercase;color:var(--ink3);margin-bottom:18px}}
.crumbs a{{color:var(--ink3);text-decoration:none}}.crumbs a:hover{{color:var(--gold)}}
.body ul li::before{{content:'◇';position:absolute;left:0;color:var(--gold);font-size:10px;line-height:2.2}}
.quote{{border-left:2px solid var(--gold);padding:22px 32px;margin:44px 0;background:rgba(184,146,42,.04)}}
.quote p{{font-style:italic;font-size:20px;color:var(--ink);margin:0;line-height:1.75}}
.quote cite{{font-family:'Josefin Sans',sans-serif;font-weight:100;font-size:8px;letter-spacing:4px;text-transform:uppercase;color:var(--ink3);display:block;margin-top:12px}}
.stat{{background:linear-gradient(135deg,var(--ink) 0%,#2d2010 100%);padding:28px 36px;margin:40px 0;display:flex;align-items:center;gap:28px}}
.stat-n{{font-family:'Cormorant Garamond',serif;font-weight:300;font-size:52px;color:var(--gold2);line-height:1;flex-shrink:0}}
.stat-t{{font-style:italic;font-size:17px;color:rgba(253,250,245,.82);line-height:1.75}}
.article-form-cta{{max-width:740px;margin:0 auto;padding:0 40px 48px}}
.afc-inner{{border:1px solid rgba(184,146,42,.18);padding:36px 40px;background:rgba(184,146,42,.03);text-align:center}}
.afc-eyebrow{{font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:7px;letter-spacing:7px;text-transform:uppercase;color:var(--gold);margin-bottom:12px}}
.afc-title{{font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:300;font-size:26px;color:var(--ink);line-height:1.2;margin-bottom:10px}}
.afc-sub{{font-family:'Cormorant Garamond',serif;font-style:italic;font-size:15px;color:var(--ink3);line-height:1.7;margin-bottom:24px}}
.afc-btn{{display:inline-block;font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:8px;letter-spacing:5px;text-transform:uppercase;color:var(--white);background:var(--ink);padding:13px 32px;text-decoration:none;transition:background .3s}}
.afc-btn:hover{{background:var(--gold)}}
.related{{max-width:740px;margin:0 auto;padding:0 40px 64px}}
.rl{{padding-top:28px;border-top:1px solid rgba(184,146,42,.12);margin-bottom:24px;font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:8px;letter-spacing:7px;text-transform:uppercase;color:var(--gold)}}
.rg{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.rc{{text-decoration:none;display:flex;flex-direction:column;border:1px solid rgba(184,146,42,.12);overflow:hidden;transition:transform .3s,box-shadow .3s;background:var(--white)}}
.rc:hover{{transform:translateY(-3px);box-shadow:0 10px 30px rgba(0,0,0,.08)}}
.rc img{{width:100%;aspect-ratio:4/3;object-fit:cover;display:block;transition:transform .5s}}
.rc:hover img{{transform:scale(1.03)}}
.rcb{{padding:14px 16px 16px;display:flex;flex-direction:column;gap:6px}}
.rcd{{font-family:'Josefin Sans',sans-serif;font-weight:100;font-size:7px;letter-spacing:3px;text-transform:uppercase;color:var(--ink3)}}
.rct{{font-weight:600;font-size:15px;color:var(--ink);line-height:1.3}}
.rca{{font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:7px;letter-spacing:3px;text-transform:uppercase;color:var(--gold);margin-top:4px}}
.fc{{background:var(--ink);padding:72px 40px;text-align:center}}
.fci{{max-width:560px;margin:0 auto}}
.fco{{display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:28px}}
.fcl{{width:40px;height:1px;background:linear-gradient(to right,transparent,rgba(184,146,42,.5))}}
.fcd{{width:6px;height:6px;border:1px solid rgba(184,146,42,.6);transform:rotate(45deg)}}
.fct{{font-style:italic;font-weight:300;font-size:clamp(28px,4vw,40px);color:var(--white);line-height:1.2;margin-bottom:32px}}
.fct strong{{font-style:normal;font-weight:600;color:var(--gold2)}}
.fcb{{font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:9px;letter-spacing:5px;text-transform:uppercase;color:var(--white);background:var(--gold);border:1px solid var(--gold);padding:16px 40px;text-decoration:none;display:inline-block;transition:all .35s}}
.fcb:hover{{background:var(--gold2)}}
.fcn{{font-family:'Josefin Sans',sans-serif;font-weight:100;font-size:7px;letter-spacing:4px;text-transform:uppercase;color:rgba(253,250,245,.35);display:block;margin-top:16px}}
footer{{background:var(--white);border-top:1px solid rgba(184,146,42,.12);padding:20px 52px;display:flex;align-items:center;justify-content:space-between}}
.ftc{{font-family:'Josefin Sans',sans-serif;font-weight:100;font-size:7px;letter-spacing:3px;text-transform:uppercase;color:var(--ink);opacity:.85}}
.ftl{{display:flex;gap:24px}}
.ftl a{{font-family:'Josefin Sans',sans-serif;font-weight:100;font-size:7px;letter-spacing:3px;text-transform:uppercase;color:var(--ink);opacity:.75;text-decoration:none;transition:color .3s}}
.ftl a:hover{{color:var(--gold)}}
.author{{max-width:740px;margin:0 auto;padding:0 40px 48px}}
.author-inner{{border:1px solid rgba(184,146,42,.15);padding:24px 32px;display:flex;align-items:center;gap:24px;background:rgba(184,146,42,.03)}}
.author-txt{{}}
.author-by{{font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:7px;letter-spacing:5px;text-transform:uppercase;color:var(--ink3);margin-bottom:4px}}
.author-name{{font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:300;font-size:22px;color:var(--ink);line-height:1.2;margin-bottom:2px}}
.author-role{{font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:7px;letter-spacing:4px;text-transform:uppercase;color:var(--gold)}}
@media(max-width:768px){{nav{{padding:16px 20px}}.hero{{height:360px}}.hc{{bottom:32px;padding:0 20px}}.wrap{{padding:40px 20px 0}}.cta-mid{{padding:0 20px 40px}}.cta-inner{{padding:24px 20px}}.related{{padding:0 20px 44px}}.rg{{grid-template-columns:1fr}}.fc{{padding:52px 20px}}footer{{padding:16px 20px;flex-direction:column;gap:10px;align-items:flex-start}}}}
.mid-img,.rc-img img{{height:auto}}
.related .rc img{{width:100%;height:auto;aspect-ratio:4/3;object-fit:cover}}
.see-also{{font-style:italic}}
</style>
</head>
<body>
<div id="pb"></div>
<nav><a class="logo" href="/">Etrah</a><a class="back" href="magazine.html">← Magazine</a></nav>

<div style="padding-top:65px">
  <div class="hero">
    <img src="{hero_url}" alt="{hero_alt}" width="1400" height="788" fetchpriority="high">
    <div class="hc">
      <span class="hcat">{category}</span>
      <h1 class="htitle">{title_esc}</h1>
    </div>
  </div>

  <div class="wrap">
    <nav class="crumbs" aria-label="Fil d'Ariane" style="position:static;padding:0;background:none;border:0;backdrop-filter:none;display:block"><a href="/">Accueil</a> › <a href="magazine.html">Magazine</a> › <span>{title_esc}</span></nav>
    <div class="meta">
      <span class="mdate">{date_fr}</span>
      <div class="msep"></div>
      <span class="mtime">{read_time}</span>
    </div>
    <p class="intro">{intro}</p>
    <div class="body" id="ab">
{body}
    </div>
  </div>

  <div class="article-form-cta">
    <div class="afc-inner">
      <p class="afc-eyebrow">Prêts à vous lancer ?</p>
      <h3 class="afc-title">Démarrez votre projet<br>en 2 minutes</h3>
      <p class="afc-sub">Dites-nous tout sur votre mariage — nous revenons vers vous sous 24h avec une proposition personnalisée.</p>
      <a class="afc-btn" href="/#contact">Démarrer mon projet →</a>
    </div>
  </div>


  <div class="author">
    <div class="author-inner">
      <div class="author-avatar" style="width:64px!important;height:64px!important;min-width:64px;min-height:64px;max-width:64px;max-height:64px;border-radius:50%;overflow:hidden;border:2px solid rgba(184,146,42,.35);flex-shrink:0;display:block"><img src="rayan-polizzi-avatar.webp" width="64" height="64" loading="lazy" decoding="async" alt="Rayan Polizzi, fondateur d'Etrah" style="width:64px;height:64px;object-fit:cover;object-position:45% 75%;filter:brightness(1.4) contrast(1.1);display:block"></div>
      <div class="author-txt">
        <p class="author-by">Rédigé par</p>
        <p class="author-name">Rayan Polizzi</p>
        <p class="author-role">Fondateur · Etrah</p>
      </div>
    </div>
  </div>

{related}
  <div class="fc"><div class="fci">
    <div class="fco"><div class="fcl"></div><div class="fcd"></div><div class="fcl" style="background:linear-gradient(to left,transparent,rgba(184,146,42,.5))"></div></div>
    <h2 class="fct">Votre mariage mérite<br>un site <strong>inoubliable</strong></h2>
    <a class="fcb" href="/#contact">Démarrer mon projet</a>
    <span class="fcn">Sur-mesure · 500€ · Livraison en 10 jours</span>
  </div></div>
</div>

<footer>
  <span class="ftc">© 2026 Etrah · Tous droits réservés</span>
  <div class="ftl">
    <a href="mentions-legales.html">Mentions légales</a>
    <a href="politique-confidentialite.html">Confidentialité</a>
    <a href="cgv.html">CGV</a>
  </div>
</footer>

<script>
(function(){{var b=document.getElementById('pb');if(!b)return;function u(){{var e=document.documentElement,h=e.scrollHeight-e.clientHeight,p=h>0?(e.scrollTop||document.body.scrollTop)/h*100:0;b.style.width=Math.min(p,100)+'%'}}window.addEventListener('scroll',u,{{passive:true}});u();}})();
(function(){{var b=document.getElementById('ab');if(!b)return;var hs=b.querySelectorAll('h2');if(hs.length<2)return;var t=document.createElement('div');t.className='toc';var l=document.createElement('p');l.className='toc-lbl';l.textContent='Dans cet article';t.appendChild(l);var ol=document.createElement('ol');hs.forEach(function(h,i){{h.id='s'+i;var li=document.createElement('li');var a=document.createElement('a');a.href='#s'+i;a.textContent=h.textContent;li.appendChild(a);ol.appendChild(li);}});t.appendChild(ol);b.insertBefore(t,b.firstChild);}})();
</script>
</body>
</html>"""

def build_html(title, data, slug, hero_url, date_fr, date_iso, related_html=""):
    body = "\n".join(section_html(s) for s in data.get("sections", []))
    page_url = f"{SITE_URL}/{slug}.html"
    title_tag = f"{title} | Etrah" if len(title) <= 52 else title
    return ARTICLE_TEMPLATE.format(
        title_tag   = html.escape(title_tag),
        json_ld     = json_ld(title, data, page_url, hero_url, date_iso),
        title_esc   = html.escape(title),
        meta_desc   = html.escape(data.get("meta_description", "")),
        hero_url    = hero_url,
        hero_alt    = html.escape(data.get("hero_alt", title)),
        category    = html.escape(data.get("category", "Magazine")),
        date_fr     = date_fr,
        date_iso    = date_iso,
        read_time   = html.escape(data.get("read_time", "5 min de lecture")),
        intro       = html.escape(data.get("intro", "")),
        body        = body,
        page_url    = page_url,
        related     = related_html,
    )

# ── MISE À JOUR SITEMAP ───────────────────────────────────────────────────────
def update_sitemap(slug, date_iso):
    p = BASE_DIR / "sitemap.xml"
    c = p.read_text(encoding="utf-8")
    if f"{SITE_URL}/{slug}.html" in c:
        return
    entry = f"""  <url>
    <loc>{SITE_URL}/{slug}.html</loc>
    <lastmod>{date_iso}</lastmod>
  </url>"""
    marker = "  <!-- Pages légales -->"
    if marker in c:
        c = c.replace(marker, entry + "\n\n" + marker)
    else:
        c = c.replace("</urlset>", entry + "\n\n</urlset>")
    p.write_text(c, encoding="utf-8")

def touch_sitemap(files, date_iso):
    """Met à jour <lastmod> des pages modifiées (accueil, magazine, articles qui reçoivent un lien)."""
    p = BASE_DIR / "sitemap.xml"
    c = p.read_text(encoding="utf-8")
    for f in files:
        loc = f"{SITE_URL}/" if f == "index.html" else f"{SITE_URL}/{f}"
        c = re.sub(rf"(<loc>{re.escape(loc)}</loc>\s*<lastmod>)[^<]*(</lastmod>)", rf"\g<1>{date_iso}\g<2>", c)
    p.write_text(c, encoding="utf-8")


# ── MAILLAGE INTERNE ──────────────────────────────────────────────────────────
NON_ARTICLES = {"index.html", "404.html", "studio.html", "generateur-articles.html",
                "formulaire-maries.html", "magazine.html", "mentions-legales.html",
                "politique-confidentialite.html", "cgv.html"}
STOP = set("le la les un une des de du d l et ou a au aux en pour par sur avec votre vos son sa ses "
           "ce ces qui que quoi comment pourquoi quand est sont plus tout tous site mariage web".split())

def load_articles():
    """Liste des articles publiés (lus depuis leurs données structurées)."""
    arts = []
    for f in sorted(BASE_DIR.glob("*.html")):
        if f.name in NON_ARTICLES:
            continue
        c = f.read_text(encoding="utf-8")
        for block in re.findall(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', c, re.S):
            try:
                d = json.loads(block)
            except Exception:
                continue
            # format simple {"@type":"Article"} ou format {"@graph":[...]}
            d = next((g for g in d.get("@graph", []) if g.get("@type") == "Article"), d)
            if d.get("@type") == "Article":
                desc = re.search(r'<meta name="description" content="([^"]*)"', c)
                img = re.search(r'<meta property="og:image" content="([^"]*)"', c)
                arts.append({"file": f.name, "title": html.unescape(d.get("headline", f.stem)),
                             "desc": html.unescape(desc.group(1)) if desc else "",
                             "date": d.get("datePublished", ""), "img": img.group(1) if img else HERO_IMAGES[0]})
                break
    return arts

def words(t):
    """Racines des mots significatifs (6 premières lettres : « photos »/« photographe » se rejoignent)."""
    t = slugify(t).replace("-", " ")
    return {w[:6] for w in t.split() if len(w) > 2 and w not in STOP}

def most_related(title, arts, n=3, exclude=None):
    """Articles les plus proches par le sujet ; à égalité, les plus récents d'abord."""
    w = words(title)
    pool = [a for a in arts if a["file"] != exclude]
    pool.sort(key=lambda a: a["date"], reverse=True)          # récents d'abord…
    pool.sort(key=lambda a: -len(w & words(a["title"] + " " + a["desc"])))  # …puis par proximité (tri stable)
    return pool[:n]

def month_fr(iso):
    try:
        return f"{MONTH_FR[iso[5:7]]} {iso[:4]}"
    except Exception:
        return ""

def related_block(rel):
    if not rel:
        return ""
    cards = ""
    for a in rel:
        thumb = a["img"].replace("w=1400", "w=400")
        cards += (f'      <a class="rc" href="{a["file"]}">\n'
                  f'        <img src="{thumb}" alt="{html.escape(a["title"])}" loading="lazy" width="400" height="300">\n'
                  f'        <div class="rcb"><span class="rcd">{month_fr(a["date"])}</span>'
                  f'<span class="rct">{html.escape(a["title"])}</span><span class="rca">Lire →</span></div>\n      </a>\n')
    return ('  <div class="related">\n    <div class="rl">À lire aussi</div>\n    <div class="rg">\n'
            + cards + '    </div>\n    <p style="text-align:center;margin-top:24px"><a href="magazine.html">Tous les articles du magazine →</a></p>\n  </div>\n')

def add_backlinks(new_file, new_title, rel, max_links=3):
    """Ajoute un lien vers le nouvel article dans les anciens articles les plus proches.
    Renvoie la liste des fichiers modifiés."""
    done = []
    for a in rel:
        if len(done) >= max_links:
            break
        p = BASE_DIR / a["file"]
        c = p.read_text(encoding="utf-8")
        if f'href="{new_file}"' in c or c.count('class="see-also"') >= 4:
            continue   # déjà lié, ou assez de liens « À lire aussi » sur cet article
        line = f'<p class="see-also">À lire aussi : <a href="{new_file}">{html.escape(new_title)}</a></p>\n'
        if '<div class="article-form-cta">' in c:
            c = c.replace('<div class="article-form-cta">', line + '  <div class="article-form-cta">', 1)
        elif '<div class="author">' in c:
            c = c.replace('<div class="author">', line + '  <div class="author">', 1)
        else:
            continue
        p.write_text(c, encoding="utf-8")
        done.append(a["file"])
    return done

def build_magazine(arts):
    """Page hub listant tous les articles (évite les articles orphelins)."""
    arts = sorted(arts, key=lambda a: a["date"], reverse=True)
    items = ""
    for a in arts:
        thumb = a["img"].replace("w=1400", "w=600")
        items += (f'  <article class="mc"><a href="{a["file"]}">'
                  f'<img src="{thumb}" alt="{html.escape(a["title"])}" loading="lazy" width="600" height="338">'
                  f'<span class="md">{month_fr(a["date"])}</span><h2>{html.escape(a["title"])}</h2>'
                  f'<p>{html.escape(a["desc"])}</p></a></article>\n')
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Magazine Etrah",
          "url": f"{SITE_URL}/magazine.html",
          "mainEntity": {"@type": "ItemList", "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "url": f"{SITE_URL}/{a['file']}", "name": a["title"]}
              for i, a in enumerate(arts)]}}
    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Magazine mariage : conseils pour votre site de mariage | Etrah</title>
<meta name="description" content="Tous les articles du magazine Etrah : organisation, budget, faire-part digital, RSVP et idées pour créer un site de mariage qui vous ressemble.">
<link rel="canonical" href="{SITE_URL}/magazine.html">
<meta property="og:url" content="{SITE_URL}/magazine.html"><meta property="og:title" content="Magazine mariage | Etrah"><meta property="og:image" content="{SITE_URL}/og-image.jpg">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>
:root{{--ink:#1a1612;--ink3:#3a2e24;--gold:#7f6218;--white:#fdfaf5}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--white);color:var(--ink);font-family:Georgia,'Times New Roman',serif}}
nav{{display:flex;justify-content:space-between;align-items:center;padding:20px 40px;border-bottom:1px solid rgba(184,146,42,.2)}}
nav a{{color:var(--ink);text-decoration:none}} .logo{{font-size:28px}} .back{{font-size:13px;letter-spacing:3px;text-transform:uppercase;color:var(--gold)}}
header{{max-width:1100px;margin:0 auto;padding:56px 24px 24px;text-align:center}}
h1{{font-weight:400;font-style:italic;font-size:clamp(32px,5vw,52px)}} header p{{color:var(--ink3);margin-top:14px;font-size:18px;line-height:1.6}}
.grid{{max-width:1100px;margin:0 auto;padding:24px;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:28px}}
.mc a{{display:block;text-decoration:none;color:inherit}} .mc img{{width:100%;height:auto;aspect-ratio:16/9;object-fit:cover;display:block}}
.md{{display:block;margin-top:14px;font-size:12px;letter-spacing:3px;text-transform:uppercase;color:var(--gold)}}
.mc h2{{font-weight:400;font-size:22px;margin:8px 0;line-height:1.3}} .mc p{{color:var(--ink3);line-height:1.6;font-size:16px}}
.cta{{text-align:center;padding:56px 24px}} .cta a{{display:inline-block;background:#b8922a;color:#fff;padding:16px 36px;text-decoration:none;letter-spacing:3px;text-transform:uppercase;font-size:13px}}
footer{{text-align:center;padding:24px;font-size:13px;color:var(--ink3)}} footer a{{color:var(--ink3);margin:0 8px}}
</style>
</head>
<body>
<nav><a class="logo" href="/">Etrah</a><a class="back" href="/">← Accueil</a></nav>
<header><h1>Le magazine du site de mariage</h1>
<p>Conseils d'organisation, budget, faire-part digital et RSVP : tout pour préparer un site de mariage qui vous ressemble.</p></header>
<main class="grid">
{items}</main>
<div class="cta"><a href="/#contact">Démarrer mon projet</a></div>
<footer><a href="mentions-legales.html">Mentions légales</a><a href="politique-confidentialite.html">Confidentialité</a><a href="cgv.html">CGV</a></footer>
</body>
</html>
"""
    (BASE_DIR / "magazine.html").write_text(page, encoding="utf-8")

def update_llms(file, title):
    p = BASE_DIR / "llms.txt"
    if not p.exists():
        return
    c = p.read_text(encoding="utf-8")
    url = f"{SITE_URL}/{file}"
    if url in c or "## Magazine" not in c:
        return
    c = c.replace("## Magazine\n\n", f"## Magazine\n\n- [{title}]({url})\n", 1)
    p.write_text(c, encoding="utf-8")

# ── MISE À JOUR INDEX ─────────────────────────────────────────────────────────
def update_index(title, slug, category, date_fr, hero_url, excerpt):
    p = BASE_DIR / "index.html"
    c = p.read_text(encoding="utf-8")
    thumb = hero_url.replace("w=1400", "w=800")

    # Nouvel article — toujours en 1ère position (gauche), sans delay
    new_card = f"""    <!-- {html.escape(title)} -->
    <article class="blog-card rv" onclick="window.location='{slug}.html'" style="cursor:pointer">
      <div class="blog-img">
        <img src="{thumb}" alt="{html.escape(title)}" loading="lazy">
      </div>
      <div class="blog-body">
        <p class="blog-cat">{html.escape(category)}</p>
        <h3 class="blog-title">{html.escape(title)}</h3>
        <p class="blog-excerpt">{html.escape(excerpt)}</p>
        <div class="blog-footer">
          <span class="blog-date">{date_fr}</span>
          <a class="blog-read" href="{slug}.html">Lire l'article →</a>
        </div>
      </div>
    </article>"""

    # Extraire les articles existants dans la grid
    grid_m = re.search(r'(<div class="blog-grid">)(.*?)(</div>\s*</section>)', c, re.DOTALL)
    if not grid_m:
        # Fallback simple si structure non trouvée
        marker = '<div class="blog-grid">'
        c = c.replace(marker, marker + "\n\n" + new_card + "\n")
        p.write_text(c, encoding="utf-8")
        return

    grid_content = grid_m.group(2)
    # Récupérer les articles existants (en ordre d'apparition)
    existing = re.findall(r'(<article class="blog-card[^"]*".*?</article>)', grid_content, re.DOTALL)

    # Garder seulement les 2 premiers (ils passent en positions 2 et 3)
    kept = existing[:2]

    # Appliquer les transition-delays : pos 1=rien, pos 2=.1s, pos 3=.2s
    delays = ['', 'transition-delay:.1s;', 'transition-delay:.2s;']
    ordered_cards = [new_card]
    for i, art in enumerate(kept):
        # Supprimer tout transition-delay existant dans le style
        art = re.sub(r'transition-delay:[^;]+;', '', art)
        # Injecter le bon delay
        art = re.sub(r'style="(cursor:pointer)"', f'style="{delays[i+1]}\\1"', art)
        ordered_cards.append(art)

    new_grid_content = '\n\n'.join(ordered_cards) + '\n\n  '
    c = c[:grid_m.start(2)] + '\n\n' + new_grid_content + c[grid_m.end(2):]
    p.write_text(c, encoding="utf-8")

# ── MAIN ──────────────────────────────────────────────────────────────────────
def audit_page(path):
    """Vérifie la page générée : balises SEO et liens internes qui pointent vers des pages existantes."""
    c = path.read_text(encoding="utf-8")
    problems = []
    for tag, rx in [("title", r"<title>[^<]{10,}</title>"), ("meta description", r'<meta name="description" content="[^"]{100,}"'),
                    ("canonical", r'<link rel="canonical" href="https://www\.site-mariage\.com/[^"]+\.html"'),
                    ("h1 unique", r"<h1[ >]")]:
        if not re.search(rx, c):
            problems.append(f"{tag} manquant")
    if len(re.findall(r"<h1[ >]", c)) != 1:
        problems.append("il doit y avoir exactement un H1")
    for block in re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', c, re.S):
        try:
            json.loads(block)
        except Exception as e:
            problems.append(f"JSON-LD invalide ({e})")
    body = c.split('id="ab"', 1)[-1].split('class="article-form-cta"', 1)[0]
    for href in re.findall(r'href="([^"#:]+\.html)"', body):
        if not (path.parent / href).exists():
            problems.append(f"lien cassé : {href}")
    return problems

def main():
    global BASE_DIR
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        # Test complet sans toucher au site : on travaille sur une copie temporaire
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp(prefix="etrah-test-"))
        for f in list(BASE_DIR.glob("*.html")) + [BASE_DIR / "sitemap.xml", BASE_DIR / "llms.txt"]:
            if f.exists():
                shutil.copy(f, tmp / f.name)
        BASE_DIR = tmp
        print(f"MODE TEST : rien n'est publié (copie de travail : {tmp})")

    # Anthropic SDK
    try:
        import anthropic
    except ImportError:
        print("Installation anthropic...")
        os.system(f"{sys.executable} -m pip install anthropic -q")
        import anthropic

    # Clé API (jamais de saisie interactive en automatique)
    api_key = os.environ.get("ANTHROPIC_API_KEY") or ("" if not sys.stdin.isatty() else input("Clé API Anthropic : ").strip())
    if not api_key:
        sys.exit("❌ Clé API manquante (secret GitHub ANTHROPIC_API_KEY)")
    client = anthropic.Anthropic(api_key=api_key)

    # Titre(s)
    if args:
        titles = [" ".join(args)]
    else:
        raw = input("Titre(s) de l'article (sépare par | pour plusieurs) : ").strip()
        titles = [t.strip() for t in raw.split("|") if t.strip()]

    failed = 0
    for title in titles:
        print(f"\n✦  «{title}»")
        print("   → Génération du contenu...")
        arts = load_articles()
        existing_txt = "\n".join(f"- {a['title']} → {a['file']}" for a in arts)
        ALLOWED_LINKS.update(a["file"] for a in arts)
        try:
            data = generate(title, client, existing_txt)
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            failed += 1
            continue

        slug     = slugify(data.get("slug") or title)[:80].strip("-") or slugify(title)
        hero_url = pick_hero(slug)
        excerpt  = data.get("excerpt") or data.get("meta_description", "")
        category = data.get("category", "Magazine")

        if (BASE_DIR / f"{slug}.html").exists():
            slug = f"{slug}-{TODAY[:7]}"
        rel = most_related(title, arts, 3)
        html_content = build_html(title, data, slug, hero_url, DATE_FR, TODAY, related_block(rel))

        # Sauvegarder article puis l'auditer avant de toucher au reste du site
        out = BASE_DIR / f"{slug}.html"
        out.write_text(html_content, encoding="utf-8")
        issues = audit_page(out)
        if issues:
            out.unlink()
            print("   ❌ page refusée : " + " ; ".join(issues))
            failed += 1
            continue
        links = internal_links(data)
        print(f"   ✓ {slug}.html  ({len(html_content)//1024}KB) — mot-clé : {data.get('keyword','?')} — "
              f"{len(set(links))} liens internes : {', '.join(sorted(set(links)))}")

        # Sitemap
        try:
            update_sitemap(slug, TODAY)
            print("   ✓ sitemap.xml mis à jour")
        except Exception as e:
            print(f"   ⚠ sitemap : {e}")

        # Index
        try:
            update_index(title, slug, category, DATE_FR, hero_url, excerpt)
            print("   ✓ index.html mis à jour")
        except Exception as e:
            print(f"   ⚠ index : {e}")

        # Maillage : liens depuis les anciens articles proches + hub + llms.txt
        touched = []
        try:
            # liens retour : on parcourt plus de candidats que nécessaire (certains peuvent être déjà pleins)
            touched = add_backlinks(f"{slug}.html", title, most_related(title, arts, 6))
            build_magazine(load_articles())
            update_llms(f"{slug}.html", title)
            touch_sitemap(touched + ["index.html", "magazine.html"], TODAY)
            print(f"   ✓ maillage : lien ajouté dans {', '.join(touched) or 'aucun article'}, magazine.html à jour")
        except Exception as e:
            print(f"   ⚠ maillage : {e}")

        if dry_run:
            print(f"   ✓ TEST RÉUSSI — article de test : {out}")
            out_dir = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--out=")), "")
            if out_dir:
                import shutil
                dst = Path(out_dir); dst.mkdir(parents=True, exist_ok=True)
                for f in [out.name, "sitemap.xml", "magazine.html", "index.html", "llms.txt"] + touched:
                    if (BASE_DIR / f).exists():
                        shutil.copy(BASE_DIR / f, dst / f)
                (dst / "article.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if failed:
        sys.exit(f"❌ {failed} article(s) non générés")


if __name__ == "__main__":
    main()
