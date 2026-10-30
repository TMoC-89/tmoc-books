# The Four Journeys — bilingual edition notes

This nine-volume edition presents the original Arabic of Mullā Ṣadrā's *al-Ḥikma al-mutaʿāliya fī al-asfār al-ʿaqliyya al-arbaʿa* alongside the supplied English translation. All 18 downloadable Markdown volumes are kept with the reader pages. The supplied printed Arabic PDFs were consulted for the seven unmatched notes reported in the earlier formatting cleanup.

## Editorial disposition of seven unmatched notes

The supplied text contains footnote definitions with the identifiers below, but initially had no callouts in the body. Where the printed Arabic supplied adequate context, callouts have now been restored in the matching passages in **both** languages. The wording of the notes has not been rewritten.

| Note ID | Printed Arabic PDF | Editorial decision |
| --- | --- | --- |
| `V05-30` | Volume 5, around PDF page 172 | Reference restored beside the argument about a single body and its place or position. |
| `V06-28` | Volume 6, around PDF page 17 | Reference restored at the explanation that lack belongs to an effect. |
| `V06-37` | Volume 6, around PDF page 22 | Reference restored beside the distinction between essence and existence in graded being. |
| `V06-110` | Volume 6, around PDF page 65 | Reference restored after the discussion of Ibn Kammūna's objection. |
| `V06-168` | Volume 6, around PDF page 104 | **Preserved without a new callout.** The note explains `السيب` (a gift or giving), but a matching term or definite callout was not found in the digitized main text. The website displays it in the notes section with a clear editorial label. A reference was not invented. |
| `V08-575` | Volume 8, around PDF page 367 | Reference restored after the report about souls or spirits returning to bodies. |
| `V08-667` | Volume 8, around PDF page 427 | Reference restored at the second proposed option about the soul's prior existence. |

*PDF pages in this table are approximate viewer-page locations, not claims about a printed page-number sequence.* For full editorial certainty, the isolated `V06-168` may need checking against another typeset edition or the printed page image at greater magnification. We have not silently removed it.

## Presentation and data integrity

- Each of the nine volumes has its own reader, contents, and separate Arabic and English views. The paired language sections have matching keys, so the language switch and Reviewer Mode can navigate corresponding topics.
- All endnote definitions appear in a notes section at the end of **each** volume, separately for each language. Every callout points to an existing definition. Unreferenced `V06-168` remains available in both note sections.
- The reader offers individual Markdown downloads. The series page offers the complete 18-file bilingual ZIP download.
- Both languages appear in the site's full-text search; no printed page-marker comments are carried into the main text.
- The initial text import uses `python3 tools/import_four_journeys.py /path/to/bilingual-folder`. A new import must be followed by a fresh contents review as described below, then `python3 tools/build.py`. Do not re-import for heading-only changes: that can change passage references used by saved reading positions and reviews.

## Reviewed contents and edition numbering — 29 October 2026

The nine volumes now have an explicit `contents.json` next to each `book.json`. This records the reviewed parent levels and short sidebar labels for every existing heading. The sidebar uses the same shared appearance and controls as *Within Iranian Islam*. Only the deepest levels in Volume IV have a small spacing adjustment in `four-journeys/contents.css`.

- Main reading divisions form the top level. Introductory umbrella headings stay under **Opening pages**, rather than forcing readers through several single-item levels before reaching the chapters.
- Chapters are numbered consecutively within their immediate parent division: Roman numerals in English and Arabic digits in Arabic. The paired chapter groups have the same counts and order. This is a sequence for this edition; it resolves omitted, repeated and conflicting numbers in the supplied headings.
- Smaller discussions stay inside their chapter. Numbered smaller sections use ordinary digits. The original Arabic sometimes has fewer separate discussion headings than the translation; the review preserves that difference rather than adding unsupported headings.
- Named divisions use a colon. The body headings, printed contents lists, separate Markdown downloads and complete bilingual ZIP use the same chapter sequence and division terminology. Long descriptive division titles remain complete in the body; the sidebar can show a shorter label.
- Two source headings have a chapter number but no title: Volume II, Stage Six, chapter XII, and Volume VI, Station Three, chapter X. They are labelled **Untitled chapter** / **فصل بلا عنوان**. No descriptive title has been invented.
- In Volume IV, **Part** consistently names the four main divisions; **Section** names the four divisions within Part Two; **Book** and **Article** retain their smaller grouping roles. The first section contains five books, as the Arabic and the actual headings show.
- Long branches start folded; a brief first main division can start open. Chapters with smaller sections start folded. The existing reader opens the path to the current passage and retains its normal desktop and mobile sidebar controls.

The main source-outline corrections are in Volume III (kinds inside a chapter do not contain the later chapters), Volume V (the Stage Four reminder belongs within Part Five; Part Six is a peer), and Volume VII (a kind inside the chapter on good and evil does not contain later chapters). Volume VII's printed contents now includes its two existing approach headings so the three discussions have their proper parent. No argument, paragraph or note prose was edited.

Existing heading and passage references, paired language-section keys and Reviewer Mode storage versions are retained. Before rebuilding, `tools/build.py` checks each reviewed outline against the navigation source and refuses a stale or incomplete map. After any future source update, review the explicit maps rather than guessing parent levels from heading words or Markdown sizes. A full re-import can replace `book.json`; restore its `contentsFile` and `contentsStylesheet` settings and recheck all targets before building.

The local audit, untouched pre-heading snapshot, heading-change list and verification tools are in `/Users/semy/Documents/WorkspaceCodex/tmoc-books-reviews/2026-10-29-contents/`. That folder is a review record, not website content. These local changes remain unpublished pending the user's final review.

## Scope of review

### Volume III correction — 30 October 2026

The second, third and fourth kinds of power in Stage Seven, Chapter II are prose cases, not smaller chapters. Their English and Arabic text is now ordinary paragraphs and is omitted from the sidebar and printed contents. Their wording, passage IDs, note callouts, paired section keys and review storage version are retained. The old section boundaries remain as continuous parts of the same reading flow so saved positions and review references still work. `data-continuation`, `data-continues` and `data-contents-parent` keep the text continuous and the current chapter highlighted; the builder puts the previous/next controls only at the end of the full group. Both Markdown volumes and the complete bilingual ZIP agree with this correction. Do not promote these cases back to headings during a future import.

This is an editorial, structure and publication-quality check, not an independent word-by-word verification of the entire Arabic text against all nine printed volumes or a review of every English translation choice. The six restored note callouts are editorial placements made using the available printed PDF context. The isolated note is reported openly instead of being assigned an uncertain passage.
