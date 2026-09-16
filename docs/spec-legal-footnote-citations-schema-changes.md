# Specification: Schema changes to align `schema/` with the TEI footnote-citation proposal

| | |
| --- | --- |
| **Status** | Draft |
| **Issue** | [mpilhlt/grobid-footnote-flavour#41](https://github.com/mpilhlt/grobid-footnote-flavour/issues/41) |
| **Source proposal** | `docs/tei-proposal-legal-footnote-citations.md` |
| **Predecessor** | `docs/spec-legal-references.md` (#41, round 1 — implemented in commit `38c7114`) |
| **Affects** | `schema/grobid.training.references.rng` (all changes below) |
| **Not affected** | `schema/grobid.training.references.referenceSegmenter.rng`, `schema/shared/bibl-struct.rng`, `schema/shared/common-elements.rng`, `schema/grobid.training.segmentation.rng` |

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used as in
RFC 2119.

---

## 1. Method

This spec audits `docs/tei-proposal-legal-footnote-citations.md` (Parts A and B, and the
worked examples in §5) item by item against the current `schema/*.rng`, and proposes the
concrete RNG changes needed to close each gap. For every affected value, the existing
corpus (`batches/**/*.training.references.tei.xml`, 30 files) was checked so the
recommendation accounts for real migration cost:

```
bibl/@type                 -> 0 files use it
orgName/@type=court         -> 0 files use it
orgName/@type=jurisdiction  -> 0 files use it
ref/@type (any value)       -> 0 files use it
seg (any)                    -> 0 files use it
quote                       -> 0 files use it
authority                   -> 0 files (element doesn't exist in schema yet)
```

None of the elements/values this spec touches are used anywhere in the existing training
corpus yet. Round 1 (#41) landed the *schema*, but no batch has been (re-)annotated
against it. Author decision: existing documents **will** be re-annotated regardless, so
this spec optimizes for the semantically correct target vocabulary rather than for
minimizing churn against what's already there — see §3.

Every proposed diff (§5) was written into a scratch copy of `schema/` and verified:
`scripts/build-schema.py` flattens it with no duplicate-`<define>` errors, `jing`
validates all 30 existing `*.training.references.tei.xml` files against it with no new
failures (one pre-existing, unrelated `xml:space` failure affects the same file before
*and* after this change — see §6), and a hand-built encoding of the proposal's final
§5.1 and §5.3 examples validates cleanly. Negative controls confirm the schema actually
enforces the changes: `<ref type="anaphoric">` (the old value) and
`<orgName type="court">` (the value `<authority>` now supersedes) both correctly fail
against the patched schema; run against the *original*, unpatched schema, the corrected
§5.3 example fails on exactly the vocabulary/element gaps identified below and nothing
else (§6) — confirming there is no additional structural gap hiding beyond §4.1-4.3.

## 2. Already conforms — no change needed

These proposal items were implemented in round 1 and match the new proposal exactly:

| Proposal § | Concept | Current schema |
| --- | --- | --- |
| B1 | `<bibl type="legislation">` / `<bibl type="decision">` | `bibl`'s `@type` choice, `grobid.training.references.rng:60-77` |
| B2 | `<citedRange unit="…">` pinpoint vs. `<biblScope>` container extent | `references_citedRange`, same file, identical 8-value `@unit` list (`section`, `subSection`, `sentence`, `number`, `letter`, `margin`, `recital`, `page`) |
| B4 | `<idno type="docket">` / `<idno type="ECLI">` / `<idno type="CELEX">` | `references_idno` |
| B5 | `<title level="a" type="caseName">` | `references_title` |
| B6 | `<title level="m" type="legislation" key="…">` | `references_title` |

No action needed on any of these.

## 3. Part A / B3 — adopt `<authority>` now

**Revised from an earlier draft of this spec.** The first pass recommended keeping the
`<orgName type="court">` fallback and deferring `<authority>` until the TEI Maintenance
Committee accepts Part A, reasoning that a brand-new element is a materially bigger
GROBID CRF training cost than a new attribute value on an element the model already
predicts (`<orgName>` already carries `institution`/`collaboration`/`department`/
`laboratory`). **Overridden by author decision: adopt `<authority>` authoritatively now,
independent of the upstream TEI outcome; existing documents will be re-annotated.**
Since nothing in the current corpus uses `orgName@type="court"` yet (§1), there is in
any case no existing gold data to relabel — the migration-cost argument no longer
applies, only the training-cost-of-a-new-label-class one, which the author has decided
to accept.

This repository's schema is a self-contained GROBID-flavour grammar, not a subset of the
TEI Guidelines' own schema — it does not need Part A to be accepted upstream (or even
submitted) before defining a local `<authority>` element; Part A only concerns what the
*official* TEI Guidelines permit.

**Scope of the local `<authority>` element:**

- `@type`: `court` (Proposal 1's first example) and `legislature` (Proposal 1's second
  example) — both attested in the proposal text; open to extension the same way every
  other `@type` list in this schema is.
- `@key`: optional resolvable short key (mirrors `references_title`'s `@key`, and the
  `att.canonical` hook the proposal's §6 conformance table already lists as standard).
- Content: text, interleaved with zero or more nested `<orgName>` — per proposal §B3,
  "`<orgName>` **MAY** still be used *inside* `<authority>` to decompose a compound
  institutional name, e.g. a court plus its deciding panel."

**Consequence for `<orgName>`:** drop `court` from `orgName`'s `@type` enumeration (now
superseded by `<authority type="court">`). Leave `jurisdiction` untouched — it is not
part of the TEI proposal at all (the proposal never mentions it) and is out of scope for
this round; `institution`/`collaboration`/`department`/`laboratory` are unaffected
(pre-existing, in active corpus use for non-authority purposes such as thesis/
report institutional authorship).

## 4. Gaps requiring a schema change

### 4.1 `<ref>` — anaphoric-device vocabulary (proposal §B7)

**Current** (`references_ref`, `grobid.training.references.rng:425-446`): a two-way
`anaphoric` / `cataphoric` split, with only `@target`.

**Proposal:** a four-way split — `precedingWork`, `subsequentWork`, `precedingAuthor`,
`footnote` (carrying `@n`, the footnote number) — because "id."/"op. cit." (points at the
*work*), "ders."/"idem" (points at the *author*, work unspecified), and an explicit
cross-reference like "N. 22" (points at a *footnote*, by number) are three distinct
lexical devices that a binary anaphoric/cataphoric split conflates. The proposal's own
worked example (§5.3, `Kaiser (oben N. 22) 89`) deliberately splits *oben* from *N. 22*
into two adjacent `<ref>`s for exactly this reason.

**Recommendation:** adopt the four-way split as spelled in the (now-corrected) proposal:
`precedingWork` / `subsequentWork` / `precedingAuthor` / `footnote`. An earlier draft of
this spec flagged a spelling issue (`preceedingWork`/`preceedingAuthor`, a doubled "e");
that has since been fixed directly in
`docs/tei-proposal-legal-footnote-citations.md`, so schema and proposal now agree.
`@target` is kept (resolved-pointer hook, optional); `@n` is added, scoped to
`type="footnote"` only, following this file's own `references_title` convention of
grouping an attribute combination as a named preset rather than leaving independent
optional attributes that could combine nonsensically (e.g. `n` on a `precedingWork` ref,
which means nothing).

### 4.2 `<seg>` — citation-signal vocabulary rename (proposal §B8)

**Current** (`references_seg`, same file, lines 405-417): `type="signal"`, documented as
"Discourse signal word".

**Proposal:** `type="citationContext"`, and — importantly — scoped to a whole
**introductory phrase** ("For further analysis of the marriage contract, see"), not a
single trigger word.

**Recommendation:** rename the value and broaden the documentation to "phrase" (a pure
rename since the element/attribute shape is unchanged and unused in the corpus — zero
migration cost).

### 4.3 `<quote>` — new element (proposal §5.3, not covered by B1-B8)

Not defined anywhere in `schema/`. Needed to pair a direct quotation from the body text
with the `<bibl>` that supports it — the composite-footnote worked example's closing
citation:

```xml
<bibl><seg type="citationContext">…</seg><quote>„The U. S. law and development movement …"</quote>, <author>Merryman</author>, …</bibl>
```

**Recommendation:** add a minimal local `references_quote` define — text content only, no
attributes (quotation marks and trailing punctuation stay in the source text, matching
how this schema already treats separator punctuation elsewhere, e.g. the `–` before a
docket/case-name per `docs/spec-legal-references.md` §6.1). Scope it to
`grobid.training.references.rng` only (not `referenceSegmenter.rng` or
`segmentation.rng`) — the pattern only appears in fully-annotated `<bibl>` output, per
YAGNI.

### 4.4 Composite footnotes — no structural change needed

**Revised twice from earlier drafts of this spec.** The first draft misread the
proposal's original §5.3 example as requiring `<bibl>` to nest inside `<bibl>` and
recommended a self-reference in `bibl`'s content model. A second draft, after the author
corrected that example to a flat run of sibling `<bibl>` elements with the connecting
prose and `<seg type="citationContext">` as **listBibl-level siblings between them**,
instead recommended widening `listBibl`'s content model to interleave text and `<seg>`
around the existing `oneOrMore(<bibl>)`.

**The author has since revised the example again, and this draft supersedes both.** The
final §5.3 (see `docs/tei-proposal-legal-footnote-citations.md`, which now includes a
"note on this example's shape" explaining the rationale) nests `<seg type="citationContext">`
and `<quote>` **inside** the `<bibl>` they belong to, rather than placing them as
siblings between citations. As the proposal now explains: this is the annotation as it
is actually produced for GROBID's *references* model, whose label set is a flat,
per-`<bibl>` sequence with no notion of a labeled span between two `<bibl>`s — not a
faithful semantic markup of the source text (which would instead treat the connecting
prose and signal phrases as true siblings of the citations they introduce). Keeping the
signal/quote inside the citation's own `<bibl>` also has a practical advantage: it is
always unambiguous which citation a given signal phrase or quotation belongs to. Which
spans of running text join which `<bibl>` is a decision made upstream, by the
referenceSegmenter annotation task that first splits a footnote into `<bibl>` spans —
not by this vocabulary.

**Consequence: no schema change is needed for this pattern beyond §4.1-4.3.** A composite
footnote is just several ordinary sibling `<bibl>` elements — already unconditionally
legal under the existing, unmodified `oneOrMore(<bibl>)` `listBibl` content model — each
carrying its own `<seg>`/`<ref>`/`<quote>`/etc. internally, exactly like a single-citation
footnote's `<bibl>` already does. This was confirmed directly (§6): validating the
proposal's final §5.3 example against the *unpatched* schema produces only the
vocabulary/element errors already identified in §4.1-4.3 (`seg@type`, `ref@type`, `ref@n`,
`quote`) and nothing structural.

## 5. Recommended profile — concrete RNG diff

All changes are in `schema/grobid.training.references.rng`. `text`/`listBibl` is
**unchanged** (see §4.4).

**1. `bibl`'s content-model choice** — add `authority` and `references_quote`:

```diff
             <ref name="label"/>
             <ref name="lb"/>
             <ref name="author"/>
             <ref name="orgName"/>
+            <ref name="authority"/>
             <ref name="references_title"/>
             <ref name="references_date"/>
             <ref name="references_biblScope"/>
             <ref name="references_citedRange"/>
             <ref name="publisher"/>
             <ref name="pubPlace"/>
             <ref name="editor"/>
             <ref name="references_edition"/>
             <ref name="references_ptr"/>
             <ref name="references_idno"/>
             <ref name="references_note"/>
             <ref name="references_seg"/>
             <ref name="references_ref"/>
+            <ref name="references_quote"/>
           </choice>
```

**2. `orgName`** — drop `court` (superseded by `<authority>`); leave everything else
unchanged:

```xml
  <define name="orgName">
    <element name="orgName">
      <a:documentation>Institution for theses or technical reports</a:documentation>
      <optional>
        <attribute name="type">
          <choice>
            <!-- legal (#41), out of scope for this round -->
            <value>jurisdiction</value>
            <!-- pre-existing, in use in batches/**/*.training.references.tei.xml -->
            <value>institution</value>
            <group>
              <a:documentation>Project-based collaboration acting as an author group</a:documentation>
              <value>collaboration</value>
            </group>
            <value>department</value>
            <value>laboratory</value>
          </choice>
        </attribute>
      </optional>
      <text/>
    </element>
  </define>
```

**3. New `authority` define** (placed after `orgName`):

```xml
  <!-- <authority type="…"> names the institution responsible for the
       cited work (CSL `authority` / Zotero `court`): a court, a
       legislature, or (outside the legal domain) a regulator or other
       issuing body. Not <author> (an institution, not a person) and not
       a generic <orgName> (no "responsible for this work" role). @type
       is open-ended; court/legislature are the values attested in
       current legal-citation practice. <orgName> MAY be nested inside to
       decompose a compound institutional name, e.g. a court plus its
       deciding panel. -->
  <define name="authority">
    <element name="authority">
      <a:documentation>Institution responsible for the cited work (court, legislature, regulator).</a:documentation>
      <optional>
        <attribute name="type">
          <choice>
            <group>
              <a:documentation>Court issuing a decision</a:documentation>
              <value>court</value>
            </group>
            <group>
              <a:documentation>Legislature enacting a statute</a:documentation>
              <value>legislature</value>
            </group>
          </choice>
        </attribute>
      </optional>
      <optional>
        <attribute name="key">
          <a:documentation>Short resolvable key for the authority, so it can later be linked to an external institution registry.</a:documentation>
        </attribute>
      </optional>
      <interleave>
        <text/>
        <zeroOrMore>
          <ref name="orgName"/>
        </zeroOrMore>
      </interleave>
    </element>
  </define>
```

**4. `references_seg`** — rename `signal` to `citationContext`, add `references_quote`
immediately after it:

```xml
  <!-- <seg type="citationContext"> marks a citation-signal phrase that
       introduces or frames a citation with evaluative/directional force,
       e.g. "See", "See also", "Cf.", "But see", "Contra", "vgl.",
       "anderer Ansicht" (common in legal/footnote citations). Marks only
       the signal phrase itself, not the citation that follows it. Stays
       inside the <bibl> of the citation it introduces (see the
       composite-footnote worked example and the note on its shape in
       the source proposal) rather than sitting between citations as a
       listBibl-level sibling. -->
  <define name="references_seg">
    <element name="seg">
      <optional>
        <attribute name="type">
          <group>
            <a:documentation>Citation-signal phrase introducing or framing a citation (e.g. 'see', 'vgl.', 'cf.')</a:documentation>
            <value>citationContext</value>
          </group>
        </attribute>
      </optional>
      <text/>
    </element>
  </define>

  <!-- <quote> pairs a direct quotation from the body text with the <bibl>
       that supports it (see the composite-footnote worked example). No
       attributes: quotation marks/punctuation stay in the source text. -->
  <define name="references_quote">
    <element name="quote">
      <a:documentation>Direct quotation from the body text, paired with the citation that supports it.</a:documentation>
      <text/>
    </element>
  </define>
```

**5. `references_ref`** — replace the anaphoric/cataphoric define with the four-way
split plus `@n`:

```xml
  <!-- <ref type="…"> marks an intra-footnote anaphoric device that avoids
       repeating a citation just given:
         precedingWork   -> the work just cited, e.g. "id.", "op. cit.",
                             "a.a.O.", "supra"
         subsequentWork  -> a work cited later, e.g. "infra", "below"
         precedingAuthor -> the author just named, work unspecified,
                             e.g. "ders.", "idem"
         footnote        -> explicit cross-reference to another footnote,
                             carrying @n with the footnote number
       @target optionally holds a resolved pointer once the citation is
       resolved in post-processing; not required for training annotation. -->
  <define name="references_ref">
    <element name="ref">
      <optional>
        <choice>
          <group>
            <a:documentation>The work just cited, e.g. "id.", "op. cit.", "a.a.O.", "supra"</a:documentation>
            <attribute name="type"><value>precedingWork</value></attribute>
          </group>
          <group>
            <a:documentation>A work cited later, e.g. "infra", "below"</a:documentation>
            <attribute name="type"><value>subsequentWork</value></attribute>
          </group>
          <group>
            <a:documentation>The author just named, work unspecified, e.g. "ders.", "idem"</a:documentation>
            <attribute name="type"><value>precedingAuthor</value></attribute>
          </group>
          <group>
            <a:documentation>Explicit cross-reference to another footnote, carrying @n with the footnote number, e.g. "n. 7", "N. 22"</a:documentation>
            <attribute name="type"><value>footnote</value></attribute>
            <optional>
              <attribute name="n"/>
            </optional>
          </group>
        </choice>
      </optional>
      <optional>
        <attribute name="target"/>
      </optional>
      <text/>
    </element>
  </define>
```

No changes to `schema/shared/bibl-struct.rng`, `schema/shared/common-elements.rng`,
`schema/grobid.training.segmentation.rng`, or
`schema/grobid.training.references.referenceSegmenter.rng` — the referenceSegmenter's
`<bibl>` stays label/lb/text-only; it segments raw footnote text into candidate
citations, it does not carry the richer B7/B8/quote/authority annotation.

## 6. Validation performed

- `uv run python scripts/build-schema.py` on the patched sources: no duplicate-`<define>`
  errors, flattens cleanly.
- `jing` against all 30 existing `*.training.references.tei.xml` files: identical result
  before and after this patch — 29 pass, 1 fails on a pre-existing, unrelated
  `xml:space` issue on the root `<text>` element (present in the *published*
  `docs/schema/grobid.training.references.rng` today too; not introduced or affected by
  this spec, and not in scope here).
- A hand-built encoding of the proposal's §5.1 court-decision example
  (`<authority type="court">EuGH</authority>`, plus the nested-`<orgName>` decomposition
  and a `<authority type="legislature">` case) validates cleanly against the patched
  schema.
- A hand-built encoding of the proposal's final §5.3 composite footnote (four sibling
  `<bibl>`, each carrying its own `<seg type="citationContext">`/`<ref>`/`<quote>`
  internally, per §4.4) validates cleanly against the patched schema.
- The same §5.3 encoding, run against the **unpatched** schema, fails with exactly six
  errors, all vocabulary/element gaps already identified above and nothing else:
  `seg@type` must be `"signal"` (×3), `ref@type` must be `"anaphoric"`/`"cataphoric"`
  (×2), `n` not allowed on `<ref>`, and `quote` not allowed inside `<bibl>`. This
  positively confirms §4.4's conclusion that no structural (`listBibl`) change is needed.
- Negative controls: `<ref type="anaphoric">` (the old value) and
  `<orgName type="court">` (the value `<authority>` now supersedes) both correctly fail
  against the patched schema, confirming §4.1 and §3 are real, enforced changes rather
  than documentation-only ones.

## 7. Rollout

1. Land the §5 diff in `schema/grobid.training.references.rng`.
2. `uv run python scripts/build-schema.py`; commit the regenerated `docs/schema/`
   (`git commit -m "Regenerate schemas"`, per `README.md`).
3. Add a "Legal references: the issuing authority, anaphoric devices, citation-signal
   phrases, quotations, composite footnotes" section to `docs/guidelines.md` (currently
   has none of this documented for annotators at all) using the proposal's §5.1/§5.2/§5.3
   examples, including the note on why composite-footnote signal/quote spans nest inside
   their `<bibl>` rather than sitting between citations.
4. Flag the `seg@type` rename, the `ref@type` vocabulary change, and the new `authority`
   element to `pdf-tei-editor` (the downstream consumer that generates its
   annotation-chip UI directly from this schema's `<a:documentation>`, per
   `docs/superpowers/spec/2026-09-05-annotation-chip-schema-changes-plan.md`) — all three
   change what that UI renders.
5. Re-annotate the corpus (per the author's decision in §3, this includes retargeting
   any `orgName@type="court"` — currently none exist — to `<authority type="court">`)
   with particular attention to composite, multi-citation footnotes, to confirm the
   in-`<bibl>` signal/quote placement trains sensibly before committing to it across the
   full corpus.

## 8. Open questions carried from the TEI proposal

- Proposal §7.2 asks the TEI list whether `precedingWork`/`subsequentWork`/
  `precedingAuthor` is the right three-way split (four, counting `footnote`) or whether
  established prior art exists. This spec adopts it now for the local schema (§4.1) since
  it is a strict improvement over the current two-way split either way, but the
  vocabulary may still change again if the list surfaces a better-established term —
  low cost given zero current corpus usage.
- Proposal §7.3 asks whether extending `model.imprintPart` is the right place for
  `<authority>` in the *official* Guidelines. That question is orthogonal to §3 above:
  this repo's local `<authority>` is defined independently of where (or whether) the TEI
  Guidelines end up placing it.
- Proposal §7.5 (citation-signal polarity — `see` vs. `cf.`/`contra` — as a further
  `@type` refinement on `<seg>`, or left to downstream classification) is left open here
  too; nothing in this spec forecloses adding a polarity attribute to
  `references_seg` later.

## 9. References

- `docs/tei-proposal-legal-footnote-citations.md` — the proposal this spec implements
  the local-schema portion of.
- `docs/spec-legal-references.md` — round 1 (#41), already implemented.
- `docs/superpowers/spec/2026-09-05-annotation-chip-schema-changes-plan.md` —
  `pdf-tei-editor` chip-generation consumer of this schema.
- Issue #41 — <https://github.com/mpilhlt/grobid-footnote-flavour/issues/41>
