from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def make_report(report):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallNote", parent=styles["BodyText"], textColor=colors.grey, fontSize=8))
    story = [Paragraph("AI Resume Analyzer", styles["Title"]),
             Paragraph("ATS Compatibility Report", styles["Heading2"]), Spacer(1, 10)]
    story.append(Paragraph(f"<b>Job:</b> {report.get('job_title','Not specified')}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Estimated score:</b> {report.get('ats_score',0)}/100", styles["Heading1"]))
    story.append(Paragraph("This is an estimate, not an official ATS result or a guarantee of selection.", styles["SmallNote"]))
    story.append(Spacer(1, 12))
    for title, key in [("Matched skills","matched_skills"),("Missing skills","missing_skills"),
                       ("Matched keywords","matched_keywords"),("Missing keywords","missing_keywords"),
                       ("Strengths","strengths"),("Weaknesses","weaknesses"),("Recommendations","suggestions")]:
        story.append(Paragraph(title, styles["Heading2"]))
        values = report.get(key) or ["None identified"]
        story.append(ListFlowable([ListItem(Paragraph(str(x), styles["BodyText"])) for x in values[:30]], bulletType="bullet"))
        story.append(Spacer(1, 6))
    doc.build(story)
    buffer.seek(0)
    return buffer
