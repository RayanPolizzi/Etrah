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
]

# ── HELPERS ───────────────────────────────────────────────────────────────────
def slugify(t):
    s = t.lower()
    for a, b in [("àáâãä","a"),("èéêë","e"),("ìíîï","i"),("òóôõö","o"),("ùúûü","u"),("ç","c"),("ñ","n")]:
        for c in a: s = s.replace(c, b)
    s = re.sub(r"[^a-z0-9\s-]","",s)
    return re.sub(r"-+","-",re.sub(r"\s+","-",s.strip()))

def parse_inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*([^*]+)\*",     r"<em>\1</em>", t)
    return t

def pick_hero(slug):
    idx = int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(HERO_IMAGES)
    return HERO_IMAGES[idx]

# ── GÉNÉRATION DU CONTENU VIA CLAUDE ─────────────────────────────────────────
SYSTEM = (
    "Tu es rédacteur expert pour Etrah, agence française de sites de mariage sur-mesure (500€, "
    "livraison 10-14 jours, basé à Nice). Style : élégant, direct, orienté couples français, "
    "avec données concrètes et témoignages réalistes. SEO naturel."
)

PROMPT = """Génère un article de blog complet et SEO-optimisé pour le titre : "{title}"

Public : couples français qui planifient leur mariage.
Longueur : 900-1100 mots de contenu réel.
Structure : introduction percutante + 5-7 sections variées + conclusion orientée action.

Réponds UNIQUEMENT avec un JSON valide, structure exacte :

{{
  "slug": "slug-sans-accents-avec-tirets",
  "category": "Catégorie · Sous-catégorie",
  "meta_description": "Description SEO max 155 caractères",
  "read_time": "X min de lecture",
  "hero_alt": "Description courte de l'image idéale pour cet article",
  "intro": "2-3 phrases d'accroche percutantes en italique",
  "sections": [
    {{"type":"text",  "h2":"Titre section", "paragraphs":["Para 1 avec **gras** possible.","Para 2..."]}},
    {{"type":"stat",  "number":"67%", "description":"Explication de la stat en une phrase précise."}},
    {{"type":"quote", "text":"Citation réaliste d'un couple fictif mais crédible.", "author":"Prénom & Prénom, Ville, mois 2026"}},
    {{"type":"list",  "h2":"Titre liste", "items":["**Item 1** — explication","**Item 2** — explication"]}},
    {{"type":"text",  "h2":"Autre section", "paragraphs":["..."]}},
    {{"type":"quote", "text":"Deuxième citation si pertinente.", "author":"Prénom & Prénom, Ville, 2026"}},
    {{"type":"text",  "h2":"Conclusion ou section finale", "paragraphs":["..."]}}
  ],
  "excerpt": "1-2 phrases pour la miniature sur la page d'accueil."
}}

Règles strictes :
- Stats réalistes et formulées avec précision
- Citations 100% françaises, crédibles, avec détails concrets
- Mentionner Etrah dans 1 section max, naturellement
- Slug en français sans accents ni caractères spéciaux
- Chaque section "text" : au moins 2 paragraphes"""

def generate(title, client):
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        system=SYSTEM,
        messages=[{"role":"user","content":PROMPT.format(title=title)}]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?","",raw)
    raw = re.sub(r"\n?```$","",raw)
    return json.loads(raw)

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
    elif t == "list":
        lis = "\n".join(f"<li>{parse_inline(i)}</li>" for i in s.get("items",[]))
        out += f"<ul>\n{lis}\n</ul>\n"
    return out

ARTICLE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title_esc}</title>
<meta name="description" content="{meta_desc}">
<meta property="og:title" content="{title_esc}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:type" content="article">
<meta property="og:image" content="{hero_url}">
<meta property="article:published_time" content="{date_iso}T09:00:00+02:00">
<meta property="article:modified_time" content="{date_iso}T09:00:00+02:00">
<meta property="article:author" content="Rayan Polizzi">
<link rel="canonical" href="{page_url}">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600&family=Josefin+Sans:wght@100;200;300&family=Pinyon+Script&display=swap" rel="stylesheet">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Article","headline":"{title_esc}","url":"{page_url}","datePublished":"{date_iso}","dateModified":"{date_iso}","author":{{"@type":"Person","name":"Rayan Polizzi","url":"{site_url}/"}},"publisher":{{"@type":"Organization","name":"Etrah","url":"{site_url}/","logo":{{"@type":"ImageObject","url":"{site_url}/favicon.svg"}}}},"inLanguage":"fr-FR","image":"{hero_url}"}}
</script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--ink:#1a1612;--ink2:#2d2620;--ink3:#3a2e24;--cream:#f5f0e8;--cream2:#ede8dc;--gold:#b8922a;--gold2:#d4aa40;--white:#fdfaf5}}
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
.body ul li::before{{content:'◇';position:absolute;left:0;color:var(--gold);font-size:10px;line-height:2.2}}
.quote{{border-left:2px solid var(--gold);padding:22px 32px;margin:44px 0;background:rgba(184,146,42,.04)}}
.quote p{{font-style:italic;font-size:20px;color:var(--ink);margin:0;line-height:1.75}}
.quote cite{{font-family:'Josefin Sans',sans-serif;font-weight:100;font-size:8px;letter-spacing:4px;text-transform:uppercase;color:var(--ink3);display:block;margin-top:12px}}
.stat{{background:linear-gradient(135deg,var(--ink) 0%,#2d2010 100%);padding:28px 36px;margin:40px 0;display:flex;align-items:center;gap:28px}}
.stat-n{{font-family:'Cormorant Garamond',serif;font-weight:300;font-size:52px;color:var(--gold2);line-height:1;flex-shrink:0}}
.stat-t{{font-style:italic;font-size:17px;color:rgba(253,250,245,.82);line-height:1.75}}
.cta-mid{{background:var(--cream2);padding:0 40px 60px;max-width:740px;margin:0 auto}}
.cta-inner{{border:1px solid rgba(184,146,42,.2);padding:36px 40px;text-align:center}}
.cta-ey{{font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:8px;letter-spacing:6px;text-transform:uppercase;color:var(--gold);margin-bottom:16px}}
.cta-title{{font-style:italic;font-weight:300;font-size:clamp(22px,3vw,30px);color:var(--ink);margin-bottom:28px;line-height:1.25}}
.cta-btn{{font-family:'Josefin Sans',sans-serif;font-weight:200;font-size:9px;letter-spacing:5px;text-transform:uppercase;color:var(--white);background:var(--gold);padding:16px 36px;text-decoration:none;display:inline-block;transition:background .3s}}
.cta-btn:hover{{background:var(--gold2)}}
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
@media(max-width:768px){{nav{{padding:16px 20px}}.hero{{height:360px}}.hc{{bottom:32px;padding:0 20px}}.wrap{{padding:40px 20px 0}}.cta-mid{{padding:0 20px 40px}}.cta-inner{{padding:24px 20px}}.related{{padding:0 20px 44px}}.rg{{grid-template-columns:1fr}}.fc{{padding:52px 20px}}footer{{padding:16px 20px;flex-direction:column;gap:10px;align-items:flex-start}}}}
</style>
</head>
<body>
<div id="pb"></div>
<nav><a class="logo" href="index.html">Etrah</a><a class="back" href="index.html">← Magazine</a></nav>

<div style="padding-top:65px">
  <div class="hero">
    <img src="{hero_url}" alt="{hero_alt}" loading="eager">
    <div class="hc">
      <span class="hcat">{category}</span>
      <h1 class="htitle">{title_esc}</h1>
    </div>
  </div>

  <div class="wrap">
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

  <div class="cta-mid"><div class="cta-inner">
    <p class="cta-ey">Etrah · Sur-mesure</p>
    <h2 class="cta-title">Votre site de mariage, unique et inoubliable</h2>
    <a class="cta-btn" href="index.html#contact">Démarrer mon projet</a>
  </div></div>

  <div class="related">
    <div class="rl">À lire aussi</div>
    <div class="rg">
      <a class="rc" href="combien-coute-site-mariage-2026.html">
        <img src="https://images.unsplash.com/photo-1606800052052-a08af7148866?w=400&q=85&auto=format&fit=crop" alt="Budget site mariage" loading="lazy">
        <div class="rcb"><span class="rcd">Mars 2026</span><span class="rct">Combien coûte vraiment un site de mariage en 2026 ?</span><span class="rca">Lire →</span></div>
      </a>
      <a class="rc" href="site-mariage-ou-faire-part-papier.html">
        <img src="https://images.unsplash.com/photo-1537633552985-df8429e8048b?w=400&q=85&auto=format&fit=crop" alt="Faire-part ou site mariage" loading="lazy">
        <div class="rcb"><span class="rcd">Janvier 2026</span><span class="rct">Site de mariage ou faire-part papier ?</span><span class="rca">Lire →</span></div>
      </a>
    </div>
  </div>

  <div class="fc"><div class="fci">
    <div class="fco"><div class="fcl"></div><div class="fcd"></div><div class="fcl" style="background:linear-gradient(to left,transparent,rgba(184,146,42,.5))"></div></div>
    <h2 class="fct">Votre mariage mérite<br>un site <strong>inoubliable</strong></h2>
    <a class="fcb" href="index.html#contact">Démarrer mon projet</a>
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

def build_html(title, data, slug, hero_url, date_fr, date_iso):
    body = "\n".join(section_html(s) for s in data.get("sections", []))
    return ARTICLE_TEMPLATE.format(
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
        page_url    = f"{SITE_URL}/{slug}.html",
        site_url    = SITE_URL,
    )

# ── MISE À JOUR SITEMAP ───────────────────────────────────────────────────────
def update_sitemap(slug, date_iso):
    p = BASE_DIR / "sitemap.xml"
    c = p.read_text(encoding="utf-8")
    entry = f"""  <url>
    <loc>{SITE_URL}/{slug}.html</loc>
    <lastmod>{date_iso}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>"""
    marker = "  <!-- Pages légales -->"
    if marker in c:
        c = c.replace(marker, entry + "\n\n" + marker)
    else:
        c = c.replace("</urlset>", entry + "\n\n</urlset>")
    p.write_text(c, encoding="utf-8")

# ── MISE À JOUR INDEX ─────────────────────────────────────────────────────────
def update_index(title, slug, category, date_fr, hero_url, excerpt):
    p = BASE_DIR / "index.html"
    c = p.read_text(encoding="utf-8")
    thumb = hero_url.replace("w=1400", "w=800")
    card = f"""    <!-- {html.escape(title)} -->
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
    marker = '<div class="blog-grid">'
    if marker in c:
        c = c.replace(marker, marker + "\n\n" + card + "\n")
    p.write_text(c, encoding="utf-8")

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    # Anthropic SDK
    try:
        import anthropic
    except ImportError:
        print("Installation anthropic...")
        os.system(f"{sys.executable} -m pip install anthropic -q")
        import anthropic

    # Clé API
    api_key = os.environ.get("ANTHROPIC_API_KEY") or input("Clé API Anthropic : ").strip()
    if not api_key:
        sys.exit("❌ Clé API manquante")
    client = anthropic.Anthropic(api_key=api_key)

    # Titre(s)
    if len(sys.argv) > 1:
        titles = [" ".join(sys.argv[1:])]
    else:
        raw = input("Titre(s) de l'article (sépare par | pour plusieurs) : ").strip()
        titles = [t.strip() for t in raw.split("|") if t.strip()]

    for title in titles:
        print(f"\n✦  «{title}»")
        print("   → Génération du contenu...")
        try:
            data = generate(title, client)
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            continue

        slug     = data.get("slug") or slugify(title)
        hero_url = pick_hero(slug)
        excerpt  = data.get("excerpt") or data.get("meta_description", "")
        category = data.get("category", "Magazine")

        html_content = build_html(title, data, slug, hero_url, DATE_FR, TODAY)

        # Sauvegarder article
        out = BASE_DIR / f"{slug}.html"
        out.write_text(html_content, encoding="utf-8")
        print(f"   ✓ {slug}.html  ({len(html_content)//1024}KB)")

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

        print(f"   → {SITE_URL}/{slug}.html")

    print("\n✦  Terminé. Déploie le dossier sur Netlify pour mettre en ligne.\n")

if __name__ == "__main__":
    main()
