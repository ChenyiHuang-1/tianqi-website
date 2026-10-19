"""Build the Tianqi Materials site (English + Chinese) into ./public.

    python build.py --src "E:\\uv\\标化"          # rebuild changed pattern images + all pages
    python build.py                               # pages only (images already in public/img)
    python build.py --src "E:\\uv\\标化" --force  # rebuild every image

Pattern photos in --src are named <number>.jpg (101.jpg ...). Extra views of the same
pattern are <number>-2.jpg, <number>-3.jpg ... and appear on the pattern page.
All content lives in data/*.json and pages/<lang>/*.html. See README.md.
Needs Python 3.9+ and Pillow (pip install pillow).
"""
import argparse, datetime, html, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUB = HERE / "public"
DATA = HERE / "data"
LANGS = ("en", "zh")
THUMB_W, THUMB_H, FULL_W, HERO_W = 360, 480, 1000, 1800


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


SITE, COMPANY, CATS, PRODUCTS, PATTERNS, T, CUSTOMERS = (load(n) for n in
    ("site.json", "company.json", "categories.json", "products.json", "patterns.json", "i18n.json", "customers.json"))
e = html.escape


def t(key, lang):
    return T[key][lang]


def L(obj, lang):
    """Pick the language from a {"en":..,"zh":..} value."""
    if obj is None:
        return ""
    if isinstance(obj, dict):
        return obj.get(lang) or obj.get("en", "")
    return str(obj)


def url(lang, path=""):
    return ("/zh/" if lang == "zh" else "/") + path


# ------------------------------------------------------------------ images
# The photos carry a Chinese label ("浙江天琦-101") in the bottom 15%; the web images leave it out.
FULL_KEEP = 0.85


def make_images(src, force):
    from PIL import Image
    made = 0

    def out_of_date(out, f):
        return force or not out.exists() or out.stat().st_mtime < f.stat().st_mtime

    def save(im, out, w, crop_h=None, q=74):
        out.parent.mkdir(parents=True, exist_ok=True)
        h = round(im.height * w / im.width)
        im2 = im.resize((w, h), Image.LANCZOS)
        if crop_h and crop_h < 1:
            crop_h = round(h * crop_h)
        if crop_h:
            im2 = im2.crop((0, 0, w, min(h, crop_h)))
        im2.save(out, "WEBP", quality=q, method=6)

    for p in PATTERNS:
        files = [src / f"{p['id']}.jpg"] + sorted(src.glob(f"{p['id']}-*.jpg"))
        for i, f in enumerate(files):
            if not f.exists():
                continue
            suffix = "" if i == 0 else f"-{i + 1}"
            targets = [(PUB / "img/patterns/full" / f"{p['id']}{suffix}.webp", FULL_W, FULL_KEEP, 74)]
            if i == 0:
                targets.append((PUB / "img/patterns/thumb" / f"{p['id']}.webp", THUMB_W, THUMB_H, 68))
            todo = [x for x in targets if out_of_date(x[0], f)]
            if not todo:
                continue
            with Image.open(f) as im:
                im.draft("RGB", (FULL_W * 2, FULL_W * 4))
                im = im.convert("RGB")
                for out, w, ch, q in todo:
                    save(im, out, w, ch, q)
                    made += 1
    hero = src / f"{SITE['hero_pattern']}.jpg"
    out = PUB / "img/hero.webp"
    if hero.exists() and out_of_date(out, hero):
        with Image.open(hero) as im:
            im = im.convert("RGB")
            w, h = im.size
            box_h = int(w * 9 / 16)
            top = max(0, (h - box_h) // 3)
            im = im.crop((0, top, w, top + box_h)).resize((HERO_W, int(HERO_W * 9 / 16)), Image.LANCZOS)
            out.parent.mkdir(parents=True, exist_ok=True)
            im.save(out, "WEBP", quality=78, method=6)
            made += 1
    print(f"images written: {made}")


def views(pid):
    full = PUB / "img/patterns/full"
    extra = sorted(full.glob(f"{pid}-*.webp"), key=lambda f: int(f.stem.split("-")[1]))
    return [f"/img/patterns/full/{pid}.webp"] + [f"/img/patterns/full/{f.name}" for f in extra]


# ------------------------------------------------------------------ pieces
def img_src(ref, kind="thumb"):
    """Product images: 'pattern:181' uses a pattern photo, otherwise assets/img/<name>.webp."""
    if not ref:
        return ""
    if ref.startswith("pattern:"):
        return f"/img/patterns/{kind}/{ref.split(':')[1]}.webp"
    return f"/assets/img/{ref}.webp"


def picture(ref, alt, lang, cls="", kind="thumb"):
    s = img_src(ref, kind)
    if not s:
        return f'<div class="ph-empty {cls}"><span>{t("photo_soon", lang)}</span></div>'
    return f'<img class="{cls}" src="{s}" alt="{e(alt)}" loading="lazy">'


def chunks(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs), n) if len(xs[i:i + n]) == n]


def carousel_extra(featured, total=24):
    """More patterns for the home carousel: round-robin across pattern types so each page mixes styles."""
    seen = {p["id"] for p in featured}
    groups = {}
    for p in PATTERNS:
        tv = p.get("tags_verified") or {}
        if p["id"] not in seen and tv.get("effect") == "bold":
            groups.setdefault((p.get("tags_verified") or {}).get("pattern", ""), []).append(p)
    pools = [g[::max(1, len(g) // 8)] for g in groups.values()]
    out = []
    while len(out) < total and any(pools):
        for g in pools:
            if g and len(out) < total:
                out.append(g.pop(0))
    return out


def pattern_carousel(slides, lang):
    pages = "".join(f'<ul class="pgrid featured car-page" aria-label="{i + 1} / {len(slides)}">'
                    + "".join(pattern_card(p, lang, True) for p in sl) + "</ul>" for i, sl in enumerate(slides))
    dots = "".join(f'<button type="button" class="car-dot" aria-label="{i + 1}"></button>' for i in range(len(slides)))
    return (f'<div class="pcar" data-carousel><div class="car-track">{pages}</div>'
            f'<div class="car-nav"><button type="button" class="car-btn prev" aria-label="{t("prev", lang)}">&#8592;</button>'
            f'<div class="car-dots">{dots}</div>'
            f'<button type="button" class="car-btn next" aria-label="{t("next", lang)}">&#8594;</button></div></div>')


# Words used to describe a pattern from its tags, in titles, descriptions and image text.
PATTERN_WORDS = {
    "en": {"silver": "Silver", "pearl": "Pearl", "holographic": "Rainbow", "geometric": "Geometric", "fluid": "Fluid",
           "texture": "Texture", "lines": "Light-Beam", "motif": "Motif",
           "subtle": "a subtle", "medium": "a medium", "bold": "a bold"},
    "zh": {"silver": "银色", "pearl": "珍珠彩", "holographic": "彩虹", "geometric": "几何", "fluid": "流体",
           "texture": "肌理", "lines": "线条光束", "motif": "主题图案",
           "subtle": "低调", "medium": "适中", "bold": "强烈"},
}


def pattern_kind(p, lang):
    """'Pearl Texture Holographic Pattern' / '珍珠彩肌理光刻纹样', or '' when the pattern has no tags."""
    tv = p.get("tags_verified") or {}
    w = PATTERN_WORDS[lang]
    words = [w[tv[k]] for k in ("finish", "pattern") if tv.get(k) in w]
    if not words:
        return ""
    return " ".join(words) + " Holographic Pattern" if lang == "en" else "".join(words) + "光刻纹样"


def pattern_alt(p, lang):
    kind = pattern_kind(p, lang)
    name = f'{t("pattern", lang)} {p["id"]}'
    if not kind:
        return name
    return f"{name}, {kind.lower()}" if lang == "en" else f"{name}，{kind}"


def similar_patterns(p, n=7):
    """Patterns with the same pattern type (same finish first), nearest numbers first."""
    tv = p.get("tags_verified") or {}
    if not tv.get("pattern"):
        return []
    same = [q for q in PATTERNS if q is not p and (q.get("tags_verified") or {}).get("pattern") == tv["pattern"]]
    num = int(p["id"]) if p["id"].isdigit() else 0
    same.sort(key=lambda q: ((q.get("tags_verified") or {}).get("finish") != tv.get("finish"),
                             abs((int(q["id"]) if q["id"].isdigit() else 0) - num)))
    return same[:n]


def pattern_card(p, lang, button=False):
    pid = p["id"]
    href = url(lang, f"holographic-patterns/{pid}/")
    tags = p.get("tags_verified") or {}
    data = " ".join(f'data-{k}="{e(v)}"' for k, v in tags.items())
    btn = f'<a class="btn small-btn" href="{href}">{t("view_pattern", lang)}</a>' if button else ""
    return (f'<li class="pcard" data-id="{pid}" {data}><a class="pimg" href="{href}">'
            f'<img loading="lazy" src="/img/patterns/thumb/{pid}.webp" alt="{e(pattern_alt(p, lang))}" width="{THUMB_W}" height="{THUMB_H}"></a>'
            f'<div class="pmeta"><a href="{href}"><span class="code">{t("pattern", lang) + " " if button else ""}{pid}</span></a>{btn}</div></li>')


def product_card(pr, lang):
    href = url(lang, f"products/{pr['slug']}/")
    attrs = " ".join(f'data-{k}="{e(v)}"' for k, v in pr.get("attrs", {}).items())
    return (f'<article class="card prod" {attrs}><a class="cimg" href="{href}">{picture(pr["image"], L(pr["name"], lang), lang)}</a>'
            f'<div class="cbody"><h3><a href="{href}">{e(L(pr["name"], lang))}</a></h3><p>{e(L(pr["summary"], lang))}</p>'
            f'<a class="more-link" href="{href}">{t("view_product", lang)} →</a></div></article>')


def public_products(cat=None, sub=None):
    return [p for p in PRODUCTS if (cat is None or p["category"] == cat) and (sub is None or p["sub"] == sub)]


def sub_visible(cat, ch):
    # a sub-category shows when marked public and it has products, or it is a finished-product type
    return ch["public"] and (cat["id"] == "finished-products" or public_products(cat["id"], ch["id"]))


def contact_link(k, v=None):
    v = SITE[k] if v is None else v
    if isinstance(v, list):
        return " / ".join(contact_link(k, x) for x in v)
    if k == "email":
        return f'<a href="mailto:{e(v)}">{e(v)}</a>'
    if k == "whatsapp":
        return f'<a href="https://wa.me/{re.sub(r"[^0-9]", "", v)}" target="_blank" rel="noopener">{e(v)}</a>'
    if k == "phone":
        return f'<a href="tel:{re.sub(r"[^0-9+]", "", v)}">{e(v)}</a>'
    return e(v)


def contact_href(lang, **q):
    from urllib.parse import urlencode
    return url(lang, "contact/") + ("?" + urlencode(q) if q else "")


# ------------------------------------------------------------------ page shell
BASE = (HERE / "templates/base.html").read_text(encoding="utf-8")
# version tag for CSS/JS links, so browsers fetch the new file after each change
import hashlib
ASSET_V = hashlib.md5(b"".join((PUB / f).read_bytes() for f in ("assets/css/site.css", "assets/js/site.js"))).hexdigest()[:8]


def fill(tpl, vals):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(vals[m.group(1)]) if m.group(1) in vals else m.group(0), tpl)


def ld_script(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def organization_ld(lang):
    base = SITE["site_url"].rstrip("/")
    org = {"@context": "https://schema.org", "@type": "Organization", "@id": base + "/#org",
           "name": SITE["brand"] if lang == "en" else "天琦材料", "legalName": L(SITE["legal_name"], lang),
           "url": base + url(lang), "logo": base + "/assets/img/logo.png",
           "address": {"@type": "PostalAddress", "addressRegion": "Zhejiang", "addressCountry": "CN"}}
    if SITE.get("email"):
        org["email"] = SITE["email"]
    phones = SITE.get("phone") or []
    if phones:
        org["telephone"] = phones[0] if isinstance(phones, list) else phones
    return org


def crumb_names(lang, path):
    """Readable name for each step of a page path, for the breadcrumb data."""
    names = {"products": t("nav_products", lang), "holographic-patterns": t("nav_patterns", lang),
             "customisation": t("nav_custom", lang), "about": t("nav_about", lang), "contact": t("nav_contact", lang)}
    names.update({c["id"]: L(c["name"], lang) for c in CATS})
    names.update({pr["slug"]: L(pr["name"], lang) for pr in PRODUCTS})
    parts = [x for x in path.split("/") if x]
    out = []
    for i, x in enumerate(parts):
        if parts[0] == "holographic-patterns" and i == 1:
            out.append((f'{t("pattern", lang)} {x}', parts[:i + 1]))
        elif x in names:
            out.append((names[x], parts[:i + 1]))
    return out


def page_ld(lang, path):
    base = SITE["site_url"].rstrip("/")
    blocks = []
    if not path:
        blocks.append(organization_ld(lang))
        blocks.append({"@context": "https://schema.org", "@type": "WebSite", "url": base + url(lang),
                       "name": SITE["brand"] if lang == "en" else "天琦材料", "inLanguage": "zh-Hans" if lang == "zh" else "en",
                       "publisher": {"@id": base + "/#org"}})
    elif path == "about/":
        blocks.append(organization_ld(lang))
    crumbs = crumb_names(lang, path)
    if crumbs:
        items = [(t("nav_home", lang), base + url(lang))] + [(n, base + url(lang, "/".join(ps) + "/")) for n, ps in crumbs]
        blocks.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]})
    return "\n".join(ld_script(b) for b in blocks)


def shell(lang, path, section, title, desc, body, og_image=None):
    other = "zh" if lang == "en" else "en"
    v = {f"t_{k}": T[k][lang] for k in T}
    drop = []
    for c in CATS:
        subs = "".join(f'<a href="{url(lang, "products/" + c["id"] + "/")}#{ch["id"]}">{e(L(ch["name"], lang))}</a>'
                       for ch in c["children"] if sub_visible(c, ch))
        drop.append(f'<div class="drop-col"><a class="drop-head" href="{url(lang, "products/" + c["id"] + "/")}">{e(L(c["name"], lang))}</a>{subs}</div>')
    contact_lines = "".join(f'<span class="ct">{lab}: {contact_link(k)}</span>' for k, lab in
                            (("whatsapp", "WhatsApp"), ("email", "Email"), ("phone", "Tel")) if SITE.get(k))
    v.update(asset_v=ASSET_V, lang=lang, html_lang="zh-Hans" if lang == "zh" else "en", other_lang=other, section=section,
             title=e(title), desc=e(desc), body=body, jsonld=page_ld(lang, path), og_locale="zh_CN" if lang == "zh" else "en_US", year=datetime.date.today().year,
             canonical=SITE["site_url"].rstrip("/") + url(lang, path),
             href_en=SITE["site_url"].rstrip("/") + url("en", path), href_zh=SITE["site_url"].rstrip("/") + url("zh", path),
             href_other=url(other, path), href_en_rel=url("en", path), href_zh_rel=url("zh", path), og_image=SITE["site_url"].rstrip("/") + (og_image or "/img/hero.webp"),
             home=url(lang), u_products=url(lang, "products/"), u_patterns=url(lang, "holographic-patterns/"),
             u_custom=url(lang, "customisation/"), u_about=url(lang, "about/"), u_contact=url(lang, "contact/"),
             nav_drop="".join(drop), legal_name=e(L(SITE["legal_name"], lang)), city=e(L(SITE["city"], lang)),
             contact_lines=contact_lines,
             footer_cats="".join(f'<a href="{url(lang, "products/" + c["id"] + "/")}">{e(L(c["name"], lang))}</a>' for c in CATS))
    return fill(BASE, v)


BUILT = []


def relative(page, out):
    """Turn root links (/products/) into relative ones so pages also open from disk."""
    depth = len(out.parent.relative_to(PUB).parts)
    pre = "../" * depth or "./"
    return re.sub(r'(\s(?:href|src|data-view)=")/(?!/)', lambda m: m.group(1) + pre, page)


def write(lang, path, section, title, desc, body, og_image=None):
    out = PUB / ("zh" if lang == "zh" else "") / path / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(relative(shell(lang, path, section, title, desc, body, og_image), out), encoding="utf-8")
    BUILT.append(url(lang, path))


def page_body(lang, name, extra):
    src = (HERE / "pages" / lang / f"{name}.html").read_text(encoding="utf-8")
    m = re.match(r"\s*<!--(.*?)-->\s*", src, re.S)
    meta = dict(l.split(":", 1) for l in m.group(1).strip().splitlines())
    v = {f"t_{k}": T[k][lang] for k in T}
    v.update(extra, home=url(lang), u_products=url(lang, "products/"), u_patterns=url(lang, "holographic-patterns/"),
             u_custom=url(lang, "customisation/"), u_about=url(lang, "about/"), u_contact=url(lang, "contact/"),
             design_fee=L(SITE["design_fee"], lang))
    return fill(meta["title"].strip(), v), fill(meta["desc"].strip(), v), fill(src[m.end():], v)


# ------------------------------------------------------------------ generated pages
def facts_html(lang, with_certs=False):
    fs = [f for f in COMPANY["facts"] if f["confirmed"]]
    if not fs:
        return ""
    cells = "".join(f'<div><strong>{e(f["value"])}</strong><span>{e(L(f["label"], lang))}</span></div>' for f in fs)
    cs = [c for c in COMPANY["certificates"] if c["confirmed"] and c.get("img")] if with_certs else []
    if cs:
        # home factory block: certificates fill the cell next to patents (Hailey 2026-10-16)
        thumbs = "".join(f'<a href="/assets/img/{c["img"]}.webp"><img src="/assets/img/{c["img"]}.webp" alt="{e(L(c, lang))}" loading="lazy"></a>' for c in cs)
        names = " · ".join(e(c["short"]) for c in cs)
        cells += f'<div class="fact-certs"><div><strong>{names}</strong><span>{"certifications" if lang == "en" else "资质认证"}</span></div><p class="ct-thumbs">{thumbs}</p></div>'
    return '<div class="facts">' + cells + "</div>"


def stats_html(lang):
    """Dark strip of confirmed headline figures under the home hero."""
    fs = [f for f in COMPANY["facts"] if f["confirmed"] and f["id"] in ("capacity", "machines", "patents")]
    if not fs:
        return ""
    return ('<section class="stats"><div class="wrap stats-in">' + "".join(
        f'<div><strong>{e(f["value"])}</strong><span>{e(L(f["label"], lang))}</span></div>' for f in fs) + "</div></section>")


# Hero bubbles: x, y (% of hero), size (px), drift (px), duration (s). Fixed so builds are stable.
BUBBLE_SPOTS = [(94.5, 46.4, 200, 10, 18), (86.1, 72.1, 200, 8, 14), (82.4, 29.3, 200, 6, 20), (73.4, 7.6, 170, 8, 20),
                (98.2, 84.1, 170, 8, 22), (75.2, 53.6, 170, 8, 12), (89.0, 3.8, 170, 12, 22), (101.1, -1.2, 170, 10, 12),
                (68.6, 73.8, 140, 12, 22), (89.1, 99.0, 140, 12, 12), (68.9, 32.9, 140, 8, 22), (71.9, 94.8, 140, 8, 12),
                (63.2, -1.7, 140, 6, 14), (61.8, 100.4, 140, 12, 16), (51.6, 99.4, 140, 8, 16), (53.0, -1.8, 140, 6, 16),
                (44.0, 2.6, 115, 6, 18), (35.7, 1.5, 115, 12, 18), (42.5, 97.2, 115, 8, 12), (98.4, 20.8, 115, 8, 16),
                (27.1, 3.5, 115, 12, 16), (34.1, 99.2, 115, 10, 16), (18.9, 0.7, 115, 10, 18), (25.6, 98.2, 115, 8, 22),
                (10.2, 1.2, 115, 10, 14), (17.3, 101.4, 115, 8, 14), (2.7, 6.4, 95, 8, 18), (80.6, 95.2, 95, 10, 20),
                (9.9, 95.8, 95, 10, 22), (3.8, 88.5, 95, 6, 14), (2.3, 22.2, 95, 6, 20), (1.0, 37.5, 95, 8, 16),
                (1.6, 73.5, 95, 6, 18), (3.6, 58.9, 95, 6, 18), (76.3, 75.7, 75, 12, 18), (66.2, 52.5, 75, 6, 20),
                (100.8, 64.6, 75, 12, 20), (65.6, 13.9, 60, 6, 16), (92.2, 24.4, 60, 6, 18), (2.4, 100.7, 60, 8, 16),
                (83.6, 52.2, 60, 6, 20), (5.2, 46.1, 60, 12, 12), (81.0, 0.6, 58, 6, 14), (95.3, 66.8, 58, 4, 12),
                (78.2, 84.8, 48, 4, 14), (0.7, 49.1, 48, 4, 18), (5.7, 32.4, 48, 4, 14), (20.8, 90.2, 48, 4, 16),
                (65.6, 87.4, 48, 4, 16), (81.2, 9.7, 48, 6, 16), (56.9, 90.0, 48, 8, 14), (58.0, 8.4, 48, 4, 16),
                (30.0, 89.6, 40, 6, 12), (65.2, 61.6, 40, 4, 12), (14.5, 90.1, 40, 6, 16), (5.9, 78.6, 40, 4, 12)]


def bubble_source(img):
    return PUB / (f"img/patterns/thumb/{img[8:]}.webp" if img.startswith("pattern:") else f"assets/img/{img}.webp")


def bubble_name(img):
    return img.replace("pattern:", "p")


def make_bubbles(force=False):
    """Square bubble images with matched exposure and neutral white balance, so the
    rainbow colours come from the materials, not from how each photo was lit."""
    from PIL import Image, ImageEnhance, ImageStat
    out_dir = PUB / "img/bubbles"
    out_dir.mkdir(parents=True, exist_ok=True)
    for img in SITE.get("hero_bubbles", []):
        src, out = bubble_source(img), out_dir / f"{bubble_name(img)}.webp"
        if not src.exists() or (not force and out.exists() and out.stat().st_mtime >= src.stat().st_mtime):
            continue
        with Image.open(src) as im:
            im = im.convert("RGB")
            side = min(im.size)
            left, top = (im.width - side) // 2, (im.height - side) // 2
            im = im.crop((left, top, left + side, top + side)).resize((240, 240), Image.LANCZOS)
            means = ImageStat.Stat(im).mean
            grey = sum(means) / 3
            # pull each channel 60% of the way towards neutral grey
            gains = [1 + 0.6 * (grey / max(m, 1) - 1) for m in means]
            im = Image.merge("RGB", [ch.point(lambda v, g=g: min(255, int(v * g))) for ch, g in zip(im.split(), gains)])
            # same brightness, contrast and saturation for every bubble; highlights kept below pure white
            L = ImageStat.Stat(im.convert("L"))
            mean, std = L.mean[0], max(L.stddev[0], 1)
            k = min(1.4, max(0.7, 46 / std))
            im = im.point(lambda v: max(0, min(255, int((v - mean) * k + 112))))
            im = ImageEnhance.Color(im).enhance(0.85)
            im = im.point(lambda v: int(v * 0.9))
            im.save(out, "WEBP", quality=80, method=6)


def bubbles_html():
    out = []
    for i, (img, (x, y, s, d, t)) in enumerate(zip(SITE.get("hero_bubbles", []), BUBBLE_SPOTS)):
        src = f"/img/bubbles/{bubble_name(img)}.webp"
        out.append(f'<span class="bub" style="--x:{x}%;--y:{y}%;--s:{s}px;--d:{d}px;--t:{t}s;--dl:-{(i * 1.7) % t:.1f}s">'
                   f'<img src="{src}" alt="" decoding="async" width="{s}" height="{s}"></span>')
    return '<div class="bubbles" aria-hidden="true">' + "".join(out) + "</div>"


def customers_html(lang):
    """Past customers on About: hidden until data/customers.json says confirmed. Each language uses its own logo."""
    if not CUSTOMERS.get("confirmed"):
        return ""
    label = "Customers" if lang == "en" else "客户"
    items = []
    for c in CUSTOMERS["customers"]:
        name = e(L(c, lang))
        logo = c.get("logo_" + lang)
        inner = (f'<img src="/assets/img/{logo}.webp" alt="{name}" loading="lazy">' if logo
                 else f'<span class="wordmark">{name}</span>')
        items.append(f'<li title="{name}">{inner}</li>')
    return (f'<section class="section wrap customers"><div class="sec-head"><div><p class="label">{label}</p>'
            f'<h2>{e(L(CUSTOMERS["heading"], lang))}</h2><p>{e(L(CUSTOMERS["intro"], lang))}</p></div></div>'
            f'<ul class="logos">{"".join(items)}</ul></section>')


def certs_html(lang):
    cs = [c for c in COMPANY["certificates"] if c["confirmed"]]
    if not cs:
        return ""
    head = "Certifications" if lang == "en" else "资质认证"
    cells = []
    for c in cs:
        # full certificate scans on both languages (Hailey 2026-10-16: show unedited, like the factory gate photo)
        img = (f'<a class="cert-img" href="/assets/img/{c["img"]}.webp"><img src="/assets/img/{c["img"]}.webp" alt="{e(L(c, lang))}" loading="lazy"></a>'
               if c.get("img") else "")
        detail = f'<p>{e(L(c["detail"], lang))}</p>' if c.get("detail") else ""
        cells.append(f'<li class="cert">{img}<div><h4>{e(L(c, lang))}</h4>{detail}</div></li>')
    return f'<h3 class="mini-head">{head}</h3><ul class="certs">' + "".join(cells) + "</ul>"


def equipment_html(lang, n=6):
    return '<div class="equip">' + "".join(
        f'<figure><img src="/assets/img/{x["img"]}.webp" alt="{e(L(x, lang))}" loading="lazy"><figcaption>{e(L(x, lang))}</figcaption></figure>'
        for x in COMPANY["equipment"][:n]) + "</div>"


def category_cards(lang):
    out = []
    for c in CATS:
        href = url(lang, f"products/{c['id']}/")
        subs = "".join(f"<li>{e(L(ch['name'], lang))}</li>" for ch in c["children"] if sub_visible(c, ch))
        tag = f'<span class="rtag">{t("render_tag", lang)}</span>' if c["image"].startswith("render/") else ""
        out.append(f'<article class="card cat"><a class="cimg" href="{href}">{picture(c["image"], L(c["name"], lang), lang)}{tag}</a>'
                   f'<div class="cbody"><h3><a href="{href}">{e(L(c["name"], lang))}</a></h3><p>{e(L(c["intro"], lang))}</p>'
                   f'<ul class="sublist">{subs}</ul><a class="more-link" href="{href}">{t("view_product", lang)} →</a></div></article>')
    return '<div class="cards three">' + "".join(out) + "</div>"


FILTER_KEYS = ("colour", "surface", "effect")


def filters_for(products, lang):
    groups = []
    for k in FILTER_KEYS:
        vals = sorted({p["attrs"][k] for p in products if p.get("attrs", {}).get(k)})
        if len(vals) < 2:
            continue
        chips = f'<button class="chip" type="button" data-v="" aria-pressed="true">{t("all", lang)}</button>' + "".join(
            f'<button class="chip" type="button" data-v="{v}" aria-pressed="false">{t("v_" + v, lang)}</button>' for v in vals)
        groups.append(f'<div class="fgroup"><span class="label">{t("filter_" + k, lang)}</span><div class="chips" data-f="{k}">{chips}</div></div>')
    return f'<div class="filter-bar" data-filter-target="prod-grid">{"".join(groups)}</div>' if groups else ""


def custom_block(c, lang):
    items = c.get("custom") or []
    if not items:
        return ""
    cells = "".join(f'<div class="opt"><h3>{e(L(x["title"], lang))}</h3><p>{e(L(x["text"], lang))}</p></div>' for x in items)
    return (f'<section class="custom-opts"><div class="sec-head"><div><p class="label">{t("custom_head", lang)}</p>'
            f'<p>{t("custom_intro", lang)}</p></div><a class="btn" href="{contact_href(lang, type="custom", product=c["id"])}">{t("custom_cta", lang)}</a></div>'
            f'<div class="opts">{cells}</div></section>')


def cat_nav(lang, current):
    """Sticky product directory: back to the overview, or switch category."""
    links = [f'<a class="all" href="{url(lang, "products/")}">← {t("all_products", lang)}</a>']
    for c in CATS:
        cur = ' aria-current="page"' if c["id"] == current else ""
        links.append(f'<a href="{url(lang, "products/" + c["id"] + "/")}"{cur}>{e(L(c["name"], lang))}</a>')
    return f'<nav class="cat-nav"><div class="wrap">{"".join(links)}</div></nav>'


def build_category(c, lang):
    secs = []
    for ch in c["children"]:
        if not sub_visible(c, ch):
            continue
        prods = public_products(c["id"], ch["id"])
        if prods:
            inner = '<div class="cards four" data-grid>' + "".join(product_card(p, lang) for p in prods) + "</div>"
        else:
            inner = (f'<div class="notice"><p>{t("custom_quote_note", lang)}</p>'
                     f'<a class="btn primary" href="{contact_href(lang, type="custom", product=ch["id"])}">{t("request_custom_quote", lang)}</a></div>')
            if ch.get("image"):
                cap = f'<figcaption>{t("render_caption", lang)}</figcaption>' if ch.get("image_is_render") else ""
                inner = (f'<div class="sub-show"><figure class="render-fig"><img src="{img_src(ch["image"])}" alt="{e(L(ch["name"], lang))}" '
                         f'loading="lazy" width="1200" height="900">{cap}</figure>{inner}</div>')
        extra = ""
        if ch["id"] == "patterned-holographic-paperboard":
            extra = f'<a class="btn" href="{url(lang, "holographic-patterns/")}">{t("browse_patterns", lang)}</a>'
        secs.append(f'<section class="sub" id="{ch["id"]}"><div class="sub-head"><div><h2>{e(L(ch["name"], lang))}</h2>'
                    f'<p>{e(L(ch["desc"], lang))}</p></div>{extra}</div>{inner}</section>')
    allp = public_products(c["id"])
    jump = "".join(f'<a href="#{ch["id"]}">{e(L(ch["name"], lang))}</a>' for ch in c["children"] if sub_visible(c, ch))
    body = (f'<div class="page-head"><div class="wrap"><p class="crumbs"><a href="{url(lang)}">{t("nav_home", lang)}</a> / '
            f'<a href="{url(lang, "products/")}">{t("nav_products", lang)}</a></p><h1>{e(L(c["name"], lang))}</h1>'
            f'<p>{e(L(c["intro"], lang))}</p><nav class="jump">{jump}</nav></div></div>{cat_nav(lang, c["id"])}'
            f'<div class="wrap section">{custom_block(c, lang)}{filters_for(allp, lang)}<div id="prod-grid">{"".join(secs)}</div></div>')
    name = L(c["name"], lang)
    write(lang, f"products/{c['id']}/", "products", f"{name} | Tianqi Materials", L(c["intro"], lang), body)


def spec_rows(pr, lang):
    rows = []
    for key in ("structure", "process", "effect"):
        if pr.get(key):
            rows.append(f"<tr><th>{t(key, lang)}</th><td>{e(L(pr[key], lang))}</td></tr>")
    for s in pr.get("specs", []):
        rows.append(f"<tr><th>{e(L(s['label'], lang))}</th><td>{e(L(s['value'], lang))}</td></tr>")
    return "".join(rows)


def build_product(pr, lang):
    cat = next(c for c in CATS if c["id"] == pr["category"])
    sub = next(ch for ch in cat["children"] if ch["id"] == pr["sub"])
    name = L(pr["name"], lang)
    btns = [f'<a class="btn primary" href="{contact_href(lang, type="quote", product=pr["slug"])}">{t("quote", lang)}</a>',
            f'<a class="btn" href="{contact_href(lang, type="sample", product=pr["slug"])}">{t("request_sample", lang)}</a>']
    if pr.get("uv"):
        btns += [f'<a class="btn" href="{url(lang, "holographic-patterns/")}">{t("browse_patterns", lang)}</a>',
                 f'<a class="btn" href="{contact_href(lang, type="custom", product=pr["slug"])}">{t("customise_pattern", lang)}</a>']
    note = f'<p class="notice small">{t("pending_review", lang)}</p>' if pr["status"] == "pending-review" else ""
    related = ""
    if pr.get("uv"):
        ids = SITE["featured_patterns"][:8]
        related = (f'<section class="section"><div class="sec-head"><h2>{t("related_patterns", lang)}</h2>'
                   f'<a class="btn" href="{url(lang, "holographic-patterns/")}">{t("browse_patterns", lang)}</a></div>'
                   f'<ul class="pgrid">{"".join(pattern_card(p, lang) for p in PATTERNS if p["id"] in ids)}</ul></section>')
    siblings = [p for p in public_products(pr["category"], pr["sub"]) if p is not pr]
    sib = ""
    if siblings:
        sib = (f'<section class="section"><div class="sec-head"><h2>{t("in_category", lang)}</h2></div>'
               f'<div class="cards four">{"".join(product_card(p, lang) for p in siblings)}</div></section>')
    body = (cat_nav(lang, cat["id"]) + f'<div class="wrap section"><p class="crumbs dark"><a href="{url(lang)}">{t("nav_home", lang)}</a> / '
            f'<a href="{url(lang, "products/")}">{t("nav_products", lang)}</a> / <a href="{url(lang, "products/" + cat["id"] + "/")}">{e(L(cat["name"], lang))}</a> / '
            f'<a href="{url(lang, "products/" + cat["id"] + "/")}#{sub["id"]}">{e(L(sub["name"], lang))}</a></p>'
            f'<div class="detail"><div class="gallery">{picture(pr["image"], name, lang, "main", "full")}</div>'
            f'<div class="dinfo"><p class="label">{e(L(sub["name"], lang))}</p><h1>{e(name)}</h1>'
            + (f'<p class="dsub">{e(L(pr["subtitle"], lang))}</p>' if pr.get("subtitle") else "") +
            f'<p class="lead">{e(L(pr["summary"], lang))}</p>{note}'
            f'<table class="spec">{spec_rows(pr, lang)}</table><p class="small">{t("specs_on_request", lang)}</p>'
            f'<div class="btns">{"".join(btns)}</div></div></div></div>'
            f'<div class="wrap">{related}{sib}</div>')
    write(lang, f"products/{pr['slug']}/", "products", f"{name} | Tianqi Materials", L(pr["summary"], lang), body,
          og_image=img_src(pr["image"], "full") or None)


def build_pattern(p, i, lang):
    pid = p["id"]
    vs = views(pid)
    prev, nxt = PATTERNS[i - 1], PATTERNS[(i + 1) % len(PATTERNS)]
    thumbs = ""
    if len(vs) > 1:
        thumbs = '<div class="views">' + "".join(
            f'<button type="button" data-view="{v}" aria-label="{t("more_views", lang)} {n + 1}"><img src="{v}" alt="" loading="lazy"></button>'
            for n, v in enumerate(vs)) + "</div>"
    tags = p.get("tags_verified") or {}
    tag_html = "".join(f'<span class="tag">{t("pv_" + v, lang)}</span>' for v in tags.values())
    sims = similar_patterns(p)
    similar = ""
    if sims:
        similar = (f'<section class="section"><div class="sec-head"><h2>{"Similar patterns" if lang == "en" else "同类纹样"}</h2>'
                   f'<a class="btn" href="{url(lang, "holographic-patterns/")}">{t("browse_patterns", lang)}</a></div>'
                   f'<ul class="pgrid">{"".join(pattern_card(q, lang) for q in sims)}</ul></section>')
    body = (f'<div class="wrap section"><p class="crumbs dark"><a href="{url(lang)}">{t("nav_home", lang)}</a> / '
            f'<a href="{url(lang, "holographic-patterns/")}">{t("nav_patterns", lang)}</a> / {pid}</p>'
            f'<div class="detail"><div class="gallery"><img class="main" id="main-view" src="{vs[0]}" alt="{e(pattern_alt(p, lang))}">{thumbs}</div>'
            f'<div class="dinfo"><p class="label">{t("nav_patterns", lang)}</p><h1>{t("pattern", lang)} <span class="code">{pid}</span></h1>'
            f'{"<div class=tags>" + tag_html + "</div>" if tag_html else ""}'
            f'<table class="spec"><tr><th>{t("design_status", lang)}</th><td>{t("design_ready", lang)}</td></tr></table>'
            f'<div class="btns"><a class="btn primary" href="{contact_href(lang, type="pattern", pattern=pid)}">{t("quote", lang)}</a>'
            f'<a class="btn" href="{contact_href(lang, type="sample", pattern=pid)}">{t("request_sample", lang)}</a>'
            f'<a class="btn" href="{contact_href(lang, type="custom", pattern=pid)}">{t("customise_pattern", lang)}</a></div>'
            f'<p class="notice small">{t("reserved_note", lang)}</p><p class="small">{t("angle_note", lang)}</p>'
            f'<div class="pager"><a href="{url(lang, "holographic-patterns/" + prev["id"] + "/")}">← {t("prev", lang)} {prev["id"]}</a>'
            f'<a href="{url(lang, "holographic-patterns/" + nxt["id"] + "/")}">{t("next", lang)} {nxt["id"]} →</a></div></div></div>'
            f'{similar}</div>')
    kind = pattern_kind(p, lang)
    effect = PATTERN_WORDS[lang].get(tags.get("effect"), "")
    if lang == "en":
        title = f"Pattern {pid}: {kind} | Tianqi Materials" if kind else f"Pattern {pid} | Holographic Patterns | Tianqi Materials"
        desc = (f"{kind} {pid}" + (f" with {effect} effect" if effect else "") + ". "
                "Design ready: request a quote, a sample or a custom version.") if kind else (
                f"Holographic pattern {pid} for holographic paperboard and film, design ready. Request a quote, a sample or a custom version.")
    else:
        title = f"纹样 {pid}｜{kind}｜天琦材料" if kind else f"纹样 {pid}｜光刻纹样｜天琦材料"
        desc = (f"{kind} {pid}" + (f"，效果{effect}" if effect else "") + "。设计已完成，可询价、申请样品或定制。") if kind else (
                f"光刻纹样 {pid}，设计已完成。可询价、申请样品或定制。")
    write(lang, f"holographic-patterns/{pid}/", "holographic-patterns", title, desc, body, og_image=vs[0])


PATTERN_TAGS = {"finish": ["silver", "pearl", "holographic"],
                "pattern": ["geometric", "fluid", "texture", "lines", "motif"],
                "effect": ["subtle", "medium", "bold"]}


def pattern_filters(lang):
    groups = []
    for k, order in PATTERN_TAGS.items():
        used = {(p.get("tags_verified") or {}).get(k) for p in PATTERNS}
        vals = [v for v in order if v in used]
        if len(vals) < 2:
            continue
        chips = f'<button class="chip" type="button" data-v="" aria-pressed="true">{t("all", lang)}</button>' + "".join(
            f'<button class="chip" type="button" data-v="{e(v)}" aria-pressed="false">{t("pv_" + v, lang)}</button>' for v in vals)
        groups.append(f'<div class="fgroup"><span class="label">{t("filter_" + k, lang)}</span><div class="chips" data-f="{e(k)}">{chips}</div></div>')
    return "".join(groups)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", help="folder of pattern photos (101.jpg ...)")
    ap.add_argument("--force", action="store_true", help="rebuild every image")
    a = ap.parse_args()
    if a.src:
        src = Path(a.src)
        if not src.is_dir():
            sys.exit(f"Photo folder not found: {src}")
        make_images(src, a.force)

    make_bubbles(a.force)
    global PATTERNS
    PATTERNS = [p for p in PATTERNS if (PUB / "img/patterns/thumb" / f"{p['id']}.webp").exists()]
    if not PATTERNS:
        sys.exit("No pattern images in public/img/patterns. Run with --src first.")
    slugs = [p["slug"] for p in PRODUCTS]
    clash = set(slugs) & {c["id"] for c in CATS}
    if clash or len(slugs) != len(set(slugs)):
        sys.exit(f"Product slugs must be unique and differ from category ids: {clash or slugs}")

    for lang in LANGS:
        featured = [p for p in PATTERNS if p["id"] in SITE["featured_patterns"]]
        slides = [featured] + [g for g in chunks(carousel_extra(featured), 8)]
        common = dict(cat_cards=category_cards(lang), facts=facts_html(lang), facts_certs=facts_html(lang, True), stats=stats_html(lang), customers=customers_html(lang), bubbles=bubbles_html(), certs=certs_html(lang),
                      equipment=equipment_html(lang), equipment4=equipment_html(lang, 4),
                      featured_patterns=pattern_carousel(slides, lang),
                      innovation_products="".join(f"<li>{e(L(x, lang))}</li>" for x in COMPANY["innovation"]["products"]),
                      innovation_tech="".join(f"<li>{e(L(x, lang))}</li>" for x in COMPANY["innovation"]["technologies"]),
                      pattern_grid="".join(pattern_card(p, lang) for p in PATTERNS), pattern_filters=pattern_filters(lang),
                      contact_direct="".join(f"<p>{lab}: <b>{contact_link(k)}</b></p>" for k, lab in
                                             (("whatsapp", "WhatsApp"), ("email", "Email"), ("phone", "Tel")) if SITE.get(k)),
                      form_endpoint=e(SITE["form_endpoint"]), form_files="1" if SITE["form_accepts_files"] else "",
                      file_note=e(L(SITE["form_file_note"], lang)), address=e(L(SITE["address"], lang) or L(SITE["city"], lang)),
                      legal_name=e(L(SITE["legal_name"], lang)), email_js=e(SITE["email"]))
        for name, path, section in (("home", "", "home"), ("products", "products/", "products"), ("holographic-patterns", "holographic-patterns/", "holographic-patterns"),
                                    ("customisation", "customisation/", "customisation"), ("about", "about/", "about"), ("contact", "contact/", "contact")):
            title, desc, body = page_body(lang, name, common)
            write(lang, path, section, title, desc, body)
        for c in CATS:
            build_category(c, lang)
        for pr in PRODUCTS:
            build_product(pr, lang)
        for i, p in enumerate(PATTERNS):
            build_pattern(p, i, lang)

    nf = (f'<div class="page-head"><div class="wrap"><h1>{t("not_found", "en")}</h1>'
          f'<div class="btns" style="justify-content:center"><a class="btn primary" href="/">Home</a></div></div></div>')
    (PUB / "404.html").write_text(shell("en", "", "home", "Page not found | Tianqi Materials", "", nf), encoding="utf-8")

    base = SITE["site_url"].rstrip("/")
    today = datetime.date.today().isoformat()
    (PUB / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                     + "".join(f"<url><loc>{base}{u}</loc><lastmod>{today}</lastmod></url>" for u in BUILT) + "</urlset>", encoding="utf-8")
    (PUB / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    print(f"Built {len(BUILT)} pages ({len(PATTERNS)} patterns, {len(PRODUCTS)} products, 2 languages) into {PUB}")
    version_images()
    check_english()


CJK = re.compile(r"[\u3000-\u303f\u3400-\u9fff\uf900-\ufaff\uff00-\uffef]+")


def version_images():
    """Add ?v=<content hash> to image links, so a replaced photo shows at once despite the long /img cache."""
    import hashlib, re
    pat = re.compile(r'((?:src|href)=")([^"?#:]+\.(?:webp|png|jpe?g|svg))"')
    cache = {}
    for h in PUB.rglob("*.html"):
        def tag(m, d=h.parent):
            link = m.group(2)
            f = PUB / link.lstrip("/") if link.startswith("/") else (d / link).resolve()
            if f not in cache:
                cache[f] = hashlib.md5(f.read_bytes()).hexdigest()[:8] if f.is_file() else None
            return f'{m.group(1)}{link}?v={cache[f]}"' if cache[f] else m.group(0)
        text = h.read_text(encoding="utf-8")
        new = pat.sub(tag, text)
        if new != text:
            h.write_text(new, encoding="utf-8")


def check_english():
    """English pages must not contain any Chinese: stop with a list of what was found."""
    found = []
    for f in sorted(PUB.rglob("*.html")):
        rel = f.relative_to(PUB)
        if rel.parts[0] == "zh":
            continue
        for m in CJK.finditer(f.read_text(encoding="utf-8")):
            found.append(f"  {rel.as_posix()}: {m.group(0)}")
    if found:
        sys.exit("Chinese text found on English pages (fix the en text in data/ or pages/en/):\n" + "\n".join(found[:40]))
    print("English pages checked: no Chinese text.")


if __name__ == "__main__":
    main()
