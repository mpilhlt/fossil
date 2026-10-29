# CLAUDE.md

Guidance for code assistants working in this repository.

## Annotation guidelines

The annotation guidelines exist in two versions:

- `docs/guidelines.md` — the full guide for human annotators (rationale, links, many examples).
- `docs/guidelines-llm.md` — a condensed version of the same rules for LLMs. The PDF-TEI-Editor's GROBID plugin points the "machine" annotation-rule refs of its documents at its sections, so the LLM Reviewer sends these instead of the full guide.

`docs/guidelines-llm.md` is maintained from the PDF-TEI-Editor, not by coding agents: its document rules editor updates the machine rules from a changed guide section with a language model, and proposes both sections upstream with recomputed `<!-- sync: ... -->` markers. Do not mirror changes between the two files and do not edit the sync markers.

- Change the rules in `docs/guidelines.md`. The editor then shows the affected machine rules as outdated until they are updated from it.
- Edit `docs/guidelines-llm.md` directly only when asked to. The editor then shows the section as edited by hand.
- Each `##` section of `docs/guidelines-llm.md` condenses the `##` section of `docs/guidelines.md` with the same heading. Keep the headings identical, since the editor finds the sections by their heading anchors (`#citation-model` etc.). Renaming a heading also requires updating the URLs in the editor's GROBID plugin config (`annotation_guides.py` in mpilhlt/pte-plugins).
