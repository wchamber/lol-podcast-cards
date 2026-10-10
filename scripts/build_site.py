#!/usr/bin/env python3
"""Build a portable static gallery from publication-safe episode JSON. No dependencies."""
import json
import re
import shutil
from datetime import date
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def url(value, host):
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != host or parsed.username or parsed.password:
        raise ValueError(f"Expected a public HTTPS URL on {host}")
    return escape(value, quote=True)


def load_episodes():
    episodes = []
    for path in sorted((ROOT / "data/episodes").glob("*.json")):
        episode = json.loads(path.read_text())
        if set(episode) != {"slug", "title", "feed_date", "unresolved_count", "cards"}:
            raise ValueError(f"Unexpected public fields: {path.name}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", episode["slug"]):
            raise ValueError("Unsafe episode slug")
        if not isinstance(episode["title"], str) or not episode["title"].strip():
            raise ValueError("Missing title")
        date.fromisoformat(episode["feed_date"])
        if not isinstance(episode["unresolved_count"], int) or episode["unresolved_count"] < 0:
            raise ValueError("Invalid unresolved count")
        if not episode["cards"]:
            raise ValueError("Empty card gallery")
        seen = set()
        for card in episode["cards"]:
            if set(card) != {"name", "image_url", "scryfall_url"} or not card["name"] or card["name"] in seen:
                raise ValueError("Invalid or duplicated public card")
            url(card["scryfall_url"], "scryfall.com")
            if card["image_url"] is not None:
                url(card["image_url"], "cards.scryfall.io")
            seen.add(card["name"])
        episodes.append(episode)
    if not episodes or len({e["slug"] for e in episodes}) != len(episodes):
        raise ValueError("No episodes or duplicated slugs")
    return sorted(episodes, key=lambda e: (e["feed_date"], e["slug"]), reverse=True)


def readable_date(episode):
    return date.fromisoformat(episode["feed_date"]).strftime("%b %d, %Y").replace(" 0", " ")


def card_markup(card, index):
    name = escape(card["name"])
    link = url(card["scryfall_url"], "scryfall.com")
    if card["image_url"]:
        image = f'<img class="card-image" src="{url(card["image_url"], "cards.scryfall.io")}" alt="{escape(card["name"], quote=True)}" width="215" height="300" loading="lazy" decoding="async">'
    else:
        image = f'<div class="image-unavailable">{name}<small>Image unavailable</small></div>'
    return f'<figure class="card-container"><a class="card-link" href="{link}">{image}<figcaption>{index}. {name}</figcaption></a></figure>'


def build():
    episodes = load_episodes()
    template = Template((ROOT / "templates/page.html").read_text())
    output = ROOT / "docs"
    # Only generated episode pages are cleared; source files are never modified.
    if (output / "episodes").exists():
        shutil.rmtree(output / "episodes")
    (output / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "assets/style.css", output / "assets/style.css")
    (output / ".nojekyll").write_text("")

    def write(path, title, description, root, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template.substitute(title=escape(title), description=escape(description, quote=True), root=root, content=content), encoding="utf-8")

    rows = []
    for index, episode in enumerate(episodes):
        badge = '<br><span class="badge">Latest gallery</span>' if index == 0 else ""
        rows.append(f'<li><a class="episode-row" href="episodes/{episode["slug"]}/"><span class="date"><time datetime="{episode["feed_date"]}">{readable_date(episode)}</time>{badge}</span><strong>{escape(episode["title"])}</strong><span class="count">{len(episode["cards"])} cards ↗</span></a></li>')
        cards = "\n".join(card_markup(card, i + 1) for i, card in enumerate(episode["cards"]))
        unresolved = episode["unresolved_count"]
        notice = f'<p class="notice">{unresolved} ambiguous mention{"s" if unresolved != 1 else ""} left unresolved and excluded from this gallery.</p>' if unresolved else ""
        older = episodes[index + 1] if index + 1 < len(episodes) else None
        newer = episodes[index - 1] if index else None
        nav = '<nav class="episode-nav" aria-label="Adjacent episodes">'
        nav += f'<a rel="prev" href="../{older["slug"]}/">← Older<br>{escape(older["title"])}</a>' if older else '<span></span>'
        nav += f'<a rel="next" href="../{newer["slug"]}/">Newer →<br>{escape(newer["title"])}</a>' if newer else '<span></span>'
        nav += '</nav>'
        content = f'<p class="eyebrow">Episode gallery</p><h1>{escape(episode["title"])}</h1><p class="meta"><time datetime="{episode["feed_date"]}">{readable_date(episode)}</time> · Early-access feed date · {len(episode["cards"])} cards</p>{notice}<section class="cards-grid" aria-label="Cards in first-mention order">{cards}</section>{nav}'
        write(output / "episodes" / episode["slug"] / "index.html", episode["title"] + " — Cards mentioned", f'{len(episode["cards"])} cards mentioned in {episode["title"]}', "../..", content)
    content = '<p class="eyebrow">The episode archive</p><h1>Heard on the podcast.<br>Here on the page.</h1><p class="intro">The cards mentioned on Lords of Limited, collected in one place. Pick an episode to browse its gallery.</p><p class="meta">Dates reflect the early-access feed and may precede public release.</p><ol class="episode-list">' + "\n".join(rows) + '</ol>'
    write(output / "index.html", "Lords of Limited — Cards mentioned", "Browse card galleries from Lords of Limited episodes.", ".", content)
    return {"episodes": len(episodes), "cards": sum(len(e["cards"]) for e in episodes), "output": str(output)}


if __name__ == "__main__":
    print(json.dumps(build()))
