# Proposal: Annotating Footnote-Based Bibliographic Citation in Legal and Humanities Scholarship

| | |
| --- | --- |
| **Status** | Draft proposal for discussion on the TEI mailing list |
| **Origin** | GROBID footnote-flavour project — [mpilhlt/grobid-footnote-flavour#41](https://github.com/mpilhlt/grobid-footnote-flavour/issues/41) |

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used as in
RFC 2119.

Authors:
- Christian Boulanger, Max Planck Institute for Legal History and Legal Theory
- Luca Foppiano, ScenciaLAB
- Daniel Fejzo, Max Planck Institute for Legal History and Legal Theory

(The proposal was written with the help of Claude Sonnet 5)

---

## 1. Motivation and scope

We are building training data for [GROBID](https://github.com/kermitt2/grobid)-style
sequence-labeling models that extract bibliographic references from scholarly text. Our
corpus is legal scholarship and the humanities disciplines that share its citation culture
(history, philology, area studies) — genres in which the citation apparatus lives almost
entirely in **footnotes**, and in which footnotes routinely do things that citation
markup for citation apparatus at the end of a text does not have to do:

- cite courts and legislatures as the "author" of a work (`EuGH, Urt. v. 8.9.2016 – …`);
- point into a work at a level below the page — a statute section, a marginal number
  (*Randnummer*), a recital — rather than, or in addition to, a page;
- refer elliptically to a citation given earlier in the same footnote apparatus
  (`id.`, `op. cit.`, `a.a.O.`, `ibid.`, *supra*, *infra*, "N. 22", "above") rather than
  repeating it;
- embed citations inside argumentative prose, introduced by a citation signal
  (`see`, `cf.`, `vgl.`, `contra`, `siehe auch`) whose polarity and force is itself a
  meaningful research signal for citation-context analysis.

**Our aim is deliberately narrow: an annotation ontology sufficient to train a footnote
citation-extraction model, not a scheme for the complete semantic markup of a legal
document.** Resolving citations to norm/case databases, or marking up the cited
norms and judgments themselves, is the job of standards such as Akoma Ntoso/LegalDocML
(see §2.5) — we do not attempt to duplicate that. At the same time, the vocabulary
proposed here is chosen so that it remains valid and useful under a *fuller*
annotation of the same footnote (e.g. with `@key`/`@ref` resolution hooks, nested
`<orgName>` inside `<authority>`, or additional pinpoint units) — none of the choices
below is a training-data shortcut that a richer annotation would have to undo.

Everything proposed is (a) plain TEI P5, (b) TEI element/attribute *vocabulary* borrowed
from a citation-vocabulary standard (chiefly CSL 1.0.2 and Zotero, which are the most
likely crosswalk targets for a resolved citation), or (c) two narrowly scoped extensions
to the TEI content model, listed in Part A. We ask the list's guidance particularly on
Part A and on the open naming questions in §6.

## 2. Prior art

### 2.1 TEI P5 core

`<biblScope>` and `<citedRange>` are both members of `att.citing` and both valid
directly inside `<bibl>`. The Guidelines distinguish them by meaning: `<biblScope>`
"defines the scope of a bibliographic reference … a named subdivision of a larger
work" (the cited work's *own* extent — its volume, issue, first page); `<citedRange>`
"defines the range of cited content" (the specific place inside it being pointed at).
`@unit` is an open list; the Guidelines *suggest* `volume, issue, page, line, chapter,
part, column, entry` but do not close it.

### 2.2 EpiDoc

EpiDoc's bibliography guidance uses `<biblScope>` for a work's own extent and
`<citedRange>` for the pinpoint into it, with an **extended, open `@unit` list** beyond
the TEI suggestions
(<https://epidoc.stoa.org/gl/latest/supp-bibliography.html>). This is the precedent for
extending `@unit` with domain tokens rather than treating the list as closed.

### 2.3 CSL 1.0.2 / Zotero

CSL defines legal item types (`legal_case`, `legislation`, `treaty`, `regulation`) and
legal variables. Two are directly relevant here:

| Concept | CSL variable | Zotero field |
| --- | --- | --- |
| court / issuing body | `authority` | `court` |
| case name | `title` | `caseName` |

`authority` is the standard citation-vocabulary term for "the institution responsible
for a work," covering courts, legislatures, and regulators alike — precisely the role
TEI's own `<authority>` element already describes.

### 2.4 ECLI / CELEX

ECLI (European Case Law Identifier) and CELEX (EU legal-act identifier) are official
identifier schemes; both belong in `<idno type="…">`. No universal identifier exists for
most non-EU case law, where the docket number (*Aktenzeichen*) is the de-facto key.

### 2.5 Akoma Ntoso / LegalDocML

The OASIS standard for marking up the norms and judgments *themselves* (FRBR-based
URIs, `<ref href="…">`, `<rref>`), not bibliographic citation strings embedded in
scholarly prose. Out of scope here, but its Naming Convention URIs are a good target for
an optional `@ref` on the elements below once resolution is attempted.

## 3. Design principles

1. Prefer standard TEI elements; prefer standard attribute *values* — TEI, then CSL,
   then ECLI/CELEX — over inventing new ones. Invent only where no standard token
   exists, and say so explicitly (§7).
2. Every label must be recoverable from a single, comparatively short span of running
   text — footnote citation strings are dense and mix several such spans in one
   sentence.
3. Structural punctuation that is part of a citation marker (`§`, `Tz.`, `Rn.`) stays
   inside its semantic element, alongside the value it marks, so the two are never split.
4. Keep the distinction between a work's *own* extent (`<biblScope>`) and the *pinpoint*
   into it (`<citedRange>`) — this single distinction resolves most of what is otherwise
   ambiguous in legal and humanities pinpoint citations (§5.2).

---

## Part A — Proposals requiring a change to the TEI Guidelines

Both proposals concern a single element, `<authority>`, and were checked against the
current Guidelines (`ref-authority.html`, `ref-bibl.html`, `ref-model.biblPart.html`):
`<authority>` today is declared only inside `model.publicationStmtPart.agency`, valid
solely as a child of `<publicationStmt>` or `<monogr>`; it carries `att.global` and
`att.canonical` but **not** `att.typed`; and it is **not** reachable from `<bibl>`,
because `model.imprintPart` (the sub-class of `model.biblPart` that supplies `<bibl>`'s
imprint-like children) currently lists only `biblScope`, `distributor`, `pubPlace`, and
`publisher`.

### Proposal 1 — Add `@type` to `<authority>`

**Problem.** A citation's issuing authority is not always a court: it may be a
legislature, a regulator, an administrative agency, or (outside the legal domain) a
standards body or funding agency. TEI's own mechanism for this kind of sub-classification
is `att.typed`, already used for exactly this purpose on `<bibl>`, `<idno>`, `<title>`,
and `<ref>` — but not on `<authority>`.

**Proposed change.** Add `att.typed` to the attribute-class list of `<authority>`.

**Example.**

```xml
<authority type="court">EuGH</authority>
<authority type="legislature">Deutscher Bundestag</authority>
```

**Impact.** Purely additive (a new optional attribute); no existing document is
affected.

### Proposal 2 — Permit `<authority>` in loosely structured bibliographic citations

**Problem.** `<authority>` — "the name of a person or other agency responsible for
making [a] work available" — is exactly the CSL `authority` / Zotero `court` concept,
and reads naturally as an imprint-like part of a citation. But it is currently
unreachable from `<bibl>`, `<biblStruct>`, or any other consumer of `model.biblPart`,
forcing projects that need it to reuse `<author>` (semantically wrong — a court is an
institution, not a person) or `<orgName>` (semantically weaker — it names *any*
organisation, with no notion of "the agency responsible for this work").

**Proposed change.** Add `<authority>` to `model.imprintPart`, alongside `<biblScope>`,
`<distributor>`, `<pubPlace>`, and `<publisher>`. Because `model.imprintPart` already
feeds `model.biblPart`, this single class-membership change makes `<authority>` valid
in `<bibl>`, `<biblStruct>`, and `<monogr>` without further customization, and without
special-casing `<bibl>`.

*Alternative considered:* adding `model.publicationStmtPart.agency` itself to `<bibl>`'s
content model. We prefer the `model.imprintPart` route because it is the smaller,
single-class change and keeps `<authority>` grouped with the other imprint-like parts
it is used alongside in practice.

**Example.**

```xml
<bibl type="decision">
  <authority type="court">EuGH</authority>,
  <date type="decision" when="2016-09-08">Urt. v. 8.9.2016</date> –
  <idno type="docket">C-160/15</idno>, …
</bibl>
```

**Impact.** Purely additive (a new option in an open-content class); no existing
document is affected.

---

## Part B — Domain-specific refinements (no TEI change needed)

Everything below already validates against stock TEI P5 (given Part A). It is the
annotation *convention* we ask the list to review and, where useful, adopt as informal
precedent for other citation-heavy corpora.

### B1. Genre of the cited work

```
<bibl type="legislation">   <bibl type="decision">
```

`legislation` is the exact CSL item-type name. `decision` is project vocabulary (CSL's
own term, `legal_case`, was judged to read awkwardly as an XML token); we mark it as an
open question (§7).

### B2. Pinpoint vs. container extent

`<biblScope>` carries the cited work's *own* extent (reporter volume/issue/page,
publication year). `<citedRange>` carries the *pinpoint* into it — whatever level of
granularity the citing text actually names. If a work has no pagination at all (a
decision cited only by marginal number, say), there is simply no `<biblScope
unit="page">` — only `<citedRange>`.

Recommended, extended `@unit` vocabulary (open list, per EpiDoc precedent):

| `@unit` | Matches | Source |
| --- | --- | --- |
| `section` | `§ 19a`, `Art. 5`, `Sec. 2` | exact CSL variable |
| `sub-section` | `Abs. 2` | project vocabulary |
| `sentence` | `S. 1`, `Satz 1` | project vocabulary |
| `number` | `Nr. 3` | TEI-suggested / CSL variable |
| `letter` | `lit. b`, `Buchst. b` | project vocabulary |
| `margin` | `Tz. 24`, `Rn. 20`, `Rdnr. 7` | project vocabulary |
| `recital` | `ErwGr. 21` (EU recitals) | project vocabulary |
| `page` | an in-text pinpoint page, e.g. the `(240)` in `233 (240)` | TEI-suggested |

`from`/`to`/`n` on `<citedRange>` and the `n`/`target` attributes used below on `<ref>`
are all **optional** in training annotation and are not required for a span to be
useful gold data; they are typically filled in during post-processing, once the
surrounding citation is resolved.

### B3. The issuing authority

```xml
<authority type="court">EuGH</authority>
```

once Part A lands. Until then, `<orgName type="court">` remains valid TEI and is a
reasonable fallback for schemas that cannot adopt Proposal 2. `<orgName>` **MAY** still
be used *inside* `<authority>` to decompose a compound institutional name, e.g. a court
plus its deciding panel — that finer structuring is itself a domain-specific
refinement, not required for baseline annotation:

```xml
<authority type="court"><orgName>Oberlandesgericht Frankfurt am Main</orgName>, 5. Zivilsenat</authority>
```

### B4. Docket and official identifiers

```xml
<idno type="docket">C-160/15</idno>
<idno type="ECLI">ECLI:EU:C:2016:644</idno>
<idno type="CELEX">…</idno>
```

### B5. Case short-name

```xml
<title level="a" type="caseName">GS Media/Sanoma</title>
```

(`caseName` is the exact Zotero field name.) Tagging the short-name explicitly, rather
than leaving it as trailing free text, is what stops a segmentation model from treating
`– GS Media/Sanoma` as the start of a new reference.

### B6. Statute short-title

```xml
<title level="m" type="legislation" key="UrhG">UrhG</title>
```

### B7. Intra-footnote anaphoric reference (new)

Legal and humanities footnotes constantly avoid repeating a citation just given,
using devices such as *id.*, *op. cit.*, *ibid.*, *a.a.O.*, *ders.*, *supra*, *infra*,
"above," "N. 22." These devices point either to the **preceding work** cited, to a
**work cited later** in the same discussion, to the **preceding author** without
repeating the work, or explicitly to **another footnote**. `<ref>` is already
`att.typed` in stock TEI, so this needs no schema change — only a controlled, open
`@type` vocabulary:

| `@type` | Meaning | Examples |
| --- | --- | --- |
| `preceedingWork` | the work just cited | *supra*, *above*, `id.`, `op. cit.`, `a.a.O.` |
| `subsequentWork` | a work cited later | *infra*, *below* |
| `preceedingAuthor` | the author just named, work unspecified | `ders.`, `idem` |
| `footnote` | an explicit cross-reference to another footnote, carrying `@n` | `n. 7`, `N. 22`, "oben N. 22" |

(This list is intentionally open — see §7.1.)

```xml
<bibl><author>Vogel</author>, <ref type="preceedingWork">id.</ref>,
  <citedRange unit="page" from="79" to="79">p. 79</citedRange></bibl>

<bibl><author>Vogel</author>, <ref type="preceedingWork">op. cit.</ref>,
  <ref type="footnote" n="7">n. 7</ref>,
  <citedRange unit="page" from="80" to="81">pp. 80–1.</citedRange></bibl>

<bibl><ref type="preceedingAuthor">Ders.</ref>, <ref type="preceedingWork">a.a.O.</ref>,
  <citedRange unit="page" from="123" to="123">S. 123</citedRange>.</bibl>

<bibl><author>Carbonnier</author> (<ref type="footnote">vorige N.</ref>),
  <ref type="preceedingWork">a.a.O.</ref>.</bibl>
```

(All four follow a consistent convention for the enclosing parenthesis — kept as plain
text outside the `<ref>`, matching how the em-dash before a docket or case name is
handled in B5/B4.)

### B8. Citation-signal phrases (new)

Phrases that introduce a citation with an evaluative or directional stance —
`see`, `see also`, `cf.`, `contra`, `vgl.`, `anderer Ansicht`, `for a comprehensive
overview … see` — carry citation-context information (agreement, contrast, further
reading) that is valuable for citation-context-analysis research and is lost if the
phrase is dropped as unlabeled prose. `<note>` is too broad a label for this (it says
nothing about the phrase's function and is not anchored to the citation it
introduces). We propose `<seg type="citationContext">`, again needing no schema change:

```xml
<seg type="citationContext">For further analysis of the marriage contract, see</seg>
<author>K. O'Donovan</author>, <title level="m">Family Matters</title>
(<date type="publication" when="1993">1993</date>), especially
<citedRange unit="page" from="43" to="59">43–59</citedRange>.

<seg type="citationContext">Zur höheren Wahrscheinlichkeit der Normierung von Verhalten
in weniger komplexen Beziehungen vgl. die Konflikttheorie von</seg>
<author>Gessner</author> <date type="publication">1976</date>, insbesondere
<citedRange unit="page" from="170" to="183">S. 170—183</citedRange>.
```

`<seg type="citationContext">` marks only the signal phrase itself, not the citation
that follows it; the two remain siblings, which keeps the signal reusable regardless of
how many citations follow it (see the worked example in §5.3, where one signal
introduces two citations).

---

## 5. Worked examples

### 5.1 Statute and court-decision citations

```xml
<bibl type="legislation">
  <citedRange unit="section">§ 19a</citedRange>
  <citedRange unit="sub-section">Abs. 2</citedRange>
  <title level="m" type="legislation" key="UrhG">UrhG</title>
</bibl>
```

```xml
<bibl type="decision">
  <authority type="court">EuGH</authority>,
  <date type="decision" when="2016-09-08">Urt. v. 8.9.2016</date> –
  <idno type="docket">C-160/15</idno>,
  <idno type="ECLI">ECLI:EU:C:2016:644</idno>,
  <title level="j">GRUR</title> <date>2016</date>,
  <biblScope unit="page">1152</biblScope>
  <citedRange unit="margin">Tz. 24</citedRange> –
  <title level="a" type="caseName">GS Media/Sanoma</title>
</bibl>
```

### 5.2 Anaphoric footnote references and signal phrases

See B7 and B8 above.

### 5.3 A composite footnote

The following footnote combines a footnote-number label, a
short elliptical citation, an explicit back-reference to another footnote, a
multi-work citation joined by a signal phrase, general prose, and a citation
supporting a direct quotation — every device introduced in this proposal, in one
paragraph:

> 30 Dazu etwa Smelser 175 f. — Für die Kriminologie siehe Kaiser (oben N. 22) 89 sowie
> Blazicek/Janeksela, Some Comments on Comparative Methodologies in Criminal Justice,
> Int. J. Crim. Pen 6 (1978) 233 (240). Als besonders gefährlich hat sich die
> unkritische Übertragung solcher Konzepte auf Länder der Dritten Welt erwiesen. So kam
> man etwa zu dem Ergebnis: „The U. S. law and development movement was largely a
> parochial expression of the American legal style", Merryman, Comparative Law and
> Social Change - On the Origins, Style, Decline and Revival of the Law and Development
> Movement, Am. J. Comp. L. 25 (1977) 457 (479).

```xml
<bibl>
  <label>30</label>
  <seg type="citationContext">Dazu etwa</seg>
  <author>Smelser</author>
    <biblScope unit="page" from="175" to="176">175 f.</biblScope>
</bibl>
 — <seg type="citationContext">Für die Kriminologie siehe</seg>
<bibl>
  <author>Kaiser</author>
  (<ref type="preceedingWork">oben</ref> <ref type="footnote" n="22">N. 22</ref>)
  <biblScope unit="page" from="89" to="89">89</biblScope>
</bibl>
 sowie
<bibl>
  <author>Blazicek</author>/<author>Janeksela</author>,
  <title level="a">Some Comments on Comparative Methodologies in Criminal Justice</title>,
  <title level="j">Int. J. Crim. Pen</title>
  <biblScope unit="volume">6</biblScope>
  (<date type="publication" when="1978">1978</date>)
  <biblScope unit="page">233</biblScope>
  <citedRange unit="page">(240)</citedRange>.
</bibl>
<seg type="citationContext">Als besonders gefährlich hat sich die unkritische Übertragung solcher Konzepte auf Länder der Dritten Welt erwiesen. So kam man etwa zu dem Ergebnis:</seg>
<bibl>
  <quote>„The U. S. law and development movement was largely a parochial     expression of the American legal style"</quote>,
  <author>Merryman</author>,
  <title level="a">Comparative Law and Social Change - On the Origins, Style, Decline and Revival of the Law and Development Movement</title>,
  <title level="j">Am. J. Comp. L.</title> <biblScope unit="volume">25</biblScope>
  (<date type="publication" when="1977">1977</date>)
  <biblScope unit="page">457</biblScope>
  <citedRange unit="page">(479)</citedRange>.</bibl>
</bibl>
```

Notes on choices made in this annotation:

- `Kaiser (oben N. 22) 89` splits *oben* (`preceedingWork`) from *N. 22*
  (`footnote`, `@n="22"`) rather than fusing them into one `<ref>`, for the same reason
  `op. cit.` and `n. 7` are split in B7's second example: they are two distinct
  lexical devices that happen to sit next to each other, not a single fixed phrase.
- `<quote>` needs no schema change — it is already a member of `model.biblPart` and
  therefore already valid as a child of `<bibl>`; using it to pair a direct quotation
  with the `<bibl>` that supports it is existing, if underused, TEI practice.
- `233 (240)` and `457 (479)` are the classic law-review pattern of *first page
  (pinpoint page)*; `<citedRange unit="page">` is precisely CSL/TEI's suggested `page`
  unit used at the pinpoint level rather than the container level, and is the
  motivating case for keeping `page` as a legal `@unit` value on `<citedRange>` and not
  only on `<biblScope>`.

## 6. Conformance note

| Name | Status |
| --- | --- |
| `<bibl>`, `<title>`, `<authority>`, `<idno>`, `<biblScope>`, `<citedRange>`, `<date>`, `<label>`, `<quote>`, `<seg>`, `<ref>` | Standard TEI P5 elements |
| `@type` on `<authority>`; `<authority>` in `model.imprintPart` | **Proposed TEI change (Part A)** |
| `@type`, `@level`, `@unit`, `@from`, `@to`, `@when`, `@key`, `@ref`, `@n` | Standard TEI P5 attributes (`att.typed`, `att.citing`, `att.canonical`, `att.datable`, `att.pointing`); `@level` uses the closed TEI list, the rest are open datatypes |
| `bibl/@type = legislation` | Borrowed from CSL 1.0.2 |
| `bibl/@type = decision` | Project vocabulary (CSL equivalent: `legal_case`) — open question, §7 |
| `citedRange/@unit = section, number, page` | Aligned with CSL variables / the TEI-suggested `@unit` list |
| `citedRange/@unit = sub-section, sentence, letter, margin, recital` | Project vocabulary (open datatype; EpiDoc precedent for extending `@unit`) |
| `authority/@type = court` | Project vocabulary; concept = CSL `authority` |
| `idno/@type = docket` | Project vocabulary; concept = CSL `number` (docket sense) |
| `idno/@type = ECLI, CELEX` | Official external identifier schemes (EU) |
| `title/@type = legislation` | Project vocabulary, mirrors `bibl/@type` |
| `title/@type = caseName` | Borrowed from the Zotero field name |
| `ref/@type = preceedingWork, subsequentWork, preceedingAuthor, footnote` | Project vocabulary — open question, §7 |
| `seg/@type = citationContext` | Project vocabulary |

No TEI-published taxonomy exists for `bibl/@type`, `idno/@type`, `ref/@type`, `seg/@type`,
or an exhaustive `citedRange/@unit` list, so project-defined values in these open
attributes are expected by the standard, not a deviation from it.

## 7. Open questions for the list

1. **§B1** — `<bibl type="decision">` vs `<bibl type="legal_case">` (exact CSL parity vs.
   XML readability).
2. **§B7** — is `preceedingWork` / `subsequentWork` / `preceedingAuthor` the right
   three-way split, and is there a better-established term for any of them (e.g. from
   existing legal-citation-standard XML vocabularies, if any list members know of one)?
   We adopted these spellings for symmetry with each other rather than because they are
   attested elsewhere, and would gladly defer to prior art if it exists.
3. **§Part A** — is extending `model.imprintPart` the right place for `<authority>`, or
   would the list prefer it to remain reachable only via a broader
   `model.publicationStmtPart.agency`-in-`<bibl>` change (with a wider blast radius, but
   arguably a more semantically direct one)?
4. **§B2/§B7** — most examples here are German- and English-language; the maintainers
   would value pointers to how other footnote-heavy citation cultures (French *op.
   cit.* practice, Romance-language *idem*, Nordic legal citation) already handle these
   devices, to keep the open lists in §B2 and §B7 genuinely cross-linguistic rather than
   Germanic-centric.
5. **§B8** — should citation-signal *polarity* (supportive `see` vs. contrastive `cf.`/
   `contra`) be a further `@type` refinement on `<seg type="citationContext">`, or is
   that better left to downstream classification once the phrase itself is
   segmented out?

## 8. References

- GROBID footnote-flavour, issue #41 —
  <https://github.com/mpilhlt/grobid-footnote-flavour/issues/41>
- TEI P5 Guidelines — `<authority>`, `<bibl>`, `model.biblPart`, `model.imprintPart`,
  `att.citing` (`<biblScope>`, `<citedRange>`), `att.typed`, `att.canonical`.
- EpiDoc Guidelines, "Encoding the Bibliography" —
  <https://epidoc.stoa.org/gl/latest/supp-bibliography.html>
- Citation Style Language 1.0.2 specification — legal item types and variables.
  <https://docs.citationstyles.org/en/stable/specification.html>
- European Case Law Identifier (ECLI) — EU Council conclusions 2011.
  <https://e-justice.europa.eu/topics/legislation-and-case-law/european-case-law-identifier-ecli-search-engine_en>
- Akoma Ntoso / OASIS LegalDocML —
  <https://docs.oasis-open.org/legaldocml/akn-core/v1.0/akn-core-v1.0-part1-vocabulary.html>
- Foppiano & Boulanger, "Digging Up Citations: FOSSIL …" —
  <https://arxiv.org/abs/2606.01109> (context for this work)
