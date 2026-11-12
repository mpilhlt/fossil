#!/usr/bin/env python3
"""Convert docs/guidelines.md into a formatted Word document and, optionally, a PDF.

    uv run python scripts/build-guidelines-docx.py [--input FILE] [--output FILE] [--pdf [FILE]]

Writes docs/guidelines.docx by default. With --pdf, also writes docs/guidelines.pdf (or the given file).

Requires pandoc on the PATH. LibreOffice is required for --pdf and otherwise optional: if present, it is used to
pre-fill the page numbers in the table of contents (these can drift slightly from Word's layout; update the field in
Word if needed). Without it, Word offers to update the table of contents when the file is opened.

All fenced code blocks are highlighted as XML, which is what the guidelines contain.
"""
import argparse
import copy
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from docx import Document
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls, qn
    from docx.shared import Cm
    from pygments.lexers import XmlLexer
    from pygments.token import Token
    from pypdf import PdfReader
except ImportError:
    sys.exit("ERROR: python-docx, pygments and pypdf are required. Install with:\n  uv sync --group dev")

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/mpilhlt/fossil"
FOOTER_TEXT = "FOSSIL annotation guidelines"
SUBTITLE_PREFIX = "FOSSIL dataset · Source: "

W = nsdecls("w")
BODY_FONT, QUOTE_FONT, CODE_FONT = "Calibri", "Cambria", "Consolas"
INK, ACCENT, MUTED, CODE_BG, CODE_LINE, CODE_TEXT = "1F2328", "1F4E79", "57606A", "F6F8FA", "D0D7DE", "24292F"
QUOTE_BAR = "C2C8D0"
TEXT_WIDTH = 9411  # A4 with 2.2 cm margins, in DXA
LIST_INDENT = 720  # DXA, matches pandoc's list numbering
MAX_IMAGE_EMU = int(14.5 * 360000)
SHORT_CODE_BLOCK_LINES = 12  # blocks up to this length are kept on one page
TOKENS = {  # style suffix: (colour, italic)
    "Tag": ("1A4FA0", False),
    "Attr": ("8A3F00", False),
    "Value": ("0A6B3D", False),
    "Comment": ("6B7280", True),
    "Entity": ("8E24AA", False),
}
CALLOUTS = {  # label: (bar colour, background)
    "Note": ("0969DA", "EDF4FC"),
    "Tip": ("1A7F37", "EBF7EE"),
    "Warning": ("B26A00", "FFF6E0"),
    "Important": ("8250DF", "F4EFFC"),
    "Caution": ("CF222E", "FDEEEF"),
}

# GitHub alerts -> one-cell tables (older pandoc: blockquotes starting with [!KIND]; newer: Divs);
# <sup> -> superscript; <hr> in quoted footnotes -> styled rule; lone images -> image + caption.
# Callouts inside lists get a "Nested" suffix per list level, which post-processing turns into an indent.
LUA_FILTER = r"""
local LABELS = {NOTE='Note', TIP='Tip', WARNING='Warning', IMPORTANT='Important', CAUTION='Caution'}

local function callout(kind, blocks_in)
  local blocks = pandoc.Blocks{
    pandoc.Div({pandoc.Para{pandoc.Str(LABELS[kind])}}, {['custom-style'] = 'Callout Label ' .. LABELS[kind]})
  }
  for _, b in ipairs(blocks_in) do blocks:insert(b) end
  local body = {attr = pandoc.Attr(), head = {}, row_head_columns = 0, body = {pandoc.Row{pandoc.Cell(blocks)}}}
  return pandoc.Table({long = {}}, {{'AlignDefault', 'ColWidthDefault'}}, pandoc.TableHead(), {body}, pandoc.TableFoot())
end

local function Inlines(ils)
  local out, sup = pandoc.Inlines{}, nil
  for _, il in ipairs(ils) do
    if il.t == 'RawInline' and il.format:match('html') and il.text == '<sup>' then
      sup = pandoc.Inlines{}
    elseif il.t == 'RawInline' and il.format:match('html') and il.text == '</sup>' then
      out:insert(pandoc.Superscript(sup)); sup = nil
    elseif sup then sup:insert(il)
    else out:insert(il) end
  end
  return out
end

local function BlockQuote(el)
  local first = el.content[1]
  if first and first.t == 'Para' and first.content[1] and first.content[1].t == 'Str' then
    local kind = first.content[1].text:match('^%[!(%u+)%]$')
    if kind and LABELS[kind] then
      local ils = pandoc.List(first.content); ils:remove(1)
      if ils[1] and (ils[1].t == 'SoftBreak' or ils[1].t == 'Space') then ils:remove(1) end
      local rest = pandoc.Blocks{}
      if #ils > 0 then rest:insert(pandoc.Para(ils)) end
      for i = 2, #el.content do rest:insert(el.content[i]) end
      return callout(kind, rest)
    end
  end
end

local function Div(el)
  local kind = el.classes[1] and el.classes[1]:upper()
  local first = el.content[1]
  if kind and LABELS[kind] and first and first.t == 'Div' and first.classes:includes('title') then
    local rest = pandoc.Blocks{}
    for i = 2, #el.content do rest:insert(el.content[i]) end
    return callout(kind, rest)
  end
end

local function HorizontalRule()
  return pandoc.Div({pandoc.Para{pandoc.Str('\u{00A0}')}}, {['custom-style'] = 'Footnote Rule'})
end

local function Para(el)
  if #el.content == 1 and el.content[1].t == 'Image' then
    local img = el.content[1]
    return {
      pandoc.Div({pandoc.Para{img}}, {['custom-style'] = 'Figure'}),
      pandoc.Div({pandoc.Para(img.caption)}, {['custom-style'] = 'Figure Caption'})
    }
  end
end

local function mark_nested(list)
  return list:walk{Div = function(d)
    local s = d.attributes['custom-style']
    if s and s:match('^Callout Label') then
      d.attributes['custom-style'] = s .. ' Nested'
      return d
    end
  end}
end

return {
  {Inlines = Inlines}, {HorizontalRule = HorizontalRule}, {Para = Para},
  {BlockQuote = BlockQuote, Div = Div},
  {OrderedList = mark_nested, BulletList = mark_nested},
}
"""

PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"]
SETTINGS_ORDER = ["zoom", "embedSystemFonts", "proofState", "stylePaneFormatFilter", "doNotTrackMoves", "defaultTabStop", "drawingGridHorizontalSpacing", "drawingGridVerticalSpacing", "displayHorizontalDrawingGridEvery", "displayVerticalDrawingGridEvery", "characterSpacingControl", "savePreviewPicture", "updateFields", "footnotePr", "endnotePr", "compat", "rsids", "mathPr", "themeFontLang", "clrSchemeMapping", "decimalSymbol", "listSeparator"]


# ---------- styles ----------
def fonts(font):
    return f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}" w:eastAsia="{font}"/>'


def para_style(sid, name, based="Normal", nxt=None, ppr="", rpr="", quick=True):
    return (
        f'<w:style {W} w:type="paragraph" w:styleId="{sid}"><w:name w:val="{name}"/>'
        + (f'<w:basedOn w:val="{based}"/>' if based else "")
        + (f'<w:next w:val="{nxt}"/>' if nxt else "")
        + ("<w:qFormat/>" if quick else "")
        + f"<w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>"
    )


def char_style(sid, name, based=None, rpr=""):
    return (
        f'<w:style {W} w:type="character" w:styleId="{sid}"><w:name w:val="{name}"/>'
        + (f'<w:basedOn w:val="{based}"/>' if based else "")
        + f"<w:rPr>{rpr}</w:rPr></w:style>"
    )


def heading_style(level, size, before, after, color=ACCENT):
    return para_style(
        f"Heading{level}",
        f"heading {level}",
        nxt="BodyText",
        ppr=f'<w:keepNext/><w:keepLines/><w:spacing w:before="{before}" w:after="{after}"/><w:outlineLvl w:val="{level - 1}"/>',
        rpr=f'{fonts(BODY_FONT)}<w:b/><w:bCs/><w:color w:val="{color}"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/>',
    )


def toc_style(level, ppr_extra, rpr=""):
    return para_style(
        f"TOC{level}",
        f"toc {level}",
        nxt="BodyText",
        quick=False,
        ppr=f'<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{TEXT_WIDTH}"/></w:tabs>{ppr_extra}',
        rpr=rpr,
    )


def define_styles(doc):
    styles = doc.styles.element
    code_box = "".join(f'<w:{side} w:val="single" w:sz="4" w:space="{space}" w:color="{CODE_LINE}"/>' for side, space in [("top", 3), ("left", 5), ("bottom", 3), ("right", 5)])
    quote_bar = f'<w:left w:val="single" w:sz="18" w:space="10" w:color="{QUOTE_BAR}"/>'
    new = [
        para_style("Normal", "Normal", based=None, ppr='<w:spacing w:before="0" w:after="120" w:line="269" w:lineRule="auto"/>', rpr=f'<w:color w:val="{INK}"/>'),
        para_style("BodyText", "Body Text", ppr='<w:spacing w:before="0" w:after="120"/>'),
        para_style("FirstParagraph", "First Paragraph", based="BodyText", nxt="BodyText"),
        para_style("Compact", "Compact", based="BodyText", ppr='<w:spacing w:before="20" w:after="40"/>'),
        para_style("Title", "Title", nxt="Subtitle", ppr='<w:keepNext/><w:spacing w:before="0" w:after="60" w:line="240" w:lineRule="auto"/>', rpr=f'{fonts(BODY_FONT)}<w:b/><w:bCs/><w:color w:val="{ACCENT}"/><w:sz w:val="52"/><w:szCs w:val="52"/>'),
        para_style("Subtitle", "Subtitle", nxt="BodyText", ppr=f'<w:pBdr><w:bottom w:val="single" w:sz="8" w:space="8" w:color="{ACCENT}"/></w:pBdr><w:spacing w:before="0" w:after="280"/>', rpr=f'<w:color w:val="{MUTED}"/><w:sz w:val="20"/><w:szCs w:val="20"/>'),
        heading_style(1, 34, 400, 120),
        heading_style(2, 28, 300, 100),
        heading_style(3, 24, 240, 80),
        heading_style(4, 22, 200, 60, color=CODE_TEXT),
        para_style("TOCHeading", "TOC Heading", nxt="BodyText", ppr='<w:keepNext/><w:spacing w:before="120" w:after="120"/>', rpr=f'{fonts(BODY_FONT)}<w:b/><w:bCs/><w:color w:val="{ACCENT}"/><w:sz w:val="28"/><w:szCs w:val="28"/>'),
        toc_style(1, '<w:spacing w:before="110" w:after="30"/>', "<w:b/><w:bCs/>"),
        toc_style(2, '<w:spacing w:before="0" w:after="20"/><w:ind w:left="240"/>'),
        toc_style(3, '<w:spacing w:before="0" w:after="10"/><w:ind w:left="480"/>', f'<w:color w:val="{MUTED}"/><w:sz w:val="20"/><w:szCs w:val="20"/>'),
        para_style("BlockText", "Block Text", nxt="BodyText", ppr=f'<w:pBdr>{quote_bar}</w:pBdr><w:spacing w:before="0" w:after="80"/><w:ind w:left="284" w:right="113"/>', rpr=f'{fonts(QUOTE_FONT)}<w:noProof/><w:color w:val="3D444D"/><w:sz w:val="20"/><w:szCs w:val="20"/>'),
        para_style("FootnoteRule", "Footnote Rule", based="BlockText", nxt="BlockText", ppr=f'<w:pBdr>{quote_bar}<w:bottom w:val="single" w:sz="4" w:space="1" w:color="8C959F"/></w:pBdr><w:spacing w:before="0" w:after="0" w:line="120" w:lineRule="exact"/>', rpr='<w:sz w:val="8"/><w:szCs w:val="8"/>'),
        para_style("SourceCode", "Source Code", ppr=f'<w:keepLines/><w:pBdr>{code_box}</w:pBdr><w:shd w:val="clear" w:color="auto" w:fill="{CODE_BG}"/><w:spacing w:before="0" w:after="0" w:line="220" w:lineRule="exact"/><w:ind w:left="340" w:right="113" w:hanging="227"/>', rpr=f'{fonts(CODE_FONT)}<w:noProof/><w:color w:val="{CODE_TEXT}"/><w:sz w:val="17"/><w:szCs w:val="17"/>'),
        char_style("VerbatimChar", "Verbatim Char", rpr=f'{fonts(CODE_FONT)}<w:noProof/><w:color w:val="{CODE_TEXT}"/><w:sz w:val="20"/><w:szCs w:val="20"/><w:shd w:val="clear" w:color="auto" w:fill="EEF1F4"/>'),
        char_style("Hyperlink", "Hyperlink", rpr='<w:color w:val="0B5CAD"/><w:u w:val="single"/>'),
        para_style("Figure", "Figure", nxt="FigureCaption", ppr='<w:keepNext/><w:spacing w:before="120" w:after="60" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/>'),
        para_style("FigureCaption", "Figure Caption", nxt="BodyText", ppr='<w:spacing w:before="0" w:after="200"/><w:jc w:val="center"/>', rpr=f'<w:i/><w:iCs/><w:color w:val="{MUTED}"/><w:sz w:val="19"/><w:szCs w:val="19"/>'),
        para_style("Footer", "footer", quick=False, ppr=f'<w:tabs><w:tab w:val="right" w:pos="{TEXT_WIDTH}"/></w:tabs><w:spacing w:before="0" w:after="0"/>', rpr=f'<w:color w:val="{MUTED}"/><w:sz w:val="18"/><w:szCs w:val="18"/>'),
        f'<w:style {W} w:type="table" w:styleId="Table"><w:name w:val="Table"/><w:basedOn w:val="TableNormal"/><w:qFormat/></w:style>',
    ]
    for label, (color, _) in CALLOUTS.items():
        new.append(para_style(f"CalloutLabel{label}", f"Callout Label {label}", ppr='<w:keepNext/><w:spacing w:before="20" w:after="40"/>', rpr=f'<w:b/><w:bCs/><w:color w:val="{color}"/><w:sz w:val="21"/><w:szCs w:val="21"/>'))
    for suffix, (color, italic) in TOKENS.items():
        it = "<w:i/><w:iCs/>" if italic else ""
        new.append(char_style(f"Code{suffix}", f"Code {suffix}", rpr=f'{it}<w:color w:val="{color}"/>'))
        new.append(char_style(f"Inline{suffix}", f"Inline {suffix}", based="VerbatimChar", rpr=f'{it}<w:color w:val="{color}"/>'))

    replaced = {parse_xml(xml).get(qn("w:styleId")) for xml in new}
    for old in styles.findall(qn("w:style")):
        sid = old.get(qn("w:styleId"))
        if sid in replaced or sid.endswith("Nested"):
            styles.remove(old)
            continue
        for rpr in old.iter(qn("w:rPr")):  # pandoc's default styles carry stray text here
            rpr.text = None
            for child in rpr:
                child.tail = None
    for xml in new:
        el = parse_xml(xml)
        if el.get(qn("w:styleId")) == "Normal":
            el.set(qn("w:default"), "1")
        styles.append(el)

    defaults = styles.find(qn("w:docDefaults"))
    if defaults is not None:
        styles.remove(defaults)
    styles.insert(0, parse_xml(f'<w:docDefaults {W}><w:rPrDefault><w:rPr>{fonts(BODY_FONT)}<w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="en-US" w:eastAsia="en-US" w:bidi="ar-SA"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr/></w:pPrDefault></w:docDefaults>'))


# ---------- helpers ----------
def style_of(p):
    s = p.find(qn("w:pPr") + "/" + qn("w:pStyle"))
    return (s.get(qn("w:val")) if s is not None else "") or ""


def set_ppr(p, tag, **attrs):
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        ppr = parse_xml(f"<w:pPr {W}/>")
        p.insert(0, ppr)
    old = ppr.find(qn(tag))
    if old is not None:
        ppr.remove(old)
    a = "".join(f' w:{k}="{v}"' for k, v in attrs.items())
    ppr.append(parse_xml(f"<{tag} {W}{a}/>"))


def drop_jc(p):
    jc = p.find(qn("w:pPr") + "/" + qn("w:jc"))
    if jc is not None:
        jc.getparent().remove(jc)


def make_run(text, style=None, rpr=None):
    r = parse_xml(f"<w:r {W}/>")
    pr = copy.deepcopy(rpr) if rpr is not None else None
    if style:
        if pr is None:
            pr = parse_xml(f"<w:rPr {W}/>")
        s = pr.find(qn("w:rStyle"))
        if s is None:
            s = parse_xml(f"<w:rStyle {W}/>")
            pr.insert(0, s)
        s.set(qn("w:val"), style)
    if pr is not None:
        r.append(pr)
    t = parse_xml(f'<w:t {W} xml:space="preserve"/>')
    t.text = text
    r.append(t)
    return r


def text_of(p):
    return "".join(t.text or "" for t in p.iter(qn("w:t")))


def field(instruction, placeholder=None):
    frags = [f'<w:r {W}><w:fldChar w:fldCharType="begin"/></w:r>', f'<w:r {W}><w:instrText xml:space="preserve"> {instruction} </w:instrText></w:r>', f'<w:r {W}><w:fldChar w:fldCharType="separate"/></w:r>']
    if placeholder:
        frags.append(f"<w:r {W}><w:t>{placeholder}</w:t></w:r>")
        frags.append(f'<w:r {W}><w:fldChar w:fldCharType="end"/></w:r>')
    return [parse_xml(f) for f in frags]


# ---------- highlighting ----------
LEXER = XmlLexer(stripnl=False, ensurenl=False, stripall=False)


def token_class(tok):
    if tok in Token.Name.Tag:
        return "Tag"
    if tok in Token.Name.Attribute:
        return "Attr"
    if tok in Token.Literal.String or tok in Token.Error:  # the guidelines' "a"|"b" shorthand is not strict XML
        return "Value"
    if tok in Token.Comment:
        return "Comment"
    if tok in Token.Name.Entity:
        return "Entity"
    return None


def tokenize(code):
    toks = [(token_class(t), v) for t, v in LEXER.get_tokens(code)]
    if "".join(v for _, v in toks) != code:
        raise RuntimeError(f"Highlighter changed the text of: {code[:80]!r}")
    return toks


def format_code_blocks(body):
    """Split each code block into one highlighted paragraph per line, so wrapped lines can get a hanging indent."""
    for p in [p for p in body.iter(qn("w:p")) if style_of(p) == "SourceCode"]:
        code = ""
        for r in p.findall(qn("w:r")):
            for c in r:
                if c.tag == qn("w:t"):
                    code += c.text or ""
                elif c.tag == qn("w:br"):
                    code += "\n"
        lines = [[]]
        for cls, val in tokenize(code):
            for i, part in enumerate(val.split("\n")):
                if i:
                    lines.append([])
                if part:
                    lines[-1].append((cls, part))
        base = p.find(qn("w:pPr"))
        parent = p.getparent()
        at = parent.index(p)
        in_callout = parent.tag == qn("w:tc")
        parent.remove(p)
        for n, toks in enumerate(lines):
            q = parse_xml(f"<w:p {W}/>")
            q.append(copy.deepcopy(base))
            drop_jc(q)
            if len(lines) <= SHORT_CODE_BLOCK_LINES and n < len(lines) - 1:
                set_ppr(q, "w:keepNext")
            set_ppr(q, "w:spacing", before=120 if n == 0 else 0, after=160 if n == len(lines) - 1 else 0, line=220, lineRule="exact")
            if in_callout:
                set_ppr(q, "w:shd", val="clear", color="auto", fill="FFFFFF")
            for cls, val in toks:
                q.append(make_run(val, f"Code{cls}" if cls else None))
            parent.insert(at + n, q)


def format_inline_code(body):
    """Highlight inline code that starts like an XML tag, except in headings."""
    for r in list(body.iter(qn("w:r"))):
        pr = r.find(qn("w:rPr"))
        s = pr.find(qn("w:rStyle")) if pr is not None else None
        if s is None or s.get(qn("w:val")) != "VerbatimChar":
            continue
        p = r.getparent()
        while p.tag != qn("w:p"):
            p = p.getparent()
        if style_of(p).startswith("Heading"):
            continue
        txt = "".join(t.text or "" for t in r.findall(qn("w:t")))
        if not txt.startswith("<"):
            continue
        parent = r.getparent()
        at = parent.index(r)
        parent.remove(r)
        for i, (cls, val) in enumerate(tokenize(txt)):
            parent.insert(at + i, make_run(val, f"Inline{cls}" if cls else "VerbatimChar", pr))


# ---------- tables ----------
def set_cell_props(tc, width, shade=None):
    old = tc.find(qn("w:tcPr"))
    if old is not None:
        tc.remove(old)
    s = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else ""
    tc.insert(0, parse_xml(f'<w:tcPr {W}><w:tcW w:w="{width}" w:type="dxa"/>{s}</w:tcPr>'))


def set_table_props(t, widths, indent, borders, margins):
    t.remove(t.find(qn("w:tblPr")))
    top, left, bottom, right = margins
    t.insert(0, parse_xml(f'<w:tblPr {W}><w:tblStyle w:val="Table"/><w:tblW w:w="{sum(widths)}" w:type="dxa"/><w:tblInd w:w="{indent}" w:type="dxa"/><w:tblBorders>{borders}</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="{top}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tblCellMar><w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="1" w:noVBand="1"/></w:tblPr>'))
    grid = t.find(qn("w:tblGrid"))
    for c in list(grid):
        grid.remove(c)
    for w in widths:
        grid.append(parse_xml(f'<w:gridCol {W} w:w="{w}"/>'))


def format_callout(t, first_p):
    m = re.fullmatch(r"CalloutLabel(\w+?)((?:Nested)*)", style_of(first_p))
    label, depth = m.group(1), len(m.group(2)) // len("Nested")
    first_p.find(qn("w:pPr") + "/" + qn("w:pStyle")).set(qn("w:val"), f"CalloutLabel{label}")
    color, tint = CALLOUTS[label]
    indent = LIST_INDENT * depth
    width = TEXT_WIDTH - indent
    borders = f'<w:top w:val="nil"/><w:left w:val="single" w:sz="24" w:space="0" w:color="{color}"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
    set_table_props(t, [width], indent + 30, borders, (70, 170, 40, 170))
    tc = t.find(qn("w:tr")).find(qn("w:tc"))
    set_cell_props(tc, width, shade=tint)
    paras = tc.findall(qn("w:p"))
    for p in paras:
        drop_jc(p)
    if style_of(paras[-1]) != "SourceCode":
        set_ppr(paras[-1], "w:spacing", before=0, after=60)


def format_data_table(t, rows):
    n = len(rows[0].findall(qn("w:tc")))
    lengths, longest_word = [0] * n, [0] * n
    for r in rows:
        for i, tc in enumerate(r.findall(qn("w:tc"))):
            for p in tc.findall(qn("w:p")):
                txt = text_of(p)
                lengths[i] = max(lengths[i], len(txt))
                longest_word[i] = max([longest_word[i]] + [len(w) for w in txt.split()])
    floor = [w * 118 + 260 for w in longest_word]  # identifiers must not split mid-word
    raw = [min(x, 46) + 5 for x in lengths]
    spare = max(TEXT_WIDTH - sum(floor), 0)
    widths = [f + round(spare * x / sum(raw)) for f, x in zip(floor, raw)]
    widths[-1] += TEXT_WIDTH - sum(widths)
    borders = '<w:top w:val="single" w:sz="4" w:space="0" w:color="BFC6CE"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="BFC6CE"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="BFC6CE"/>'
    set_table_props(t, widths, 0, borders, (40, 90, 40, 90))
    for ri, r in enumerate(rows):
        old = r.find(qn("w:trPr"))
        if old is not None:
            r.remove(old)
        r.insert(0, parse_xml(f"<w:trPr {W}><w:cantSplit/>" + ("<w:tblHeader/>" if ri == 0 else "") + "</w:trPr>"))
        for i, tc in enumerate(r.findall(qn("w:tc"))):
            set_cell_props(tc, widths[i], shade="DCE6F1" if ri == 0 else None)
            for p in tc.findall(qn("w:p")):
                drop_jc(p)
                if ri == 0:
                    set_ppr(p, "w:keepNext")
                    for run in p.iter(qn("w:r")):
                        pr = run.find(qn("w:rPr"))
                        if pr is None:
                            pr = parse_xml(f"<w:rPr {W}/>")
                            run.insert(0, pr)
                        pr.insert(1 if pr.find(qn("w:rStyle")) is not None else 0, parse_xml(f"<w:b {W}/>"))


def format_tables(body):
    for t in body.findall(qn("w:tbl")):
        rows = t.findall(qn("w:tr"))
        first_p = rows[0].find(qn("w:tc")).find(qn("w:p"))
        if style_of(first_p).startswith("CalloutLabel"):
            format_callout(t, first_p)
        else:
            format_data_table(t, rows)
        nxt = t.getnext()
        if nxt is not None and nxt.tag == qn("w:p") and not style_of(nxt).startswith("Heading"):
            sp = nxt.find(qn("w:pPr") + "/" + qn("w:spacing")) if nxt.find(qn("w:pPr")) is not None else None
            if sp is None:
                set_ppr(nxt, "w:spacing", before=160)
            else:
                sp.set(qn("w:before"), "160")


# ---------- quotes, figures, pagination ----------
def format_quotes(body):
    """Align quoted sources with the list text and keep the side bar continuous across footnote rules."""
    for p in body.findall(qn("w:p")):
        st = style_of(p)
        if st in ("BlockText", "FootnoteRule"):
            ppr = p.find(qn("w:pPr"))
            num = ppr.find(qn("w:numPr"))
            if num is not None:
                ppr.remove(num)
                set_ppr(p, "w:ind", left=900, right=113, hanging=0)
        if st == "FootnoteRule":
            before = p.getprevious()
            if before is not None and style_of(before) == "BlockText":
                set_ppr(before, "w:spacing", before=0, after=0)


def keep_with_code(body):
    for p in body.findall(qn("w:p")):
        nxt = p.getnext()
        if nxt is not None and nxt.tag == qn("w:p") and style_of(nxt) == "SourceCode" and style_of(p) != "SourceCode":
            set_ppr(p, "w:keepNext")


def scale_images(body):
    wp = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
    a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    for extent in body.iter(wp + "extent"):
        cx, cy = int(extent.get("cx")), int(extent.get("cy"))
        size = {"cx": str(MAX_IMAGE_EMU), "cy": str(int(cy * MAX_IMAGE_EMU / cx))}
        for el in [extent, *extent.getparent().iter(a + "ext")]:
            el.set("cx", size["cx"])
            el.set("cy", size["cy"])


# ---------- front matter ----------
def add_front_matter(doc, source_label, source_url, page_numbers):
    body = doc.element.body
    heads = []
    for p in body.findall(qn("w:p")):
        m = re.fullmatch(r"Heading([123])", style_of(p))
        if m:
            bookmark = p.getprevious()
            if bookmark is None or bookmark.tag != qn("w:bookmarkStart"):
                raise RuntimeError(f"Heading without bookmark: {text_of(p)}")
            heads.append((int(m.group(1)), text_of(p), bookmark.get(qn("w:name"))))

    title = next(p for p in body.findall(qn("w:p")) if style_of(p) == "Title")
    subtitle = parse_xml(f'<w:p {W}><w:pPr><w:pStyle w:val="Subtitle"/></w:pPr></w:p>')
    subtitle.append(make_run(SUBTITLE_PREFIX))
    rid = doc.part.relate_to(source_url, RT.HYPERLINK, is_external=True)
    link = parse_xml(f'<w:hyperlink {W} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="{rid}"/>')
    link.append(make_run(source_label, "Hyperlink"))
    subtitle.append(link)
    title.addnext(subtitle)

    toc_head = parse_xml(f'<w:p {W}><w:pPr><w:pStyle w:val="TOCHeading"/></w:pPr></w:p>')
    toc_head.append(make_run("Contents"))
    subtitle.addnext(toc_head)
    prev = toc_head
    for i, (level, text, anchor) in enumerate(heads):
        p = parse_xml(f'<w:p {W}><w:pPr><w:pStyle w:val="TOC{level}"/></w:pPr></w:p>')
        if i == 0:
            for el in field('TOC \\o "1-3" \\h \\z \\u'):
                p.append(el)
        h = parse_xml(f'<w:hyperlink {W} w:anchor="{anchor}" w:history="1"/>')
        h.append(make_run(text))
        h.append(parse_xml(f"<w:r {W}><w:tab/></w:r>"))
        h.append(make_run(str(page_numbers.get(anchor, "")) or "–"))
        p.append(h)
        if i == len(heads) - 1:
            p.append(parse_xml(f'<w:r {W}><w:fldChar w:fldCharType="end"/></w:r>'))
        prev.addnext(p)
        prev = p
    set_ppr(prev.getnext(), "w:pageBreakBefore")
    return heads


def setup_page(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.2)
    sec.footer_distance = Cm(1.1)
    sec.header_distance = Cm(1)
    sec.gutter = 0
    footer = sec.footer.paragraphs[0]
    footer.style = doc.styles["footer"]
    footer._p.append(make_run(FOOTER_TEXT))
    footer._p.append(parse_xml(f"<w:r {W}><w:tab/></w:r>"))
    for el in field("PAGE", placeholder="1"):
        footer._p.append(el)


def fix_schema_order(doc, update_toc_on_open):
    """Pandoc writes some elements out of schema order, which strict consumers reject."""
    rank = {qn("w:" + n): i for i, n in enumerate(PPR_ORDER)}
    for ppr in [*doc.element.body.iter(qn("w:pPr")), *doc.styles.element.iter(qn("w:pPr"))]:
        kids = sorted(ppr, key=lambda c: rank.get(c.tag, 99))
        for c in list(ppr):
            ppr.remove(c)
        ppr.extend(kids)
    for nsid in doc.part.numbering_part.element.iter(qn("w:nsid")):
        nsid.set(qn("w:val"), re.sub(r"\D", "", nsid.get(qn("w:val"))).zfill(8))
    settings = doc.settings.element
    if update_toc_on_open:
        settings.append(parse_xml(f'<w:updateFields {W} w:val="true"/>'))
    order = {qn("w:" + n) if ":" not in n else n: i for i, n in enumerate(SETTINGS_ORDER)}
    order[qn("m:mathPr")] = SETTINGS_ORDER.index("mathPr")
    kids = sorted(settings, key=lambda c: order.get(c.tag, 50))
    for c in list(settings):
        settings.remove(c)
    settings.extend(kids)


def post_process(raw_docx, output, source_label, source_url, page_numbers, update_toc_on_open):
    doc = Document(str(raw_docx))
    body = doc.element.body
    define_styles(doc)
    format_code_blocks(body)
    format_inline_code(body)
    format_tables(body)
    format_quotes(body)
    keep_with_code(body)
    scale_images(body)
    heads = add_front_matter(doc, source_label, source_url, page_numbers)
    setup_page(doc)
    fix_schema_order(doc, update_toc_on_open)
    props = doc.core_properties
    props.title = FOOTER_TEXT
    props.author = ""
    props.comments = source_label
    doc.save(str(output))
    return heads


# ---------- pipeline ----------
def run_pandoc(source, raw_docx, workdir):
    reference = workdir / "reference.docx"
    reference.write_bytes(subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"], check=True, capture_output=True).stdout)
    lua = workdir / "filter.lua"
    lua.write_text(LUA_FILTER, encoding="utf8")
    subprocess.run(["pandoc", "-f", "gfm", "-t", "docx", str(source), "--no-highlight", "--shift-heading-level-by=-1", f"--lua-filter={lua}", f"--reference-doc={reference}", f"--resource-path={source.parent}", "-o", str(raw_docx)], check=True, stderr=sys.stderr)


def find_soffice():
    return shutil.which("soffice") or shutil.which("libreoffice") or next((p for p in ["/Applications/LibreOffice.app/Contents/MacOS/soffice"] if Path(p).exists()), None)


def render_pdf(soffice, docx_path, workdir):
    """Render with LibreOffice, keeping the headings as PDF bookmarks. Returns the PDF path."""
    subprocess.run([soffice, f"-env:UserInstallation=file://{workdir}/lo-profile", "--headless", "--convert-to", 'pdf:writer_pdf_Export:{"ExportBookmarks":{"type":"boolean","value":"true"}}', "--outdir", str(workdir), str(docx_path)], check=True, capture_output=True)
    return workdir / (docx_path.stem + ".pdf")


def heading_pages(pdf_path, heads):
    """Read each heading's page number from the PDF outline."""
    reader = PdfReader(str(pdf_path))
    outline = []

    def walk(items):
        for item in items:
            if isinstance(item, list):
                walk(item)
            else:
                outline.append((item.title.strip(), reader.get_destination_page_number(item) + 1))

    walk(reader.outline)
    remaining = iter(outline)
    pages = {}
    for _, text, anchor in heads:
        for title, page in remaining:
            if title == text.strip():
                pages[anchor] = page
                break
        else:
            raise RuntimeError(f"Heading not found in rendered PDF: {text}")
    return pages


def source_reference(source):
    """Link text and URL naming the commit the source file comes from."""
    rel = source.relative_to(REPO_ROOT).as_posix()
    git = ["git", "-C", str(REPO_ROOT)]
    sha = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run([*git, "status", "--porcelain", "--", rel], check=True, capture_output=True, text=True).stdout.strip()
    label = f"mpilhlt/fossil, {rel} at commit {sha[:7]}" + (" with uncommitted changes" if dirty else "")
    return label, f"{REPO_URL}/blob/{sha}/{rel}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, default=REPO_ROOT / "docs" / "guidelines.md")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "docs" / "guidelines.docx")
    parser.add_argument("--pdf", type=Path, nargs="?", const=REPO_ROOT / "docs" / "guidelines.pdf", help="also write a PDF version (default: docs/guidelines.pdf); requires LibreOffice")
    args = parser.parse_args()
    source, output = args.input.resolve(), args.output.resolve()
    pdf_output = args.pdf.resolve() if args.pdf else None

    if not shutil.which("pandoc"):
        sys.exit("pandoc not found on the PATH: https://pandoc.org/installing.html")
    soffice = find_soffice()
    if pdf_output and not soffice:
        sys.exit("LibreOffice (soffice) not found on the PATH; it is required for --pdf: https://www.libreoffice.org/download/")
    label, url = source_reference(source)
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        raw = workdir / "raw.docx"
        run_pandoc(source, raw, workdir)
        draft = workdir / output.name
        if soffice:
            pages = {}
            for _ in range(4):  # filling in the numbers can shift the layout, so repeat until stable
                heads = post_process(raw, draft, label, url, pages, update_toc_on_open=False)
                pdf = render_pdf(soffice, draft, workdir)
                new_pages = heading_pages(pdf, heads)
                if new_pages == pages:
                    break
                pages = new_pages
            shutil.copyfile(draft, output)
            if pdf_output:  # the last rendering is of the final document
                shutil.copyfile(pdf, pdf_output)
        else:
            print("LibreOffice not found: Word will offer to update the table of contents on opening.", file=sys.stderr)
            post_process(raw, output, label, url, {}, update_toc_on_open=True)
    print(f"Wrote {output}")
    if pdf_output:
        print(f"Wrote {pdf_output}")


if __name__ == "__main__":
    main()
