"""Build the BAIC 2026 Word file from paper/baic/paper.md.

One-column title, then a two-column RTL body. B Nazanin, A4.
Tables are fixed to a single column width so they do not paint over the
other column. The embedded face is copied from the previous camera-ready file.
"""

from __future__ import annotations

import shutil
import uuid
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, Twips

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper" / "baic" / "paper.md"
TEMPLATE = ROOT / "paper" / "baic" / "BAIC2026_Jamei.docx"
OUT = ROOT / "paper" / "baic" / "BAIC2026_Jamei.docx"
FONT_KEY = "{93468E4A-5ADC-4EF9-A182-E6A3A5312047}"
COLUMN_DXA = 4876
HEADER = (
    "نخستین کنگره ملی مهندسی پزشکی، هوش مصنوعی و علوم شناختی"
    " — دانشگاه فردوسی مشهد، آبان ۱۴۰۵"
)


def _rfonts(run, size_pt: float, bold: bool = False, italic: bool = False) -> None:
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size_pt)
    run.font.name = "Times New Roman"
    rpr = run._r.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    fonts.set(qn("w:ascii"), "Times New Roman")
    fonts.set(qn("w:hAnsi"), "Times New Roman")
    fonts.set(qn("w:cs"), "B Nazanin")
    fonts.set(qn("w:eastAsia"), "B Nazanin")
    half = str(int(size_pt * 2))
    for tag in ("w:sz", "w:szCs"):
        node = rpr.find(qn(tag))
        if node is None:
            node = OxmlElement(tag)
            rpr.append(node)
        node.set(qn("w:val"), half)


def _bidi(paragraph, align: str) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    if ppr.find(qn("w:bidi")) is None:
        ppr.append(OxmlElement("w:bidi"))
    jc = ppr.find(qn("w:jc"))
    if jc is None:
        jc = OxmlElement("w:jc")
        ppr.append(jc)
    jc.set(qn("w:val"), align)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    paragraph.paragraph_format.line_spacing = 1.08


def _soften(text: str) -> str:
    parts: list[str] = []
    token: list[str] = []

    def flush() -> None:
        word = "".join(token)
        token.clear()
        if len(word) >= 18 and any(ch in word for ch in "/_"):
            word = word.replace("/", "/\u200b").replace("_", "_\u200b")
        parts.append(word)

    for ch in text:
        if ch.isspace():
            flush()
            parts.append(ch)
        else:
            token.append(ch)
    flush()
    return "".join(parts)


def _add_runs(paragraph, text: str, size: float, bold: bool = False) -> None:
    parts = _soften(text).split("`")
    for index, part in enumerate(parts):
        if not part:
            continue
        run = paragraph.add_run(part)
        _rfonts(run, size, bold=bold, italic=(index % 2 == 1))


def _para(doc: Document, text: str, size: float, align: str, bold: bool = False, after: float = 2, before: float = 0):
    paragraph = doc.add_paragraph()
    _bidi(paragraph, align)
    paragraph.paragraph_format.space_before = Pt(before)
    paragraph.paragraph_format.space_after = Pt(after)
    _add_runs(paragraph, text, size, bold=bold)
    return paragraph


def _set_page(section, columns: int) -> None:
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Twips(907)
    section.right_margin = Twips(907)
    section.top_margin = Twips(1000)
    section.bottom_margin = Twips(900)
    section.header_distance = Twips(500)
    section.footer_distance = Twips(400)
    sect = section._sectPr
    if sect.find(qn("w:bidi")) is None:
        sect.append(OxmlElement("w:bidi"))
    cols = sect.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sect.append(cols)
    if columns == 1:
        if qn("w:num") in cols.attrib:
            del cols.attrib[qn("w:num")]
    else:
        cols.set(qn("w:num"), str(columns))
    cols.set(qn("w:space"), "340")


def _header_footer(section) -> None:
    header = section.header
    header.is_linked_to_previous = False
    paragraph = header.paragraphs[0]
    paragraph.clear()
    _bidi(paragraph, "center")
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(HEADER)
    _rfonts(run, 8)
    footer = section.footer
    footer.is_linked_to_previous = False
    fpara = footer.paragraphs[0]
    fpara.clear()
    _bidi(fpara, "center")
    run_a = fpara.add_run()
    _rfonts(run_a, 9)
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    run_a._r.append(fld_begin)
    run_b = fpara.add_run()
    _rfonts(run_b, 9)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    run_b._r.append(instr)
    run_c = fpara.add_run()
    _rfonts(run_c, 9)
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run_c._r.append(fld_end)


def _shade(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), "EFEFEF")
    tc_pr.append(shd)


def _set_table_geometry(table, columns: int) -> None:
    width = COLUMN_DXA
    table.autofit = False
    table.allow_autofit = False
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(width))
    tbl_w.set(qn("w:type"), "dxa")
    if tbl_pr.find(qn("w:bidiVisual")) is None:
        tbl_pr.append(OxmlElement("w:bidiVisual"))
    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")
    each = width // columns
    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for col in grid.findall(qn("w:gridCol")):
            col.set(qn("w:w"), str(each))
    for row in table.rows:
        for cell in row.cells:
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(each))
            tc_w.set(qn("w:type"), "dxa")


def _table(doc: Document, rows: list[list[str]]) -> None:
    """In-column lines. A real grid overflows the RTL column in LibreOffice."""
    heads = [cell.replace("`", "") for cell in rows[0]]
    parts = []
    for row in rows[1:]:
        cells = [cell.replace("`", "") for cell in row]
        parts.append("، ".join(f"{head}: {cell}" for head, cell in zip(heads, cells)))
    _para(doc, " — ".join(parts), 9, "both", after=3)


def _blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    buf: list[str] = []
    kind = "p"

    def flush() -> None:
        nonlocal buf, kind
        body = "\n".join(buf).strip()
        buf = []
        if body:
            blocks.append((kind, body))
        kind = "p"

    for line in text.splitlines():
        if line.startswith("|"):
            if kind != "table":
                flush()
                kind = "table"
            buf.append(line)
            continue
        if kind == "table":
            flush()
        if not line.strip():
            flush()
            continue
        buf.append(line)
    flush()
    return blocks


def _parse_table(body: str) -> list[list[str]]:
    rows = []
    for line in body.splitlines():
        if set(line.replace("|", "").strip()) <= {"-", ":", " "}:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


def build() -> None:
    raw = SOURCE.read_text(encoding="utf-8")
    if not TEMPLATE.exists() or TEMPLATE.stat().st_size < 1000:
        raise SystemExit("template docx with embedded B Nazanin is missing")
    staging = ROOT / "paper" / "baic" / "_font_source.docx"
    shutil.copyfile(TEMPLATE, staging)

    doc = Document()
    section = doc.sections[0]
    _set_page(section, 1)
    _header_footer(section)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10)

    lines = raw.splitlines()
    title = lines[0][2:].strip()
    english = lines[2][2:].strip()
    _para(doc, title, 14, "center", bold=True, after=2)
    _para(doc, english, 11, "center", bold=False, after=2)
    _para(doc, "پرواز جمیعی", 11, "center", bold=True, after=0)
    _para(doc, "پژوهشگر مستقل، مشهد، ایران، parvaz.jamie@gmail.com", 9, "center", after=0)
    _para(doc, "ORCID: 0009-0002-9980-270X", 9, "center", after=4)

    abstract_at = next(i for i, line in enumerate(lines) if line.startswith("چکیده"))
    rest = "\n".join(lines[abstract_at:])
    pre, _sep, post = rest.partition("\n## ")
    for kind, body in _blocks(pre):
        if kind == "p":
            _para(doc, body, 10, "both", after=3)

    doc.add_section(WD_SECTION.CONTINUOUS)
    body_section = doc.sections[-1]
    _set_page(body_section, 2)
    _header_footer(body_section)

    body = "## " + post
    for kind, block in _blocks(body):
        if kind == "table":
            _table(doc, _parse_table(block))
            continue
        first = block.splitlines()[0]
        if first.startswith("## "):
            _para(doc, first[3:].strip(), 12, "right", bold=True, before=8, after=2)
            tail = "\n".join(block.splitlines()[1:]).strip()
            if tail:
                _para(doc, tail, 11, "both", after=3)
            continue
        if first.startswith("# "):
            continue
        size = 9 if block.startswith("[") else 11
        after = 2 if size == 9 else 4
        _para(doc, block, size, "both", after=after)

    core = doc.core_properties
    core.author = "پرواز جمیعی / Parvaz Jamei"
    core.title = title
    core.subject = "BAIC 2026 evidence audit"
    core.category = "BAIC2026"
    tmp = OUT.with_suffix(".tmp.docx")
    doc.save(tmp)
    _embed_font(tmp, staging, OUT)
    tmp.unlink(missing_ok=True)
    staging.unlink(missing_ok=True)


def _embed_font(src: Path, font_source: Path, dest: Path) -> None:
    with zipfile.ZipFile(font_source) as zin:
        odttf = zin.read("word/fonts/BNazanin.odttf")
    with zipfile.ZipFile(src) as zin:
        payload = {name: zin.read(name) for name in zin.namelist()}
    font_table = payload["word/fontTable.xml"].decode("utf-8")
    needle = '<w:font w:name="B Nazanin">'
    embed = f'<w:embedRegular r:id="rFontNazanin" w:fontKey="{FONT_KEY}"/>'
    if needle not in font_table:
        font_table = font_table.replace(
            "</w:fonts>",
            "<w:font w:name=\"B Nazanin\">"
            "<w:charset w:val=\"B2\"/><w:family w:val=\"auto\"/><w:pitch w:val=\"variable\"/>"
            f"{embed}</w:font></w:fonts>",
        )
    elif "embedRegular" not in font_table:
        font_table = font_table.replace(needle, needle + embed, 1)
    payload["word/fontTable.xml"] = font_table.encode("utf-8")
    rels_name = "word/_rels/fontTable.xml.rels"
    rels = payload.get(rels_name)
    if rels is None:
        rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rFontNazanin" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/font" '
            'Target="fonts/BNazanin.odttf"/></Relationships>'
        )
    else:
        rels_xml = rels.decode("utf-8")
        if "rFontNazanin" not in rels_xml:
            rels_xml = rels_xml.replace(
                "</Relationships>",
                '<Relationship Id="rFontNazanin" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/font" '
                'Target="fonts/BNazanin.odttf"/></Relationships>',
            )
    payload[rels_name] = rels_xml.encode("utf-8")
    payload["word/fonts/BNazanin.odttf"] = odttf
    ctypes = payload["[Content_Types].xml"].decode("utf-8")
    if 'Extension="odttf"' not in ctypes:
        ctypes = ctypes.replace(
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="odttf" '
            'ContentType="application/vnd.openxmlformats-officedocument.obfuscatedFont"/>',
            1,
        )
    payload["[Content_Types].xml"] = ctypes.encode("utf-8")
    uuid.UUID(FONT_KEY)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in payload.items():
            zout.writestr(name, data)


if __name__ == "__main__":
    build()
    print(OUT)
