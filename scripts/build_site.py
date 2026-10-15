#!/usr/bin/env python3
"""Build a portable static gallery from publication-safe episode JSON. No dependencies."""
import json
import math
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
        if set(episode) - {"slug", "title", "feed_date", "unresolved_count", "cards", "sections"} or not {"slug", "title", "feed_date", "unresolved_count", "cards"} <= set(episode):
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
                image_path = urlparse(card["image_url"]).path
                if not image_path.startswith("/grid/") or not image_path.endswith(".webp"):
                    raise ValueError("Gallery images must use Scryfall grid WebP URLs")
            seen.add(card["name"])
        if "sections" in episode:
            validate_sections(episode["sections"], seen)
        episodes.append(episode)
    if not episodes or len({e["slug"] for e in episodes}) != len(episodes):
        raise ValueError("No episodes or duplicated slugs")
    return sorted(episodes, key=lambda e: (e["feed_date"], e["slug"]), reverse=True)


def readable_date(episode):
    return date.fromisoformat(episode["feed_date"]).strftime("%b %d, %Y").replace(" 0", " ")


def finite_time(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def validate_sections(sections, catalogue):
    if not isinstance(sections, list) or not sections:
        raise ValueError("Missing sections")
    previous_end, referenced = 0, set()
    for section in sections:
        if set(section) != {"title", "start_seconds", "end_seconds", "mentions"}:
            raise ValueError("Unexpected public section fields")
        start, end = section["start_seconds"], section["end_seconds"]
        if not isinstance(section["title"], str) or not section["title"].strip() or len(section["title"]) > 160:
            raise ValueError("Invalid section heading")
        if not finite_time(start) or not finite_time(end) or not previous_end <= start < end or start - previous_end > 2:
            raise ValueError("Invalid section chronology")
        if not isinstance(section["mentions"], list):
            raise ValueError("Invalid section mentions")
        previous_time, signatures = start, set()
        for mention in section["mentions"]:
            if set(mention) != {"names", "approx_seconds", "certainty"}:
                raise ValueError("Unexpected public mention fields")
            names, stamp = mention["names"], mention["approx_seconds"]
            if not isinstance(names, list) or not names or any(not isinstance(n, str) or n not in catalogue for n in names) or len(set(names)) != len(names):
                raise ValueError("Section references missing/duplicated card candidates")
            if not finite_time(stamp) or not previous_time <= stamp <= end:
                raise ValueError("Invalid mention time")
            if mention["certainty"] not in ("confirmed", "ambiguous") or mention["certainty"] == "confirmed" and len(names) != 1:
                raise ValueError("Invalid certainty/candidates")
            signature = (mention["certainty"], tuple(sorted(names)))
            if signature in signatures:
                raise ValueError("Duplicate mention within section")
            signatures.add(signature)
            referenced.update(names)
            previous_time = stamp
        previous_end = end
    if referenced != catalogue:
        raise ValueError("Section cards differ from catalogue")


def timecode(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}" if seconds >= 3600 else f"{seconds // 60}:{seconds % 60:02d}"


def section_counts(episode):
    sections = episode.get("sections", [])
    return (sum(len(m["names"]) for s in sections for m in s["mentions"]),
            sum(m["certainty"] == "ambiguous" for s in sections for m in s["mentions"]))


def card_markup(card, index, possible=False):
    name = escape(card["name"])
    link = url(card["scryfall_url"], "scryfall.com")
    if card["image_url"]:
        image = f'<img class="card-image" src="{url(card["image_url"], "cards.scryfall.io")}" alt="{escape(card["name"], quote=True)}" width="215" height="300" loading="lazy" decoding="async">'
    else:
        image = f'<div class="image-unavailable">{name}<small>Image unavailable</small></div>'
    badge = '<span class="possible-label">Possible match</span>' if possible else ''
    return f'<figure class="card-container"><a class="card-link" href="{link}">{image}<figcaption>{index}. {name}{badge}</figcaption></a></figure>'


def section_markup(episode):
    catalogue = {card["name"]: card for card in episode["cards"]}
    links, blocks, index = [], [], 0
    for number, section in enumerate(episode["sections"], 1):
        anchor = f"section-{number}"
        label = escape(section["title"])
        stamp = f'{timecode(section["start_seconds"])}–{timecode(section["end_seconds"])}'
        links.append(f'<a href="#{anchor}"><span>{timecode(section["start_seconds"])}</span> {label}</a>')
        cards = []
        for mention in section["mentions"]:
            possible = mention["certainty"] == "ambiguous"
            group = []
            for name in mention["names"]:
                index += 1
                group.append(card_markup(catalogue[name], index, possible))
            markup = ''.join(group)
            if possible:
                explanation = 'Alternatives for one unclear reference, not separately confirmed mentions.' if len(group) > 1 else 'Uncertain identification, not a confirmed mention.'
                markup = f'<aside class="possible-matches" aria-label="Possible card matches"><p><strong>Possible match · ~{timecode(mention["approx_seconds"])}</strong><br>{explanation}</p><div class="cards-grid">{markup}</div></aside>'
            cards.append(markup)
        grid = '<div class="cards-grid">' + ''.join(cards) + '</div>' if cards else '<p class="meta">No named cards in this section.</p>'
        blocks.append(f'<section class="discussion-section" id="{anchor}" aria-labelledby="{anchor}-title"><p class="section-time">Approx. {stamp}</p><h2 id="{anchor}-title">{label}</h2>{grid}</section>')
    return f'<details class="section-index"><summary>Jump to a discussion · {len(episode["sections"])} sections</summary><nav aria-label="Jump to discussion">' + ''.join(links) + '</nav></details>' + ''.join(blocks)


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
        appearances, ambiguous = section_counts(episode)
        if "sections" in episode:
            cards = section_markup(episode)
            summary = f'{len(episode["cards"])} unique cards · {appearances} appearances · {len(episode["sections"])} sections'
            guidance = '<p class="notice">Rough listening timestamps. Cards reappear when the discussion returns to them; possible matches are labelled and may include alternatives.</p>'
            if ambiguous:
                guidance += f'<p class="notice">{ambiguous} uncertain reference{"s" if ambiguous != 1 else ""} shown as possible matches. Card counts include these candidates.</p>'
        else:
            cards = '<section class="cards-grid" aria-label="Cards in first-mention order">' + "\n".join(card_markup(card, i + 1) for i, card in enumerate(episode["cards"])) + '</section>'
            summary, guidance = f'{len(episode["cards"])} cards', ''
        unresolved = episode["unresolved_count"]
        notice = f'<p class="notice">{unresolved} reference{"s" if unresolved != 1 else ""} could not be matched to defensible candidates and remain excluded.</p>' if unresolved else ""
        older = episodes[index + 1] if index + 1 < len(episodes) else None
        newer = episodes[index - 1] if index else None
        nav = '<nav class="episode-nav" aria-label="Adjacent episodes">'
        nav += f'<a rel="prev" href="../{older["slug"]}/">← Older<br>{escape(older["title"])}</a>' if older else '<span></span>'
        nav += f'<a rel="next" href="../{newer["slug"]}/">Newer →<br>{escape(newer["title"])}</a>' if newer else '<span></span>'
        nav += '</nav>'
        content = f'<p class="eyebrow">Episode gallery</p><h1>{escape(episode["title"])}</h1><p class="meta"><time datetime="{episode["feed_date"]}">{readable_date(episode)}</time> · Early-access feed date · {summary}</p>{guidance}{notice}{cards}{nav}'
        write(output / "episodes" / episode["slug"] / "index.html", episode["title"] + " — Cards mentioned", f'{len(episode["cards"])} cards mentioned in {episode["title"]}', "../..", content)
    content = '<p class="eyebrow">The episode archive</p><h1>Heard on the podcast.<br>Here on the page.</h1><p class="intro">The cards mentioned on Lords of Limited, collected in one place. Pick an episode to browse its gallery.</p><p class="meta">Dates reflect the early-access feed and may precede public release.</p><ol class="episode-list">' + "\n".join(rows) + '</ol>'
    write(output / "index.html", "Lords of Limited — Cards mentioned", "Browse card galleries from Lords of Limited episodes.", ".", content)
    return {"episodes": len(episodes), "cards": sum(len(e["cards"]) for e in episodes), "output": str(output)}


if __name__ == "__main__":
    print(json.dumps(build()))
