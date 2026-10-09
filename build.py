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
GLOSSARY = load("glossary.json")["terms"]
CATS = SITE["categories"]
TONIGHT = None
_tonight_path = os.path.join(SRC, "tonight.json")
if os.path.exists(_tonight_path):
    with open(_tonight_path, encoding="utf-8") as _f:
        TONIGHT = json.load(_f)
DOMAIN = SITE["domain"]
BASE = f"https://{DOMAIN}"

# Best-of roundups: explicit pick lists; name/tagline/price render from products.json.
ROUNDUPS = [
    {
        "title": "Best telescopes under $500",
        "slug": "best-telescopes-under-500",
        "description": "The telescopes under $500 I’d actually hand to family — ranked by price, tradeoffs included.",
        "intro": "Every scope here costs under $500 — ranked from cheapest to priciest, because I know that’s how you’re reading it. This is the sweet spot for a first telescope: enough aperture for Saturn’s rings and real deep-sky objects, without the regret if you upgrade later. (You probably will. We all do.)",
        "picks": [
            ("celestron-astromaster-70az", "The honest $150 start. A real refractor with zero collimation fuss — lovely on the Moon and planets, and cheap enough that it doesn't matter if the hobby doesn't stick."),
            ("orion-starblast-4-5", "The tabletop Dobsonian classic. More sky per dollar than cheap refractors — though you’ll need to put it on something sturdy, like the world’s most exciting side table."),
            ("skywatcher-evostar-102", "A sharp 4-inch refractor — but heads up, it’s the tube only, so save room in the budget for a mount and tripod."),
            ("skywatcher-heritage-150p", "My sweet-spot pick, and I’ll defend it at family dinner: 6 inches of Dobsonian showing Saturn’s rings, Jupiter’s bands, and hundreds of deep-sky objects."),
            ("orion-skyquest-xt6", "The full-size 6-inch Dobsonian — the one that’s been making beginners happy for decades. Classics are classics for a reason."),
            ("celestron-starsense-explorer-dx-130az", "Your phone guides you to 100+ targets — training wheels that actually teach you the constellations instead of doing your homework for you."),
        ],
    },
    {
        "title": "Best binoculars for stargazing",
        "slug": "best-binoculars-stargazing",
        "description": "The binoculars I’d hand to family — from $40 sweepers to the buy-once upgrade.",
        "intro": "If you only buy one thing for the night sky, make it binoculars — yes, I’m serious, and yes, I’ll keep saying it. Ranked cheapest to priciest; every pair here is genuinely lovely under the stars, not a daytime compromise.",
        "picks": [
            ("celestron-cometron-7x50", "The $40 wide-field sweeper. Light, forgiving, and the cheapest honest way to learn the sky — cheaper than the pizza you’ll order while using them."),
            ("nikon-aculon-a211-10x50", "The benchmark beginner pair. Bright, sharp enough, and useful forever — yes, even after you buy a telescope. Especially after."),
            ("celestron-nature-dx-8x42", "Wider and steadier than 10x pairs — the pick if 10x feels shaky in your hands. No shame; steady beats shaky."),
            ("celestron-skymaster-15x70", "Huge light grasp for the price — but fair warning, your arms will vote for a tripod during long sessions."),
            ("vortex-diamondback-hd-10x42", "The buy-once upgrade: noticeably sharper glass, plus a warranty so good it covers your own clumsiness."),
        ],
    },
    {
        "title": "Best star trackers for beginners",
        "slug": "best-star-trackers-beginners",
        "description": "The two star trackers worth buying first — ranked by price — and how to choose between them.",
        "intro": "A star tracker is the biggest single upgrade in beginner astrophotography: it rotates your camera with the Earth, turning 8-second exposures into 2-minute ones. Only two trackers made my beginner list — both proven, both loved by the community, neither will waste your money.",
        "picks": [
            ("skywatcher-star-adventurer-2i", "The community standard: portable, proven, and it turns any DSLR or mirrorless camera into a deep-sky rig. Start here unless you know you need the bigger one."),
            ("ioptron-skyguider-pro", "Heavier 11-lb payload for telephoto lenses, plus an autoguider port for when you're ready to go deeper. The 'I’ve caught the bug' upgrade."),
        ],
    },
]

def product_by_slug(slug):
    return next(p for p in PRODUCTS if p["slug"] == slug)


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
) + '<a href="/roundups/">Roundups</a><a href="/tonight/">Tonight</a><a href="/guides/">Guides</a>'

def newsletter_block(compact=False):
    ep = SITE.get("newsletter_endpoint", "")
    if ep:
        form = (
            f'<form class="nl-form" method="post" action="{esc(ep)}">'
            '<input type="email" name="email" required placeholder="you@example.com" aria-label="Email address">'
            '<button class="btn" type="submit">Subscribe</button></form>'
        )
    else:
        form = '<p class="nl-soon">Email alerts are coming soon — check back.</p>'
    if compact:
        return f'<div class="nl-compact"><p class="fine"><strong>Sky alerts.</strong> One email when the good stuff happens.</p>{form}</div>'
    return (
        '<section class="newsletter"><h2>Get the sky in your inbox</h2>'
        '<p class="lede">Meteor showers, planet highlights, new gear picks — one short email, only when it\u2019s worth looking up.</p>'
        f'{form}</section>'
    )


FOOTER = f"""
<footer>
  <div class="wrap">
    <p class="brand">{esc(SITE['brand'])}</p>
    <nav class="footer-nav" aria-label="Site">{NAV_LINKS}<a href="/compare/">Compare</a><a href="/finder/">Finder</a><a href="/about/">About</a></nav>
    <p class="disc">Affiliate disclosure: {esc(SITE['brand'])} is reader-supported. When you buy through links on our site we may earn an affiliate commission — it costs you nothing extra. As an Amazon Associate we earn from qualifying purchases. Prices shown are approximate; check the retailer for the live price.</p>
    {newsletter_block(compact=True)}
    <p class="fine"><a href="/about/">About</a> · <a href="/feed.xml">RSS</a> · <a href="/llms.txt">llms.txt</a> · <a href="mailto:{esc(SITE['email'])}">{esc(SITE['email'])}</a></p>
    <p class="fine">© {datetime.date.today().year} {esc(SITE['brand'])}. Look up.</p>
  </div>
</footer>"""


THEME_HEAD_SCRIPT = """<script>(function(){try{var t=localStorage.getItem('wtn-theme')||'dark';document.documentElement.setAttribute('data-theme',t);var m=document.getElementById('meta-theme-color');if(m)m.setAttribute('content',t==='light'?'#fbfbfe':'#05070f');}catch(e){document.documentElement.setAttribute('data-theme','dark');}})();</script>"""

THEME_TOGGLE = """<button class="theme-toggle" id="theme-toggle" aria-label="Toggle light/dark theme" title="Toggle light/dark theme"><svg class="icon-sun" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg><svg class="icon-moon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg></button>"""

THEME_SCRIPT = """<script>(function(){var b=document.getElementById('theme-toggle');if(!b)return;b.addEventListener('click',function(){var h=document.documentElement;var t=h.getAttribute('data-theme')==='light'?'dark':'light';h.setAttribute('data-theme',t);var m=document.getElementById('meta-theme-color');if(m)m.setAttribute('content',t==='light'?'#fbfbfe':'#05070f');try{localStorage.setItem('wtn-theme',t);}catch(e){}if(window.__wtnGiscusTheme)window.__wtnGiscusTheme(t);});})();</script>"""


COMPARE_TRAY_SCRIPT = """<script>
(function(){
var KEY='wtn-cmp', MAX=3;
function get(){ try{ return JSON.parse(localStorage.getItem(KEY))||[]; }catch(e){ return []; } }
function set(v){ try{ localStorage.setItem(KEY, JSON.stringify(v)); }catch(e){} }
var tray=document.createElement('div');
tray.className='cmp-tray'; tray.id='cmp-tray';
document.body.appendChild(tray);
function render(){
  var s=get();
  document.querySelectorAll('.cmp-add input').forEach(function(cb){ cb.checked=s.indexOf(cb.dataset.slug)>=0; });
  if(s.length>=2){
    var q=s.map(function(x,i){ return 'abc'[i]+'='+encodeURIComponent(x); }).join('&');
    tray.innerHTML='<span class="muted">'+s.length+' selected</span><a class="btn" href="/compare/?'+q+'">Compare now</a><button class="cmp-clear" aria-label="Clear selection">\\u00d7</button>';
    tray.classList.add('show');
    tray.querySelector('.cmp-clear').addEventListener('click',function(){ set([]); render(); });
  }else{
    tray.classList.remove('show');
  }
}
document.addEventListener('change',function(e){
  var cb=e.target&&e.target.closest?e.target.closest('.cmp-add input'):null;
  if(!cb) return;
  var s=get(), i=s.indexOf(cb.dataset.slug);
  if(cb.checked&&i<0){ if(s.length>=MAX){ cb.checked=false; return; } s.push(cb.dataset.slug); }
  if(!cb.checked&&i>=0){ s.splice(i,1); }
  set(s); render();
});
window.__wtnTrayRender=render;
render();
})();
</script>"""


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
<meta property="og:image" content="{BASE}/og-image.jpg">
<meta name="twitter:card" content="summary">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" id="meta-theme-color" content="#05070f">
{THEME_HEAD_SCRIPT}
<link rel="stylesheet" href="/style.css">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
{jd}
</head>
<body>
<header>
  <div class="wrap nav">
    <a class="logo" href="/"><img src="/logo.png" alt="" width="28" height="28"> {esc(SITE['brand'])}</a>
    {THEME_TOGGLE}
  </div>
</header>
<main class="wrap">
{body}
</main>
{FOOTER}
{THEME_SCRIPT}
{COMPARE_TRAY_SCRIPT}
</body>
</html>
"""


def card(p):
    price = f'<p class="price">around ${p["price_usd"]:,}</p>' if p.get("price_usd") else ""
    return f"""
<div class="cardwrap">
<a class="card" href="/gear/{p['slug']}/">
  <p class="kicker">{esc(CATS[p['category']]['label'])}</p>
  <h3>{esc(p['name'])}</h3>
  <p class="tagline">{esc(p['tagline'])}</p>
  {price}
  <span class="cta">Read the pick →</span>
</a>
<label class="cmp-add"><input type="checkbox" data-slug="{p['slug']}" aria-label="Add {esc(p['name'])} to compare"> Compare</label>
</div>"""


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
  <div class="grid">""" + "".join(guide_card(g) for g in GUIDES) + f"""</div>
</section>
<section class="how">
  <h2>How we pick</h2>
  <p>Every pick here is something I'd recommend to my own cousin who just saw something strange in the sky and wants to look for themselves. I care about three things: views per dollar, portability you'll actually use, and upgrade paths that don't dead-end. Prices are approximate street prices — the retailer page has the live number. And if something isn't worth your money, I'll tell you that too.</p>
</section>
{newsletter_block()}"""
    return page(SITE["tagline"], SITE["description"], "/", body)


def category_page(cat, meta):
    items = [p for p in PRODUCTS if p["category"] == cat]
    body = f"""
<p class="crumb"><a href="/">Home</a> / {esc(meta['label'])}</p>
<h1>{esc(meta['label'])}</h1>
<p class="lede">{esc(meta['blurb'])}</p>
<div class="grid">{''.join(card(p) for p in items)}</div>"""
    return page(meta["label"], meta["blurb"], f"/category/{cat}/", body)


SPEC_SECTIONS = [
    ("Optics", ["aperture", "focal", "optical design", "eyepiece", "magnification", "prism", "field of view", "coating", "glass"]),
    ("Mount & tracking", ["mount", "tracking", "goto", "slow-motion", "tripod", "polar"]),
    ("Camera & imaging", ["sensor", "payload", "wifi", "intervalometer", "shutter", "iso"]),
    ("Power & physical", ["power", "battery", "weight", "dimensions", "length", "brightness", "color"]),
]


def spec_groups(p):
    groups, used = [], set()
    for title, keys in SPEC_SECTIONS:
        items = [(k, v) for k, v in p["specs"].items()
                 if k not in used and any(q in k.lower() for q in keys)]
        if items:
            groups.append((title, items))
            used.update(k for k, _v in items)
    rest = [(k, v) for k, v in p["specs"].items() if k not in used]
    if rest:
        groups.append(("Details", rest))
    return groups


def giscus_block():
    g = SITE.get("giscus") or {}
    if not g.get("repo_id") or not g.get("category_id"):
        return ""
    return f"""
<div id="giscus-root"></div>
<script>(function(){{
  var cfg = {json.dumps({"repo": "hectorchanht/watchthenight", "repo_id": g["repo_id"], "category": g.get("category", "General"), "category_id": g["category_id"]})};
  var theme = 'transparent_dark';
  try{{ if((localStorage.getItem('wtn-theme')||'dark')==='light') theme='light'; }}catch(e){{}}
  var s = document.createElement('script');
  s.src = 'https://giscus.app/client.js';
  s.async = true; s.crossOrigin = 'anonymous';
  var attrs = {{"data-repo": cfg.repo, "data-repo-id": cfg.repo_id, "data-category": cfg.category, "data-category-id": cfg.category_id, "data-mapping": "pathname", "data-strict": "0", "data-reactions-enabled": "1", "data-emit-metadata": "0", "data-input-position": "top", "data-theme": theme, "data-lang": "en"}};
  for(var k in attrs){{ s.setAttribute(k, attrs[k]); }}
  document.getElementById('giscus-root').appendChild(s);
  window.__wtnGiscusTheme = function(t){{
    var f = document.querySelector('iframe.giscus-frame');
    if(f) f.contentWindow.postMessage({{giscus:{{setConfig:{{theme: t==='light'?'light':'transparent_dark'}}}}}}, 'https://giscus.app');
  }};
}})();</script>
"""


def product_page(p):
    pros = "".join(f"<li>{esc(x)}</li>" for x in p["pros"])
    cons = "".join(f"<li>{esc(x)}</li>" for x in p["cons"])
    specs = "".join(
        f'<h3 class="spech">{esc(title)}</h3><table class="specs">'
        + "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in items)
        + "</table>"
        for title, items in spec_groups(p)
    )
    related = [q for q in PRODUCTS if q["category"] == p["category"] and q["slug"] != p["slug"]][:3]
    rel_html = "".join(card(q) for q in related)
    body = f"""
<p class="crumb"><a href="/">Home</a> / <a href="/category/{p['category']}/">{esc(CATS[p['category']]['label'])}</a> / {esc(p['name'])}</p>
<h1>{esc(p['name'])}</h1>
<p class="tagline big">{esc(p['tagline'])}</p>
<p class="price big">{'around $' + format(p['price_usd'], ',d') if p.get('price_usd') else 'Check price'}</p>
<p class="lede">{esc(p['blurb'])}</p>
{buy_box(p)}
<p class="fine"><a href="/compare/?a={p['slug']}">Compare the {esc(p['name'])} with another pick →</a></p>
<div class="cols">
  <div><h2>Why we like it</h2><ul class="pros">{pros}</ul></div>
  <div><h2>Keep in mind</h2><ul class="cons">{cons}</ul></div>
</div>
<h2>Specs</h2>
{specs}
<h2>User opinions</h2>
{giscus_block()}
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
            **({"price": p["price_usd"]} if p.get("price_usd") else {}),
        },
    }
    return page(p["name"], p["tagline"], f"/gear/{p['slug']}/", body, jsonld)


COMPARE_SCRIPT = """<script>
(function(){
var data = JSON.parse(document.getElementById('cmp-data').textContent);
var bySlug = {};
data.forEach(function(p){ bySlug[p.slug] = p; });
var sels = ['A','B','C'].map(function(k){ return document.getElementById('cmp-'+k); });
var table = document.getElementById('cmp-table');
var hint = document.getElementById('cmp-hint');
var diffBox = document.getElementById('cmp-diff');
function esc(s){ return String(s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
function money(n){ return n ? 'around $' + Number(n).toLocaleString('en-US') : '\\u2014'; }
function render(){
  var picks = sels.map(function(s){ return bySlug[s.value]; }).filter(Boolean);
  var params = new URLSearchParams();
  var keys = ['a','b','c'];
  sels.forEach(function(s,i){ if(s.value) params.set(keys[i], s.value); });
  var qs = params.toString();
  try{ history.replaceState(null,'', qs ? '/compare/?'+qs : '/compare/'); }catch(e){}
  try{ localStorage.setItem('wtn-cmp', JSON.stringify(sels.map(function(s){ return s.value; }).filter(Boolean))); }catch(e){}
  if(picks.length < 2){ table.hidden = true; hint.hidden = false; return; }
  hint.hidden = true; table.hidden = false;
  var specKeys = [];
  picks.forEach(function(p){ Object.keys(p.specs).forEach(function(k){ if(specKeys.indexOf(k)<0) specKeys.push(k); }); });
  if(diffBox && diffBox.checked){
    specKeys = specKeys.filter(function(k){
      var vals = picks.map(function(p){ return p.specs[k]||''; });
      return new Set(vals).size > 1;
    });
  }
  var html = '<thead><tr><th scope="col"><span class="muted">Pick</span></th>' + picks.map(function(p){
    return '<th scope="col"><a href="/gear/'+p.slug+'/">'+esc(p.name)+'</a><br><span class="muted">'+esc(p.cat)+'</span></th>';
  }).join('') + '</tr></thead><tbody>';
  function row(label, cells){
    html += '<tr><th scope="row" class="rowlabel">'+esc(label)+'</th>' + cells.map(function(c){ return '<td>'+c+'</td>'; }).join('') + '</tr>';
  }
  row('Price', picks.map(function(p){ return '<strong>'+money(p.price)+'</strong>'; }));
  row('Tagline', picks.map(function(p){ return esc(p.tagline); }));
  specKeys.forEach(function(k){
    row(k, picks.map(function(p){ return p.specs[k] ? esc(p.specs[k]) : '<span class="muted">\\u2014</span>'; }));
  });
  row('Pros', picks.map(function(p){ return '<ul class="pros">'+p.pros.map(function(x){ return '<li>'+esc(x)+'</li>'; }).join('')+'</ul>'; }));
  row('Cons', picks.map(function(p){ return '<ul class="cons">'+p.cons.map(function(x){ return '<li>'+esc(x)+'</li>'; }).join('')+'</ul>'; }));
  row('Full review', picks.map(function(p){ return '<a class="btn" href="/gear/'+p.slug+'/">Read the full pick</a>'; }));
  html += '</tbody>';
  table.innerHTML = html;
}
sels.forEach(function(s){ s.addEventListener('change', render); });
if(diffBox){ diffBox.addEventListener('change', render); }
var q = new URLSearchParams(location.search);
var vals = [q.get('a'), q.get('b'), q.get('c')];
if(!vals[0] && !vals[1] && !vals[2]){
  try{
    var saved = JSON.parse(localStorage.getItem('wtn-cmp'))||[];
    if(saved.length >= 2){ vals = [saved[0]||null, saved[1]||null, saved[2]||null]; }
    else { vals = ['celestron-nexstar-8se','apertura-ad8-dobsonian',null]; }
  }catch(e){ vals = ['celestron-nexstar-8se','apertura-ad8-dobsonian',null]; }
}
vals.forEach(function(v,i){ if(v && bySlug[v]) sels[i].value = v; });
render();
})();
</script>"""


def compare_page():
    data = [
        {
            "slug": p["slug"],
            "name": p["name"],
            "cat": CATS[p["category"]]["label"],
            "price": p.get("price_usd"),
            "tagline": p["tagline"],
            "specs": p["specs"],
            "pros": p["pros"],
            "cons": p["cons"],
        }
        for p in PRODUCTS
    ]
    data_json = json.dumps(data).replace("<", "\\u003c")
    opts = "".join(
        f'<optgroup label="{esc(v["label"])}">'
        + "".join(
            f'<option value="{p["slug"]}">{esc(p["name"])}</option>'
            for p in PRODUCTS
            if p["category"] == c
        )
        + "</optgroup>"
        for c, v in CATS.items()
    )
    selects = "".join(
        f'<div><label for="cmp-{k}">Product {k}</label>'
        f'<select id="cmp-{k}"><option value="">— Choose —</option>{opts}</select></div>'
        for k in ("A", "B", "C")
    )
    body = f"""
<p class="crumb"><a href="/">Home</a> / Compare</p>
<h1>Compare gear side by side</h1>
<p class="lede">Pick up to three products and compare full specs, prices, strengths and tradeoffs in one table. Every spec comes straight from our product pages — no hidden rankings, no thumb on the scale.</p>
<div class="compare-selects">{selects}</div>
<p><label class="diff-toggle"><input type="checkbox" id="cmp-diff"> Show differences only</label></p>
<div class="compare-wrap"><table class="compare" id="cmp-table" hidden></table></div>
<p class="fine" id="cmp-hint">Choose at least two products to start comparing.</p>
<script type="application/json" id="cmp-data">{data_json}</script>
{COMPARE_SCRIPT}
"""
    return page(
        "Compare gear",
        "Side-by-side comparison of telescopes, binoculars, star trackers and accessories: full specs, prices, pros and cons.",
        "/compare/",
        body,
    )


FINDER_SCRIPT = """<script>
(function(){
var data = JSON.parse(document.getElementById('f-data').textContent);
function esc(s){ return String(s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
function apertureMm(p){
  var v = p.specs['Aperture'] || '';
  var m = v.match(/([\\d.]+)\\s*mm/);
  return m ? parseFloat(m[1]) : 0;
}
function isGoto(p){ return /goto/i.test(p.name + ' ' + JSON.stringify(p.specs)); }
var prices = data.map(function(p){ return p.price||0; }).filter(Boolean);
var apers = data.map(apertureMm).filter(Boolean);
var pMax = Math.ceil(Math.max.apply(null, prices)/500)*500;
var aMax = Math.ceil(Math.max.apply(null, apers)/50)*50;
var fCat=document.getElementById('f-cat'), fPrice=document.getElementById('f-price'),
    fAper=document.getElementById('f-aper'), fGoto=document.getElementById('f-goto'),
    pOut=document.getElementById('f-price-out'), aOut=document.getElementById('f-aper-out'),
    res=document.getElementById('f-results'), count=document.getElementById('f-count');
fPrice.max=pMax; fPrice.value=pMax; fAper.max=aMax; fAper.value=0;
function cardHtml(p){
  var price = p.price ? '<p class="price">around $'+Number(p.price).toLocaleString('en-US')+'</p>' : '';
  return '<div class="cardwrap"><a class="card" href="/gear/'+p.slug+'/"><p class="kicker">'+esc(p.catlabel)+'</p><h3>'+esc(p.name)+'</h3><p class="tagline">'+esc(p.tagline)+'</p>'+price+'<span class="cta">Read the pick \\u2192</span></a><label class="cmp-add"><input type="checkbox" data-slug="'+p.slug+'" aria-label="Add '+esc(p.name)+' to compare"> Compare</label></div>';
}
function render(){
  var cat=fCat.value, mp=parseFloat(fPrice.value), ma=parseFloat(fAper.value), go=fGoto.checked;
  pOut.textContent = '$'+Number(mp).toLocaleString('en-US');
  aOut.textContent = ma>0 ? ma+' mm' : 'any';
  var out = data.filter(function(p){
    if(cat!=='all' && p.cat!==cat) return false;
    if(p.price && p.price>mp) return false;
    if(ma>0 && apertureMm(p)<ma) return false;
    if(go && !isGoto(p)) return false;
    return true;
  }).sort(function(a,b){ return (a.price||1e9)-(b.price||1e9); });
  count.textContent = out.length + (out.length===1?' pick':' picks') + ' match';
  res.innerHTML = out.map(cardHtml).join('') || '<p class="lede">Nothing matches — loosen a filter.</p>';
  if(window.__wtnTrayRender) window.__wtnTrayRender();
}
[fCat,fPrice,fAper,fGoto].forEach(function(el){ el.addEventListener('input', render); el.addEventListener('change', render); });
render();
})();
</script>"""


def finder_page():
    data = [
        {
            "slug": p["slug"],
            "name": p["name"],
            "cat": p["category"],
            "catlabel": CATS[p["category"]]["label"],
            "price": p.get("price_usd"),
            "tagline": p["tagline"],
            "specs": p["specs"],
        }
        for p in PRODUCTS
    ]
    data_json = json.dumps(data).replace("<", "\\u003c")
    cat_opts = '<option value="all">All categories</option>' + "".join(
        f'<option value="{c}">{esc(v["label"])}</option>' for c, v in CATS.items()
    )
    body = f"""
<p class="crumb"><a href="/">Home</a> / Finder</p>
<h1>Gear finder</h1>
<p class="lede">Filter every pick by what matters to you — category, budget, aperture, GoTo. Like a phone finder, but for the night sky. I'll sort the bargains to the top.</p>
<div class="finder-filters">
  <div><label for="f-cat">Category</label><select id="f-cat">{cat_opts}</select></div>
  <div><label for="f-price">Max price: <output id="f-price-out"></output></label><input type="range" id="f-price" min="0" step="50" value="4000"></div>
  <div><label for="f-aper">Min aperture: <output id="f-aper-out"></output></label><input type="range" id="f-aper" min="0" step="10" value="0"></div>
  <div><label class="check" for="f-goto"><input type="checkbox" id="f-goto"> GoTo / computerized only</label></div>
</div>
<p class="fine" id="f-count"></p>
<div class="grid" id="f-results"></div>
<script type="application/json" id="f-data">{data_json}</script>
{FINDER_SCRIPT}
"""
    return page(
        "Gear finder",
        "Filter every Watch the Night pick by category, budget, aperture and GoTo — find the right telescope, binoculars or star tracker.",
        "/finder/",
        body,
    )


def about_page():
    body = f"""
<h1>About {esc(SITE['brand'])}</h1>
<p class="lede">{esc(SITE['description'])}</p>
<p>This site exists for one reason: you looked up, saw something you couldn't explain, and wanted better tools than a phone camera and a guess. Think of me as the cousin who got obsessed with telescopes years ago and never quite recovered — except I've done the homework so you don't have to. Every pick is gear I'd hand to family: honest advice, real tradeoffs, zero hype.</p>
<h2>Affiliate disclosure</h2>
<p>{esc(SITE['brand'])} is reader-supported. When you buy through links on our site, we may earn an affiliate commission at no extra cost to you. As an Amazon Associate we earn from qualifying purchases. Here's my promise: I only recommend gear I'd suggest to family — commissions never decide the picks, and I'll tell you when something isn't worth it.</p>
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
<p class="lede">Plain-talk explainers for people who want to look at the night sky themselves — written by someone who remembers being confused by all of it, and wants to save you the trouble.</p>
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


# ---------------------------------------------------------------- roundups

def roundup_card(r):
    n = len(r["picks"])
    return f"""
<a class="card" href="/roundups/{r['slug']}/">
  <p class="kicker">{n} ranked picks</p>
  <h3>{esc(r['title'])}</h3>
  <p class="tagline">{esc(r['description'])}</p>
  <span class="cta">See the ranking →</span>
</a>"""


def roundups_index():
    body = """
<h1>Best-of roundups</h1>
<p class="lede">Ranked, opinionated, honest: my best-of lists, built from the same product data as every gear page — prices and tradeoffs included. No sponsored slots, ever.</p>
<div class="grid">""" + "".join(roundup_card(r) for r in ROUNDUPS) + "</div>"
    return page("Roundups", "Ranked best-of lists: best telescopes under $500, best binoculars for stargazing, best star trackers for beginners.", "/roundups/", body)


def roundup_page(r):
    rows = []
    for i, (slug, verdict) in enumerate(r["picks"], 1):
        p = product_by_slug(slug)
        cons = "".join(f"<li>{esc(x)}</li>" for x in p["cons"][:2])
        rows.append(f"""
<article class="rank">
  <p class="kicker">#{i}</p>
  <h3><a href="/gear/{p['slug']}/">{esc(p['name'])}</a> <span class="price">{'around $' + format(p['price_usd'], ',d') if p.get('price_usd') else 'Check price'}</span></h3>
  <p class="verdict">{esc(verdict)}</p>
  <p class="tagline">{esc(p['tagline'])}</p>
  <ul class="cons"><li><strong>Watch out:</strong></li>{cons}</ul>
  <a class="cta" href="/gear/{p['slug']}/">Read the full pick →</a>
</article>""")
    body = f"""
<p class="crumb"><a href="/">Home</a> / <a href="/roundups/">Roundups</a> / {esc(r['title'])}</p>
<h1>{esc(r['title'])}</h1>
<p class="lede">{esc(r['intro'])}</p>
{''.join(rows)}
<h2>More roundups</h2>
<div class="grid">""" + "".join(roundup_card(o) for o in ROUNDUPS if o["slug"] != r["slug"]) + """</div>"""
    jsonld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": r["title"],
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "name": product_by_slug(slug)["name"],
                "url": f"{BASE}/gear/{product_by_slug(slug)['slug']}/",
            }
            for i, (slug, _v) in enumerate(r["picks"], 1)
        ],
    }
    return page(r["title"], r["description"], f"/roundups/{r['slug']}/", body, jsonld)


# ---------------------------------------------------------------- tonight page

def tonight_page():
    t = TONIGHT or {}
    hero = ""
    if t:
        hero = (
            '<section class="tonight">\n'
            f'  <h2>Tonight\'s sky <span class="date">{esc(t.get("date", ""))}</span></h2>\n'
            f'  <p class="moon">{t.get("emoji", "")} <strong>{esc(t.get("phase", ""))}</strong> — {t.get("illumination_pct", "")}% illuminated</p>\n'
            f'  <p class="tip">Tonight\'s tip: {esc(t.get("tip", ""))}</p>\n'
            "</section>"
        )
    body = f"""
<h1>Tonight's sky</h1>
<p class="lede">What's worth looking at, updated daily. Monthly highlights below — positions shift through the season, so confirm details in a free planetarium app (Stellarium, SkySafari) before you go out.</p>
{hero}
<h2>October 2026</h2>
<p><strong>Orionids — peak night of Oct 21–22.</strong> Debris from Halley's Comet, roughly 20 fast meteors an hour. The Moon is bright early in the night (waning gibbous), so wait until after moonset — roughly 3am — for the best hours before dawn. Best with just your eyes and a reclining chair; <a href="/gear/nikon-aculon-a211-10x50/">binoculars</a> help sweep the sky between meteors.</p>
<p><strong>Saturn</strong> is just past its early-October opposition — this is prime ring-viewing season. Any of our <a href="/roundups/best-telescopes-under-500/">telescopes under $500</a> will show the rings.</p>
<h2>November 2026</h2>
<p><strong>Leonids — peak night of Nov 16–17.</strong> Swift meteors, about 10 an hour, with occasional bright fireballs. Best after midnight; the Moon is out of the way this year.</p>
<p><strong>Mars meets Jupiter.</strong> The two planets share the pre-dawn sky all month and pass close together around Nov 14 — a fine binocular sight. <strong>Venus</strong> climbs back into the morning sky as the month goes on, brilliant before sunrise.</p>
<h2>December 2026</h2>
<p><strong>Geminids — peak night of Dec 13–14.</strong> The year's best meteor shower: up to ~100 multicoloured meteors an hour under near-moonless skies. Dress warm, bring a <a href="/gear/red-led-astronomy-flashlight/">red flashlight</a> and a <a href="/gear/planisphere-40n/">planisphere</a>, and give it at least an hour.</p>
<p><strong>Mars at opposition (Dec 8).</strong> The red planet at its biggest and brightest of the year — small telescopes show surface shading and the polar cap. Jupiter keeps brightening in the evening sky behind it.</p>
<h2>Gear for the season</h2>
<div class="grid">""" + "".join(
        card(product_by_slug(s))
        for s in ["nikon-aculon-a211-10x50", "red-led-astronomy-flashlight", "planisphere-40n"]
    ) + """</div>"""
    return page("Tonight's sky", "Tonight's moon phase plus October–December 2026 highlights: Orionids, Leonids, Geminids, and the planets.", "/tonight/", body)


# ---------------------------------------------------------------- seo files

def sitemap():
    urls = ["/", "/about/", "/tonight/", "/guides/", "/roundups/", "/compare/", "/finder/"] + [f"/category/{c}/" for c in CATS] + [
        f"/gear/{p['slug']}/" for p in PRODUCTS
    ] + [f"/guides/{g['slug']}/" for g in GUIDES] + [f"/roundups/{r['slug']}/" for r in ROUNDUPS]
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
    lines += ["", "## Roundups", ""]
    for r in ROUNDUPS:
        lines.append(f"- [{r['title']}]({BASE}/roundups/{r['slug']}/) — {r['description']}")
    lines += ["", "## Tonight", ""]
    lines.append(f"- [Tonight's sky]({BASE}/tonight/) — Tonight's moon phase plus Oct–Dec 2026 meteor and planet highlights.")
    lines += ["", "## Tools", ""]
    lines.append(f"- [Compare gear]({BASE}/compare/) — Side-by-side comparison of any products: full specs, prices, pros and cons.")
    lines.append(f"- [Gear finder]({BASE}/finder/) — Filter every pick by category, budget, aperture and GoTo.")
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
    items += "".join(
        f"""  <item>
    <title>Guide: {esc(g['title'])}</title>
    <link>{BASE}/guides/{g['slug']}/</link>
    <guid>{BASE}/guides/{g['slug']}/</guid>
    <description>{esc(g['description'])}</description>
    <pubDate>{TODAY}</pubDate>
  </item>
""" for g in GUIDES
    )
    items += "".join(
        f"""  <item>
    <title>Roundup: {esc(r['title'])}</title>
    <link>{BASE}/roundups/{r['slug']}/</link>
    <guid>{BASE}/roundups/{r['slug']}/</guid>
    <description>{esc(r['description'])}</description>
    <pubDate>{TODAY}</pubDate>
  </item>
""" for r in ROUNDUPS
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
    for asset in ("logo.png", "og-image.jpg", "apple-touch-icon.png", "icon-192.png", "icon-512.png",
                  "favicon.ico", "favicon-32x32.png", "favicon-16x16.png"):
        shutil.copy(os.path.join(SRC, "assets", asset), os.path.join(DIST, asset))
    write("site.webmanifest", json.dumps({
        "name": "Watch the Night",
        "short_name": "WatchNight",
        "description": SITE["description"],
        "start_url": "/",
        "display": "standalone",
        "background_color": "#05070f",
        "theme_color": "#05070f",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }, indent=2))
    write("index.html", index_page())
    write("about/index.html", about_page())
    write("tonight/index.html", tonight_page())
    write("guides/index.html", guides_index())
    for g in GUIDES:
        write(f"guides/{g['slug']}/index.html", guide_page(g))
    write("roundups/index.html", roundups_index())
    for r in ROUNDUPS:
        write(f"roundups/{r['slug']}/index.html", roundup_page(r))
    write("compare/index.html", compare_page())
    write("finder/index.html", finder_page())
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
    print(f"built {len(PRODUCTS)} products, {len(CATS)} categories, {len(GUIDES)} guides, {len(ROUNDUPS)} roundups -> {DIST}")
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
                f"('{p['slug']}', '{name}', '{ret}', '{url_q}', {('NULL' if not p.get('price_usd') else int(p['price_usd'] * 100))}) "
                "ON CONFLICT(slug, retailer) DO UPDATE SET url=excluded.url, price_cents=excluded.price_cents;"
            )


if __name__ == "__main__":
    if "--dump-sql" in sys.argv:
        dump_sql()
    else:
        build()
