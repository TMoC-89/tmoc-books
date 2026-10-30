# Edition notes — America Against America / 美国反对美国

**Author:** Wang Huning (王沪宁). **Original Chinese publication:** Shanghai Literature and Art
Publishing House (上海文艺出版社), January 1991. This site presents the full
English and Chinese texts in the same reader.

## Source treatment

- The two user-supplied Markdown files were used directly. Both contain the
  same **11 chapters and 85 numbered sections**, in the same sequence.
- The Chinese Markdown was prepared from a transcription of the 1991 publication.
  Original publication details are retained with the text.
- A formatting pass made the Chinese `##` section headings consistent, with
  numbering such as `## 1. 美国制造的疑惑`. It normalized line endings and
  repeated blank lines in both files. No body passages were translated, rewritten,
  dropped, merged, or assigned invented notes.
- Printed contents and the publishing details remain at the beginning of both
  versions, before Chapter 1; no separate endnote section was added because none
  exists in these source files.
- Both full cleaned texts are freely downloadable as Markdown individually or
  together in the bilingual ZIP, without replacing them with shortened excerpts.

## Reading and navigation

- Each version has an opening section, preface, printed contents, and 85 paired
  numbered reading sections; each chapter title remains at the beginning of its
  first section. Both use the same stable `data-key` in each paired section.
- The sidebar contents gives the original preface, contents, all 11 chapter
  titles, and all 85 section titles. `contents.json` records each item, type and
  hierarchy in a separately reviewed and hash-checked structure. The builder
  refuses to apply an old contents review after heading/ID changes.
- English is the default view. Chinese uses native Simplified Chinese font stacks
  and line breaking, with no forced word hyphenation. Language switching keeps
  the corresponding section in view.
- Reviewer Mode displays matching chapter/section context for the two languages.
  Where paragraph divisions differ, source spans are approximate; neither the
  Chinese nor the English text has been artificially split to make paragraphs match.
- The global index contains both English and Chinese passages. Chinese lookup
  indexes overlapping two-character sequences and groups them into compact files,
  while preserving the site's existing Arabic, French, German and English search.

## Rebuild and checks

## Release review — 30 October 2026

- English chapter divisions use a colon consistently in the reading text, contents, downloads and source importer. Paragraph prose remains unchanged.
- This reader opts out of automatic browser translation, so Chinese source text stays Chinese, including in Reviewer Mode. Language switching remains available through the reader's own button.
- Chinese and Latin characters are separated correctly when indexing and searching mixed-script text, such as `CA985经过`. Chinese phrase search, highlighting and links back to the original passage were checked alongside English, Arabic, French and German search.
- Desktop and phone-size layouts, the contents hierarchy, section matching, text-size slider, saved reading position, saved review edits and JSON export were checked locally. The JSON includes the full proposed English and Chinese source context with stable passage identifiers.
- The supplied complete sources have 11 chapters and 85 numbered sections in each language. All are retained. This review checks faithful inclusion and the reading tools; it does not claim an independent line-by-line translation review against the printed book. Paragraph matching in Reviewer Mode remains approximate because the sources have different paragraph boundaries.

Run `python3 tools/import_america_against_america.py ENGLISH.md CHINESE.md`,
then `python3 tools/build.py` and `python3 tools/build.py --check` from the
repository root. To check the import structure, see the generated `book.json` and
`contents.json`.
