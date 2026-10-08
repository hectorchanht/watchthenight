#!/usr/bin/env python3
"""Nightwatch gear site — static generator.

    python3 build.py            # build dist/
    python3 build.py --dump-sql # emit INSERTs for the D1 gear_picks table

Source of truth: src/products.json (+ src/site.json).
Amazon tag: env AMAZON_TAG wins, else src/site.json "amazon_tag", else yourtag-20 placeholder.
Retailer URLs starting with 'TODO:' render as 'link coming soon' placeholders.
"""
import datetime
import html
import json
import os
import secrets
import shutil
import sys
from urllib.parse import quote_plus

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
DIST = os.path.join(ROOT, "dist")
TODAY = datetime.date.today().isoformat()


def load(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return json.load(f)


def esc(s):
    return html.escape(str(s), quote=True)


SITE = load("site.json")
AMAZON_TAG = os.environ.get("AMAZON_TAG") or SITE.get("amazon_tag") or "yourtag-20"
PRODUCTS = load("products.json")["products"]
GUIDES = load("guides.json")["guides"]
CATS = SITE["categories"]
TONIGHT = None
_tonight_path = os.path.join(SRC, "tonight.json")
if os.path.exists(_tonight_path):
    with open(_tonight_path, encoding="utf-8") as _f:
        TONIGHT = json.load(_f)
DOMAIN = SITE["domain"]
BASE = f"https://{DOMAIN}"


def amazon_url(query):
    return f"https://www.amazon.com/s?k={quote_plus(query)}&tag={AMAZON_TAG}"


def retailer_url(r, product):
    u = r["url"]
    if u == "AMAZON":
        return amazon_url(product["amazon_query"])
    if u.startswith("TODO:"):
        return None
    return u


# ---------------------------------------------------------------- templates

NAV_LINKS = "".join(
    f'<a href="/category/{c}/">{esc(v["label"])}</a>' for c, v in CATS.items()
) + '<a href="/guides/">Guides</a>'

FOOTER = f"""
<footer>
  <div class="wrap">
    <p class="brand">{esc(SITE['brand'])}</p>
    <p class="disc">Affiliate disclosure: {esc(SITE['brand'])} is reader-supported. When you buy through links on our site we may earn an affiliate commission — it costs you nothing extra. As an Amazon Associate we earn from qualifying purchases. Prices shown are approximate; check the retailer for the live price.</p>
    <p class="fine"><a href="/about/">About</a> · <a href="/feed.xml">RSS</a> · <a href="/llms.txt">llms.txt</a> · <a href="mailto:{esc(SITE['email'])}">{esc(SITE['email'])}</a></p>
    <p class="fine">© {datetime.date.today().year} {esc(SITE['brand'])}. Look up.</p>
  </div>
</footer>"""


def page(title, desc, path, body, jsonld=None):
    canon = BASE + path
    jd = f'<script type="application/ld+json">{json.dumps(jsonld)}</script>' if jsonld else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {esc(SITE['brand'])}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE['brand'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canon}">
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#05070f">
<link rel="stylesheet" href="/style.css">
{jd}
</head>
<body>
<header>
  <div class="wrap nav">
    <a class="logo" href="/">✦ {esc(SITE['brand'])}</a>
    <nav>{NAV_LINKS}<a href="/about/">About</a></nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
{FOOTER}
</body>
</html>
"""


def card(p):
    price = f'<p class="price">around ${p["price_usd"]:,}</p>' if p.get("price_usd") else ""
    return f"""
<a class="card" href="/gear/{p['slug']}/">
  <p class="kicker">{esc(CATS[p['category']]['label'])}</p>
  <h3>{esc(p['name'])}</h3>
  <p class="tagline">{esc(p['tagline'])}</p>
  {price}
  <span class="cta">Read the pick →</span>
</a>"""


def buy_box(p):
    rows = []
    for r in p["retailers"]:
        url = retailer_url(r, p)
        if url:
            rows.append(
                f'<div class="buyrow"><div><strong>{esc(r["name"])}</strong>'
                f'<p>{esc(r.get("note", ""))}</p></div>'
                f'<a class="btn" href="{esc(url)}" rel="nofollow sponsored noopener" target="_blank">Check price</a></div>'
            )
        else:
            rows.append(
                f'<div class="buyrow"><div><strong>{esc(r["name"])}</strong>'
                f'<p>{esc(r.get("note", ""))}</p></div>'
                f'<span class="btn disabled">Link coming soon</span></div>'
            )
    return '<div class="buybox"><h2>Where to buy</h2>' + "".join(rows) + "</div>"


# ---------------------------------------------------------------- pages

def index_page():
    cats_html = "".join(
        f'<a class="card" href="/category/{c}/"><p class="kicker">{len([p for p in PRODUCTS if p["category"] == c])} picks</p>'
        f"<h3>{esc(v['label'])}</h3><p class='tagline'>{esc(v['blurb'])}</p>"
        f'<span class="cta">Browse →</span></a>'
        for c, v in CATS.items()
    )
    picks_html = "".join(card(p) for p in PRODUCTS)
    tonight_html = ""
    if TONIGHT:
        t = TONIGHT
        tonight_html = (
            '\n<section class="tonight">\n'
            f'  <h2>Tonight\'s sky <span class="date">{esc(t["date"])}</span></h2>\n'
            f'  <p class="moon">{t["emoji"]} <strong>{esc(t["phase"])}</strong> — {t["illumination_pct"]}% illuminated</p>\n'
            f'  <p class="tip">Tonight\'s tip: {esc(t["tip"])}</p>\n'
            "</section>"
        )
    body = f"""
<section class="hero">
  <p class="kicker">Citizen skywatch gear guide</p>
  <h1>{esc(SITE['tagline'])}</h1>
  <p class="lede">{esc(SITE['description'])}</p>
</section>{tonight_html}
<section>
  <h2>Shop by category</h2>
  <div class="grid">{cats_html}</div>
</section>
<section>
  <h2>Featured picks</h2>
  <div class="grid">{picks_html}</div>
</section>
<section>
  <h2>Guides</h2>
  <div class="grid">""" + "".join(guide_card(g) for g in GUIDES) + """</div>
</section>
<section class="how">
  <h2>How we pick</h2>
  <p>Every pick is gear we'd recommend to a friend who just saw something strange in the sky and wants to look for themselves. We favour aperture per dollar, portability you'll actually use, and upgrade paths that don't dead-end. Prices are approximate street prices — the retailer page has the live number.</p>
</section>"""
    return page(SITE["tagline"], SITE["description"], "/", body)


def category_page(cat, meta):
    items = [p for p in PRODUCTS if p["category"] == cat]
    body = f"""
<p class="crumb"><a href="/">Home</a> / {esc(meta['label'])}</p>
<h1>{esc(meta['label'])}</h1>
<p class="lede">{esc(meta['blurb'])}</p>
<div class="grid">{''.join(card(p) for p in items)}</div>"""
    return page(meta["label"], meta["blurb"], f"/category/{cat}/", body)


def product_page(p):
    pros = "".join(f"<li>{esc(x)}</li>" for x in p["pros"])
    cons = "".join(f"<li>{esc(x)}</li>" for x in p["cons"])
    specs = "".join(
        f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in p["specs"].items()
    )
    related = [q for q in PRODUCTS if q["category"] == p["category"] and q["slug"] != p["slug"]][:3]
    rel_html = "".join(card(q) for q in related)
    body = f"""
<p class="crumb"><a href="/">Home</a> / <a href="/category/{p['category']}/">{esc(CATS[p['category']]['label'])}</a> / {esc(p['name'])}</p>
<h1>{esc(p['name'])}</h1>
<p class="tagline big">{esc(p['tagline'])}</p>
<p class="price big">around ${p['price_usd']:,}</p>
<p class="lede">{esc(p['blurb'])}</p>
{buy_box(p)}
<div class="cols">
  <div><h2>Why we like it</h2><ul class="pros">{pros}</ul></div>
  <div><h2>Keep in mind</h2><ul class="cons">{cons}</ul></div>
</div>
<h2>Specs</h2>
<table class="specs">{specs}</table>
{f'<h2>Also in {esc(CATS[p["category"]]["label"])}</h2><div class="grid">{rel_html}</div>' if rel_html else ""}"""
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": p["name"],
        "description": p["tagline"],
        "url": f"{BASE}/gear/{p['slug']}/",
        "offers": {
            "@type": "Offer",
            "priceCurrency": "USD",
            "price": p["price_usd"],
        },
    }
    return page(p["name"], p["tagline"], f"/gear/{p['slug']}/", body, jsonld)


def about_page():
    body = f"""
<h1>About {esc(SITE['brand'])}</h1>
<p class="lede">{esc(SITE['description'])}</p>
<p>This site exists for one reason: people look up, see something they can't explain, and want better tools than a phone camera and a guess. We cover the gear that actually helps — telescopes, binoculars, star trackers, accessories — picked for real night-sky use, not spec-sheet racing.</p>
<h2>Affiliate disclosure</h2>
<p>{esc(SITE['brand'])} is reader-supported. When you buy through links on our site, we may earn an affiliate commission at no extra cost to you. As an Amazon Associate we earn from qualifying purchases. We only recommend gear we'd suggest to a friend — commissions never decide the picks.</p>
<h2>Contact</h2>
<p><a href="mailto:{esc(SITE['email'])}">{esc(SITE['email'])}</a></p>"""
    return page("About", SITE["description"], "/about/", body)


# ---------------------------------------------------------------- guides

def guide_card(g):
    return f"""
<a class="card" href="/guides/{g['slug']}/">
  <p class="kicker">Guide</p>
  <h3>{esc(g['title'])}</h3>
  <p class="tagline">{esc(g['description'])}</p>
  <span class="cta">Read the guide →</span>
</a>"""


def guides_index():
    body = """
<h1>Skywatch guides</h1>
<p class="lede">No-nonsense explainers for people who want to look at the night sky themselves — written from the citizen-skywatch angle, not the spec sheet.</p>
<div class="grid">""" + "".join(guide_card(g) for g in GUIDES) + "</div>"
    return page("Guides", "Practical skywatch guides: choosing your first telescope, starting with binoculars.", "/guides/", body)


def guide_page(g):
    body = f"""
<p class="crumb"><a href="/">Home</a> / <a href="/guides/">Guides</a> / {esc(g['title'])}</p>
<h1>{esc(g['title'])}</h1>
{ g['body_html'] }
<h2>More guides</h2>
<div class="grid">""" + "".join(guide_card(o) for o in GUIDES if o["slug"] != g["slug"]) + "</div>"
    return page(g["title"], g["description"], f"/guides/{g['slug']}/", body)


# ---------------------------------------------------------------- seo files

def sitemap():
    urls = ["/", "/about/", "/guides/"] + [f"/category/{c}/" for c in CATS] + [
        f"/gear/{p['slug']}/" for p in PRODUCTS
    ] + [f"/guides/{g['slug']}/" for g in GUIDES]
    items = "".join(
        f"  <url><loc>{BASE}{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{items}</urlset>
"""


def robots():
    return f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n"


def llms_txt():
    lines = [f"# {SITE['brand']}", "", SITE["description"], "", "## Picks", ""]
    for p in PRODUCTS:
        lines.append(f"- [{p['name']}]({BASE}/gear/{p['slug']}/) — {p['tagline']}")
    lines += ["", "## Categories", ""]
    for c, v in CATS.items():
        lines.append(f"- [{v['label']}]({BASE}/category/{c}/)")
    lines += ["", "## Guides", ""]
    for g in GUIDES:
        lines.append(f"- [{g['title']}]({BASE}/guides/{g['slug']}/) — {g['description']}")
    return "\n".join(lines) + "\n"


def feed():
    items = "".join(
        f"""  <item>
    <title>{esc(p['name'])} — {esc(p['tagline'])}</title>
    <link>{BASE}/gear/{p['slug']}/</link>
    <guid>{BASE}/gear/{p['slug']}/</guid>
    <description>{esc(p['blurb'])}</description>
    <pubDate>{TODAY}</pubDate>
  </item>
""" for p in PRODUCTS
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{esc(SITE['brand'])} — gear picks</title>
  <link>{BASE}/</link>
  <description>{esc(SITE['description'])}</description>
{items}</channel>
</rss>
"""


def indexnow_key():
    key_path = os.path.join(SRC, "indexnow.key")
    if os.path.exists(key_path):
        with open(key_path) as f:
            return f.read().strip()
    key = secrets.token_hex(16)
    with open(key_path, "w") as f:
        f.write(key + "\n")
    print(f"generated new IndexNow key -> {key_path}")
    return key


# ---------------------------------------------------------------- main

def write(path, content):
    full = os.path.join(DIST, path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


def build():
    os.makedirs(DIST, exist_ok=True)
    shutil.copy(os.path.join(SRC, "style.css"), os.path.join(DIST, "style.css"))
    write("index.html", index_page())
    write("about/index.html", about_page())
    write("guides/index.html", guides_index())
    for g in GUIDES:
        write(f"guides/{g['slug']}/index.html", guide_page(g))
    for c, v in CATS.items():
        write(f"category/{c}/index.html", category_page(c, v))
    for p in PRODUCTS:
        write(f"gear/{p['slug']}/index.html", product_page(p))
    write("sitemap.xml", sitemap())
    write("robots.txt", robots())
    write("llms.txt", llms_txt())
    write("feed.xml", feed())
    key = indexnow_key()
    write(f"{key}.txt", key)
    print(f"built {len(PRODUCTS)} products, {len(CATS)} categories -> {DIST}")
    print(f"AMAZON_TAG={AMAZON_TAG}" + ("  <-- PLACEHOLDER, set env AMAZON_TAG" if AMAZON_TAG == "yourtag-20" else ""))


def dump_sql():
    print("-- gear_picks seed — generated from src/products.json by build.py --dump-sql")
    for p in PRODUCTS:
        for r in p["retailers"]:
            url = retailer_url(r, p)
            if not url:
                continue
            name = p["name"].replace("'", "''")
            ret = r["name"].replace("'", "''")
            url_q = url.replace("'", "''")
            print(
                "INSERT INTO gear_picks (slug, product_name, retailer, url, price_cents) VALUES "
                f"('{p['slug']}', '{name}', '{ret}', '{url_q}', {int(p['price_usd'] * 100)}) "
                "ON CONFLICT(slug, retailer) DO UPDATE SET url=excluded.url, price_cents=excluded.price_cents;"
            )


if __name__ == "__main__":
    if "--dump-sql" in sys.argv:
        dump_sql()
    else:
        build()
