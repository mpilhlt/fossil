# Annotation guidelines

The annotation guidelines are a collection of best practices and indications on how the
data should be annotated to support documents containing references in footnotes. They
complement what is described in the related models in the
[Grobid documentation](https://grobid.readthedocs.io/en/latest/training/General-principles/).

The official Grobid documentation is written with documents that have a conventional,
structured bibliography in mind — a numbered or alphabetical list of references
gathered at the end of the text. These guidelines instead focus specifically on legal
scholarship and the humanities disciplines that share its citation culture (history,
philology, area studies), where the citation apparatus lives almost entirely in
footnotes instead.

> [!NOTE]
> These guidelines assume that annotators:
> - are familiar with the type of documents to be annotated
> - work with the [PDF-TEI-Editor](https://github.com/mpilhlt/pdf-tei-editor/) — though
>   annotation can always be done with any XML editor instead

The PDF-TEI-Editor has a visual mode in which annotation is done by marking a span of
text and picking the matching tag from a chip palette, rather than by typing XML by
hand. Even so, annotators must first familiarize themselves with the raw XML markup
described in this document, since it is what defines the underlying schema — the chip
palette only makes that schema faster to apply; it does not replace understanding it.

## General strategy

The way annotations are expressed is not always unique, and different interpretations
from different people (with perhaps different experience and background) are expected.
For this reason these guidelines are a "living" document and may change over time.

There are different strategies for annotation:
- blind annotations + review: annotators work on the same documents and one reviewer
  consolidates the different annotations
- double round + review: each annotator works on a portion of the dataset, and 
  then revises other annotators' work; the reviewer checks the final result

The work will be organised in iterations where the team performs the following tasks on a batch of documents:
1. automatic extraction from the source PDF
2. annotation (either blind or double)
3. review, feedback and corrections, update of guidelines if necessary
4. training/evaluation of the model
5. proceed with 1. on a new batch

The input files are PDF documents that are pre-annotated by the ML models. The
annotators then have to correct the pre-annotated output from the model.

> [!WARNING]
> Questions, discussions and decisions must always go through GitHub issues at
> <https://github.com/mpilhlt/fossil/issues>.

## Layered model architecture

Grobid does not annotate a document in one pass. It works through three separate
models, one after the other, each one handed only the part of the document that the
previous model marked out for it. First, the
[document segmentation model](#document-segmentation-model) looks at the whole document
and divides it into broad zones — the header, the body, the footnotes, and so on.
Next, the [reference segmentation model](#reference-segmentation-model) takes only the
zones marked as footnotes and splits that raw text into individual citations. Finally,
the [citation model](#citation-model) takes each of those individual citations and
works out its fine-grained structure — who the authors are, what the title is, which
year it was published, and so on.

The practical consequence of this pipeline is worth keeping in mind while annotating:
each model can only "see" what the model before it correctly identified and handed
down. If a piece of text is not tagged correctly at an earlier stage — for example, if
a footnote is not marked as such by the segmentation model — it never reaches the later
models at all, and no amount of careful annotation further down the pipeline can fix
that. This is why getting the earlier, coarser distinctions right (what is a footnote,
what is body text, what is a header) matters just as much as getting the later, more
detailed ones right.

## Data correction

The most important principle when correcting the pre-annotated training data is to keep
the stream of text untouched. Only the tags can be moved; the text itself shall not be
modified or corrected. The stream of text present in the training file after extraction
of the content of the PDF is similar to the stream of text Grobid will have to process
once the models are (re)created. It is thus important to have Grobid trained on this
real-world input, even if it contains OCR errors, noise, unknown unicode characters,
etc. Therefore, **never** correct mistakes in the text — leave everything as it is.

There are three exceptions to this main rule:

1. Actual end-of-lines from the PDF files are indicated by the element `<lb/>`. These
   tags are not annotation tags, but should be considered part of the stream of text.
   They therefore must not be moved or removed with respect to the overall text stream.

2. Line breaks and changes of indentation are accepted outside the main tags to make
   the formatting more readable.

   > [!TIP]
   > Example:
   >
   > ```xml
   > <text>
   >             <body>...</body><listBibl>...</listBibl><page>...</page>
   > </text>
   > ```
   >
   > can safely be reformatted to
   >
   > ```xml
   > <text>
   >     <body>...</body>
   >
   >     <listBibl>...</listBibl>
   >
   >     <page>...</page>
   > </text>
   > ```

3. In the TEI/XML files, an end-of-line is equivalent to a space character — it is thus
   possible to add or remove end-of-line characters as long as the spacing is
   preserved.

   > [!TIP]
   > See this example from the
   > [Grobid documentation](https://grobid.readthedocs.io/en/latest/training/General-principles/):
   >
   > ```xml
   > <title level="a">In XML training files, end-of-line and space are the same</title> <lb/> <author>Kermitt Jr</author> <lb/> <date>2017</date>
   > ```
   >
   > is equivalent to
   >
   > ```xml
   > <title level="a">In XML training files, end-of-line and space are
   >     the same</title> <lb/>
   >     <author>Kermitt Jr</author>
   >     <lb/>
   >
   >     <date>2017</date>
   > ```

## Document segmentation model

> [!NOTE]
> Model name in the PDF-TEI-Editor: `grobid.training.segmentation`, training files end
> in `.training.segmentation.tei.xml`

This section complements what's described in the
[related model in the Grobid documentation](https://grobid.readthedocs.io/en/latest/training/segmentation/).

The general structure of the files is:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <!-- document metadata -->
  </teiHeader>
  <text>
    <titlePage>
      Cover page, or pages that are leftover from the journal that are not fully related to the article
    </titlePage>

    <div type="toc">
      Table of content
    </div>

    <front>
      Front matter content. This includes:
        - title
        - abstract
        - footnotes containing affiliations and acknowledgements
      line breaks: <lb/>
    1<lb/>
    </front>

    <!-- more <front> tags as needed -->

    <note place="headnote">Headers, if any, such as journal name or edition, author name, title of the article from Page 2<lb/></note>

    <body>
      Body content: this is the text of the article / chapter without the footnotes, including section headings, illustrations, etc.<lb/>
    </body>

    <listBibl>
      All footnotes that contain reference data<lb/>
    </listBibl>

    <note place="footnote">Any footnotes that do not contain references, or footers containing repeating text, similar to the headnote<lb/></note>

    <!-- more <note>, <body> and <listBibl> tags -->

    <note place="footnote">Endnotes, if any, which do not contain references, otherwise use listBibl<lb/></note>

    <div type="acknowledgment|availability|funding|annex">
      Any type of annex for acknowledgement, availability, funding or other information that is not in the header but attached to the end of the article
    </div>

  </text>
</TEI>
```

### Tags

The following TEI elements are used by the segmentation model:

* `<titlePage>` for the cover page
* `<front>` for the document header
* `<note place="headnote">` for the page header
* `<note place="footnote">` for the page footer and numbered footnotes
* `<body>` for the document body
* `<listBibl>` for the bibliographical section
* `<page>` to indicate page numbers
* `<div type="toc">` for table of content
* `<div type="conflict">` for conflict of interest statements (when not placed in the header)
* `<div type="contribution">` for author contribution statements (when not placed in the header)
* `<div type="acknowledgement">` for acknowledgment statement in the annex (note that both British and American spelling are accepted by Grobid)
* `<div type="availability">` for data and code availability statement annex (when not placed in the header)
* `<div type="funding">` for funding information annex (when not placed in the header)
* `<div type="annex">` for any other annexes

These substructures must be identified whenever they interrupt the flow of the
`<body>`. Figures and tables (including their potential titles, captions and notes) are
considered part of the body, so they are contained by the `<body>` element.

Note that the markup overall follows the [TEI](http://www.tei-c.org) conventions.

> [!TIP]
> It is highly recommended to study the existing training documents for the
> segmentation model first, to see examples of how these elements should be used.

### Analysis

The following sections provide detailed information and examples on how to handle
certain typical cases.

#### Start of the document (cover page and header)

##### Cover page (`<titlePage>`)

An optional cover page — usually added by the publisher to summarize the
bibliographical and copyright information — might be present, and needs to be entirely
identified by the `<titlePage>` element. The cover page is considered an addition to a
standalone well-formed article. The content of a cover page is usually redundant with
the bibliographical information found in the article header. A cover page usually
corresponds to the content of the entire first page.

##### Header (`<front>`)

The header section typically contains bibliographical information, such as the
document's title, author(s) possibly with affiliations, abstract, keywords, container
journal title, etc. The header usually covers everything until the start of the article
body (e.g. until reaching the introduction of the article). While a cover page is
optional, an article should always include a header, even if limited to the title.

> [!NOTE]
> For the segmentation model, there are no `<title>` or `<author>` elements, because
> they are handled by the `header` model, which runs in cascade at the next stage on
> the content the segmentation model identified as "header".

All this material should be contained within the `<front>` element. In addition, any
footnotes that are referenced from within the header (for example when author
affiliations and addresses are expressed in footnotes) should also be annotated under a
`<front>` element. Furthermore, the footer that contains the first page number should
also be treated as part of the header, since the first page number is useful, common
bibliographical information.

In general, we expect to find all the bibliographical information of the document as
part of the header. This principle should be followed in every document in order to
ensure homogeneity of the "header" content across the training data.

The following bibliographical-metadata lines, when they appear as a footnote on the
first page of the document, should be contained inside a `<front>` element:
* Received: [date]
* Revised: [date]
* Accepted: [date]

However, any footnotes referenced from within the `<body>` should remain outside the
header element, even if they are on the first page or surrounded by `<front>`
fragments.

There should be as many `<front>` elements as necessary to contain all the content
identified as "front content" (bibliographical information), not necessarily limited to
the first pages. `<front>` can contain items that are not always at the beginning of
the document, such as:

* Copyright information / Open Access licence and statement
* Correspondence information
* Detailed affiliation and address information
* Submission information: when the document was received, approved and published

These items often appear at the very end of an article or just after the document
body. However, for consistency, they should be annotated under `<front>`
because they are bibliographical information covered by the header model.

The following information blocks sometimes appear inside the article header, so they
should be annotated as `<front>`:

* Author contributions
* Ethics and competing interests
* Funding
* Data / code availability statement

However, when they instead appear as annexes after the document body, they should be
annotated as `<div type="annex">` (see next section), not under `<front>`.

It is possible that the position of a title in the text flow of a document differs from
the visual layout of the document.

The following TEI XML annotation shows the presence of a `<front>` element surrounding
both the topic and the title:

```xml
virus. <lb/>But is the role of LGP2 in CD8 + T cell <lb/>survival and function cell
intrinsic <lb/></body>

<front>A N T I V I R A L I M U N I T Y <lb/>LGP2 rigs CD8 + T cells for
survival <lb/></front>

<body> or extrinsic? T cell receptor-and <lb/>IFNβ-mediated signalling in CD8 + T
```

> [!NOTE]
> In general, whether the `<lb/>` (line break) element is inside or outside `<front>`
> or other elements is of no importance. However, as indicated in
> [Data correction](#data-correction), the `<lb/>` element should not be removed and
> should follow the stream of text.

Sometimes an article starts mid-page, with the end of the preceding one occupying the
upper first third of the page. As this content does not belong to the article in
question, do not add any elements, and remove any `<front>` or `<body>` elements that
could appear in the preceding article.

#### Additional information `<div type="...">`

Additional and supporting information sections, which are located **after the body** of
the article (typically after the conclusion), should be annotated under
`<div type="annex">` or the following more specific annex types:

* `<div type="acknowledgment">` for acknowledgment annex (including funding/grant acknowledgement when inside an acknowledgement section)
* `<div type="availability">` for data and code availability statement annex
* `<div type="funding">` for funding information annex

> [!NOTE]
> Different annex-type sections should be segmented into separate `<div type="annex">`
> elements to capture the start and end of each section block.

Supplementary texts, supplementary figures and tables, and any similar appendices
should all be encoded under `<div type="annex">`.

#### Elements interrupting the document body: headnotes and footnotes

Any information appearing in the page header needs to be surrounded by a
`<note place="headnote">`.

![Example of a headnote](img/note-place-headnote.png)

The contents of the grey band in the screenshot above should be surrounded by a
`<note place="headnote">`, except on the first page, where this type of information
would be inside the `<front>` element.

Any information appearing in the page footer needs to be put inside a
`<note place="footnote">`, as shown in the following example:

![Example of a footnote](img/note-place-footnote.png)

Corresponding TEI XML:

```xml
<note place="footnote">NATURE REVIEWS | IMMUNOLOGY <lb/>VOLUME 12 |
	SEPTEMBER 2012 <lb/>© 2012 Macmillan Publishers Limited. All rights reserved</note>
```

The `<page>` element, which contains the page number, should be outside any of the
above `<note>` elements.

Any notes to the left of the main body text are to be encoded as `<note>` if they are
related to an element of the `<body>`; if they concern header elements, they go into a
`<front>` element. See this screenshot as an example:

![Example of different note types](img/different-note-examples.png)

References are also expected to appear in footnotes, in four different styles:

1. Header information, such as affiliation or publication information.

   ![Example of header information in a footnote](img/example-footnote-header.png)

   The `*` note should be annotated as `<front>...</front>` because it is part of the
   bibliographic information header.

   ![Example of affiliation/acknowledgment in a footnote](img/example-footnote-header-2.png)

   Both references 1 and 2 are affiliation and acknowledgment, and should be annotated
   as `<front>...</front>`.

2. A pure footnote with a comment related to content in the text, annotated as
   `<note place="footnote">.....</note>`.

   ![Example of a pure footnote comment](img/example-footnotes-body.png)

   "see reference 8" should be annotated as `<note place="footnote">`.

3. A pure reference, with the data of the referred article, annotated as
   `<listBibl>....</listBibl>`.

   Example: footnotes 4, 5, 6, 7 and 9 in the screenshot above should be annotated as
   `<listBibl>`.

4. Mixed content, with a comment related to the body and a reference annexed to it,
   annotated as `<listBibl>....</listBibl>` as well (see footnote 9 in the same
   screenshot). See [Reference segmentation model](#reference-segmentation-model) below
   for how the commentary and the citation(s) it introduces are annotated together.

> [!WARNING]
> - Due to the way text is extracted from the PDF, `<note place="headnote">`,
>   `<note place="footnote">`, and `<page>` elements are not necessarily where you
>   expect them — sometimes they are all placed at the bottom of the page. Just
>   annotate, do not move the elements around.
> - The page text extraction algorithm also sometimes strips the numbering of the
>   headers and places it elsewhere. Do not correct this either.

#### Tables and figures

Figures and tables belong to the main body structure: they are not specifically encoded
at the segmentation level.

Figures and tables, including captions, appearing after the references but related to
the body (e.g. a list of figures in preprints), should be under `<body>`. If a figure
or table appears inside an annex of an article, it should remain inside the
`<div type="annex">` element. If a figure or table appears in an abstract (which is
rare but might happen), it should remain within the `<front>` element.

#### Hidden characters

It happens that Grobid picks up hidden text that is present but not visible on the
PDF's page for the reader. Such content should not be surrounded by any element, to
indicate to Grobid that it should be ignored.

```xml
visible in lane 10 (longer exposure), where anti-rabbit secondary antibodies<lb/> were used. <lb/></body>

print ncb1110 17/3/04 2:58 PM Page 309 <lb/>

<note place="footnote">© 2004 Nature Publishing Group <lb/></note>
```

## Reference segmentation model

> [!NOTE]
> Model name in the PDF-TEI-Editor: `grobid.training.references.referenceSegmenter`,
> training files end in `.training.references.referenceSegmenter.tei.xml`

The reference segmenter is a model that takes the content of the `<listBibl>` label
produced by the segmentation model and does a more fine-grained segmentation, which can
then be parsed by the final citation (`references`) model.

The reference segmenter model is trained with two labels only:

- `<label>` — the reference number, e.g. "[1]" in a numbered bibliography, or the
  footnote number (as in "^1^ This is the first footnote.")
- `<bibl>` — encloses an individual reference
- `<bibl type="footnote">` — encloses an individual comment or note that does not
  refer to any reference (discussion:
  [#20](https://github.com/mpilhlt/fossil/issues/20)). This is to catch incorrect
  classification in the upstream "segmentation" annotation.

For footnote references, we use one `<bibl>` element per reference. The `references`
model (see [Citation model](#citation-model) below) then parses the content of each
`<bibl>` and extracts the reference metadata.

If there is commentary (i.e. content that is not bibliographic metadata), including
introductory signal words ("See also", "Vgl. z.B.", "Anderer Meinung:", etc.), include
it with the `<bibl>` it belongs to semantically. The comment will mostly precede but
sometimes also follow the reference (see below for examples). You need to look closely;
if in doubt, ask.

> [!NOTE]
> The `references` model has no notion of a labeled span sitting *between* two
> `<bibl>`s. When one comment or signal phrase introduces several references, it is
> annotated only once, inside the `<bibl>` it is closest to (see
> [Citation model](#citation-model) for how that same convention carries through into
> `<seg type="citationContext">` at the next stage).

### Examples

Here are some examples that we will expand with more cases as needed.

**Several references in one footnote**

![Several references in one footnote](img/refseg-several-references.png)

```xml
<bibl><label>2</label> Ronald H. Coase, The Problem of Social Cost, 56 J.L &amp; ECON 837 (1960); </bibl>
<bibl>GUIDO CALABRESI, THE COSTS<lb/> OF ACCIDENTS: A LEGAL AND ECONOMIC ANALYSIS (1970); </bibl>
<bibl>RICHARD A. POSNER, THE ECONOMICS OF JUSTICE<lb/> (1981); </bibl>
<bibl>RICHARD A. POSNER, ECONOMIC ANALYSIS OF LAW (9th ed. 2014); </bibl>
<bibl>ROBERT COOTER &amp; THOMAS<lb/> ULEN, LAW &amp; ECONOMICS (2000); </bibl>
<bibl>ROBIN P. MALLOY, LAW AND MARKET ECONOMY: REINTERPRETING THE<lb/> VALUES OF LAW AND ECONOMICS (2000); </bibl>
<bibl>NICHOLAS MERCURO &amp; STEVEN G. MEDEMA, ECONOMICS AND THE<lb/> LAW: FROM POSNER TO POST-MODERNISM AND BEYOND (2d ed. 2006).<lb/> </bibl>
```

**German legal citation**

![German legal citation](img/refseg-german-legal-citation.png)

```xml
<bibl><label>2</label> Dazu etwa: Hofmann, ZGE 2016, 482, 498; </bibl>
<bibl>Becker, ZGE 2016, 239, 273; </bibl>
<bibl>Raue, ZGE 2014,<lb/> 387, 389.<lb/> </bibl>
```

**Introductory comment**

![Introductory comment, example 1](img/refseg-introductory-comment-1.png)

```xml
<bibl><label>3</label> Zur Frage, ob der Erwerb eines (digitalen) Werkexemplars mit dem Erwerb eines dinglichen<lb/> Genussrechts verbunden ist, vgl.: Kuschel, Der Erwerb digitaler Werkexemplare zur privaten<lb/> Nutzung, 2019.<lb/> </bibl>
```

![Introductory comment, example 2](img/refseg-introductory-comment-2.png)

```xml
<bibl><label>15</label> Arguing that national corporate due diligence laws potentially breach the principle of consent in<lb/> international law and the sovereignty of host States, and perpetuate power imbalances of colonial<lb/> derivation, see e.g.: C. OMARI LICHUMA, (Laws) Made in the 'First World', cit., pp. 517-518; </bibl>
<bibl>F. DEHBI, O.<lb/> MARTIN-ORTEGA, An integrated approach to corporate due diligence from a human rights, environmental,<lb/> and TWAIL perspective, in Regulation &amp; Governance, 2023, n. 17, pp. 927-943, in particular pp. 932-935.<lb/> </bibl>
<bibl>In contrast, affirming that such national legislations are to be regarded as instruments facilitating home<lb/> States' compliance with their international obligations, rather than as breaches of the host States'<lb/> sovereignty, see: A. BONFANTI, Imprese multinazionali, diritti umani e ambiente. Profili di diritto<lb/> internazionale pubblico e privato, Milano, 2012, p. 136.<lb/> </bibl>
```

Here, the signal phrase ("Arguing that..., see e.g.:") semantically belongs to the
first and second references, but this cannot be expressed at the referenceSegmenter
stage, so it is put into the first `<bibl>` only. (At the `references` stage, this same
phrase is what becomes `<seg type="citationContext">` — see
[Citation-signal phrases](#citation-signal-phrases) below.)

**Trailing comment**

![Trailing comment](img/refseg-trailing-comment.png)

```xml
<bibl><label>9 </label>See e.g.: Inter-American Court of Human Rights, judgment of 16 February 2020, Indigenous Communities<lb/> of the Lhaka Honhat (Our Land) Association v. Argentina, par. 254, quoting the amicus curiae intervention<lb/> of the former UN Special Rapporteur on the Right to Food, De Schutter: «Many indigenous peoples<lb/> understand the right to adequate food as a collective right. They often see subsistence activities such as<lb/> hunting, fishing and gathering as essential not only to their right to food, but to nurturing their cultures,<lb/> languages, social life and identity». The cultural value of food is recognized -with respect to indigenous<lb/> peoples in particular -also under art. 27 of the International Covenant on Civil and Political Rights<lb/> (ICCPR). See infra, section 3.2.<lb/> </bibl>
```

**Court decisions**

![Court decisions](img/refseg-court-decisions.png)

```xml
<bibl><label>6</label> See, ex multis: African Commission on Human and Peoples Rights, decision of 27 October 2001, Social<lb/> and Economic Rights Action Center (SERAC) and Center for Economic and Social Rights (CESR) v.<lb/> Nigeria; </bibl>
<bibl>Inter-American Court of Human Rights, judgment of 27 June 2012, Case of the Kichwa Indigenous<lb/> People of Sarayaku v. Ecuador.<lb/> </bibl>
```

**Comments not related to any citation in the footnote**

See examples in [#20](https://github.com/mpilhlt/fossil/issues/20).

**References to other references** (`id.`, `op. cit.`, `a.a.O.`, `ders.`, *supra*,
*infra*, "N. 22", "above") are, at the referenceSegmenter stage, simply part of the
`<bibl>` they occur in — no separate label exists for them here. They are only broken
out into their own `<ref type="...">` elements at the `references` stage; see
[Intra-footnote references](#intra-footnote-references) below.

### Example from the demo

Sometimes the references are in separate sentences rather than separated by semicolons:

![Example from the demo](img/refseg-demo-example.png)

## Citation model

> [!NOTE]
> Model name in the PDF-TEI-Editor: `references`, training files end in
> `.training.references.tei.xml`

This section complements what's described in the
[related model in the Grobid documentation](https://grobid.readthedocs.io/en/latest/training/Bibliographical-references/).
The `references` model takes each `<bibl>` produced by the reference segmenter and
labels its internal structure: author names, titles, dates, extents, identifiers, and
so on. Every element below (except `<label>` and `<lb/>`) can occur any number of
times, in any order, inside a `<bibl>`.

Most of the corpus is annotated with this base vocabulary alone. A smaller but
significant part of the corpus — legal scholarship and the humanities disciplines that
share its citation culture — needs a further, domain-specific layer on top of it, which
is documented separately in [Legal and Humanities Scholarship](#legal-and-humanities-scholarship) below.

### Basic bibliographic elements

**Authors and editors.** `<author>` and `<editor>` hold a complete sequence of names as
running text. Where the source clearly separates given name / surname, it is fine (but
not required) to decompose them with `<persName>`, `<forename>`, `<surname>`:

```xml
<author>J. Smith</author>
<author><persName><forename>J.</forename> <surname>Smith</surname></persName></author>
```

**Titles.** `<title level="...">` classifies the title by the kind of work it names:

| `@level` | Meaning |
| --- | --- |
| `a` | Article or chapter title (analytic) |
| `j` | Journal title |
| `m` | Monograph, proceedings, book, or thesis title |
| `s` | Series title |
| `u` | Unpublished work title |

An optional `@key` holds a short resolvable key for a named work (e.g. an abbreviation),
so it can later be linked to an external database.

**Dates.** `<date type="publication" when="...">` marks the publication date; `@when`
holds the machine-readable ISO form when it can be determined, the text content the
form as it appears in the source.

**Extent.** `<biblScope unit="...">` carries the cited work's own extent — its volume,
issue, or overall page range — with optional `@from`/`@to`:

| `@unit` | Matches |
| --- | --- |
| `page` | Full page range of the article |
| `volume` | Volume number |
| `issue` | Issue / number |

**Publisher and place.** `<publisher>` and `<pubPlace>` hold the publisher's name (also
used for corporate authors such as web pages) and place of publication.

**Edition.** `<edition n="...">` marks an edition statement, e.g. `n="2"` for a second
edition.

**Basic identifiers.** `<idno type="...">` accepts, among the values also documented
under [Legal and Humanities Scholarship](#legal-and-humanities-scholarship): `DOI`,
`ISSN`, `arXiv`, `report` (technical/institutional report number).

**Web pointer.** `<ptr type="web" target="...">` holds a URL as text content, excluding
prefixes like "URL:" and trailing periods.

**Miscellaneous note.** `<note type="report">` marks any note not covered by another
tag — typically the type of report or thesis (e.g. "Ph.D. thesis", "Technical Report").

**Institutional authorship.** `<orgName type="...">` names an institution that is not
itself the work's issuing authority (see [The issuing authority](#the-issuing-authority-authority)
for that case) — for example the university behind a thesis, or a project consortium
behind a technical report:

| `@type` | Meaning |
| --- | --- |
| `institution` | An institution (e.g. a university) |
| `collaboration` | Project-based collaboration acting as an author group |
| `department` | A department within an institution |
| `laboratory` | A laboratory or research group |

A non-legal example combining several of these:

```xml
<bibl><author>J. Smith</author> and <author>A. Doe</author>,
  <title level="a">A Study of Neural Machine Translation</title>,
  <title level="j">Journal of Computational Linguistics</title>
  <biblScope unit="volume">45</biblScope>(<biblScope unit="issue">2</biblScope>),
  <biblScope unit="page" from="123" to="145">123–145</biblScope>
  (<date type="publication" when="2019">2019</date>).
  <idno type="DOI">10.1162/coli_a_00345</idno>
</bibl>

<bibl><author>M. Müller</author>, <title level="m">Diffusion Models for Generative Art</title>
  (Ph.D. thesis, <orgName type="institution">ETH Zürich</orgName>,
  <date type="publication" when="2022">2022</date>).
  <note type="report">Ph.D. thesis</note>
</bibl>
```

## Legal and Humanities Scholarship

Legal scholarship and the humanities disciplines that share its citation culture
(history, philology, area studies) rely on the basic vocabulary above plus a further
layer: courts and legislatures cited as the "author" of a work, pinpoint citations
below the level of a page (a statute section, a marginal number, a recital), elliptical
back- and forward-references within the same footnote apparatus (`id.`, `op. cit.`,
`a.a.O.`, `ders.`, *supra*, *infra*), and citation-signal phrases (`see`, `cf.`, `vgl.`)
whose polarity and force is itself a meaningful research signal. This section documents
that layer.


### Genre of the cited work

```xml
<bibl type="legislation">...</bibl>
<bibl type="decision">...</bibl>
```

`legislation` marks a statute citation, `decision` a court ruling / judicial decision
citation. `type` is omitted for an ordinary reference, and reserved to `footnote` for a
comment that is not a bibliographic reference at all (see
[Reference segmentation model](#reference-segmentation-model) above).

### The issuing authority (`<authority>`)

```xml
<authority type="court">EuGH</authority>,
<date type="decision" when="2016-09-08">Urt. v. 8.9.2016</date> –
<idno type="docket">C-160/15</idno>, …
```

`<authority type="court"|"legislature">` names the institution responsible for the
cited work — a court, a legislature, or (outside the legal domain) a regulator or other
issuing body. Use it instead of `<author>` (an institution is not a person) and instead
of a bare `<orgName>` (which has no "responsible for this work" role).

`<orgName>` **may** still be nested inside `<authority>` to decompose a compound
institutional name, e.g. a court plus its deciding panel:

```xml
<authority type="court"><orgName>Oberlandesgericht Frankfurt am Main</orgName>, 5. Zivilsenat</authority>
```

 The `<date type="...">` values `decision` (date a court decision was issued) and `enacted`
(date a statute was enacted) are likewise specific to this section — outside it, `<date>`
only uses `type="publication"` (which is the default when omitted).

### Pinpoint citations (`<citedRange>`)

`<biblScope>`, introduced above, carries the cited work's *own* extent. In legal and
humanities citation practice, the citing text often also names a *pinpoint* into that
work — a level of granularity `<biblScope>`'s own `@unit` list has no room for, such as
a statute section or a court decision's marginal number. `<citedRange unit="...">`
carries that pinpoint. If a work has no pagination at all (a decision cited only by
marginal number, say), there is simply no `<biblScope unit="page">` — only
`<citedRange>`.

| `@unit` | Matches |
| --- | --- |
| `section` | `§ 19a`, `Art. 5`, `Sec. 2` |
| `subSection` | `Abs. 2` |
| `sentence` | `S. 1`, `Satz 1` |
| `number` | `Nr. 3` |
| `letter` | `lit. b`, `Buchst. b` |
| `margin` | `Tz. 24`, `Rn. 20`, `Rdnr. 7` |
| `recital` | `ErwGr. 21` (EU recitals) |
| `page` | an in-text pinpoint page, e.g. the `(240)` in `233 (240)` |

```xml
<bibl type="legislation">
  <citedRange unit="section">§ 19a</citedRange>
  <citedRange unit="subSection">Abs. 2</citedRange>
  <title level="m" type="legislation" key="UrhG">UrhG</title>
</bibl>
```

### Docket and official identifiers

```xml
<idno type="docket">C-160/15</idno>
<idno type="ECLI">ECLI:EU:C:2016:644</idno>
<idno type="CELEX">…</idno>
```

These are the legal-specific values of `<idno type="...">`, alongside the general ones
listed under [Basic bibliographic elements](#basic-bibliographic-elements).

### Case short-name and statute short-title

```xml
<title level="a" type="caseName">GS Media/Sanoma</title>
<title level="m" type="legislation" key="UrhG">Urhebergesetz</title>
```

These are the legal-specific presets of `<title>`, on top of the plain `@level` values
listed under [Basic bibliographic elements](#basic-bibliographic-elements). Tagging the
case short-name explicitly, rather than leaving it as trailing free text, is what stops
the model from treating `– GS Media/Sanoma` as the start of a new reference.

### Intra-footnote references

Legal and humanities footnotes constantly avoid repeating a citation just given, using
devices such as *id.*, *op. cit.*, *ibid.*, *a.a.O.*, *ders.*, *supra*, *infra*,
"above", or "N. 22". `<ref type="...">` labels these:

| `@type` | Meaning | Examples |
| --- | --- | --- |
| `precedingWork` | the work just cited | *supra*, *above*, `id.`, `op. cit.`, `a.a.O.` |
| `subsequentWork` | a work cited later | *infra*, *below* |
| `precedingAuthor` | the author just named, work unspecified | `ders.`, `idem` |
| `footnote` | an explicit cross-reference to another footnote, carrying `@n` | `n. 7`, `N. 22`, "oben N. 22" |

```xml
<bibl><author>Vogel</author>, <ref type="precedingWork">id.</ref>,
  <citedRange unit="page" from="79" to="79">p. 79</citedRange></bibl>

<bibl><author>Vogel</author>, <ref type="precedingWork">op. cit.</ref>,
  <ref type="footnote" n="7">n. 7</ref>,
  <citedRange unit="page" from="80" to="81">pp. 80–1.</citedRange></bibl>

<bibl><ref type="precedingAuthor">Ders.</ref>, <ref type="precedingWork">a.a.O.</ref>,
  <citedRange unit="page" from="123" to="123">S. 123</citedRange>.</bibl>
```

When two of these devices sit next to each other but are lexically distinct — e.g.
`Kaiser (oben N. 22) 89` — split them into two adjacent `<ref>`s rather than fusing
them into one:

```xml
<author>Kaiser</author>
(<ref type="precedingWork">oben</ref> <ref type="footnote" n="22">N. 22</ref>)
<biblScope unit="page" from="89" to="89">89</biblScope>
```

The same pattern applies to a *forward*-pointing reference, combining `subsequentWork`
with `footnote`, e.g. "infra note 24":

```xml
<ref type="subsequentWork">infra</ref> <ref type="footnote" n="24">note 24</ref>
```

`@target` is available to hold a resolved pointer once the citation is resolved in
post-processing; it is not required for training annotation.

### Citation-signal phrases

Phrases that introduce a citation with an evaluative or directional stance — "See",
"See also", "Cf.", "But see", "Contra", "vgl.", "anderer Ansicht" — carry citation-
context information that is lost if the phrase is left as unlabeled prose. Mark the
whole introductory phrase (not just a single trigger word) with
`<seg type="citationContext">`:

```xml
<seg type="citationContext">For further analysis of the marriage contract, see</seg>
<author>K. O'Donovan</author>, <title level="m">Family Matters</title>
(<date type="publication" when="1993">1993</date>), especially
<citedRange unit="page" from="43" to="59">43–59</citedRange>.
```

`<seg type="citationContext">` marks only the signal phrase itself, not the citation
that follows it. When several citations share one signal phrase, keep the phrase only in
the first (or nearest) `<bibl>` it introduces — see the
[pipeline example](#worked-example-the-full-annotation-pipeline) below and the
referenceSegmenter's ["introductory comment" examples](#reference-segmentation-model)
above.

### Quotations

`<quote>` pairs a direct quotation from the body text with the `<bibl>` that supports
it. No attributes: quotation marks and trailing punctuation stay in the source text.

```xml
<bibl><seg type="citationContext">…</seg><quote>„The U. S. law and development movement …"</quote>, <author>Merryman</author>, …</bibl>
```

### A real-world example: multiple references with multiple comments

Footnotes routinely mix several of the devices above in one paragraph — multiple
citations, each with its own signal phrase or `supra`-style back-reference:

![A footnote combining several signal phrases and supra-note back-references](img/complex-reference.png)

```xml
<bibl><label>23</label> <seg type="citationContext">See</seg> <author>1 William Blackstone</author>,
  <title level="m">Commentaries on the Laws of England</title>
  <citedRange unit="page">37</citedRange> (The Legal Classics Library 1983) (1765-70))
  (quoting with approval John Fortescue's endorsement that lay students "trace[] up the
  principles and grounds of the law, even to their original elements"). Blackstone's use
  of natural law in the <title level="m">Commentaries</title> may also reflect his own
  introduction to the law. It was St. German's <title level="m">Doctor and Student</title>,
  a work integrating theological and legal thought, that drew Blackstone to the law.
</bibl>
<bibl><author>Cook</author>, <ref type="precedingWork">supra</ref> <ref type="footnote" n="12">note 12</ref>,
  <citedRange unit="page">170</citedRange>. Perhaps for similar reasons, the
  <title level="m">Commentaries</title> turned students from theology to law.
</bibl>
<bibl><author>McKnight</author>, <ref type="precedingWork">supra</ref> <ref type="footnote" n="2">note 2</ref>,
  <citedRange unit="page">401</citedRange>. Note that the pagination of the various
  editions of the <title level="m">Commentaries</title> has become more or less
  standardized. This move is not without its problems, however.
</bibl>
<bibl><seg type="citationContext">See</seg> <author>Alschuler</author>,
  <ref type="precedingWork">supra</ref> <ref type="footnote" n="1">note 1</ref>,
  <citedRange unit="page">3</citedRange> n.4;
</bibl>
<bibl><seg type="citationContext">cf.</seg> <author>Carli N. Conklin</author>,
  <title level="a">The Origins of the Pursuit of Happiness</title>,
  <title level="j">7 Wash. U. Juris. Rev.</title>
  <biblScope unit="page" from="195">195</biblScope>, <citedRange unit="page" from="200" to="200">200</citedRange> (<date type="publication">2015</date>))
  (selecting for use the first edition, as does the present article);
</bibl>
<bibl><author>Alan Watson</author>, <title level="a">The Structure of Blackstone's Commentaries</title>,
  <title level="j">97 Yale L.J.</title> <biblScope unit="page" from="795">795, <citedRange unit="page" from="200" to="200">801</citedRange></biblScope> (<date type="publication">1988</date>) (same).
</bibl>
```

The point is the pattern: one comment/signal phrase per `<bibl>` it introduces, `supra
note N` split into `<ref type="precedingWork">` + `<ref type="footnote" n="N">` exactly
as in [Intra-footnote references](#intra-footnote-references), and
no special nesting for the multiple citations sharing one footnote. (This annotation
validates against `schema/grobid.training.references.rng`.)

### The reference-segmentation examples, annotated

The [reference segmentation model](#reference-segmentation-model) examples above show
each footnote only up to the point of splitting it into raw, unparsed `<bibl>`
citations. Picking most of them up again here shows what the `references` model does
with that same raw text next — the same vocabulary introduced above, applied to real
footnotes rather than invented ones. (The
[several references in one footnote](#reference-segmentation-model) example is skipped:
it is a plain, non-legal citation list with nothing further to annotate beyond ordinary
`<author>`/`<title>`/`<date>`, already covered under
[Basic bibliographic elements](#basic-bibliographic-elements).)

This is the **German legal citation** example:

![German legal citation](img/refseg-german-legal-citation.png)

```xml
<bibl><label>2</label> <seg type="citationContext">Dazu etwa:</seg> <author>Hofmann</author>,
  <title level="j">ZGE</title> <date type="publication" when="2016">2016</date>,
  <biblScope unit="page">482</biblScope>, <citedRange unit="page">498</citedRange>;
</bibl>
<bibl><author>Becker</author>, <title level="j">ZGE</title> <date type="publication" when="2016">2016</date>,
  <biblScope unit="page">239</biblScope>, <citedRange unit="page">273</citedRange>;
</bibl>
<bibl><author>Raue</author>, <title level="j">ZGE</title> <date type="publication" when="2014">2014</date>,
  <biblScope unit="page">387</biblScope>, <citedRange unit="page">389</citedRange>.
</bibl>
```

Each citation follows the German convention of *first page, pinpoint page* ("482,
498"), so the first page becomes `<biblScope unit="page">` (the article's own extent)
and the pinpoint becomes `<citedRange unit="page">` — the same
[page/pinpoint distinction](#pinpoint-citations-citedrange) as `233 (240)` in the
real-world example below.

This is **introductory comment, example 1** (Kuschel):

![Introductory comment, example 1](img/refseg-introductory-comment-1.png)

```xml
<bibl><label>3</label> <seg type="citationContext">Zur Frage, ob der Erwerb eines (digitalen) Werkexemplars mit dem Erwerb eines dinglichen Genussrechts verbunden ist, vgl.:</seg>
  <author>Kuschel</author>, <title level="m">Der Erwerb digitaler Werkexemplare zur privaten Nutzung</title>,
  <date type="publication" when="2019">2019</date>.
</bibl>
```

This is **introductory comment, example 2** (Lichuma / Dehbi & Martin-Ortega /
Bonfanti). Note how `cit.` — the Italian-style short form for "already cited above" —
is tagged the same way as `supra`/`a.a.O.` in
[Intra-footnote references](#intra-footnote-references), and how the third citation
carries its own, separate signal phrase rather than sharing the first one:

![Introductory comment, example 2](img/refseg-introductory-comment-2.png)

```xml
<bibl><label>15</label> <seg type="citationContext">Arguing that national corporate due diligence laws potentially breach the principle of consent in international law and the sovereignty of host States, and perpetuate power imbalances of colonial derivation, see e.g.:</seg>
  <author>C. Omari Lichuma</author>, <title level="a">(Laws) Made in the 'First World'</title>,
  <ref type="precedingWork">cit.</ref>, <biblScope unit="page" from="517" to="518">pp. 517-518</biblScope>;
</bibl>
<bibl>
  <author>F. Dehbi</author>, <author>O. Martin-Ortega</author>,
  <title level="a">An integrated approach to corporate due diligence from a human rights, environmental, and TWAIL perspective</title>,
  <title level="j">Regulation &amp; Governance</title>, <date type="publication" when="2023">2023</date>,
  <biblScope unit="issue">17</biblScope>, <biblScope unit="page" from="927" to="943">pp. 927-943</biblScope>,
  in particular <citedRange unit="page" from="932" to="935">pp. 932-935</citedRange>.
</bibl>
<bibl>
  <seg type="citationContext">In contrast, affirming that such national legislations are to be regarded as instruments facilitating home States' compliance with their international obligations, rather than as breaches of the host States' sovereignty, see:</seg>
  <author>A. Bonfanti</author>, <title level="m">Imprese multinazionali, diritti umani e ambiente. Profili di diritto internazionale pubblico e privato</title>,
  <pubPlace>Milano</pubPlace>, <date type="publication" when="2012">2012</date>, <biblScope unit="page">136</biblScope>.
</bibl>
```

This is the **trailing comment** example. It combines an `<authority>` (a court, not a
person), a `<title type="caseName">`, and a `<quote>` — with two separate
`<seg type="citationContext">` spans, since the signal phrase and the phrase
introducing the quotation are two distinct devices. The closing "See infra, section
3.2." points to a section of the *citing* article itself, not to another footnote or
work, so it falls outside the `<ref>` vocabulary documented above and is left as plain
text:

![Trailing comment](img/refseg-trailing-comment.png)

```xml
<bibl><label>9</label> <seg type="citationContext">See e.g.:</seg>
  <authority type="court">Inter-American Court of Human Rights</authority>,
  <date type="decision" when="2020-02-16">judgment of 16 February 2020</date>,
  <title level="a" type="caseName">Indigenous Communities of the Lhaka Honhat (Our Land) Association v. Argentina</title>,
  <citedRange unit="number">par. 254</citedRange>,
  <seg type="citationContext">quoting the amicus curiae intervention of the former UN Special Rapporteur on the Right to Food, De Schutter:</seg>
  <quote>«Many indigenous peoples understand the right to adequate food as a collective right. They often see subsistence activities such as hunting, fishing and gathering as essential not only to their right to food, but to nurturing their cultures, languages, social life and identity».</quote>
  The cultural value of food is recognized – with respect to indigenous peoples in particular – also under
  art. 27 of the International Covenant on Civil and Political Rights (ICCPR). See infra, section 3.2.
</bibl>
```

This is the **court decisions** example:

![Court decisions](img/refseg-court-decisions.png)

```xml
<bibl><label>6</label> <seg type="citationContext">See, ex multis:</seg>
  <authority type="court">African Commission on Human and Peoples Rights</authority>,
  <date type="decision" when="2001-10-27">decision of 27 October 2001</date>,
  <title level="a" type="caseName">Social and Economic Rights Action Center (SERAC) and Center for Economic and Social Rights (CESR) v. Nigeria</title>;
</bibl>
<bibl>
  <authority type="court">Inter-American Court of Human Rights</authority>,
  <date type="decision" when="2012-06-27">judgment of 27 June 2012</date>,
  <title level="a" type="caseName">Case of the Kichwa Indigenous People of Sarayaku v. Ecuador</title>.
</bibl>
```

(All five annotations above validate against `schema/grobid.training.references.rng`.)

## Worked example: the full annotation pipeline

The example below is meant to show how one passage of body text and its footnotes 
move through all three models in sequence, from raw PDF text to a fully annotated 
citation — including a backward-pointing reference (`supra`) *and* a 
forward-pointing one (`infra`).

The passage of body text reads:

> Comparative criminology has increasingly examined the transnational transfer of legal
> concepts.<sup>8</sup>. [...] This same methodological caution applies with particular force
> to law-and-development scholarship.<sup>19</sup>

Footnote 8 gives a full citation that footnote 19 later cites back to with `supra`.
Footnote 19 is the composite footnote itself — several citations joined by signal
phrases and a quotation, with a `supra` back-reference to note 8 and an `infra`
forward-reference to note 24. Footnote 24, quoted only in part below, is what that
forward reference points to.

### Stage 1: document segmentation model

At this stage the footnote text is not yet split into individual citations — each
footnote is simply wrapped in its own `<listBibl>` as raw text, exactly as extracted
from the PDF:

```xml
<body>
  Comparative criminology has increasingly examined the transnational transfer of
  legal concepts.<lb/>8 [...] This same methodological caution applies with particular
  force to law-and-development scholarship.<lb/>19
</body>

<listBibl>
8 Günther Kaiser, Kriminologie: Ein Lehrbuch (3d ed. 1996).<lb/>
</listBibl>

<listBibl>
19 See, e.g., Neil J. Smelser, Theory of Collective Behavior 175-76 (1962). On<lb/>
criminology, see Kaiser, supra note 8, at 89, as well as Blazicek &amp; Janeksela, Some<lb/>
Comments on Comparative Methodologies in Criminal Justice, 6 Int'l J. Comp. &amp; Applied<lb/>
Crim. Just. 233, 240 (1978). The uncritical transfer of such concepts to countries of<lb/>
the Third World has proven especially dangerous, as discussed further infra note 24.<lb/>
Commentators reached the following conclusion: "The U.S. law and development movement<lb/>
was largely a parochial expression of the American legal style." John Henry Merryman,<lb/>
Comparative Law and Social Change: On the Origins, Style, Decline and Revival of the<lb/>
Law and Development Movement, 25 Am. J. Comp. L. 457, 479 (1977).<lb/>
</listBibl>

<listBibl>
24 Elena Vargas, Law and Development Reconsidered 112-14 (2005) (arguing that the<lb/>
movement's failures reflected its parochial assumptions rather than any flaw in its<lb/>
underlying goals).<lb/>
</listBibl>
```

### Stage 2: reference segmentation model

The reference segmenter splits the raw footnote text into `<label>` + `<bibl>` pairs —
one `<bibl>` per footnote, or per individual citation for a footnote that (like note
19) bundles several. Nothing inside a `<bibl>` is parsed yet:

```xml
<listBibl>
  <bibl><label>8</label> Günther Kaiser, Kriminologie: Ein Lehrbuch (3d ed. 1996). </bibl>

  <bibl><label>19</label> See, e.g., Neil J. Smelser, Theory of Collective Behavior 175-76 (1962). </bibl>
  <bibl>On criminology, see Kaiser, supra note 8, at 89, as well as </bibl>
  <bibl>Blazicek &amp; Janeksela, Some Comments on Comparative Methodologies in Criminal Justice, 6 Int'l J. Comp. &amp; Applied Crim. Just. 233, 240 (1978). </bibl>
  <bibl>The uncritical transfer of such concepts to countries of the Third World has proven especially dangerous, as discussed further infra note 24. Commentators reached the following conclusion: "The U.S. law and development movement was largely a parochial expression of the American legal style." John Henry Merryman, Comparative Law and Social Change: On the Origins, Style, Decline and Revival of the Law and Development Movement, 25 Am. J. Comp. L. 457, 479 (1977).</bibl>

  <bibl><label>24</label> Elena Vargas, Law and Development Reconsidered 112-14 (2005) (arguing that the movement's failures reflected its parochial assumptions rather than any flaw in its underlying goals).</bibl>
</listBibl>
```

### Stage 3: citation (`references`) model

Finally, the `references` model labels the internal structure of each `<bibl>` —
authors, titles, extents, pinpoints, signal phrases, the quotation, and both anaphoric
references:

```xml
<listBibl>
  <bibl><label>8</label> <author>Günther Kaiser</author>, <title level="m">Kriminologie: Ein Lehrbuch</title>
    <edition n="3">3d ed.</edition> (<date type="publication" when="1996">1996</date>).
  </bibl>

  <bibl><label>19</label> <seg type="citationContext">See, e.g.,</seg>
    <author>Neil J. Smelser</author>, <title level="m">Theory of Collective Behavior</title>
    <biblScope unit="page" from="175" to="176">175-76</biblScope>
    (<date type="publication" when="1962">1962</date>).
  </bibl>
  <bibl><seg type="citationContext">On criminology, see</seg>
    <author>Kaiser</author>, <ref type="precedingWork">supra</ref> <ref type="footnote" n="8">note 8</ref>,
    <biblScope unit="page" from="89" to="89">89</biblScope>, as well as
  </bibl>
  <bibl>
    <author>Blazicek</author> &amp; <author>Janeksela</author>,
    <title level="a">Some Comments on Comparative Methodologies in Criminal Justice</title>,
    <biblScope unit="volume">6</biblScope>
    <title level="j">Int'l J. Comp. &amp; Applied Crim. Just.</title>
    <biblScope unit="page" from="233" to="233">233</biblScope>,
    <citedRange unit="page">240</citedRange>
    (<date type="publication" when="1978">1978</date>).
  </bibl>
  <bibl>
    <seg type="citationContext">The uncritical transfer of such concepts to countries of the Third World has proven especially dangerous, as discussed further</seg>
    <ref type="subsequentWork">infra</ref> <ref type="footnote" n="24">note 24</ref>.
    <seg type="citationContext">Commentators reached the following conclusion:</seg>
    <quote>The U.S. law and development movement was largely a parochial expression of the American legal style.</quote>
    <author>John Henry Merryman</author>,
    <title level="a">Comparative Law and Social Change: On the Origins, Style, Decline and Revival of the Law and Development Movement</title>,
    <biblScope unit="volume">25</biblScope>
    <title level="j">Am. J. Comp. L.</title>
    <biblScope unit="page">457</biblScope>
    <citedRange unit="page">479</citedRange>
    (<date type="publication" when="1977">1977</date>).
  </bibl>

  <bibl><label>24</label> <author>Elena Vargas</author>, <title level="m">Law and Development Reconsidered</title>
    <biblScope unit="page" from="112" to="114">112-14</biblScope>
    (<date type="publication" when="2005">2005</date>)
    (arguing that the movement's failures reflected its parochial assumptions rather than any flaw in its underlying goals).
  </bibl>
</listBibl>
```