# Lords of Limited — cards mentioned

A small, unofficial card-gallery website. Plain HTML, one stylesheet, and a Python standard-library build script. No accounts, database, JavaScript framework, or package installation required.

## Build

```sh
python3 scripts/build_site.py
```

The generated website lives in `docs/`. Commit the source and generated files together. In **Settings → Pages**, select **Deploy from a branch**, **main**, and **/docs**. Links are relative, so the site works under a GitHub Pages repository URL without configuration.

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
      "image_url": "https://cards.scryfall.io/normal/front/...jpg",
      "scryfall_url": "https://scryfall.com/card/..."
    }
  ]
}
```

The card array is in first-mention order. A stable slug becomes `/episodes/your-slug/`; the build updates the archive and previous/next navigation automatically. Feed dates are from the early-access feed, and may precede public release dates.

## Style all episodes in one place

- `assets/style.css`: colors, spacing, typography, responsive card layout.
- `templates/page.html`: the shared page shell and footer.
- `scripts/build_site.py`: archive and episode markup.

Images load directly from Scryfall; no reader-side card-name API lookups. Internet access is needed for images. All content is pre-rendered and usable without JavaScript.

## Publication boundary

Only episode titles, feed dates, card names, image/link URLs, and a count of unresolved mentions belong here. **Never commit Patreon/RSS credentials, audio links or files, transcripts, private manifests, internal evidence, or Tasklet configuration.**

This is an unofficial fan project, not affiliated with Lords of Limited, Scryfall, or Wizards of the Coast. Card names and imagery belong to their respective owners. Automated card identification can miss or misidentify a mention.
