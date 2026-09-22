"""English BAIC manuscript in the conference Word template.

Styles, numbering, and page setup come from the supplied template.
Heading 1 and the reference list are numbered by the template.
The output is paper/baic/BAIC2026_Jamei_en.docx.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Twips

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "paper" / "baic" / "ieee_template.docx"
OUT = ROOT / "paper" / "baic" / "BAIC2026_Jamei_en.docx"
COL_TWIPS = 4700


def _styles(doc: Document) -> dict:
    return {style.style_id: style for style in doc.styles}


def _p(doc: Document, styles: dict, style_id: str, text: str = ""):
    paragraph = doc.add_paragraph(text)
    paragraph.style = styles[style_id]
    if style_id == "Tablehead":
        paragraph.paragraph_format.keep_with_next = True
    return paragraph


def _runs(paragraph, parts: list[tuple[str, bool]]) -> None:
    """parts are (text, italic). The paragraph style still supplies the font."""

    for text, italic in parts:
        run = paragraph.add_run(text)
        if italic:
            run.italic = True


def _set_cols(sect, count: str, space: str) -> None:
    for child in list(sect):
        if child.tag == qn("w:cols"):
            sect.remove(child)
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), count)
    cols.set(qn("w:space"), space)
    cols.set(qn("w:equalWidth"), "true")
    sect.append(cols)


def _borders(table) -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "000000")
        borders.append(element)
    tbl_pr.append(borders)
    width = OxmlElement("w:tblW")
    width.set(qn("w:w"), str(COL_TWIPS))
    width.set(qn("w:type"), "dxa")
    tbl_pr.append(width)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)


def _cell(cell, styles: dict, text: str, style_id: str) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.style = styles[style_id]
    paragraph.paragraph_format.space_before = Twips(0)
    paragraph.paragraph_format.space_after = Twips(0)
    paragraph.add_run(text)
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for edge, val in (("top", "40"), ("left", "60"), ("bottom", "40"), ("right", "60")):
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:w"), val)
        node.set(qn("w:type"), "dxa")
        mar.append(node)
    tc_pr.append(mar)


def _table(doc: Document, styles: dict, rows: list[list[str]], widths: list[int]) -> None:
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _borders(table)
    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for col, width in zip(grid.findall(qn("w:gridCol")), widths):
            col.set(qn("w:w"), str(width))
    for r_index, row in enumerate(rows):
        style_id = "Tablecolhead" if r_index == 0 else "Tablecopy"
        for c_index, text in enumerate(row):
            _cell(table.rows[r_index].cells[c_index], styles, text, style_id)
            tc_pr = table.rows[r_index].cells[c_index]._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(widths[c_index]))
            tc_w.set(qn("w:type"), "dxa")


def _clear(doc: Document):
    body = doc.element.body
    sect = body.find(qn("w:sectPr"))
    for child in list(body):
        if child is not sect:
            body.remove(child)
    return sect


def build() -> None:
    if not TEMPLATE.is_file():
        raise SystemExit(f"missing template: {TEMPLATE}")
    doc = Document(str(TEMPLATE))
    styles = _styles(doc)
    final = _clear(doc)

    _p(doc, styles, "Papertitle", "A File Label Is Not an Audit Level")
    author = _p(doc, styles, "Author")
    author.add_run("Parvaz Jamei")
    for line in (
        "Independent researcher",
        "Mashhad, Iran",
        "parvaz.jamie@gmail.com",
        "ORCID: 0009-0002-9980-270X",
    ):
        author.add_run("\n")
        run = author.add_run(line)
        run.italic = True

    abstract = (
        "Abstract—Credibility guides say what evidence a computational model "
        "should carry, but they do not grade one file from its declared label. "
        "This paper grades the bundle. The label stored in the campaign file "
        "maps only to an internal grade of 3. Public grade 4 is recorded only "
        "when replay is verified and an interval is present on at least 16 "
        "seeds. The positive control, thirty paired seeds, reaches grade 4. "
        "Its contrast of 16.49 comes from two settings changed together. A "
        "device score table that carries regulatory labels and no recorded run "
        "stays at grade 0. A declared model risk has a separate bar and does "
        "not move the grade. Six deletions of a ladder condition fall below "
        "grade 4. That count is not a rate over the published literature."
    )
    _p(doc, styles, "Abstract", abstract)
    keywords = _p(
        doc,
        styles,
        "Keywords",
        "Keywords—evidence audit, computational model credibility, unit of "
        "analysis, credibility ladder, in silico",
    )
    title_sect = deepcopy(final)
    _set_cols(title_sect, "1", "0")
    keywords._p.get_or_add_pPr().append(title_sect)
    _set_cols(final, "2", "360")

    _p(doc, styles, "Heading1", "Introduction")
    intro = _p(doc, styles, "TextBody")
    _runs(
        intro,
        [
            (
                "The November 2023 guidance of the U.S. Food and Drug "
                "Administration ties the credibility of a physics-based "
                "simulation to the decision it informs, and it places a "
                "standalone machine-learning model outside that scope [1]. "
                "The American Society of Mechanical Engineers (ASME) V&V 40 "
                "asks for the question of interest, the context of use, and "
                "the consequence of the decision [2]. NASA-STD-7009B "
                "separates the capability of a model from permission to "
                "transfer a result [3]. None of these documents returns a "
                "grade for one research file. Pathmanathan and colleagues "
                "carry the credibility chain down to the submodels of an in "
                "silico clinical trial [4]. This paper asks the same question "
                "of one auditor: with only the evidence inside the bundle, "
                "where does the claim stop.",
                False,
            )
        ],
    )
    _p(
        doc,
        styles,
        "TextBody",
        "Three measurements are reported. A file label is not the audit "
        "grade, and a declared model risk does not move that grade. A "
        "phenomenon closes only from an executed treatment arm. Six "
        "requirement deletions fall below grade 4. The third measurement is "
        "not a percentage of published claims. No dual extraction was "
        "performed, and no such rate is stated. The auditor is "
        "not an external rater.",
    )
    _p(
        doc,
        styles,
        "TextBody",
        "The engine does not know a domain, and it was not rewritten for "
        "medicine. A domain profile names the port. The names in this "
        "repository are artificial life, biomedical, and hardware. Records "
        "from Avida, a comma-separated table from MABE2, and an Overview, "
        "Design concepts, and Details description are read through that "
        "port and are not the product of this paper. An ESP32 port is "
        "implemented and is not one of the measurements below. The "
        "configuration string that would claim an ASME V&V 40 pass is "
        "rejected. This tool does not issue an ASME, FDA, or IEC certificate. "
        "Viceconti and colleagues set an in silico trial on context, risk, "
        "and a verification chain [5]. Here that chain becomes a grade on "
        "one file, not a certificate for a product.",
    )
    _p(
        doc,
        styles,
        "TextBody",
        "MIRROR assembles a local evidence bundle for inspection before "
        "release and does not offer a regulatory guarantee [6]. NovaFabric "
        "records an agent run in a signed capsule and does not set a claim "
        "ceiling [7]. The difference in this work is a grade computed from "
        "the conditions present in the bundle.",
    )

    _p(doc, styles, "Heading1", "Audit ladder")
    _p(
        doc,
        styles,
        "TextBody",
        "The auditor reads the bundle. It does not call the engine. Each "
        "grade requires every condition of the grades below it. Grade 0 "
        "means that software identity, source digest, artifact, seed list, "
        "configuration fingerprint, artifact manifest, and run record are "
        "not all present. Grade 1 has those six items and still lacks a "
        "paired treatment and control, a paired comparison, and a consistent "
        "measured difference. Grade 2 has the paired difference and still "
        "lacks an intervention or a deletion, a negative control, verified "
        "replay with a fingerprint, a direction of effect, and a complete "
        "artifact accompanied by a written limitation. Grade 3 has those "
        "and still lacks a numeric interval or at least 16 seeds. Grade 4 "
        "has the interval and the seed count. Grade 5 also requires an "
        "archive identifier separate from the identifier of the software "
        "bundle, a written limitation, and statistical evidence together "
        "with a deletion. In this implementation the public name of grade 4 "
        "is replicated effect. Table I names only the new condition at each "
        "step, not the full list.",
    )
    _p(doc, styles, "Tablehead", "Condition that holds the grade in place")
    _table(
        doc,
        styles,
        [
            ["Held", "If this is missing"],
            ["0", "Version, seeds, fingerprint, manifest, run record"],
            ["1", "Paired arms, paired comparison, consistent difference"],
            ["2", "Intervention, negative control, replay, written limit"],
            ["3", "Numeric interval, or at least 16 seeds"],
            ["4", "Archive identifier separate from the software bundle"],
        ],
        [900, 3800],
    )
    _p(
        doc,
        styles,
        "TextBody",
        "On a compared arm, more outcome rows than seeds void both the "
        "interval and the condition of 16 seeds. A subsample is not a new "
        "seed. The hash is taken from the file bytes and does not rewrite "
        "them. The default test is a sign-flip permutation with a Holm "
        "correction and a bias-corrected and accelerated interval, written "
        "BCa below. A studentized bootstrap is optional when the number of "
        "pairs is at most 40. A hardware connection is optional and does "
        "not create a second engine.",
    )

    _p(doc, styles, "Heading1", "Two controls")
    _p(
        doc,
        styles,
        "TextBody",
        "The label inside the file has a nominal map. The string intervention "
        "supported is internal grade 3. That name alone does not confer "
        "public grade 4. The auditor is separate from the engine. These "
        "thresholds belong to this implementation. They are not approval of "
        "a device.",
    )
    _p(
        doc,
        styles,
        "TextBody",
        "The positive control is the source-bias campaign HE01: replayable, "
        "with 30 paired seeds. The results file, fingerprint prefix "
        "28f812c5, contains three comparisons. Against the open channel with "
        "no source bias, the difference is 16.49, the raw Monte Carlo p "
        "value is 4.99975 × 10−5, the Holm p value is 1.50 × 10−4, and the "
        "BCa interval is 14.25 to 19.14. The p value is a floor from 20,000 "
        "draws, not a zero. The primary comparison changes two settings "
        "together. The source-fitness threshold moves from 1.5 to 0, and "
        "the acceptance policy moves from fitness-weighted to threshold. "
        "The difference 16.49 belongs to that pair of settings, not to either setting alone. "
        "Against the closed channel and against empty content the difference "
        "is 30.67 and the interval is 26.03 to 35.32. In those two contrasts, both content and "
        "bias change. An optional studentized interval on the same 30 "
        "differences runs from about 14.05 to 19.30 and leaves the results "
        "file unchanged. The auditor returns grade 4 because replay, the "
        "interval, and the seed count hold.",
    )
    _p(
        doc,
        styles,
        "TextBody",
        "The negative control is a declared score table for a device model. "
        "The question was whether a size choice would be licensed. There is "
        "no ISO 14879-1 test and no implant. Model influence is 2 and "
        "decision consequence is 3. The treatment scores are 0.12, 0.11, "
        "and 0.13. The control scores are 0.20, 0.19, and 0.21. The declared "
        "labels are software in a medical device, class B of IEC 62304 [8], "
        "category II of the International Medical Device Regulators Forum "
        "(IMDRF) [9], and evidence categories 1, 3, and 8 of the 2023 "
        "guidance, with the model declared as physics-based. Replay is not "
        "verified, and the artifact manifest is among the conditions for "
        "leaving grade 0, so the grade is 0. ASME VVUQ 40.1-2026 is a worked "
        "tibial-tray example, not a pass bit, and that example is not run "
        "here [10]. Table II records the distance between the two controls.",
    )
    _p(doc, styles, "Tablehead", "Positive and negative controls")
    _table(
        doc,
        styles,
        [
            ["Bundle", "Declared", "Executed", "Grade"],
            ["HE01", "File label", "Replay, 30 seeds, interval", "4"],
            ["Device table", "Regulatory labels", "No recorded run", "0"],
        ],
        [1100, 1200, 1800, 600],
    )
    _p(
        doc,
        styles,
        "TextBody",
        "Grade 5 on HE01 lacks only an archived artifact or a DOI for the "
        "campaign itself. The software identifier 10.5281/zenodo.20337435 "
        "is not counted as that archive. The positive control therefore "
        "stays at grade 4.",
    )
    _p(
        doc,
        styles,
        "TextBody",
        "On these two bundles, changing only declared metadata did not raise "
        "the grade. The fields tried were model influence, decision "
        "consequence, the software-in-a-device flag, the IEC and IMDRF "
        "labels, the FDA evidence categories, and the typed word adequate. "
        "The check covers the fields of this port. Declaring that a model "
        "is not physics-based records the scope note in the 2023 guidance "
        "and still does not move the ladder.",
    )

    _p(doc, styles, "Heading1", "Closure and the risk bar")
    _p(
        doc,
        styles,
        "TextBody",
        "The credibility worksheet ranks a phenomenon. The rank alone does "
        "not close it. Closure requires the arm to be in the bundle, the "
        "role to be treatment, and the arm to be side A of a comparison "
        "whose interval bounds are both finite. The auditor must be at "
        "grade 4 or higher, and replay must be verified. If the phenomenon "
        "names a maximum interval width, the interval must be no wider. One "
        "arm closes one phenomenon. A second phenomenon on the same arm is "
        "marked shared and stays open. An arm that is present but fails the "
        "checks is not closed. A rank with no arm stays declared.",
    )
    _p(
        doc,
        styles,
        "TextBody",
        "On the study bound to HE01, source-fitness bias and the life-loop "
        "campaign both close. The life loop is a campaign, not a device, and "
        "it carries no FDA evidence category, so the row is not standing in "
        "for code verification. Contact stress and patient geometry stay "
        "declared. Patient geometry remains at a usable level of 2. Because "
        "not every submodel was executed, the coupled ceiling is empty. The "
        "claim grade of the campaign is still 4. The primary interval is "
        "about 4.89 wide. A tolerance of 1.0 does not close source bias. A "
        "tolerance of 6.0 does. A closed channel is not a treatment arm and "
        "does not close a phenomenon. Two submodels that share a "
        "configuration fingerprint are not independent and do not form a "
        "ceiling. Two replayed bundles at grade 4 with different "
        "fingerprints can set a ceiling of 4. That ceiling does not change "
        "the public grade. It says only that a coupled model stays with its "
        "weakest executed part. The ranking is the phenomena identification "
        "and ranking table used in nuclear safety: importance against "
        "knowledge [11]. A high-importance row stays open unless knowledge "
        "is adequate and the row was measured. The cap on the weakest "
        "submodel is the building-block rule [3]. A submodel that is not "
        "identifiable cannot contribute above 1. Evidence limited to "
        "calibration, plausibility, or emergent behavior, categories 2, 6, "
        "and 7 of the 2023 guidance, cannot contribute above 2.",
    )
    _p(doc, styles, "Tablehead", "Phenomenon closure on the HE01 study")
    _table(
        doc,
        styles,
        [
            ["Row", "Evidence", "Result"],
            ["Source bias", "Treatment, grade 4, replay", "Closed"],
            ["Life loop", "Executed campaign", "Closed"],
            ["Contact stress", "Rank, no arm", "Declared only"],
            ["Patient geometry", "Declared submodel, level 2", "Declared only"],
        ],
        [1400, 2000, 1300],
    )
    _p(
        doc,
        styles,
        "TextBody",
        "The unit of analysis is the seed, not a row of subsamples. If a "
        "compared arm has more values than seeds, the interval and the "
        "16-seed condition both fail, and a pseudoreplication warning is "
        "stored. A subsample is not a replicate [12]. HE01 has one value "
        "per seed and remains at grade 4.",
    )
    _p(
        doc,
        styles,
        "TextBody",
        "Risk on this port is the maximum of declared influence and declared "
        "consequence. The question is the one ASME V&V 40 asks, whether the "
        "evidence is commensurate with model risk [2]. The numbers are this "
        "implementation, not an FDA table. Risk 1 asks for grade 2, risk 2 "
        "for grade 3, and risk 3 for grade 4. From risk 2 upward, an open "
        "high-importance phenomenon also blocks the bar. The bar does not "
        "call the auditor and does not change the grade. Table IV is that "
        "comparison. The device table is risk 3 at grade 0, so the bar is "
        "not met. HE01 with only the executed source-bias phenomenon meets "
        "risk 3 and stays at grade 4. The same campaign, with contact stress "
        "added and no arm for it, is still grade 4, and the bar is not met "
        "because that phenomenon is open. Declaring the risk neither closes "
        "the open phenomenon nor lowers the grade. The committed result has "
        "fingerprint prefix b053e7f1.",
    )
    _p(doc, styles, "Tablehead", "Declared risk against the audit grade")
    _table(
        doc,
        styles,
        [
            ["Bundle", "Risk", "Grade", "Bar"],
            ["Device table", "3", "0", "Not met"],
            ["HE01, source bias only", "3", "4", "Met"],
            ["HE01 plus contact stress", "3", "4", "Not met"],
        ],
        [1900, 700, 800, 1300],
    )

    _p(doc, styles, "Heading1", "Requirement deletions")
    _p(
        doc,
        styles,
        "TextBody",
        "The intact reference is grade 4. Six bundles were built by removing "
        "one condition, and all six stayed below 4. Identical arms, a "
        "zero-width interval, and an unpaired comparison stay at grade 1. "
        "Missing replay, and an empty limitation, stay at grade 2. Three "
        "seeds stay at grade 3. The population of the measurement is a "
        "deterministic deletion of a condition. The six bundles are not an "
        "independent random sample, so no binomial interval and no "
        "false-accept rate are reported. The count is not six out of seven, "
        "and it is not a percentage of papers. Table V lists the grades.",
    )
    _p(doc, styles, "Tablehead", "One condition removed from a grade-4 reference")
    _table(
        doc,
        styles,
        [
            ["Deletion", "Grade"],
            ["Identical arms", "1"],
            ["Zero-width interval", "1"],
            ["No paired comparison", "1"],
            ["No replay", "2"],
            ["Empty limitation", "2"],
            ["Three seeds instead of 16", "3"],
        ],
        [3200, 1500],
    )
    _p(
        doc,
        styles,
        "TextBody",
        "A separate row changes the label of a sensitivity arm and still "
        "receives grade 4. The row did not escape the auditor. A "
        "confirmatory negative-control arm is still in the bundle, and the "
        "flags on that row are not read. The row is a probe, not an escape "
        "trial. No external rater took part. Each deletion stops at the step "
        "that owns the removed condition. That match is what the ladder "
        "specifies. The probe was kept out of the six, and no rate was built "
        "from it.",
    )

    _p(doc, styles, "Heading1", "Discussion")
    _p(
        doc,
        styles,
        "TextBody",
        "The measurements are grades of the evidence inside a bundle. The "
        "file label does not confer grade 4. A phenomenon without an "
        "executed arm does not close. Deletions of ladder conditions stay "
        "below grade 4. The risk bar does not move the grade. A percentage "
        "of orthopedic or cardiac claims was not measured. That percentage "
        "would need an entry protocol, two extractors, and agreement "
        "between raters. This paper is not that study.",
    )
    _p(
        doc,
        styles,
        "TextBody",
        "HE01 is the reference campaign of the auditor. It is not a clinical "
        "result and not a device test. The intervention changes two settings "
        "together and reports the final energy of a receiver in the "
        "simulation. The device table is not a bench test. The phenomenon "
        "ranking and the building-block ceiling are used here only on the "
        "rows of this worksheet. The deletions follow the auditor's own "
        "conditions, so a grade below 4 is the ladder's stated expectation "
        "and not an error rate for an outside population. A change of role, "
        "while the confirmatory arm remains, is not an escape trial. The "
        "hardware port is outside these measurements. The software version "
        "is read from the project configuration and is not written as a "
        "constant inside the bundle.",
    )
    _p(
        doc,
        styles,
        "TextBody",
        "Configuration rejects the strings that would claim FDA clearance, "
        "clinical validation, IEC 62304 certification, or an ASME V&V 40 "
        "pass. Rejection is not an audit grade. It means the tool will not "
        "accept the string as configuration. Four observations can be "
        "repeated from the committed files. The campaign audit returns "
        "grade 4, and grade 5 lacks only a separate archive identifier. The "
        "device table returns grade 0 and lacks an artifact manifest. The "
        "committed study and the deletion file match the live auditor. On "
        "HE01 the risk bar leaves grade 4 unchanged: the bar is met when the "
        "listed phenomenon was executed, and it is not met when a "
        "high-importance phenomenon has no arm. The study fingerprint prefix "
        "is d176f0ab and the deletion-file prefix is 3c8a8a1f.",
    )

    _p(doc, styles, "Heading1", "Conclusion")
    _p(
        doc,
        styles,
        "TextBody",
        "A file label, an IEC 62304 class, an IMDRF phrase, a typed "
        "knowledge word, and a declared risk do not raise the audit grade. "
        "The campaign file reaches grade 4 because replay and an interval "
        "on 30 seeds hold. The table with no recorded run stays at grade 0. "
        "The same grade 4 meets the risk-3 bar when the listed phenomenon "
        "was executed, and it does not meet that bar when a high-importance "
        "phenomenon is only declared. Six requirement deletions stay below "
        "grade 4, and the count is not a literature rate. Code and the "
        "committed results are in the public repository github.com/\u200b"
        "Parvaz-Jamei/\u200bcodontrace-genesis. The software DOI is "
        "10.5281/zenodo.20337435.",
    )

    _p(doc, styles, "Heading5", "Acknowledgment")
    _p(
        doc,
        styles,
        "TextBody",
        "The biomedical labels follow the FDA, ASME, IEC, and IMDRF "
        "documents cited above. The author is solely responsible for the "
        "software and for the measurements in this paper. The study grades "
        "evidence bundles and does not report a clinical study or a "
        "regulatory submission.",
    )

    _p(doc, styles, "Heading5", "References")
    refs = [
        'U.S. Food and Drug Administration, “Assessing the credibility of computational modeling and simulation in medical device submissions,” Nov. 2023.',
        "Assessing Credibility of Computational Modeling through Verification and Validation: Application to Medical Devices, ASME V&V 40-2018. New York: ASME, 2018.",
        "NASA-STD-7009B, Standard for Models and Simulations. Washington, DC: NASA, Mar. 5, 2024.",
        'P. Pathmanathan, K. Aycock, A. Badal, R. Bighamian, J. Bodner, B. A. Craven, and S. Niederer, “Credibility assessment of in silico clinical trials for medical devices,” PLoS Comput. Biol., vol. 20, no. 8, Art. no. e1012289, Aug. 2024, doi: 10.1371/journal.pcbi.1012289.',
        'M. Viceconti, F. Pappalardo, B. Rodriguez, M. Horner, J. Bischoff, and F. Musuamba Tshinanu, “In silico trials: verification, validation and uncertainty quantification of predictive models used in the regulatory evaluation of biomedical products,” Methods, vol. 185, pp. 120–127, 2021, doi: 10.1016/j.ymeth.2020.01.011.',
        'A. Sokolov, “MIRROR: local evidence bundles for reproducible research software review,” Zenodo, May 2026, doi: 10.5281/zenodo.20463358.',
        'M. Seyedkazemi Ardebili, “NovaFabric: tamper-evident, replayable evidence for autonomous AI agent runs,” arXiv:2609.12582, 2026.',
        "IEC 62304:2006+AMD1:2015, Medical device software—Software life cycle processes. Geneva: IEC.",
        "Software as a Medical Device: Possible Framework for Risk Categorization, IMDRF/SaMD WG/N12 FINAL:2014, and Characterization Considerations, IMDRF/SaMD WG/N81 FINAL:2025.",
        "Tibial Tray Worst-Case Size Identification for Fatigue Testing, ASME VVUQ 40.1-2026. New York: ASME, 2026.",
        "Phenomena Identification and Ranking Table, NEA/CSNI/R(2017)18. Paris: OECD Nuclear Energy Agency, 2018.",
        'S. H. Hurlbert, “Pseudoreplication and the design of ecological field experiments,” Ecological Monographs, vol. 54, no. 2, pp. 187–211, 1984, doi: 10.2307/1942661.',
    ]
    for ref in refs:
        _p(doc, styles, "References", ref.replace("/", "/\u200b").replace("doi:", "doi:\u200b"))

    core = doc.core_properties
    core.author = "Parvaz Jamei"
    core.title = "A File Label Is Not an Audit Level"
    core.subject = "BAIC 2026"
    core.category = "BAIC2026"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
