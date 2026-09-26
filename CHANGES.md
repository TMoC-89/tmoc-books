# Site overhaul — September 2026

## Fixed

- **Missing words in the Glossarium.** The edition marks uncertain readings as `<word>`. These had
  been read as HTML tags, so 139 words and phrases were invisible (“The Roman  stayed with the
  individual case…”). They are restored from the English Markdown. The same happened once in
  *Sophia* (“make a <selection>”). The German source text had 150 of these; they are restored too,
  but its capitalisation and multi-word order had to be reconstructed — see “Needs a human check”.
- **Search missed text.** Paragraphs without an anchor, and parts of the Arabic and German text,
  were not indexed. The index now covers 94,400 passages (was 80,500): English 70,300,
  Arabic 18,600, German 5,500.
- Links to an Arabic section (`#ar-…`) now open the Arabic text instead of doing nothing.
- Reviewer Mode for the Glossarium said “Arabic shading” for a German source.
- A contents title in *Sophia* read “( Sophia )”.

## Reader (all eleven readers now share one design and one codebase)

- One stylesheet and one script for every book, instead of ~60 KB of slightly different inline CSS
  and JavaScript per page. *Sufi Orbits*, which used a separate engine, now works like the others
  and gains Reviewer Mode.
- Note previews: tapping a note number shows the note in place (a bottom sheet on phones) instead of
  jumping to the end of a 1,000-page book.
- Continue reading: your place is saved per book; the cover offers “Continue”, and the collection page
  lists books in progress with a progress meter.
- Quieter top bar: text size and theme (auto / light / dark) live in one “Aa” panel; downloads for
  both languages moved to the sidebar; SVG icons replace font glyphs that rendered differently on
  each platform. Reviewer Mode keeps its toolbar button.
- The sidebar can be hidden on desktop for distraction-free reading. Nested contents (volumes,
  chapters, Glossarium years and months) expand to follow your position.
- The language switch stays in the same chapter and no longer moves the page chrome around.
- Coming from search: the passage is highlighted, the search words are marked, and a “Back to search
  results” link appears.
- Printed contents with dot leaders (*Sufi Orbits*) now reflow on small screens.

## Speed

- Long books render lazily (Chromium/Firefox): the Glossarium is ready in 0.6 s instead of 3.4 s on a
  throttled mid-range phone profile; switching language in a *Materialist Tendencies* volume takes
  0.3 s instead of 4.8 s.
- Reviewer Mode (and the 2 MB German source text of the Glossarium) now loads only when opened.
- Search fetches ~20 small files per query instead of 200–500; typical queries answer 5–10× faster.
  Results are grouped by work with per-work counts, and Arabic matching ignores prefixes (ال، و، ب…)
  and letter variants.

## Collection pages

- Search box on the front page; reading time and progress on every card; more compact cards on phones.
- The four-volume landing page, search page and a new 404 page share the collection's design.
- Accurate meta descriptions, canonical URLs, Open Graph tags and schema.org `Book` data per page.

## Maintenance

- `tools/build.py` regenerates every page from `library.json` and each `book.json`, and rebuilds the
  search index (which previously had no generator in the repository). Standard-library Python only.
- CI now runs `python3 tools/build.py --check` before deploying: it validates every book (contents
  links, downloads, languages) and fails if someone edited a source without rebuilding.
- See `README.md` for how to fix text, change metadata or add a book.

## Needs a human check

German source text of the Glossarium (Reviewer Mode only), in `glossarium/source-de.html`: the
bracketed words below were rebuilt from a damaged form, so letter case may be wrong and, for
multi-word brackets, the word order is a best guess. Search the file for `&lt;` to review them
against the printed edition. English and Arabic reading text are unaffected.
