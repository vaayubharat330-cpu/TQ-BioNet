import os
import re
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

src_ppt = r"C:\Users\suraj\AppData\Local\Packages\5319275A.51895FA4EA97F_cv1g1gvanyjgm\LocalState\sessions\6FD5C0FDAB681BD5E60C2436F602390ADBD69EE3\transfers\2026-38\Batch-13 PPT.pptx"
dst_ppt = r"C:\Users\suraj\Desktop\4th yr project\Batch-13_PPT_Reviewed_Fixed.pptx"

prs = pptx.Presentation(src_ppt)

def clean_text_str(s):
    if not s:
        return s
    # Fix Schrödinger
    s = re.sub(r'Schr[\uFFFD\u00EF\u00BF\u00BD\?\w]*dinger', 'Schrödinger', s)
    s = s.replace("Schrdinger", "Schrödinger")
    s.replace("Schrödingerdinger", "Schrödinger")
    
    # Fix hyphens and ranges
    s = s.replace("0\ufffd5", "0–5").replace("0\u00a05", "0–5")
    s = s.replace("6\ufffd9", "6–9").replace("6\u00a09", "6–9")
    s = s.replace("915\ufffd931", "915–931")
    s = s.replace("1\ufffd13", "1–13")
    s = s.replace("130\ufffd137", "130–137")
    s = s.replace("45\ufffd98", "45–98")
    text_fixes = [
        ("TQ-BioNet  ", "TQ-BioNet "),
        ("\ufffd", " "),
        ("\u00a0", " ")
    ]
    for old, new in text_fixes:
        s = s.replace(old, new)
    return s

for slide in prs.slides:
    for shape in slide.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                full_p = p.text
                if "It also mentions that future work" in full_p:
                    p.text = "Future Scope: Investigate 3D topological persistence diagrams and multi-modal clinical metadata to further enhance diagnostic performance."
                else:
                    new_p = clean_text_str(full_p)
                    if new_p != full_p:
                        # set text on paragraph
                        p.text = new_p

        elif shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    if cell.text_frame:
                        for p in cell.text_frame.paragraphs:
                            full_p = p.text
                            new_p = clean_text_str(full_p)
                            if new_p != full_p:
                                p.text = new_p

# Populate Slide 12 Methodology System Pipeline Box cleanly
slide12 = prs.slides[11]
# Clear any previously added textboxes
shapes_to_keep = []
for s in list(slide12.shapes):
    if s.has_text_frame and s.name not in ["TextBox 6", "Group 2", "Group 4"]:
        # Remove extra text box added in previous run if re-running
        sp = s._element
        sp.getparent().remove(sp)

tb = slide12.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.5), Inches(5.5))
tf = tb.text_frame
tf.word_wrap = True

p0 = tf.paragraphs[0]
p0.text = "System Architecture & Processing Pipeline"
p0.font.bold = True
p0.font.size = Pt(20)
p0.font.color.rgb = RGBColor(0, 51, 102)
p0.space_after = Pt(14)

steps = [
    ("1. Input 3D CT Volume", "1,018 Thoracic CT scans from LUNA16 dataset (0.5–1.0 mm slice thickness)."),
    ("2. Candidate Patch Extraction", "Extract 32×32×32 mm³ isotropic candidate volumes centered on nodule candidates."),
    ("3. Local Z-Score IQR Normalization", "Standardize intensities via Î = [I − Median] / [IQR + 1e-6] to eliminate cross-scanner contrast drift."),
    ("4. 15D Frozen Feature Extraction", "Calculate TDA (H₀, β₁), Schrödinger potential energy states (E₀, E₁, E₂), 3D Hessian curvature (V_σ, R_B), and Lacunarity/Fractal dimension."),
    ("5. Voting Ensemble Classification", "Feed 15D feature vector into soft-voting ensemble (SVM + XGBoost) to generate calibrated nodule probability.")
]

for title, desc in steps:
    p_title = tf.add_paragraph()
    p_title.text = f"• {title}: "
    p_title.font.bold = True
    p_title.font.size = Pt(15)
    p_title.font.color.rgb = RGBColor(0, 102, 153)
    p_title.space_before = Pt(8)
    
    run_desc = p_title.add_run()
    run_desc.text = desc
    run_desc.font.bold = False
    run_desc.font.size = Pt(14)
    run_desc.font.color.rgb = RGBColor(50, 50, 50)

prs.save(dst_ppt)
print(f"Refined and saved clean fixed PPT to: {dst_ppt}")
