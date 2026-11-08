"""Collect every English string in data/*.json into i18n-work/source-en.json, keyed by file and JSON path."""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES = ["i18n.json", "categories.json", "products.json", "company.json", "customers.json", "site.json"]
# kept in English in every language: brand names, the legal company name, unused legacy keys
SKIP = ("customers.json:customers/", "site.json:legal_name", "i18n.json:lang_other")
out = {}
def walk(o, f, path):
    if isinstance(o, dict):
        if isinstance(o.get("en"), str) and o["en"].strip():
            key = f + ":" + "/".join(path)
            if not key.startswith(SKIP):
                out[key] = o["en"]
        for k, v in o.items():
            if k != "en": walk(v, f, path + [k])
    elif isinstance(o, list):
        for i, v in enumerate(o): walk(v, f, path + [str(i)])
for f in FILES:
    walk(json.loads((ROOT / "data" / f).read_text(encoding="utf-8")), f, [])
(ROOT / "i18n-work/source-en.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(out), "strings")
