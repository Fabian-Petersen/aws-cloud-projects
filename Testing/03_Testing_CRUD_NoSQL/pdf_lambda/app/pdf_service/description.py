from reportlab.platypus import Paragraph, Spacer

def build_description(jobcard, styles):
    return [
        Paragraph("<b>Job Description</b>", styles["Heading3"]),
        Paragraph(jobcard["description"], styles["Normal"]),
        Spacer(1, 10)
    ]
