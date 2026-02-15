from reportlab.platypus import Paragraph, Spacer

def build_findings(jobcard, styles):
    return [
        Paragraph("<b>Findings</b>", styles["Heading3"]),
        Paragraph(jobcard.get("findings", ""), styles["Normal"]),
        Spacer(1, 10)
    ]
