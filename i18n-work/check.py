"""Check a translation: python3 i18n-work/check.py <lang>
- i18n-work/<lang>.json has exactly the keys of source-en.json, with the same {placeholders} and HTML tags
- pages/<lang>/*.html keep the same HTML tags, attributes (except translatable ones) and {{placeholders}} as pages/en/
- no Chinese characters (except Japanese), no 'UV', no 'Tongxiang'"""
import json, pathlib, re, sys
from html.parser import HTMLParser
ROOT = pathlib.Path(__file__).resolve().parent.parent
lang = sys.argv[1]
errs = []
src = json.loads((ROOT / "i18n-work/source-en.json").read_text(encoding="utf-8"))
tr = json.loads((ROOT / f"i18n-work/{lang}.json").read_text(encoding="utf-8"))
ph = lambda s: sorted(re.findall(r"\{\{?\w+\}?\}", s))
tags = lambda s: sorted(re.findall(r"</?\w+", s))
for k in src:
    if k not in tr: errs.append(f"missing key {k}"); continue
    if ph(src[k]) != ph(tr[k]): errs.append(f"placeholders differ in {k}: {ph(src[k])} vs {ph(tr[k])}")
    if tags(src[k]) != tags(tr[k]): errs.append(f"HTML tags differ in {k}")
for k in tr:
    if k not in src: errs.append(f"extra key {k}")
TRANSLATABLE = {"alt", "title", "aria-label", "placeholder", "content", "value", "data-label"}
class P(HTMLParser):
    def __init__(s): super().__init__(convert_charrefs=False); s.seq = []
    def handle_starttag(s, t, a): s.seq.append((t, tuple((k, v) for k, v in a if k not in TRANSLATABLE)))
    def handle_endtag(s, t): s.seq.append(("/" + t,))
def seq(text):
    p = P(); p.feed(text); return p.seq
texts = list(tr.values())
for f in sorted((ROOT / "pages/en").glob("*.html")):
    g = ROOT / "pages" / lang / f.name
    if not g.exists(): errs.append(f"missing pages/{lang}/{f.name}"); continue
    a, b = f.read_text(encoding="utf-8"), g.read_text(encoding="utf-8")
    if ph(a) != ph(b): errs.append(f"{f.name}: {{{{placeholders}}}} differ: {set(ph(a)) ^ set(ph(b))}")
    sa, sb = seq(a), seq(b)
    if sa != sb:
        for i, (x, y) in enumerate(zip(sa, sb)):
            if x != y: errs.append(f"{f.name}: HTML differs at tag {i}: en {x} vs {lang} {y}"); break
        else: errs.append(f"{f.name}: HTML tag count differs ({len(sa)} vs {len(sb)})")
    if not re.match(r"\s*<!--\s*\ntitle:.*\ndesc:.*\n-->", b): errs.append(f"{f.name}: header comment must keep 'title:' and 'desc:' lines")
    texts.append(b)
allt = "\n".join(texts)
if lang != "ja" and re.search(r"[㐀-鿿]", allt): errs.append("Chinese characters found")
if re.search(r"\bUV\b", allt): errs.append("'UV' found")
if re.search(r"tongxiang|桐乡", allt, re.I): errs.append("Tongxiang found")
print("\n".join(errs) if errs else f"{lang}: OK")
sys.exit(1 if errs else 0)
