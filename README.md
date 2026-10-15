# Lords of Limited — cards mentioned

A small, unofficial card-gallery website. Plain HTML, one stylesheet, and a Python standard-library build script. No accounts, database, JavaScript framework, or package installation required.

## Build

```sh
python3 scripts/build_site.py
```

The generated website lives in `docs/`. Commit the source and generated files together. The current GitHub Pages deployment serves the repository root, whose homepage redirects to `docs/`. Preserve that redirect. A fresh deployment can instead select **Deploy from a branch**, **main**, **/docs**. All gallery links are relative.

## Add an episode

Add `data/episodes/your-slug.json`, then build again:

```json
{
  "slug": "your-slug",
  "title": "Episode title",
  "feed_date": "2026-10-08",
  "unresolved_count": 0,
  "cards": [
    {
      "name": "Canonical card name",
      "image_url": "https://cards.scryfall.io/grid/front/...webp",
      "scryfall_url": "https://scryfall.com/card/..."
    }
  ]
}
```

The card array is a unique catalogue in first-appearance order. A stable slug becomes `/episodes/your-slug/`; the build updates the archive and previous/next navigation automatically. Feed dates are from the early-access feed, and may precede public release dates. Use actual API-returned Scryfall `grid` WebP image URLs, not guessed extensions.

New episodes also contain a `sections` array. Each section has `title`, approximate `start_seconds`/`end_seconds`, and `mentions`. Each mention has `names` (references to the card catalogue), `approx_seconds` and `certainty` (`confirmed` or `ambiguous`). Confirmed mentions have one name; ambiguous mentions group plausible alternatives and are explicitly labelled possible matches. A card can recur in later sections: the gallery follows the conversation rather than globally suppressing repeats. Group by topic or established draft pick, not fixed time buckets. Old data without sections still renders as a flat gallery. No timestamps are fabricated for historical episodes.

## Style all episodes in one place

- `assets/style.css`: colors, spacing, typography, responsive card layout.
- `templates/page.html`: the shared page shell and footer.
- `scripts/build_site.py`: archive and episode markup.

Images load directly from Scryfall; no reader-side card-name API lookups. Internet access is needed for images. All content is pre-rendered and usable without JavaScript.

## Publication boundary

Only episode titles, feed dates, card names, image/link URLs, short discussion headings, rough timestamps, certainty labels, and a count of unresolved mentions belong here. **Never commit Patreon/RSS credentials, audio links or files, transcripts, private manifests, internal evidence, or Tasklet configuration.**

This is an unofficial fan project, not affiliated with Lords of Limited, Scryfall, or Wizards of the Coast. Card names and imagery belong to their respective owners. Automated card identification can miss or misidentify a mention.
