from reportlab.platypus import Paragraph, Spacer

def build_work_completed(jobcard, styles):
    return [
        Paragraph("<b>Work Completed</b>", styles["Heading3"]),
        Paragraph(jobcard["works_completed"], styles["Normal"]),
        Spacer(1, 10)
    ]