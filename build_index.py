"""
Visitors - costruisce data/index.json a partire dai digest Markdown e dalla config.
Il sito statico legge SOLO questo file. Va eseguito dopo gather.py (i workflow
lo fanno in automatico) e committato insieme ai digest.

Include un mini-renderer Markdown->HTML (niente dipendenze esterne).
"""
from __future__ import annotations

import datetime as dt
import html
import json
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).parent
CONFIG = ROOT / "config"
DIGESTS = ROOT / "digests"
OUT = ROOT / "data" / "index.json"


# --- Mini Markdown -> HTML --------------------------------------------------

def _inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        # Heading
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        # Blockquote (blocco consecutivo)
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append(f"<blockquote>{_inline(' '.join(buf))}</blockquote>")
            continue
        # Lista non ordinata
        if re.match(r"^[-*]\s+", s):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(_inline(re.sub(r"^\s*[-*]\s+", "", lines[i])))
                i += 1
            out.append("<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>")
            continue
        # Paragrafo (fino a riga vuota)
        buf = [s]
        i += 1
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,4}\s|[-*]\s|>)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        out.append(f"<p>{_inline(' '.join(buf))}</p>")
    return "\n".join(out)


# --- Parsing digest ---------------------------------------------------------

def parse(path: pathlib.Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    front, body = {}, raw
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.DOTALL)
    if m:
        for ln in m.group(1).splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                front[k.strip()] = v.strip()
        body = m.group(2)
    return {
        "id": path.stem,
        "title": front.get("titolo", path.stem),
        "meta": front.get("data") or front.get("settimana", ""),
        "html": md_to_html(body.strip()),
    }


def scan(subdir: str) -> list[dict]:
    d = DIGESTS / subdir
    if not d.exists():
        return []
    files = sorted(d.rglob("*.md"), key=lambda p: p.stem, reverse=True)
    return [parse(p) for p in files]


def load_yaml(name: str) -> dict:
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build() -> dict:
    otas = load_yaml("otas.yaml")["otas"]
    attrs = load_yaml("attractions.yaml")["attractions"]
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "month_index": dt.date.today().month - 1,
        "otas": [{"slug": o["slug"], "name": o["name"]} for o in otas],
        "attractions": [
            {"slug": a["slug"], "name": a["name"], "city": a.get("city", ""),
             "seasonality": a["seasonality"]}
            for a in attrs
        ],
        "digests": {
            "general": scan("general"),
            "general_weekly": scan("general-weekly"),
            "attractions": scan("attractions"),
            "ota": {o["slug"]: scan(f"ota/{o['slug']}") for o in otas},
        },
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=None), encoding="utf-8")
    total = (len(data["digests"]["general"]) + len(data["digests"]["general_weekly"])
             + len(data["digests"]["attractions"])
             + sum(len(v) for v in data["digests"]["ota"].values()))
    print(f"[ok] scritto {OUT.relative_to(ROOT)} - {total} digest")


if __name__ == "__main__":
    main()
