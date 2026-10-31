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
  repeated blank lines in both files. That formatting pass did not translate, rewrite, drop or merge body passages.
  The later English editorial corrections are described below.
- Printed contents and the publishing details remain at the beginning of both
  versions, before Chapter 1. The English edition now has a separate section of
  editorial notes; these are not presented as notes from the Chinese source.
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

## English editorial corrections — 31 October 2026

The English first pass has been screened for names, dates, places, titles and
other factual discrepancies. Verified corrections appear in the English text,
with numbered editorial notes explaining differences from the supplied Chinese
transcription and linking to sources. This is not a line-by-line assessment of
every translation decision. The Chinese transcription has not been altered.

- In Chapter 1, section 5, the community is identified as the **Amish**, the
  town as **Kalona**, and John M. Zielinski's book as *The Amish Across America*.
  The supplied Chinese transcription uses 亚美尼亚人, meaning “Armenians”,
  and spells the town “Kolona”. The correction is supported by the [City of
  Kalona](https://www.cityofkalona.org/index.asp?SEC=D5DB9FC7-80F0-474D-909C-D23D56F09F4B)
  and the [catalogue record for Zielinski's book](https://ci.nii.ac.jp/ncid/BD19923744).
  The source uses a feminine pronoun for Zielinski; the English now repeats
  the name instead of selecting a pronoun.
- Chapter 1, section 3 uses **BITNET**, the name of the academic network, where
  the supplied Chinese text says “Bignet”. See [Cornell's history of academic
  networks](https://www.cs.cornell.edu/wya/AcademicComputing/text/nationalnets.html).
- Chapter 9, section 2 identifies MIT's school as **Architecture and Planning**;
  the supplied Chinese text says agriculture. See the [MIT catalogue](https://dome.mit.edu/bitstream/handle/1721.3/82790/AC0598_001958.pdf?isAllowed=y&sequence=1).
- Chapter 2, section 1 restores the original English title of Commager's
  *The American Mind*, which Wang read in a Chinese translation. The previous
  English version translated its Chinese title as *The American Spirit*. See
  [Amherst College's account of Commager's work](https://archivesspace.amherst.edu/repositories/2/resources/245).
- Chapter 6, section 1 corrects the supplied Chinese text's description of
  Dukakis's position on abortion. See the [1988 debate transcript](https://millercenter.org/the-presidency/presidential-speeches/september-25-1988-debate-michael-dukakis).
  Chapter 10, section 7 corrects the sum of the source's population figures.
- Chapter 11, section 8 corrects two errors in the source:
  [George McJunkin discovered the Folsom site in 1908](https://www.nps.gov/articles/000/places-of-black-cowpokes.htm),
  before his death in 1922, and Jefferson's 1820 “wolf by the ear” remark
  [concerned slavery](https://www.monticello.org/encyclopedia/wolf-ear-quotation),
  not Native Americans.
- The debate's “Iceman” reference is clarified, authorial voice is restored in
  two passages, and a sentence about think tanks no longer adds an unsupported
  contrast. The review preserves the author's historical perspective while correcting identified factual errors.
- The notes also record corrections to names, institutional details, sales,
  geography, election history, the space race and the 1985 income comparison.
  Some identifications are reasoned inferences and are labelled as such. Where
  the original spelling of a name could not be established, a note says so.

Passage boundaries and identifiers have not changed. Reviewer drafts saved for
the previous release can be carried forward to this version on the same device.

## Release review — 30 October 2026

- English chapter divisions use a colon consistently in the reading text, contents, downloads and source importer. Paragraph prose remains unchanged.
- This reader opts out of automatic browser translation, so Chinese source text stays Chinese, including in Reviewer Mode. Language switching remains available through the reader's own button.
- Chinese and Latin characters are separated correctly when indexing and searching mixed-script text, such as `CA985经过`. Chinese phrase search, highlighting and links back to the original passage were checked alongside English, Arabic, French and German search.
- Desktop and phone-size layouts, the contents hierarchy, section matching, text-size slider, saved reading position, saved review edits and JSON export were checked locally. The JSON includes the full proposed English and Chinese source context with stable passage identifiers.
- The supplied complete sources have 11 chapters and 85 numbered sections in each language. All are retained. This review checks faithful inclusion and the reading tools; it does not claim an independent line-by-line translation review against the printed book. Paragraph matching in Reviewer Mode remains approximate because the sources have different paragraph boundaries.

## Rebuild and checks

Run `python3 tools/import_america_against_america.py ENGLISH.md CHINESE.md`,
then `python3 tools/build.py` and `python3 tools/build.py --check` from the
repository root. To check the import structure, see the generated `book.json` and
`contents.json`.
