"""Uncensored Runners — static site generator.

Reads the editable content (content/*.yml, content/pages/*.yml, content/posts/*.md),
which the client changes from the /admin panel, and writes the finished site to dist/.

    python3 build.py              -> dist/ (production, clean URLs)
    python3 build.py dist preview -> links point at index.html (for opening files locally)
"""
import os, re, sys, json, html, shutil, datetime, glob
from urllib.parse import quote, unquote
import yaml, markdown
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, 'dist')
MODE = sys.argv[2] if len(sys.argv) > 2 else 'prod'
e = lambda s: html.escape(str(s or ''), quote=True)

S = yaml.safe_load(open(f'{ROOT}/content/settings.yml', encoding='utf-8'))
HOME = yaml.safe_load(open(f'{ROOT}/content/home.yml', encoding='utf-8'))
DOMAIN = S['domain'].rstrip('/')
PHONE = S['phone']; PHONE_TEL = '+39' + re.sub(r'\D', '', PHONE)[-10:] if not PHONE.strip().startswith('+') else re.sub(r'[^\d+]', '', PHONE)
EMAIL = S['email']

PAGES = []
for f in sorted(glob.glob(f'{ROOT}/content/pages/*.yml')):
    p = yaml.safe_load(open(f, encoding='utf-8'))
    p['slug'] = p['url'].strip('/')
    PAGES.append(p)
PAGES.sort(key=lambda p: p.get('order', 99))
BYSLUG = {p['slug']: p for p in PAGES}

MONTHS = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']
def fmt_date(d): return f"{d.day} {MONTHS[d.month - 1]} {d.year}" if d else ''

def slugify(s):
    s = s.lower()
    for a, b in (('à', 'a'), ('è', 'e'), ('é', 'e'), ('ì', 'i'), ('ò', 'o'), ('ù', 'u')):
        s = s.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

POSTS = []
for f in glob.glob(f'{ROOT}/content/posts/*.md'):
    raw = open(f, encoding='utf-8').read()
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', raw, re.S)
    fm, body = (yaml.safe_load(m.group(1)), m.group(2)) if m else ({}, raw)
    if fm.get('draft'): continue
    d = fm.get('date')
    if isinstance(d, str): d = datetime.date.fromisoformat(d[:10])
    elif isinstance(d, datetime.datetime): d = d.date()
    name = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', os.path.splitext(os.path.basename(f))[0])
    url = fm.get('url') or f'/{slugify(name)}/'
    POSTS.append(dict(fm, date=d, body=body, slug=url.strip('/'), url='/' + url.strip('/') + '/'))
POSTS.sort(key=lambda p: p['date'] or datetime.date.min, reverse=True)
POSTSLUGS = {p['slug'] for p in POSTS}

MD = markdown.Markdown(extensions=['extra', 'sane_lists'])
def md(s):
    MD.reset()
    h = MD.convert(s or '')
    # bare YouTube links on their own line become video cards
    h = re.sub(r'<p>(?:<a href=")?https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{6,})[^<]*?(?:">[^<]*</a>)?</p>',
               lambda m: video(m.group(1)), h)
    return h

def canonical(slug): return DOMAIN + '/' + quote(slug + '/' if slug else '', safe='/')

# ---------------- images ----------------
IMGCACHE = {}
def image_variants(src):
    """src like /uploads/foo.jpg -> list of (url, width), height ratio"""
    if src in IMGCACHE: return IMGCACHE[src]
    path = os.path.join(ROOT, 'static', unquote(src).lstrip('/'))
    if not os.path.exists(path):
        IMGCACHE[src] = None; return None
    im = ImageOps.exif_transpose(Image.open(path))
    W, H = im.size
    base, ext = os.path.splitext(unquote(src).lstrip('/'))
    out = []
    widths = sorted({w for w in (480, 960, 1600) if w < W} | {min(W, 1600)})
    for w in widths:
        rel = f'{base}-{w}.jpg'
        dest = os.path.join(OUT, rel)
        if not os.path.exists(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            im2 = im.convert('RGB') if w == W else im.convert('RGB').resize((w, round(H * w / W)), Image.LANCZOS)
            im2.save(dest, quality=80, optimize=True, progressive=True)
        out.append(('/' + quote(rel), w))
    IMGCACHE[src] = (out, H / W)
    return IMGCACHE[src]

def img(src, alt='', sizes='(max-width: 820px) 100vw, 60vw', eager=False):
    v = image_variants(src or '')
    if not v:
        return f'<img src="{e(src)}" alt="{e(alt)}" loading="lazy">' if src else ''
    vs, ratio = v
    mid = next((u, w) for u, w in vs if w >= 960) if any(w >= 960 for _, w in vs) else vs[-1]
    load = ' fetchpriority="high"' if eager else ' loading="lazy" decoding="async"'
    srcset = ', '.join(f'{u} {w}w' for u, w in vs)
    return f'<img src="{mid[0]}" srcset="{srcset}" sizes="{sizes}" alt="{e(alt)}" width="{mid[1]}" height="{round(mid[1] * ratio)}"{load}>'

def og_image(src):
    v = image_variants(src or '')
    return DOMAIN + v[0][-1][0] if v else DOMAIN + '/assets/logo-512.png'

# ---------------- components ----------------
ARROW = '<svg class="arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
PLAY = '<svg width="26" height="26" viewBox="0 0 24 24" fill="#fff" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>'
FBICON = '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M14 8h3V4h-3c-2.8 0-4 1.8-4 4.3V10H7v4h3v8h4v-8h3l1-4h-4V8.6c0-.4.2-.6.6-.6z"/></svg>'

POSTERS = ['/uploads/parkour-padova-78f124.jpg', '/uploads/parkour-padova-ed282e.jpg', '/uploads/parkour-padova-d4acce.jpg', '/uploads/parkour-padova-2c691b.jpg']
POSTER_I = [0]
def video(yt, label='Guarda il video su YouTube', poster=None):
    """Video card: the cover is a local photo (no request to YouTube); the player loads only after consent."""
    yt = re.sub(r'.*(?:v=|youtu\.be/|embed/)([\w-]{6,}).*', r'\1', yt or '')
    if not poster:
        poster = POSTERS[POSTER_I[0] % len(POSTERS)]; POSTER_I[0] += 1
    return (f'<a class="yt" href="https://www.youtube.com/watch?v={e(yt)}" data-yt="{e(yt)}" target="_blank" rel="noopener" aria-label="{e(label)}">'
            f'{img(poster, "", sizes="(max-width:820px) 100vw, 40vw")}'
            f'<span class="play"><span>{PLAY}</span></span><span class="lbl">YouTube</span></a>')

def button(b):
    style = 'btn-red' if b.get('style') == 'rosso' else 'btn-ghost'
    link = b.get('link') or '#'
    ext = ' target="_blank" rel="noopener"' if link.startswith('http') else ''
    if b.get('question'):
        return f'<a class="btn {style} btn-block" href="{e(link)}"{ext}><span class="cta-q">{e(b["question"])}</span><span>{e(b.get("text"))} {ARROW}</span></a>'
    return f'<a class="btn {style}" href="{e(link)}"{ext}>{e(b.get("text"))} {ARROW}</a>'

def facebook_btn():
    return f'<a class="btn btn-ghost" href="{e(S["facebook"])}" target="_blank" rel="noopener">{FBICON}Segui {e(S["site_name"])} su Facebook</a>'

FORM_N = [0]
REASONS = ['Parkour bambini e ragazzi', 'Corsi per adulti', 'Formazione istruttori', 'Altro']
def form(title=''):
    FORM_N[0] += 1
    n = FORM_N[0]
    def inp(label, typ, ac, i, req=True):
        star, r = (' *', ' required') if req else (' <small>(facoltativo)</small>', '')
        return f'<div><label for="f{n}-{i}">{label}{star}</label><input id="f{n}-{i}" type="{typ}" name="{label}" autocomplete="{ac}"{r}></div>'
    opts = ''.join(f'<option>{e(o)}</option>' for o in REASONS)
    return (f'<div class="card">{f"<h3>{e(title)}</h3>" if title else ""}'
            f'<form class="form" id="form-{n}" name="contatti" method="POST" data-netlify="true" netlify-honeypot="sito-web">'
            f'<input type="hidden" name="form-name" value="contatti"><p hidden><label>Non compilare: <input name="sito-web"></label></p>'
            f'<div class="row">{inp("Nome", "text", "name", 1)}{inp("Email", "email", "email", 2)}</div>'
            f'<div class="row">{inp("Telefono", "tel", "tel", 3, False)}<div><label for="f{n}-4">Motivo del contatto *</label><select id="f{n}-4" name="Motivo del contatto" required><option value="">Seleziona…</option>{opts}</select></div></div>'
            f'<div><label for="f{n}-5">Messaggio <small>(facoltativo)</small></label><textarea id="f{n}-5" name="Messaggio" placeholder="Es. età del bambino, giorni preferiti, domande…"></textarea></div>'
            f'<label class="check"><input type="checkbox" id="f{n}-6" name="privacy" required> Dichiaro di aver letto l\'<a href="/j/privacy/">informativa privacy</a>.</label>'
            f'<button class="btn btn-red" type="submit">Invia richiesta {ARROW}</button></form>'
            f'<p class="form-ok" hidden>Grazie! Abbiamo ricevuto la tua richiesta e ti risponderemo al più presto. Per urgenze chiamaci al <strong>{e(PHONE)}</strong>.</p></div>')

def document(b):
    return (f'<a class="doc card" href="{e(b.get("file"))}" target="_blank" rel="noopener"><span class="ic">PDF</span>'
            f'<span><b>{e(b.get("title"))}</b><small>{e(b.get("description"))}</small></span></a>')

def render_blocks(blocks, ctx='page'):
    out, i = [], 0
    blocks = blocks or []
    while i < len(blocks):
        b = blocks[i]; t = b.get('type')
        if t == 'heading':
            lvl = 3 if b.get('level') == 3 else 2
            out.append(f'<h{lvl}>{e(b.get("text"))}</h{lvl}>')
        elif t == 'text':
            h = md(b.get('body'))
            if '<table' in h: h = f'<div class="table-scroll">{h}</div>'
            out.append(f'<div class="prose">{h}</div>')
        elif t == 'image':
            cap = f'<figcaption>{e(b["caption"])}</figcaption>' if b.get('caption') else ''
            im = img(b.get('src'), b.get('alt') or b.get('caption') or '')
            if b.get('link'): im = f'<a href="{e(b["link"])}">{im}</a>'
            out.append(f'<figure>{im}{cap}</figure>')
        elif t == 'divider':
            if ctx == 'page': out.append('<hr class="divider">')
        elif t == 'button':
            group = [b]
            while i + 1 < len(blocks) and blocks[i + 1].get('type') == 'button':
                i += 1; group.append(blocks[i])
            out.append('<div class="cta-row">' + ''.join(button(x) for x in group) + '</div>')
        elif t == 'video':
            group = [b]
            while i + 1 < len(blocks) and blocks[i + 1].get('type') == 'video':
                i += 1; group.append(blocks[i])
            out.append('<div class="card-list">' + ''.join(video(x.get('youtube'), poster=x.get('poster')) for x in group) + '</div>')
        elif t == 'form':
            out.append(form(b.get('title')))
        elif t == 'document':
            out.append(document(b))
        elif t == 'facebook':
            out.append(facebook_btn())
        elif t == 'columns':
            out.append(columns(b, ctx))
        i += 1
    return '\n'.join(x for x in out if x)

def split_groups(blocks):
    groups, g = [], []
    for b in blocks:
        if b.get('type') == 'divider':
            if g: groups.append(g)
            g = []
        else: g.append(b)
    if g: groups.append(g)
    return groups

def column(blocks):
    groups = split_groups(blocks or [])
    if len(groups) >= 3 and sum(1 for g in groups if g[0].get('type') == 'heading') >= len(groups) - 1:
        return '<div class="card-list">' + ''.join(
            f'<div class="card flow">{render_blocks(g, "col")}</div>' if g[0].get('type') == 'heading' and not any(x.get('type') == 'form' for x in g)
            else f'<div class="flow">{render_blocks(g, "col")}</div>' for g in groups) + '</div>'
    return f'<div class="flow">{render_blocks(blocks, "col")}</div>'

def columns(b, ctx):
    cols = [c for c in (b.get('columns') or []) if c.get('blocks')]
    if not cols: return ''
    if ctx == 'article':
        return '<div class="flow">' + ''.join(render_blocks(c['blocks'], 'col') for c in cols) + '</div>'
    lay = b.get('layout')
    if len(cols) == 2 and lay == 'stretta-larga': tmpl = 'minmax(0,2fr) minmax(0,3fr)'
    elif len(cols) == 2 and lay == 'larga-stretta': tmpl = 'minmax(0,3fr) minmax(0,2fr)'
    else: tmpl = f'repeat({len(cols)},minmax(0,1fr))'
    return f'<div class="cols" style="grid-template-columns:{tmpl}">' + ''.join(column(c['blocks']) for c in cols) + '</div>'

def first_image(blocks):
    for b in blocks or []:
        if b.get('type') == 'image' and b.get('src'): return b['src']
        if b.get('type') == 'columns':
            for c in b.get('columns') or []:
                r = first_image(c.get('blocks'))
                if r: return r
    return None

def first_text(blocks):
    for b in blocks or []:
        if b.get('type') == 'text': return plain(md(b.get('body')))
        if b.get('type') == 'columns':
            for c in b.get('columns') or []:
                r = first_text(c.get('blocks'))
                if r: return r
    return ''

def plain(h): return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', h or ''))).strip()
def trim(s, n=158): return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '…'

# ---------------- chrome ----------------
def active_section(url):
    if url.strip('/') in POSTSLUGS: return '/blog-parkour-padova/'
    for it in S['menu']:
        if url == it['link'] or any(url == c['link'] for c in it.get('children') or []): return it['link']
    return None

def header(url):
    act = active_section(url)
    items = []
    for it in S['menu']:
        ac = ' aria-current="page"' if it['link'] == act else ''
        if it.get('children'):
            subs = ''.join(f'<a href="{e(c["link"])}">{e(c["label"])}</a>' for c in it['children'])
            items.append(f'<div class="has-sub"><a href="{e(it["link"])}"{ac}>{e(it["label"])}</a>'
                         f'<button class="dd" aria-expanded="false" aria-label="Apri sottomenu {e(it["label"])}"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M6 9l6 6 6-6"/></svg></button>'
                         f'<div class="sub">{subs}</div></div>')
        else:
            items.append(f'<a href="{e(it["link"])}"{ac}>{e(it["label"])}</a>')
    mb = S.get('menu_button') or {}
    if mb.get('label'): items.append(f'<a class="btn btn-red" href="{e(mb.get("link"))}">{e(mb["label"])}</a>')
    return f'''<a class="skip" href="#main">Vai al contenuto</a>
<header class="site-header"><div class="wrap">
<a class="brand" href="/" aria-label="{e(S['site_name'])} – Home"><img src="/assets/logo-192.png" alt="" width="44" height="44"><b>{e(S['site_name'])}<span>{e(S['tagline'])}</span></b></a>
<button class="burger" aria-expanded="false" aria-controls="nav" aria-label="Menu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 6h18M3 12h18M3 18h18"/></svg></button>
<nav class="nav" id="nav" aria-label="Principale">{''.join(items)}</nav>
</div></header>'''

def footer():
    socials = ''.join(f'<li><a href="{e(S[k])}" target="_blank" rel="noopener">{n}</a></li>' for k, n in (('facebook', 'Facebook'), ('instagram', 'Instagram'), ('youtube', 'YouTube')) if S.get(k))
    return f'''<footer class="site-footer"><div class="wrap">
<div class="f-grid">
<div class="f-brand"><a class="brand" href="/"><img src="/assets/logo-192.png" alt="" width="44" height="44" loading="lazy"><b>{e(S['site_name'])}<span>{e(S['tagline'])}</span></b></a>
<p>{e(S.get('footer_text'))}</p></div>
<div><h3>Corsi</h3><ul><li><a href="/parkour-movimentonaturale-yoga-padova/">Parkour e movimento</a></li><li><a href="/bambini-e-ragazzi/">Bambini e ragazzi</a></li><li><a href="/formazione-istruttori/">Formazione istruttori</a></li><li><a href="/il-parkour/">Il parkour</a></li></ul></div>
<div><h3>Scuola</h3><ul><li><a href="/scuola-parkour-padova/">Chi siamo</a></li><li><a href="/scuola-parkour-padova/politica-economica/">Politica economica</a></li><li><a href="/blog-parkour-padova/">Blog</a></li><li><a href="/contatti/parkour-padova/">Contatti</a></li></ul></div>
<div><h3>Contatti</h3><ul><li><a href="tel:{PHONE_TEL}">{e(PHONE)}</a></li><li><a href="mailto:{e(EMAIL)}">{e(EMAIL)}</a></li>{socials}<li><a class="btn btn-red" href="/contatti/parkour-padova/">Lezione di prova gratuita</a></li></ul></div>
</div>
<div class="f-legal"><span>© {datetime.date.today().year} {e(S.get('legal_name'))} – {e(S['site_name'])}. Tutti i diritti riservati.</span>
<ul><li><a href="/j/privacy/">Privacy policy</a></li><li><a href="/cookie-policy/">Cookie policy</a></li><li><button type="button" class="linkbtn" data-consent-open>Preferenze cookie</button></li><li><a href="/sitemap/">Mappa del sito</a></li></ul></div>
</div></footer>
<div class="quickbar"><a class="btn btn-ghost" href="tel:{PHONE_TEL}">Chiama</a><a class="btn btn-red" href="/contatti/parkour-padova/">Prova gratuita</a></div>'''

FONTS = '<link rel="preload" href="/assets/fonts/fraunces-normal-latin.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="/assets/fonts/instrument-sans-normal-latin.woff2" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="/assets/fonts/fonts.css">'

def org():
    return {"@type": "SportsOrganization", "@id": DOMAIN + "/#scuola", "sport": "Parkour", "name": f"{S['site_name']} – Scuola di parkour a Padova",
            "url": DOMAIN + "/", "logo": DOMAIN + "/assets/logo-512.png", "image": og_image(HOME['hero'].get('image')),
            "telephone": PHONE_TEL, "email": EMAIL, "description": HOME.get('description'),
            "address": {"@type": "PostalAddress", "addressLocality": "Padova", "addressRegion": "PD", "addressCountry": "IT"},
            "areaServed": S.get('areas') or ['Padova'], "sameAs": [S[k] for k in ('facebook', 'instagram', 'youtube') if S.get(k)],
            "parentOrganization": {"@type": "SportsOrganization", "name": S.get('legal_name')}}

WRITTEN = []
def write_page(url, title, desc, body, crumbs=None, og=None, ld=None, noindex=False, is_post=False):
    lds = [org(), {"@type": "WebSite", "@id": DOMAIN + "/#website", "name": S['site_name'], "url": DOMAIN + "/",
                   "inLanguage": "it-IT", "publisher": {"@id": DOMAIN + "/#scuola"}}] if url == '/' else []
    if crumbs:
        lds.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": canonical(h.strip('/'))} for i, (n, h) in enumerate(crumbs)]})
    if ld: lds.append(ld)
    def clean(o):
        if isinstance(o, dict): return {k: clean(v) for k, v in o.items() if v not in (None, '', [])}
        if isinstance(o, list): return [clean(x) for x in o]
        return o
    ldj = json.dumps({"@context": "https://schema.org", "@graph": clean(lds)}, ensure_ascii=False).replace('</', '<\\/') if lds else ''
    slug = url.strip('/')
    doc = f'''<!doctype html>
<html lang="it"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical(slug)}">
{'<meta name="robots" content="noindex">' if noindex else ''}
<meta property="og:type" content="{'article' if is_post else 'website'}"><meta property="og:locale" content="it_IT"><meta property="og:site_name" content="{e(S['site_name'])}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{canonical(slug)}"><meta property="og:image" content="{e(og or og_image(HOME['hero'].get('image')))}">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#081C35">
<link rel="icon" href="/favicon.png" type="image/png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
{FONTS}
<link rel="stylesheet" href="/assets/site.css">
{f'<script type="application/ld+json">{ldj}</script>' if ldj else ''}
</head><body>
{header(url)}
<main id="main">
{body}
</main>
{footer()}
<script src="/assets/consent.js"></script>
<script src="/assets/site.js" defer></script>
</body></html>'''
    path = os.path.join(OUT, slug, 'index.html') if slug else os.path.join(OUT, 'index.html')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(doc)
    WRITTEN.append((path, slug))

def crumbs_html(crumbs):
    lis = [f'<li aria-current="page">{e(n)}</li>' if i == len(crumbs) - 1 else f'<li><a href="{e(h)}">{e(n)}</a></li>' for i, (n, h) in enumerate(crumbs)]
    return f'<nav aria-label="Percorso"><ol class="crumbs">{"".join(lis)}</ol></nav>'

def page_head(crumbs, tag, title, subtitle='', notice='', image=None, image_alt=''):
    subs = ''.join(f'<p class="sub">{e(s)}</p>' for s in (subtitle or '').split('\n') if s.strip())
    text = (f'<div class="ph-text">{crumbs_html(crumbs)}<p class="tag">{e(tag)}</p><h1>{e(title)}</h1>{subs}'
            + (f'<p class="notice">{e(notice)}</p>' if notice else '') + '</div>')
    return f'<section class="page-head"><div class="wrap">{text}</div></section>'

def take_head_image(p):
    """Use head_image if set, otherwise move the first top-level photo of the page into the header."""
    blocks = list(p.get('blocks') or [])
    if p.get('head_image'):
        return blocks, p['head_image'], p.get('head_image_alt') or p.get('title')
    for i, b in enumerate(blocks[:6]):
        if b.get('type') == 'columns': break
        if b.get('type') == 'image' and b.get('src') and not b.get('link'):
            del blocks[i]
            clean = []
            for x in blocks:  # no leading or doubled dividers after removing the photo
                if x.get('type') == 'divider' and (not clean or clean[-1].get('type') == 'divider'): continue
                clean.append(x)
            return clean, b['src'], b.get('alt') or b.get('caption') or p.get('title')
    return blocks, None, ''


def cta_aside():
    return (f'<div class="aside-cta"><h2>{e(S.get("cta_title"))}</h2>'
            f'<div class="cta-row"><a class="btn btn-red" href="/contatti/parkour-padova/">Prenota la prova {ARROW}</a>'
            f'<a class="btn btn-ghost" href="tel:{PHONE_TEL}">{e(PHONE)}</a></div></div>')

# ---------------- pages ----------------
def post_card(p, feature=False):
    cover = p.get('cover') or first_md_image(p['body'])
    ph = img(cover, p['title'], sizes='(max-width:620px) 100vw, 33vw') if cover else '<span class="ph-fallback"><img src="/assets/logo-192.png" alt="" width="192" height="192" loading="lazy"></span>'
    ex = p.get('excerpt') or trim(plain(md(p['body'])), 200)
    d = p['date']
    return (f'<a class="post-card{" feature" if feature else ""}" href="{e(p["url"])}"><div class="ph">{ph}</div>'
            f'<div class="bd"><time datetime="{d.isoformat() if d else ""}">{fmt_date(d)}</time><h2>{e(p["title"])}</h2><p>{e(ex)}</p></div></a>')

def first_md_image(body):
    m = re.search(r'!\[[^\]]*\]\(([^)\s]+)', body or '')
    return m.group(1) if m else None

def build_home():
    H = HOME; hero = H['hero']; q = H['quote']
    gal = H.get('gallery') or []
    slides = ''.join(
        f'<figure class="car-slide" role="group" aria-roledescription="slide" aria-label="{i + 1} di {len(gal)}">'
        f'{img(g.get("image"), g.get("caption") or "", sizes="(max-width:820px) 88vw, 70vw", eager=(i == 0))}'
        + (f'<figcaption>{e(g.get("caption"))}</figcaption>' if g.get('caption') else '') + '</figure>'
        for i, g in enumerate(gal))
    dots = ''.join(f'<button type="button" class="car-dot" aria-label="Vai alla foto {i + 1}"></button>' for i in range(len(gal)))
    carousel = (f'<div class="carousel" data-carousel aria-roledescription="carosello" aria-label="Foto della scuola">'
                f'<div class="car-track" tabindex="0">{slides}</div>'
                f'<div class="car-ui"><div class="car-dots">{dots}</div><div class="car-arrows">'
                f'<button type="button" class="car-prev" aria-label="Foto precedente"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 6l-6 6 6 6"/></svg></button>'
                f'<button type="button" class="car-next" aria-label="Foto successiva"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l6 6-6 6"/></svg></button>'
                f'</div></div></div>') if slides else ''
    facts = ''.join(f'<div><h3>{e(x.get("title"))}</h3><p>{e(x.get("text"))}</p></div>' for x in H.get('facts') or [])
    rows = ''.join(f'<a class="row-link" href="{e(c.get("link"))}"><span class="rl-label">{e(c.get("label"))}</span><span class="rl-text">{e(c.get("text"))}</span><span class="rl-go" aria-hidden="true">→</span></a>' for c in H.get('courses') or [])
    paths = ''.join(f'<a class="row-link" href="{e(c.get("link"))}"><span class="rl-label">{e(c.get("title"))}</span><span class="rl-text">{e(c.get("question"))} <b>{e(c.get("action"))}</b></span><span class="rl-go" aria-hidden="true">→</span></a>' for c in H.get('paths') or [])
    socials = ''.join(f'<div class="social-card">{video(v, "Video su YouTube")}</div>' for v in (H.get('videos') or [])[:2])
    withc = [x for x in POSTS if x.get('cover') or first_md_image(x['body'])][:3]
    cards = ''.join(post_card(p) for p in withc)
    body = f'''
<section class="hero"><div class="wrap">
<div class="hero-grid">
<div><p class="tag">{e(hero.get('tag'))}</p>
<h1>{e(hero.get('title_1'))} <em>{e(hero.get('title_2'))}</em> {e(hero.get('title_3'))}</h1></div>
<div class="hero-side"><p class="lead">{e(hero.get('lead'))}</p>
<div class="cta-row"><a class="btn btn-dark" href="/contatti/parkour-padova/">{e(hero.get('button'))}</a><a class="btn btn-text" href="#corsi">{e(hero.get('button_2'))} →</a></div></div>
</div>
{carousel}
</div></section>
<section class="facts-band"><div class="wrap"><div class="facts">{facts}</div></div></section>
<section class="section" id="corsi"><div class="wrap split">
<div class="split-head"><p class="tag">I corsi</p><h2>{e(H.get('courses_title'))}</h2><p>{e(H.get('courses_text'))}</p></div>
<div class="row-list">{rows}</div>
</div></section>
<section class="section"><div class="wrap split">
<div class="split-head"><p class="tag">Per iniziare</p><h2>{e(H.get('paths_title'))}</h2></div>
<div class="row-list">{paths}</div>
</div></section>
<section class="section"><div class="wrap quote-grid">
<div class="flow"><p class="tag">{e(q.get('eyebrow'))}</p>
<blockquote class="big">“{e(q.get('text'))}”</blockquote>
<p class="sig"><b>{e(q.get('author'))}</b> - {e(q.get('role'))}</p>
<a class="btn btn-text" href="/scuola-parkour-padova/">La nostra storia →</a></div>
<figure>{img(q.get('image'), q.get('author'), sizes='(max-width:820px) 100vw, 420px')}</figure>
</div></section>
<section class="section"><div class="wrap">
<div class="section-head"><h2>Dal blog</h2><a class="btn btn-text" href="/blog-parkour-padova/">Tutti gli articoli →</a></div>
<div class="posts">{cards}</div>
</div></section>
<section class="section"><div class="wrap">
<div class="section-head"><h2>{e(H.get('social_title'))}</h2></div>
<div class="social-grid">{socials}
<div class="social-card card flow"><h3>Facebook</h3><p>{e(H.get('facebook_text'))}</p>{facebook_btn()}</div>
</div></div></section>
<section class="section"><div class="wrap"><div class="contact-panel">
<div class="flow"><h2>{e(H.get('contact_title'))}</h2><p class="lede">{e(H.get('contact_text'))}</p>
<p class="big-contact"><a href="tel:{PHONE_TEL}">{e(PHONE)}</a><a href="mailto:{e(EMAIL)}">{e(EMAIL)}</a></p></div>
{form()}
</div></div></section>'''
    write_page('/', H.get('seo_title'), H.get('description'), body)

def crumbs_for(p):
    c = [('Home', '/')]
    if p.get('parent') and p['parent'].strip('/') in BYSLUG:
        par = BYSLUG[p['parent'].strip('/')]
        c.append((par.get('menu_label') or par['title'], par['url']))
    c.append((p.get('menu_label') or p['title'], p['url']))
    return c

def build_page(p):
    crumbs = crumbs_for(p)
    lay = p.get('layout')
    blocks = p.get('blocks') or []
    if p.get('head_image') and lay == 'standard':
        blocks = [{'type': 'image', 'src': p['head_image'], 'alt': p.get('head_image_alt') or p.get('title'), 'caption': p.get('head_image_caption') or ''}] + list(blocks)
    head = page_head(crumbs, p.get('tag'), p.get('title'), p.get('subtitle'), p.get('notice'))
    if lay == 'blog':
        withc = [x for x in POSTS if x.get('cover') or first_md_image(x['body'])]
        other = [x for x in POSTS if x not in withc]
        cards = (post_card(withc[0], True) + ''.join(post_card(x) for x in withc[1:])) if withc else ''
        rows = ''.join(f'<a class="post-row" href="{e(x["url"])}"><time datetime="{x["date"].isoformat() if x["date"] else ""}">{fmt_date(x["date"])}</time>'
                       f'<span><b>{e(x["title"])}</b><small>{e(x.get("excerpt") or trim(plain(md(x["body"])), 160))}</small></span>{ARROW}</a>' for x in other)
        body = head + (f'<section class="section"><div class="wrap flow"><div class="posts auto">{cards}</div>'
                       + (f'<h2 class="list-title">Altri articoli</h2><div class="post-list">{rows}</div>' if rows else '') + '</div></section>')
    elif lay == 'contatti':
        def _fig(b):
            cap = '<figcaption>' + e(b.get('caption')) + '</figcaption>' if b.get('caption') else ''
            return '<figure>' + img(b.get('src'), b.get('alt'), sizes='(max-width:820px) 100vw, 40vw') + cap + '</figure>'
        photos = ''.join(_fig(b) for b in (p.get('blocks') or []) if b.get('type') == 'image')
        fb = f'<div class="card flow"><p class="eyebrow">Seguici su Facebook</p>{facebook_btn()}</div>' if S.get('facebook') else ''
        body = head + f'''<section class="section"><div class="wrap"><div class="cols" style="grid-template-columns:minmax(0,5fr) minmax(0,7fr)">
<div class="flow">
<div class="card flow"><p class="eyebrow">Chiamaci</p><p><a href="tel:{PHONE_TEL}" style="font:800 2.2rem/1 var(--f-display);text-decoration:none">{e(PHONE)}</a></p></div>
<div class="card flow"><p class="eyebrow">Facci una domanda</p><p><a href="mailto:{e(EMAIL)}" style="font-weight:700;font-size:1.15rem">{e(EMAIL)}</a></p></div>
{fb}{photos}
</div>
<div class="flow"><h2>Scrivici</h2><p class="lede">{e(p.get('intro'))}</p>{form()}
<ul class="trust">{''.join(f'<li>{e(t)}</li>' for t in (p.get('trust') or []))}</ul></div>
</div></div></section>'''
    else:
        body = head + f'<section class="section"><div class="wrap flow page-body">{render_blocks(blocks)}{cta_aside() if p.get("show_cta") else ""}</div></section>'
    im = first_image(p.get('blocks'))
    desc = p.get('description') or trim(first_text(p.get('blocks'))) or HOME.get('description')
    write_page(p['url'], p.get('seo_title') or f"{p['title']} | {S['site_name']}", desc, body, crumbs, og_image(im) if im else None, noindex=p.get('noindex'))

def build_post(i):
    p = POSTS[i]
    crumbs = [('Home', '/'), ('Blog', '/blog-parkour-padova/'), (p['title'], p['url'])]
    cover = p.get('cover')
    body_html = md(p['body'])
    body_html = re.sub(r'<p><img ([^>]*)></p>\s*<p><em>(.*?)</em></p>', r'<figure><img \1><figcaption>\2</figcaption></figure>', body_html)
    body_html = re.sub(r'<p>(<img [^>]*>)</p>', r'<figure>\1</figure>', body_html)
    body_html = re.sub(r'<img alt="([^"]*)" src="(/uploads/[^"]+)"\s*/?>', lambda m: img(m.group(2), m.group(1), sizes='(max-width:860px) 100vw, 820px'), body_html)
    body_html = body_html.replace('<table', '<div class="table-scroll"><table').replace('</table>', '</table></div>')
    cov = f'<figure class="cover">{img(cover, p["title"], sizes="(max-width:860px) 100vw, 820px", eager=True)}</figure>' if cover and not first_md_image(p['body']) else ''
    prev_p = POSTS[i + 1] if i + 1 < len(POSTS) else None
    next_p = POSTS[i - 1] if i > 0 else None
    pn = '<div class="pn">'
    pn += f'<a class="card" href="{e(prev_p["url"])}"><small>← Articolo precedente</small><b>{e(prev_p["title"])}</b></a>' if prev_p else '<span></span>'
    pn += f'<a class="card next" href="{e(next_p["url"])}"><small>Articolo successivo →</small><b>{e(next_p["title"])}</b></a>' if next_p else '<span></span>'
    pn += '</div>'
    d = p['date']
    body = (f'<section class="page-head"><div class="wrap">{crumbs_html(crumbs)}<div><span class="tag">Blog · <time datetime="{d.isoformat() if d else ""}">{fmt_date(d)}</time></span></div>'
            f'<h1>{e(p["title"])}</h1></div></section>'
            f'<section class="section"><article class="wrap"><div class="article flow">{cov}<div class="prose">{body_html}</div>{cta_aside()}{pn}</div></article></section>')
    im = cover or first_md_image(p['body'])
    desc = p.get('description') or p.get('excerpt') or trim(plain(body_html))
    ld = {"@type": "BlogPosting", "headline": p['title'], "datePublished": d.isoformat() if d else None, "inLanguage": "it-IT",
          "author": {"@type": "Person", "name": p['author']} if p.get('author') else {"@id": DOMAIN + "/#scuola"}, "publisher": {"@id": DOMAIN + "/#scuola"},
          "mainEntityOfPage": canonical(p['slug']), "image": og_image(im) if im else None}
    write_page(p['url'], f"{p['title']} | {S['site_name']}", trim(desc), body, crumbs, og_image(im) if im else None, ld, is_post=True)

def build_sitemap_page():
    li = '<li><a href="/">Home</a></li>' + ''.join(f'<li><a href="{e(p["url"])}">{e(p.get("menu_label") or p["title"])}</a></li>' for p in PAGES if not p.get('noindex'))
    lp = ''.join(f'<li><a href="{e(p["url"])}">{e(p["title"])}</a> <small style="color:var(--muted)">· {fmt_date(p["date"])}</small></li>' for p in POSTS)
    crumbs = [('Home', '/'), ('Mappa del sito', '/sitemap/')]
    body = (page_head(crumbs, 'Mappa del sito', 'Mappa del sito') +
            f'<section class="section"><div class="wrap cols" style="grid-template-columns:1fr 1fr"><div class="prose flow"><h2>Pagine</h2><ul>{li}</ul></div>'
            f'<div class="prose flow"><h2>Articoli</h2><ul>{lp}</ul></div></div></section>')
    write_page('/sitemap/', f"Mappa del sito | {S['site_name']}", f"Tutte le pagine e gli articoli del sito {S['site_name']}, scuola di parkour a Padova.", body, crumbs)

def build_404():
    body = (f'<section class="page-head"><div class="wrap"><span class="tag">Errore 404</span><h1>Questa pagina ha fatto un salto altrove</h1>'
            f'<p class="sub">La pagina che cerchi non esiste più o è stata spostata.</p></div></section>'
            f'<section class="section"><div class="wrap cta-row"><a class="btn btn-red" href="/">Torna alla home {ARROW}</a><a class="btn btn-ghost" href="/blog-parkour-padova/">Vai al blog</a></div></section>')
    write_page('/__404/', f"Pagina non trovata | {S['site_name']}", 'Pagina non trovata', body, noindex=True)
    shutil.move(os.path.join(OUT, '__404', 'index.html'), os.path.join(OUT, '404.html'))
    os.rmdir(os.path.join(OUT, '__404'))
    WRITTEN[:] = [(p, s) for p, s in WRITTEN if s != '__404']

def to_relative(path, slug):
    """preview mode: rewrite root-absolute links so the files work without a web server."""
    depth = len([x for x in slug.split('/') if x])
    up = '../' * depth
    s = open(path, encoding='utf-8').read()
    def fix(u):
        if not u.startswith('/') or u.startswith('//'): return u
        p = u.lstrip('/')
        if p == '' or p.endswith('/'): p += 'index.html'
        return up + p
    s = re.sub(r'(href|src)="(/[^"]*)"', lambda m: f'{m.group(1)}="{fix(m.group(2))}"', s)
    s = re.sub(r'srcset="([^"]+)"', lambda m: 'srcset="' + ', '.join(fix(x.split(' ')[0]) + ' ' + x.split(' ')[1] for x in m.group(1).split(', ')) + '"', s)
    open(path, 'w', encoding='utf-8').write(s)

# ---------------- run ----------------
if os.path.exists(OUT): shutil.rmtree(OUT)
shutil.copytree(os.path.join(ROOT, 'static'), OUT)
shutil.copytree(os.path.join(ROOT, 'admin'), os.path.join(OUT, 'admin'))
build_home()
for p in PAGES: build_page(p)
for i in range(len(POSTS)): build_post(i)
build_sitemap_page()
build_404()
urls = [''] + [p['slug'] for p in PAGES if not p.get('noindex')] + [p['slug'] for p in POSTS] + ['sitemap']
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u in urls:
    p = next((x for x in POSTS if x['slug'] == u), None)
    lm = f'<lastmod>{p["date"].isoformat()}</lastmod>' if p and p['date'] else ''
    sm.append(f'<url><loc>{canonical(u)}</loc>{lm}</url>')
sm.append('</urlset>')
open(os.path.join(OUT, 'sitemap.xml'), 'w').write('\n'.join(sm))
open(os.path.join(OUT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: {DOMAIN}/sitemap.xml\n')
olds = ['paura-e-parkour', 'parkourpadova-pedagogia', 'parkour-competizioni-agonismo', 'allenamento-parkour-preparazione-adattamento',
        'forza-equilibrio-propriocezione', 'parkoureprogressività']
red = [f'/{quote(o)}.html  /{quote(o)}/  301' for o in olds] + ['/rss/blog  /blog-parkour-padova/  301', '/j/sitemap  /sitemap/  301']
open(os.path.join(OUT, '_redirects'), 'w').write('\n'.join(red) + '\n')
if MODE == 'preview':
    for path, slug in WRITTEN: to_relative(path, slug)
    to_relative(os.path.join(OUT, '404.html'), '')
print(f'Sito generato in {OUT}: {len(WRITTEN)} pagine, {len(POSTS)} articoli.')
