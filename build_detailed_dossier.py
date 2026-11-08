from pathlib import Path
import json

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "TQ_BioNet_v3_Complete_Project_Documentation.docx"
OUTPUTS = ROOT / "outputs"

BLUE = "2E74B5"
NAVY = "1F4D78"
INK = "0B2545"
MUTED = "5D6773"
PALE_BLUE = "E8EEF5"
PALE_GRAY = "F4F6F9"


def font(run, size=11, bold=False, color="222222", italic=False):
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    node = tc_pr.find(qn("w:shd"))
    if node is None:
        node = OxmlElement("w:shd")
        tc_pr.append(node)
    node.set(qn("w:fill"), fill)


def margins(cell, top=80, bottom=80, start=120, end=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    node = tc_pr.first_child_found_in("w:tcMar")
    if node is None:
        node = OxmlElement("w:tcMar")
        tc_pr.append(node)
    for side, val in (("top", top), ("bottom", bottom), ("start", start), ("end", end)):
        el = node.find(qn(f"w:{side}"))
        if el is None:
            el = OxmlElement(f"w:{side}")
            node.append(el)
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")


def table_geometry(table, widths):
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), "9360")
    tbl_w.set(qn("w:type"), "dxa")
    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")
    for row in table.rows:
        for index, width in enumerate(widths):
            cell = row.cells[index]
            cell.width = Inches(width)
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(int(width * 1440)))
            tc_w.set(qn("w:type"), "dxa")


def mark_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    node = OxmlElement("w:tblHeader")
    node.set(qn("w:val"), "true")
    tr_pr.append(node)


def add_page_number(p):
    run = p.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(end)
    font(run, 9, color=MUTED)


def setup(doc):
    sec = doc.sections[0]
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(sec, attr, Inches(1))
    sec.header_distance = Inches(0.492)
    sec.footer_distance = Inches(0.492)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25
    for style_name, size, color, before, after in [
        ("Heading 1", 16, BLUE, 18, 10),
        ("Heading 2", 13, BLUE, 14, 7),
        ("Heading 3", 12, NAVY, 10, 5),
    ]:
        style = doc.styles[style_name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = hp.add_run("TQ-BioNet v3.0 | Complete Project Documentation")
    font(r, 9, color=MUTED)
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = fp.add_run("Project dossier | Page ")
    font(r, 9, color=MUTED)
    add_page_number(fp)


def para(doc, text="", size=11, bold=False, color="222222", italic=False, after=6, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.25
    if align is not None:
        p.alignment = align
    if text:
        r = p.add_run(text)
        font(r, size=size, bold=bold, color=color, italic=italic)
    return p


def heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    font(r, {1: 16, 2: 13, 3: 12}[level], True, {1: BLUE, 2: BLUE, 3: NAVY}[level])
    return p


def bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(text)
    font(r)
    return p


def number(doc, text):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(text)
    font(r)
    return p


def callout(doc, title, body, fill=PALE_BLUE):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    table_geometry(t, [6.5])
    c = t.cell(0, 0)
    shade(c, fill)
    margins(c, 130, 130, 160, 160)
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(title)
    font(r, 10.5, True, NAVY)
    p = c.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(body)
    font(r, 10.5, color="333333")
    para(doc, after=2)


def table(doc, headers, rows, widths, font_size=9.2):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    table_geometry(t, widths)
    mark_header(t.rows[0])
    for i, value in enumerate(headers):
        c = t.rows[0].cells[i]
        shade(c, PALE_BLUE)
        margins(c)
        c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(str(value))
        font(r, font_size, True, INK)
    for row in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row):
            c = cells[i]
            margins(c)
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(str(value))
            font(r, font_size, color="222222")
    para(doc, after=2)
    return t


def formula(doc, label, expression, explanation):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    table_geometry(t, [6.5])
    c = t.cell(0, 0)
    shade(c, PALE_GRAY)
    margins(c, 100, 100, 150, 150)
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(label)
    font(r, 10, True, NAVY)
    p = c.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(expression)
    r.font.name = "Cambria Math"
    r._element.rPr.rFonts.set(qn("w:ascii"), "Cambria Math")
    r._element.rPr.rFonts.set(qn("w:hAnsi"), "Cambria Math")
    r.font.size = Pt(11)
    r.font.color.rgb = RGBColor.from_string(INK)
    p = c.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(explanation)
    font(r, 9.8, color="333333")
    para(doc, after=2)


def fig(doc, path, caption, width=6.1):
    if path.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(path), width=Inches(width))
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(caption)
        font(r, 9.5, color=MUTED, italic=True)
        p.paragraph_format.space_after = Pt(8)


def load_json(name):
    return json.loads((OUTPUTS / name).read_text())


def build():
    metrics = load_json("validation_metrics.json")
    manifest = load_json("experiment_manifest_validation.json")
    ensemble = metrics["VotingEnsemble"]
    doc = Document()
    setup(doc)

    # Cover
    para(doc, after=50)
    p = para(doc, "COMPLETE TECHNICAL PROJECT HANDBOOK", 11, True, BLUE, after=10, align=WD_ALIGN_PARAGRAPH.CENTER)
    p = para(doc, "TQ-BioNet v3.0", 30, True, INK, after=7, align=WD_ALIGN_PARAGRAPH.CENTER)
    p = para(doc, "Candidate-Level Pulmonary Nodule Classification on 3D Thoracic CT", 15, False, NAVY, after=18, align=WD_ALIGN_PARAGRAPH.CENTER)
    p = para(doc, "End-to-end design, theory, implementation, execution workflow, validation, and reproducibility record", 11.5, False, MUTED, True, after=30, align=WD_ALIGN_PARAGRAPH.CENTER)
    callout(doc, "How to use this document", "This is the master A-to-Z record for the project. It describes the purpose, the internal logic of every major module, the mathematical definitions, source files, runtime sequence, cache behavior, validation evidence, outputs, and responsible limits of the claimed results.", PALE_GRAY)
    table(doc, ["Project state", "Algorithm", "Development data", "Independent validation"], [["Frozen", "TQ-BioNet v3.0", "Subsets 0-5: 1,446 candidates", "Subsets 6-9: 926 candidates"]], [1.1, 1.25, 2.05, 2.1])
    doc.add_page_break()

    heading(doc, "1. Contents and Reading Map")
    para(doc, "The handbook is intentionally detailed. The first half explains what the system is and how it transforms CT candidates into a prediction. The second half documents how the project is executed, tested, reproduced, and interpreted.")
    table(doc, ["Part", "Sections", "Purpose"], [
        ["A. Project foundation", "2-4", "Problem definition, scope, system architecture, and data flow."],
        ["B. Technical method", "5-10", "Data construction, CT processing, mathematics, feature assembly, classifiers, and statistics."],
        ["C. Execution and evidence", "11-16", "Run sequence, cache/manifest behavior, results, audits, repository guide, and outputs."],
        ["D. Governance", "17-18", "Limits, responsible interpretation, glossary, formulas, and checklists."],
    ], [1.55, 1.1, 3.85])
    callout(doc, "Important interpretation", "TQ-BioNet evaluates candidate-centred CT patches. A positive result means the patch is classified as a positive candidate in this project-defined LUNA16 task. It is not a whole-patient cancer diagnosis, a prognosis, a clinical recommendation, or evidence of hospital deployment readiness.")

    heading(doc, "2. Project Identity and Purpose")
    heading(doc, "2.1 What the project does", 2)
    para(doc, "TQ-BioNet is a reproducible machine-learning project for pulmonary nodule candidate classification in 3D thoracic CT. It assumes that a preceding candidate-generation stage has already supplied anatomical coordinates. At each coordinate, the project extracts a fixed-size CT patch, transforms the patch into deterministic mathematical descriptors, and predicts whether the candidate belongs to the positive or negative class defined by the LUNA16-derived target construction.")
    heading(doc, "2.2 Why a candidate-classification stage is needed", 2)
    para(doc, "Candidate generators deliberately favour high sensitivity and may return many anatomical false positives. Vessels, vessel bifurcations, pleural attachments, scars, and noise can resemble nodules when viewed locally. TQ-BioNet is intended as a false-positive-reduction classifier: it receives candidate patches and assigns an evidence-based class probability.")
    heading(doc, "2.3 Design goals", 2)
    table(doc, ["Goal", "How the implementation addresses it"], [
        ["Deterministic feature extraction", "No learned convolutional feature extractor; feature values are calculated from image content with fixed procedures."],
        ["Mixed geometric evidence", "Topology, density-well states, fractal structure, and Hessian curvature capture different patch properties."],
        ["Cohort separation", "Development Subsets 0-5 are used for model fitting; Subsets 6-9 are only used for final inference."],
        ["Traceable outputs", "Predictions, metrics, per-subset JSON, feature mapping, cache metadata, and manifests are saved."],
        ["Integrity checking", "Versioned caches are isolated per subset and X.npy is SHA256-verified before reconstruction."],
    ], [2.0, 4.5])

    heading(doc, "3. Scope, Inputs, Outputs, and Boundaries")
    heading(doc, "3.1 Inputs", 2)
    table(doc, ["Input", "Where it comes from", "How it is used"], [
        ["CT scan", "LUNA16 subset folder", "Read by SimpleITK, resampled to 1.0 mm spacing, converted to a NumPy volume."],
        ["Positive annotations", "annotations.csv", "Coordinates become class-1 candidate targets when their series UID is in the active subset."],
        ["Negative candidates", "candidates_V2.csv", "Records with class = 0 provide class-0 candidates, balanced scan-by-scan against positives."],
        ["Versioned cache", "luna16_data/cache/tq_bionet_v3/subsetN", "Stores features, labels, group IDs, coordinates, and metadata for a single subset."],
        ["Frozen configuration", "run_independent_validation.py and TQ-BioNet_v3.0_FROZEN.md", "Defines selected features, model settings, seed, threshold, and validation partition."],
    ], [1.35, 2.0, 3.15])
    heading(doc, "3.2 Outputs", 2)
    table(doc, ["Output", "Meaning"], [
        ["Candidate probabilities", "SVM, XGBoost, Random Forest, and soft-voting probabilities for each independent validation candidate."],
        ["Candidate label", "Voting-ensemble decision using the fixed threshold p >= 0.50."],
        ["Combined metrics", "Accuracy, sensitivity, specificity, precision, F1-score, AUC-ROC, confidence intervals, and confusion matrix for all validation candidates."],
        ["Per-subset metrics", "The same statistics computed separately for each held-out subset 6, 7, 8, and 9."],
        ["Manifest", "Provenance record for the validation phase, sample count, versions, seed, cache hashes, and runtime."],
    ], [1.65, 4.85])
    heading(doc, "3.3 What the project does not claim", 2)
    for item in [
        "It does not estimate a patient's probability of having lung cancer from a complete CT study.",
        "It does not evaluate a full candidate detector, scan-level sensitivity, FROC, clinical worklist reduction, or reader performance.",
        "It does not use a natural screening prevalence because the negative class is balanced per scan.",
        "It does not establish external hospital generalisation, prospective safety, clinical utility, or regulatory suitability.",
    ]:
        bullet(doc, item)

    heading(doc, "4. End-to-End Execution Flow")
    para(doc, "The active independent-validation execution is implemented in run_independent_validation.py. The workflow below describes the actual order of major operations and the state created at each stage.")
    table(doc, ["Step", "Code action", "Data state after the step", "Effect on final result"], [
        ["1", "Set validation_subsets = [6, 7, 8, 9].", "The test cohort is explicitly defined before loading data.", "Prevents ambiguity about which subsets are reported."],
        ["2", "Verify/rebuild validation caches.", "Each validation subset has a separate versioned cache directory.", "Ensures features are available and tied to a known subset."],
        ["3", "Reconstruct development data from 0-5.", "X_dev, y_dev, groups_dev, and coordinates are concatenated from only development caches.", "Makes development the only source for model fitting."],
        ["4", "Reconstruct validation data from 6-9.", "X_val, y_val, groups_val, coordinates, and subset IDs are concatenated from only validation caches.", "Keeps the held-out cohort separate."],
        ["5", "Select 15 locked feature columns.", "Both matrices have the same fixed model-input columns.", "Prevents accidental feature-order drift."],
        ["6", "Fit StandardScaler on development data; transform validation data.", "Scaler mean and standard deviation come only from X_dev.", "Avoids scaler leakage from held-out data."],
        ["7", "Fit SVM, XGBoost, and Random Forest on development data.", "All trainable parameters are estimated from the development cohort.", "Validation labels do not affect training."],
        ["8", "Predict validation probabilities and form soft vote.", "One probability vector per model and the arithmetic ensemble mean.", "Produces the score used for ROC/AUC and threshold metrics."],
        ["9", "Calculate statistics and export evidence.", "JSON, CSV, figures, and manifest are written under outputs/.", "Allows later verification of every reported result."],
    ], [0.38, 1.55, 2.45, 2.12], font_size=8.3)
    callout(doc, "No training-data mutation during validation", "The independent driver fits new frozen-configured classifiers on the complete development cohort and applies them to the untouched validation cohort. It does not append validation data to development caches or refit the scaler on validation data.")

    heading(doc, "5. Candidate Target Construction")
    heading(doc, "5.1 Positive class construction", 2)
    para(doc, "The extraction procedure reads annotations.csv and keeps annotations whose series UID belongs to a scan in the active subset. These selected annotation coordinates are assigned Label = 1. Each positive target retains the scan series UID and its world-space x, y, and z coordinates.")
    heading(doc, "5.2 Negative class construction", 2)
    para(doc, "The procedure reads candidates_V2.csv and filters to records that both belong to an active scan and have class = 0. These candidate coordinates are assigned Label = 0. For a given scan, the number of selected negatives is min(number of positives, number of available class-0 candidates). The resulting sampling is balanced within each scan when sufficient negatives are available.")
    formula(doc, "Per-scan negative target count", "n_negative_selected(scan) = min(n_positive(scan), n_negative_available(scan))", "This prevents a scan with many negative candidate records from dominating the training/validation sample count. It also means the cohort is not a natural-prevalence screening sample.")
    heading(doc, "5.3 Effect of balancing", 2)
    para(doc, "Balancing improves the ability to study discrimination between the two candidate classes without letting the dominant negative class overwhelm accuracy and the learning objective. At the same time, it changes the observed class prevalence. Therefore, accuracy and precision in this project describe the balanced candidate cohort rather than the positive predictive value that would occur in a real screening pipeline containing all detector candidates.")

    heading(doc, "6. CT Geometry, Resampling, and Patch Extraction")
    heading(doc, "6.1 Physical coordinates and voxel coordinates", 2)
    para(doc, "Candidate coordinates are stored in CT physical space. After resampling, the SimpleITK TransformPhysicalPointToIndex operation converts the physical coordinate into an image index. The returned index is reordered from x, y, z image coordinates into z, y, x array coordinates before NumPy indexing.")
    formula(doc, "Conceptual coordinate conversion", "voxel_index = round((world_coordinate - image_origin) / voxel_spacing)", "The implementation delegates the full transformation to SimpleITK so image origin and direction are respected. The equation expresses the central relationship between physical and voxel space.")
    heading(doc, "6.2 Isotropic resampling", 2)
    para(doc, "The source CT may have anisotropic spacing. The project uses linear interpolation and requests output spacing [1.0, 1.0, 1.0] mm. For each axis i, the output size is computed approximately as round(original_size_i x original_spacing_i / 1.0). This preserves the approximate physical field of view while making the extracted patch have consistent spatial sampling.")
    formula(doc, "Resampled size", "new_size_i = round(original_size_i x original_spacing_i / new_spacing_i)", "With new_spacing_i = 1.0 mm, a 32-voxel edge represents approximately 32 mm in every spatial direction.")
    heading(doc, "6.3 Patch extraction and boundary handling", 2)
    para(doc, "The patch half-width is 16 voxels. The initial patch limits are clamped to the image boundary. If an extracted patch has any dimension smaller than 32, a zero-initialized 32 x 32 x 32 volume is created and the available image voxels are copied into its leading region. This guarantees a fixed shape for later modules even when a candidate lies near the scan edge.")
    table(doc, ["Patch condition", "Implementation behavior", "Why it matters"], [
        ["Candidate is fully inside the volume", "Extract a 32 x 32 x 32 patch directly.", "Preserves the local CT context around the candidate."],
        ["Candidate is near an image boundary", "Extract the available region and zero-pad to 32 x 32 x 32.", "Keeps every feature function's input shape fixed."],
        ["Feature vector contains NaN or infinity", "Skip the candidate before saving to the cache.", "Prevents invalid numerical values from reaching the classifiers."],
    ], [1.65, 2.7, 2.15])

    heading(doc, "7. Local Intensity Standardization")
    para(doc, "The project standardizes each patch independently. Let P be the 32 x 32 x 32 patch. It computes the patch median m = median(P) and interquartile range q = Q75(P) - Q25(P). If q < 10^-6, the implementation replaces q with 1.0. It then standardizes, clips, and rescales the data.")
    formula(doc, "Local IQR standardization", "Z = (P - median(P)) / max(IQR(P), 1.0 when IQR < 10^-6)", "Subtracting the local median centres the patch; dividing by IQR scales according to its central intensity spread. This is local to the patch and has no learned global parameters.")
    formula(doc, "Clipping and normalization", "Z_clipped = clip(Z, -3, 3);  P_normalized = (Z_clipped + 3) / 6", "The output is constrained to [0, 1], which gives the downstream mathematical modules a stable intensity domain.")
    heading(doc, "7.1 Effect on the pipeline", 2)
    table(doc, ["Operation", "Effect"], [
        ["Median removal", "Reduces sensitivity to a patch-wide intensity offset."],
        ["IQR scaling", "Uses robust central spread rather than a mean/standard-deviation estimate that can be more affected by extreme values."],
        ["Clipping", "Limits the influence of unusually extreme standardized values."],
        ["Mapping to [0, 1]", "Provides a stable potential field and threshold range for the quantum, topology, and fractal modules."],
    ], [2.0, 4.5])

    heading(doc, "8. Mathematical Feature Modules")
    heading(doc, "8.1 Module integration overview", 2)
    para(doc, "The normalized patch is optionally downsampled to 16 x 16 x 16 before the eigenvalue solver. The resulting working patch feeds the quantum module. Its probability-density output feeds the topology and fractal modules. The working CT patch also feeds the Hessian module. All derived feature dictionaries are merged and alphabetically sorted before vector serialization.")

    heading(doc, "8.2 Quantum-inspired Schrödinger module", 2)
    para(doc, "The quantum module builds a sparse finite-difference approximation to a three-dimensional Laplacian. A one-dimensional second-difference matrix has -2 on the diagonal and +1 on immediate neighbours. The three-dimensional operator is formed with Kronecker products. The Hamiltonian combines a kinetic term with a potential term derived from the normalized patch.")
    formula(doc, "One-dimensional finite-difference Laplacian", "D1 = tridiag(1, -2, 1)", "D1 approximates the second spatial derivative under the implementation's boundary convention.")
    formula(doc, "Three-dimensional Laplacian", "D3 = D1 kron I kron I + I kron D1 kron I + I kron I kron D1", "The Kronecker-sum construction expands the one-dimensional operator along the three patch axes.")
    formula(doc, "Hamiltonian", "H = -m x D3 + diag(-C x P_normalized + epsilon)", "m is the mass coefficient, C is the potential scale, and epsilon is a fixed-seed 10^-5 Gaussian perturbation used to avoid exact degeneracy in the eigensolver.")
    para(doc, "The solver requests the lowest algebraic eigenvalues and their eigenvectors. The eigenvectors are reshaped to 3D wave functions and individually L2-normalized. The probability-density map used by later modules is a weighted combination of the first three squared wave functions, normalized by its maximum.")
    formula(doc, "Multi-state probability density", "rho = psi0^2 + 0.5 x psi1^2 + 0.25 x psi2^2; rho = rho / max(rho)", "The ground state contributes most strongly, while the next two states add information about local heterogeneity and structure.")
    table(doc, ["Output", "How it is derived", "Effect"], [
        ["quantum_eigenvalue_0 to quantum_eigenvalue_9", "Lowest ten eigenvalues of H in ascending order.", "Describe the low-energy density-well structure of the normalized patch."],
        ["Probability density rho", "Weighted squared wave functions, max-normalized.", "Creates a stable spatial representation for topology and fractal analysis."],
    ], [1.7, 2.5, 2.3])

    heading(doc, "8.3 Persistent-homology module", 2)
    para(doc, "The topology module first turns rho into a point cloud. It keeps coordinates with rho >= 0.01, sorts them by rho in descending order, and retains at most 400 highest-density points. If no point passes the threshold, it returns a single point at the patch centre. Ripser then computes persistence diagrams through homology dimension 1.")
    formula(doc, "Persistence lifespan", "l_i = d_i - b_i", "For each birth-death pair, the lifespan summarizes how long a topological structure persists as the filtration changes.")
    formula(doc, "Persistence entropy", "H = - sum_i p_i log(p_i + 10^-12), where p_i = l_i / sum_j l_j", "Entropy measures how evenly persistence is distributed across detected structures. The small term protects against log(0).")
    para(doc, "For H0 and H1 separately, the module records count, total persistence, maximum persistence, mean persistence, standard deviation, and entropy. Infinite deaths are replaced by 1.2 times the largest finite death for that homology dimension, or 1.0 if no finite death exists. Persistences are clipped at zero to limit numerical noise.")
    table(doc, ["Homology group", "Informal interpretation in the point-cloud representation", "Frozen features used"], [
        ["H0", "Connected components / density clusters.", "H0_entropy; H0_total_persistence."],
        ["H1", "Loops / tunnel-like structures in the point cloud.", "H1_count; H1_total_persistence."],
    ], [1.0, 2.8, 2.7])

    heading(doc, "8.4 Fractal geometry and lacunarity module", 2)
    para(doc, "The fractal module thresholds rho at 0.01 to form a binary mask. It computes a surface mask by subtracting an eroded mask from the original binary mask. The surface supports the box-counting fractal-dimension calculation; the full binary mask supports lacunarity calculations.")
    formula(doc, "Surface mask", "surface = binary_mask AND NOT binary_erosion(binary_mask)", "This retains boundary voxels and removes fully interior voxels.")
    formula(doc, "Box-counting dimension", "log N(s) = D_f log(1/s) + c", "The module counts occupied boxes at allowed powers-of-two scales and uses a linear fit; the fitted slope is D_f.")
    formula(doc, "Lacunarity", "Lambda = Var(M) / Mean(M)^2 + 1", "M is the distribution of binary-mask mass in sliding local boxes. Higher values indicate more heterogeneous gap structure.")
    para(doc, "The implementation pads the surface mask to a cubic power-of-two shape, tests box sizes 1, 2, 4, 8, and 16 when valid, and returns 0 when fewer than two scales are available. Lacunarity is calculated at sizes 2, 4, and 8; the frozen subset uses sizes 4 and 8.")

    heading(doc, "8.5 Hessian geometry module", 2)
    para(doc, "The Hessian module calculates first and second numerical gradients of the working patch. At the centre voxel, it forms a symmetric 3 x 3 Hessian matrix using the second derivatives and cross-derivatives. Its eigenvalues are converted to absolute values and sorted so L1 <= L2 <= L3.")
    formula(doc, "Hessian matrix at the patch centre", "H = [[dzz, dzy, dzx], [dzy, dyy, dyx], [dzx, dyx, dxx]]", "The components are second spatial derivatives measured at the central voxel of the working patch.")
    formula(doc, "Blobness and vesselness ratios", "R_B = L1 / (sqrt(L2 x L3) + 10^-6);  R_A = L2 / (L3 + 10^-6)", "The epsilon terms avoid division by zero. The ratios summarize relative principal-curvature magnitudes and help separate blob-like and tubular patterns.")
    table(doc, ["Hessian output", "Meaning in the code"], [
        ["hessian_L1, hessian_L2, hessian_L3", "Sorted absolute eigenvalue magnitudes at the working-patch centre."],
        ["blobness_ratio", "R_B calculated from L1, L2, and L3."],
        ["vesselness_ratio", "R_A calculated from L2 and L3."],
    ], [2.5, 4.0])

    heading(doc, "9. Feature Integration, Ordering, and Frozen Selection")
    para(doc, "The pipeline creates a feature dictionary by adding quantum eigenvalues, then updating it with topological, fractal, and Hessian feature dictionaries. It separately records extraction_time_sec but excludes it from the serialized vector. All remaining feature names are sorted alphabetically, and the vector is formed by reading the dictionary in that sorted-key order.")
    formula(doc, "Deterministic serialization", "keys = sorted(feature_names excluding extraction_time_sec);  x_j = features[keys_j]", "The same sorted names yield the same column order every time the feature extractor runs, assuming the same feature dictionary keys.")
    heading(doc, "9.1 Raw 31-feature space", 2)
    para(doc, "The raw vector contains 31 features: 12 persistence summaries, 10 quantum eigenvalues, 4 fractal/lacunarity features, and 5 Hessian features. outputs/feature_mapping.csv records the index-to-name mapping. This mapping is part of the reproducibility evidence.")
    heading(doc, "9.2 Locked 15-feature model input", 2)
    locked = [
        ["H0_entropy", "Persistent-homology entropy"], ["H0_total_persistence", "H0 total lifespan"],
        ["H1_count", "H1 feature count"], ["H1_total_persistence", "H1 total lifespan"],
        ["blobness_ratio", "Central Hessian blobness ratio"], ["fractal_dimension", "Surface box-counting slope"],
        ["hessian_L1", "First curvature magnitude"], ["hessian_L2", "Second curvature magnitude"],
        ["hessian_L3", "Third curvature magnitude"], ["lacunarity_4", "Gap variability at scale 4"],
        ["lacunarity_8", "Gap variability at scale 8"], ["quantum_eigenvalue_0", "Lowest quantum state"],
        ["quantum_eigenvalue_1", "Second quantum state"], ["quantum_eigenvalue_2", "Third quantum state"],
        ["vesselness_ratio", "Central Hessian tubular ratio"],
    ]
    table(doc, ["Feature", "Contribution to the frozen model input"], locked, [2.45, 4.05])
    para(doc, "The independent-validation driver creates a zero-valued dummy patch, obtains the same sorted raw-key list from the feature extractor, and resolves the locked names to their column indices. It applies those indices identically to the development and validation feature matrices.")

    heading(doc, "10. Classifiers, Scaling, Voting, and Decision Rule")
    heading(doc, "10.1 Development-only StandardScaler", 2)
    para(doc, "Only the SVM input is standardized by StandardScaler. The scaler is fitted on X_dev_pruned and then used to transform X_val_pruned without fitting again. XGBoost and Random Forest receive the unscaled 15-feature matrices as implemented in the current frozen driver.")
    formula(doc, "Feature scaling", "x_scaled_j = (x_j - mu_dev_j) / sigma_dev_j", "mu_dev_j and sigma_dev_j are calculated from the development cohort only. Validation values use these fixed parameters.")
    heading(doc, "10.2 SVM", 2)
    para(doc, "The SVM is instantiated as SVC(C=100.0, gamma='scale', probability=True, random_state=42). It uses an RBF kernel. The probability=True setting enables probability estimates used by the ensemble. gamma='scale' lets the library derive the RBF width from the scaled development input variance.")
    formula(doc, "RBF kernel", "K(x, z) = exp(-gamma x ||x - z||^2)", "The kernel compares two feature vectors by their squared Euclidean distance in the scaled 15-feature space.")
    heading(doc, "10.3 XGBoost and Random Forest", 2)
    para(doc, "XGBoost is configured with 200 estimators, maximum depth 5, learning rate 0.01, logloss evaluation, and random_state=42. Random Forest is configured with 150 estimators, maximum depth 4, and random_state=42. Both are fitted only on the raw pruned development features and labels.")
    heading(doc, "10.4 Soft voting", 2)
    formula(doc, "Voting-ensemble probability", "p_ensemble = (p_SVM + p_XGBoost + p_RF) / 3", "The three positive-class probabilities are equally weighted. No learned stacking layer is used.")
    formula(doc, "Fixed decision threshold", "y_hat = 1 if p_ensemble >= 0.50, otherwise 0", "Threshold-based accuracy, sensitivity, specificity, precision, F1-score, and confusion-matrix entries use this rule.")
    table(doc, ["Model", "Input matrix", "Frozen settings", "Role"], [
        ["SVM", "Scaled 15-feature development/validation matrices", "C=100; gamma='scale'; probability=True; seed 42", "Nonlinear margin-based probability model."],
        ["XGBoost", "Unscaled 15-feature matrices", "200 estimators; depth 5; learning rate 0.01; seed 42", "Boosted decision-tree probability model."],
        ["Random Forest", "Unscaled 15-feature matrices", "150 estimators; depth 4; seed 42", "Bagged tree probability model."],
        ["Voting ensemble", "Three model probabilities", "Equal average; threshold 0.50", "Final reported candidate decision."],
    ], [0.9, 1.65, 2.05, 1.9], font_size=8.35)

    heading(doc, "11. Metrics, Confidence Intervals, and Statistical Logic")
    para(doc, "The independent-validation driver computes metrics from y_true, thresholded predictions, and positive-class probabilities. Metrics are calculated for the full 926-candidate validation cohort and again for each individual held-out subset.")
    formula(doc, "Confusion-matrix quantities", "TN = count(y=0, yhat=0); FP = count(y=0, yhat=1); FN = count(y=1, yhat=0); TP = count(y=1, yhat=1)", "These four counts are the basis for the threshold-dependent metrics.")
    formula(doc, "Accuracy, sensitivity, specificity", "Accuracy = (TP + TN)/(TP + TN + FP + FN); Sensitivity = TP/(TP+FN); Specificity = TN/(TN+FP)", "Sensitivity is recall for the positive class; specificity is recall for the negative class.")
    formula(doc, "Precision and F1", "Precision = TP/(TP+FP); F1 = 2 x Precision x Sensitivity / (Precision + Sensitivity)", "The implementation uses zero_division=0 for precision and F1 to avoid exceptions in degenerate cases.")
    formula(doc, "ROC-AUC", "AUC = integral_0^1 TPR(FPR) dFPR", "The implementation uses roc_auc_score on continuous positive-class probabilities, so AUC is independent of the fixed 0.50 decision threshold.")
    heading(doc, "11.1 Wilson score intervals", 2)
    para(doc, "Wilson intervals are used for accuracy, sensitivity, specificity, and precision because these are proportions. For successes k out of n trials, p = k/n and z is the standard-normal critical value (1.96 for a 95% interval). The implementation clamps the final interval endpoints to [0, 1].")
    formula(doc, "Wilson interval", "center = (p + z^2/(2n))/(1+z^2/n); spread = z sqrt(p(1-p)/n + z^2/(4n^2))/(1+z^2/n)", "The lower and upper limits are center - spread and center + spread after clipping to the valid probability range.")
    heading(doc, "11.2 Bootstrap intervals", 2)
    para(doc, "F1-score and ROC-AUC use a non-parametric percentile bootstrap. The metric module initializes a deterministic NumPy generator with seed 42, samples n observation indices with replacement 1,000 times, calculates the selected metric, and returns the 2.5th and 97.5th percentiles. For ROC-AUC, bootstrap samples containing only one class are not scored.")
    heading(doc, "11.3 McNemar utility", 2)
    para(doc, "The repository also contains a paired McNemar test utility for comparing two classifiers on the same labels. It counts discordant cases b (model 1 correct/model 2 incorrect) and c (model 1 incorrect/model 2 correct). It uses an exact binomial test when b+c < 25, otherwise a Yates-corrected chi-square test. This utility is available in evaluation_metrics.py but is not a component of the saved independent-validation summary.")

    heading(doc, "12. Versioned Cache System")
    heading(doc, "12.1 Directory layout", 2)
    para(doc, "Every subset has its own cache directory at luna16_data/cache/tq_bionet_v3/subsetN. The independent loader never reconstructs a combined cache on disk; it loads only the requested subset directories and concatenates their arrays in memory.")
    table(doc, ["File", "Content", "Why it is stored"], [
        ["X.npy", "N x 31 raw feature matrix", "Primary feature data; SHA256 is stored in metadata and rechecked before loading."],
        ["y.npy", "N binary labels", "Needed for development fitting and validation scoring."],
        ["groups.npy", "N series UID/patient group strings", "Supports patient identity checks and traceability."],
        ["coords.npy", "N x 3 world coordinates", "Preserves candidate location provenance and supports composite identity checks."],
        ["metadata.json", "Versions, dimensions, subset ID, counts, checksum, seed, and timestamp", "Guards against loading an incompatible or misplaced subset cache."],
    ], [1.2, 2.35, 2.95])
    heading(doc, "12.2 Cache rebuild sequence", 2)
    number(doc, "Check whether the requested subset metadata and X.npy exist.")
    number(doc, "If absent, obtain the raw subset, select its targets, resample scans, extract normalized patches, and compute features.")
    number(doc, "Save X, y, groups, and coordinates into the subset-specific v3 cache directory.")
    number(doc, "Compute SHA256 over X.npy and write metadata.json with the cache identity and counts.")
    number(doc, "On later reconstruction, reload metadata and verify feature dimension = 31, algorithm_version = v3.0, feature_version = v3.0, subset_ids = [requested subset], and SHA256(X.npy) equals metadata." )
    heading(doc, "12.3 Why subset isolation matters", 2)
    para(doc, "Isolation prevents one subset from being accidentally appended to another or from being loaded through an unversioned shared matrix. The independent validation driver requests development subsets and validation subsets by explicit lists. The reconstruction function returns a parallel subset-ID vector, which is later written into validation_predictions.csv and used for per-subset metrics.")

    heading(doc, "13. Manifest and Reproducibility Record")
    para(doc, "The independent-validation manifest is saved as outputs/experiment_manifest_validation.json. It records phase, UTC date, git commit status, algorithm version, feature version, seed, validation subset list, sample count, feature dimension, cache hashes, and runtime. It is the compact provenance record for a completed validation run.")
    table(doc, ["Manifest field", "Current saved value / use"], [
        ["phase", manifest["phase"]], ["date", manifest["date"]], ["algorithm_version", manifest["algorithm_version"]],
        ["feature_version", manifest["feature_version"]], ["random_seed", manifest["random_seed"]],
        ["subset_list", str(manifest["subset_list"])], ["sample_count", manifest["sample_count"]],
        ["feature_dimension", manifest["feature_dimension"]], ["runtime_evaluation_sec", f"{manifest['runtime_evaluation_sec']:.4f}"], ["git_commit", manifest["git_commit"]],
    ], [2.25, 4.25])
    heading(doc, "13.1 Cache hashes for the independent run", 2)
    table(doc, ["Subset", "SHA256(X.npy) recorded in validation manifest"], [[k, v] for k, v in manifest["cache_hashes"].items()], [1.25, 5.25], font_size=8.5)
    callout(doc, "Determinism controls", "Feature serialization is alphabetical. The quantum perturbation uses a fixed seed. The model constructors use random_state=42. The bootstrap generator uses seed 42. The manifest records seed 42 and the exact validation cache hashes.")

    heading(doc, "14. Independent Validation Results")
    para(doc, f"The current frozen output package reports results on {manifest['sample_count']} candidate patches across validation Subsets 6-9. The voting ensemble is the final model used for the primary combined result. Its saved combined performance is accuracy {ensemble['accuracy']:.4f}, sensitivity {ensemble['sensitivity']:.4f}, specificity {ensemble['specificity']:.4f}, precision {ensemble['precision']:.4f}, F1-score {ensemble['f1']:.4f}, and AUC-ROC {ensemble['auc']:.4f}.")
    heading(doc, "14.1 Combined metrics", 2)
    rows=[]
    for label, key, ci_key in [("Accuracy","accuracy","accuracy_ci"),("Sensitivity","sensitivity","sensitivity_ci"),("Specificity","specificity","specificity_ci"),("Precision","precision","precision_ci"),("F1-score","f1","f1_ci"),("AUC-ROC","auc","auc_ci")]:
        rows.append([label] + [f"{metrics[m][key]:.4f} [{metrics[m][ci_key][0]:.3f}-{metrics[m][ci_key][1]:.3f}]" for m in ("SVM","XGBoost","VotingEnsemble")])
    table(doc, ["Metric", "SVM", "XGBoost", "Voting ensemble"], rows, [1.2, 1.75, 1.75, 1.8], font_size=8.55)
    heading(doc, "14.2 Combined confusion matrix", 2)
    cm_rows = [["True negative", 420], ["False positive", 43], ["False negative", 84], ["True positive", 379]]
    table(doc, ["Quantity", "Count"], cm_rows, [3.3, 3.2])
    para(doc, "These values correspond to the voting-ensemble threshold of 0.50 and are saved in outputs/validation_confusion_matrix.csv. They sum to 926 candidates.")
    heading(doc, "14.3 Per-subset ensemble stability", 2)
    per=[]
    for subset in (6,7,8,9):
        data = load_json(f"validation_subset{subset}_metrics.json")
        m=data["VotingEnsemble"]
        n=sum(data["confusion_matrix"].values())
        per.append([f"Subset {subset}", n, f"{m['accuracy']:.4f}", f"{m['sensitivity']:.4f}", f"{m['specificity']:.4f}", f"{m['precision']:.4f}", f"{m['f1']:.4f}", f"{m['auc']:.4f}"])
    table(doc, ["Subset","N","Accuracy","Sensitivity","Specificity","Precision","F1","AUC"], per, [0.75,0.45,0.78,0.9,0.88,0.82,0.65,0.65], font_size=8.1)
    fig(doc, OUTPUTS / "roc_curve.png", "Figure 1. ROC curve produced by the validation workflow.")
    fig(doc, OUTPUTS / "pr_curve.png", "Figure 2. Precision-recall curve produced by the validation workflow.")
    fig(doc, OUTPUTS / "validation_confusion_matrix.png", "Figure 3. Voting-ensemble confusion matrix for all held-out candidates.")
    fig(doc, OUTPUTS / "subset_comparison.png", "Figure 4. Per-subset performance summary generated from the held-out cohort.")

    heading(doc, "15. Verification, Leakage Controls, and Audit Results")
    para(doc, "A direct repository audit was performed against the active code, versioned caches, saved predictions, manifests, and JSON metrics. The checks below describe the evidence that the saved results are internally consistent.")
    table(doc, ["Audit area", "Check performed", "Observed result"], [
        ["Patient leakage", "Compare all development group IDs from Subsets 0-5 with all validation group IDs from Subsets 6-9.", "0 overlapping patient/group IDs."],
        ["Candidate leakage", "Compare composite (series UID, x, y, z, label) identities across development and validation caches.", "0 overlapping composite sample identities."],
        ["Validation duplicates", "Check composite identities inside the combined 6-9 validation cohort.", "No internal duplicate sample identities."],
        ["Cache integrity", "Recompute SHA256(X.npy) and compare with metadata for Subsets 0-9.", "All checked cache hashes matched metadata."],
        ["Metadata integrity", "Check feature dimension, subset ID, and sample count against loaded cache arrays.", "All checked metadata fields were internally consistent."],
        ["Manifest integrity", "Compare saved manifest subset list, sample count, and cache hashes with current outputs/caches.", "Manifest matched the 6-9 prediction set and cache hashes."],
        ["Metric integrity", "Recompute all combined and per-subset metrics from validation_predictions.csv.", "Accuracy, sensitivity, specificity, precision, F1, AUC, and ensemble confusion matrices matched JSON artifacts."],
        ["Scaler leakage", "Inspect validation driver scaling calls.", "fit_transform is applied only to development data; validation uses transform only."],
        ["Import/execution integrity", "Import active validation, cache, metric, integrity, and pipeline modules in the execution environment.", "Active modules imported successfully."],
    ], [1.25, 3.15, 2.1], font_size=8.4)

    heading(doc, "16. Repository Guide and File-Level Responsibilities")
    table(doc, ["File", "Responsibility", "Key effects on execution"], [
        ["run_independent_validation.py", "Active final independent-validation driver.", "Defines 6-9 test cohort; trains on 0-5; writes validation evidence."],
        ["tq_bionet/scale_clinical_validation.py", "Target selection, patch extraction, cache creation, metadata validation, and development reconstruction.", "Defines candidate balancing, local IQR normalization, versioned cache format, and subset reconstruction."],
        ["tq_bionet/pipeline.py", "Feature integration and raw-vector serialization.", "Sets sorted raw feature order and joins the four mathematical modules."],
        ["tq_bionet/quantum_module.py", "Sparse Hamiltonian construction and low-state solution.", "Produces quantum eigenvalues and probability-density map."],
        ["tq_bionet/topological_module.py", "Point-cloud selection and persistent homology.", "Produces H0/H1 persistence summaries."],
        ["tq_bionet/fractal_module.py", "Surface fractal dimension and lacunarity.", "Produces spatial boundary/texture descriptors."],
        ["tq_bionet/data_integrity.py", "Duplicate, coordinate, feature-vector, ID, and split checks.", "Supports detection of accidental data integrity problems."],
        ["tq_bionet/evaluation_metrics.py", "Wilson CI, bootstrap CI, McNemar, and plotting utilities.", "Implements reported uncertainty intervals and figures."],
        ["outputs/", "Generated evidence bundle.", "Provides reportable outputs and provenance for the final run."],
    ], [2.15, 2.65, 1.7], font_size=8.35)

    heading(doc, "17. Operating Instructions")
    heading(doc, "17.1 Runtime prerequisites", 2)
    para(doc, "A working Python environment must supply the packages imported by the project, including NumPy, pandas, SciPy, scikit-learn, XGBoost, SimpleITK, scikit-image, Ripser, Persim, Matplotlib, and pydicom. The local project root must include run_independent_validation.py, the tq_bionet package, outputs/, and the LUNA16 data/cache directory structure.")
    heading(doc, "17.2 Standard run sequence", 2)
    number(doc, "Ensure the desired LUNA16 subset raw data or valid versioned caches are available under luna16_data.")
    number(doc, "Run py tq_bionet/run_all_subsets_scaling.py when development-subset cache processing or development retraining is needed.")
    number(doc, "Run py run_independent_validation.py to verify/build caches for Subsets 6-9, fit the frozen models on Subsets 0-5, and evaluate Subsets 6-9.")
    number(doc, "Review outputs/experiment_manifest_validation.json, outputs/validation_metrics.json, outputs/validation_predictions.csv, per-subset JSON files, and generated figures.")
    heading(doc, "17.3 Expected independent-run output files", 2)
    table(doc, ["File", "Contents"], [
        ["validation_predictions.csv", "Candidate UID, subset, coordinates, true label, SVM/XGBoost/RF/ensemble probabilities, and final ensemble prediction."],
        ["validation_metrics.json", "Combined metrics and confidence intervals for SVM, XGBoost, and the voting ensemble."],
        ["validation_subset6_metrics.json ... validation_subset9_metrics.json", "Separate metrics for each independent subset."],
        ["validation_confusion_matrix.csv", "Combined voting-ensemble TN, FP, FN, and TP counts."],
        ["experiment_manifest_validation.json", "Independent-run phase, version, seed, subset, sample, hash, and runtime record."],
        ["validation_summary.md", "Human-readable combined summary generated by the run."],
    ], [2.45, 4.05])

    heading(doc, "18. Limitations, Risks, and Responsible Use")
    heading(doc, "18.1 Methodological boundaries", 2)
    for text in [
        "The results are candidate-level results on a public LUNA16-derived cohort; they are not patient-level diagnostic performance measures.",
        "The class balancing procedure means the prevalence of negative candidates differs from a real screening workflow. Precision and accuracy cannot be transferred directly to natural-prevalence clinical screening.",
        "The validation cohort is held out by LUNA16 subset and was audited as patient-disjoint from development, but it remains within the same benchmark family rather than an external hospital dataset.",
        "The reported prediction probability is a model score, not a calibrated clinical risk probability or a treatment recommendation.",
        "The manifest records git_commit as unavailable in this workspace. Cache hashes, output JSON, source files, and frozen configuration files are therefore the available provenance anchors.",
    ]:
        bullet(doc, text)
    heading(doc, "18.2 Responsible wording for reports and presentations", 2)
    table(doc, ["Use wording like", "Avoid wording like"], [
        ["Candidate-level classification on held-out LUNA16 Subsets 6-9.", "Cancer diagnosis accuracy in patients."],
        ["Independent LUNA16 subset validation with zero observed patient overlap from the development cohort.", "Clinically validated across hospitals."],
        ["High discrimination in the balanced candidate cohort.", "Real-world screening precision or deployment-ready performance."],
        ["Frozen reproducible evaluation with saved manifests and cache hashes.", "Guaranteed identical results on any environment without documenting dependencies."],
    ], [3.25, 3.25])

    doc.add_page_break()
    heading(doc, "Appendix A. Complete Raw Feature Serialization Order")
    mapping = (OUTPUTS / "feature_mapping.csv").read_text().strip().splitlines()[1:]
    table(doc, ["Index", "Feature name"], [line.split(",", 1) for line in mapping], [1.0, 5.5])
    heading(doc, "Appendix B. Artifact Inventory")
    table(doc, ["Artifact", "Purpose in the evidence package"], [
        ["TQ-BioNet_v3.0_FROZEN.md", "Formal methodology-freeze certificate with version, selected features, classifier settings, seeds, and development cache hashes."],
        ["outputs/feature_mapping.csv", "Raw 31-feature index/name mapping."],
        ["outputs/reproducibility_indices.json", "Development patient split and index information."],
        ["outputs/validation_predictions.csv", "Record-level validation evidence used to recompute reported metrics."],
        ["outputs/validation_metrics.json", "Combined model metrics and confidence intervals."],
        ["outputs/validation_subset6_metrics.json through validation_subset9_metrics.json", "Subset-specific metrics and confidence intervals."],
        ["outputs/validation_confusion_matrix.csv", "Combined voting-ensemble threshold outcomes."],
        ["outputs/experiment_manifest_validation.json", "Independent-validation provenance and cache hashes."],
        ["outputs/roc_curve.png, pr_curve.png, validation_confusion_matrix.png, subset_comparison.png", "Visual performance artifacts generated from the validation workflow."],
    ], [2.7, 3.8])
    heading(doc, "Appendix C. Glossary")
    table(doc, ["Term", "Meaning in this project"], [
        ["Candidate", "A coordinate-centred CT patch supplied by the annotation/candidate target construction process."],
        ["Development cohort", "LUNA16 Subsets 0-5, used for frozen model fitting."],
        ["Independent validation cohort", "LUNA16 Subsets 6-9, used only after the frozen model has been fitted."],
        ["Feature vector", "Numerical representation of a normalized candidate patch used by the classifiers."],
        ["H0/H1", "Persistent-homology dimensions for connected components and loops in the selected point cloud."],
        ["IQR", "Interquartile range: 75th percentile minus 25th percentile."],
        ["Lacunarity", "A measure of spatial gap variability in the thresholded probability-density mask."],
        ["Manifest", "JSON provenance record describing a completed experiment."],
        ["Soft voting", "Arithmetic mean of the three model probability scores."],
        ["Versioned cache", "Subset-isolated cache folder carrying data arrays and metadata for a particular algorithm/feature version."],
    ], [1.7, 4.8])
    heading(doc, "Appendix D. Final Demonstration Checklist")
    for text in [
        "Open the complete project documentation before a viva, review, or demonstration to explain the system from data to output.",
        "Use validation_metrics.json and experiment_manifest_validation.json as the numerical and provenance source of truth.",
        "Show validation_predictions.csv when explaining that every reported validation metric can be recomputed from saved predictions.",
        "Use the feature-mapping appendix to explain exactly what each model-input column represents.",
        "Use the limitations section to keep claims consistent with the candidate-level, balanced-cohort evaluation design.",
    ]:
        bullet(doc, text)

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
