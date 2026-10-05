# Within Iranian Islam — October 2026

- **Added Henry Corbin’s *Within Iranian Islam* (*En Islam iranien*), all four volumes**, in English
  with the complete French original, as work № 10 on the French shelf and the latest addition. It
  has its own landing page, like *Materialist Tendencies*, with a reader per volume: Twelver Shiism;
  Sohrawardî and the Platonists of Persia; The Faithful of Love · Shiism and Sufism; The School of
  Isfahan · The Shaykhi School · The Twelfth Imam.
- Each volume opens on its title pages and front matter; each of the seven Books is introduced at
  the start of its first chapter, and the contents fold out from Book to chapter to numbered
  section. The language switch keeps your place, chapter by chapter, in either direction.
- 1,720 notes open in place as previews. The figures (Volume I’s diagrams, Volume II’s three
  figures, Volume III’s manuscript diagrams and charts) enlarge on tap, and are drawn light on dark
  in the dark theme. The very large scans in Volume III were scaled down for the web (1.2 MB instead
  of 6.4 MB).
- Downloads per volume and language, plus all eight Markdown files as one zip.
- Search covers both languages of all four volumes (French has its own filter).
- **Reviewer Mode pairs passages far more accurately** for this work: English and French passages
  that cite the same note are matched directly, headings by their position in the chapter, and
  the passages in between by shared names, terms and cognates. Tested against held-out notes, 96–99%
  of passages land on the right French paragraph (previously about 44%, by length alone).
- The importer is `tools/import_en_islam_iranien.py` (see the README). It checked that the English
  and French have the same chapters and sections in every volume, and that every note is defined
  and cited; the text on the site matches the supplied Markdown word for word apart from heading
  numbers (“I. –” → “1.”) and the Book titles, which are given in reading case.
- Corrections to the supplied files: in the English of Volume IV, two of the Shaykhi successors
  (Zaynol-ʿÂbidîn-Khân, Sarkâr Âghâ) and Chapter III “Some Points of Doctrine” were bold text rather
  than headings, so they were missing from the contents and the chapter list; they are now
  headings. The English title pages now read *Within Iranian Islam*.

## Site

- Series pages work for any source language (French titles, “Tome” in the French interface).
- Long contents fold more usefully: top-level parts stay open, deeper levels fold (also improves
  the *Glossarium*’s contents, where each Book now shows its years).
- Fixed a stray brace in `reader.css`, introduced with the phone fixes, that had switched off the
  large title style at the start of every section.
- Removed files left over from before the overhaul that were still in the repository but no longer
  used (`README.txt`, `assets/page-transitions.css`, `assets/reader-accessibility.js`,
  `assets/reader-search.js`, `assets/reading-polish.css`, `assets/review-alignment.js`,
  `search/search.css`, `materialist-tendencies/SITE_STRUCTURE.md`).

# The City of Isis — 28 September 2026

- Added Pierre Rossi’s *The City of Isis: The True History of the Arabs* and the complete French
  original, *La Cité d’Isis*, to the French shelf as work № 09 and the latest addition.
- Preserved both final Markdown files as downloads, including the English translator’s note.
  Added matching sections for the preface, ten chapters, printed contents, colophon and footnotes.
- Extended reader controls, language visibility, chapter pagers, downloads and Reviewer Mode’s
  contents to support an English/French edition. Existing Arabic editions keep their controls.
- Indexed both languages and added French to the global search filter and result labels.
- Search links into long source paragraphs now bring the first highlighted match into view.
  Reviewer Mode pairs corresponding front matter and notes directly, and leaves the English-only
  translator’s note without a source pairing.

# Performance fixes for phones — September 2026

Reported on Chrome for Android: opening the contents could take 2+ seconds the first time, text size
changes stalled intermittently, and Reviewer Mode froze for long stretches. The site before the
overhaul did not do this.

- **Books are laid out up front again, like the previous site.** The overhaul made long books render
  lazily (CSS `content-visibility`): text far from the screen was only laid out when needed. That
  made pages start faster in tests, but it moved work to the moment you tap something, which is what
  showed up as stalls on a real phone. Lazy rendering is removed; opening the contents is immediate
  and a text size change costs the same as on the previous site.
- **Nothing loads on first use.** Reviewer Mode's code is now part of the page instead of being
  downloaded the first time you tap Review.
- **No automatic hyphenation on phones.** Chrome for Android loads a hyphenation dictionary and
  hyphenates every paragraph it lays out; the previous site had it switched off, and so does this one now.
- Opening the contents by touch no longer moves keyboard focus into it, and the drawer no longer
  toggles `inert` (it is already hidden from touch and screen readers while closed).
- **Reviewer Mode builds sections as you reach them** instead of a card for every passage of the
  book at once (over 100,000 page elements). Simulated mid-range phone, *Materialist Tendencies*
  vol. 1: opening 50 s on the previous site → about 1.2 s; scrolling and tapping inside it
  0.5–3.5 s → instant; leaving it 3 s → 0.3 s, back at the same passage.
- The text-size slider re-lays out the book once, when you stop dragging; repeated taps on A/A combine.
- Performance probe: open any book with `?perf=1` to show a small panel that times each tap
  (turn off with `?perf=0`). "Copy report" copies the measurements for sending to a maintainer.

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

- The 2 MB German source text of the Glossarium loads only when Reviewer Mode is opened.
  (Lazy rendering of long books was tried here and later removed — see the phone fixes above.)
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
