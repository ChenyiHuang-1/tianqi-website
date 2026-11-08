"""Write i18n-work/<lang>.json (same keys as source-en.json) into data/*.json as the <lang> value."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
lang = sys.argv[1]
tr = json.loads((ROOT / f"i18n-work/{lang}.json").read_text(encoding="utf-8"))
src = json.loads((ROOT / "i18n-work/source-en.json").read_text(encoding="utf-8"))
missing = [k for k in src if k not in tr]
if missing: print("missing:", len(missing), missing[:5])
by_file = {}
for k, v in tr.items():
    f, path = k.split(":", 1)
    by_file.setdefault(f, []).append((path.split("/") if path else [], v))
for f, items in by_file.items():
    p = ROOT / "data" / f
    d = json.loads(p.read_text(encoding="utf-8"))
    for path, v in items:
        o = d
        for x in path:
            o = o[int(x)] if isinstance(o, list) else o[x]
        o[lang] = v
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(lang, "merged", len(tr))
