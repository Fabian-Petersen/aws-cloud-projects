from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

def build_job_info(jobcard, usable_width, meta_style):
    left_table = Table([
        [Paragraph(f"<b>Requested By:</b> {jobcard['requested_by']}", meta_style)],
        [Paragraph(f"<b>Date Requested:</b> {jobcard['date']}", meta_style)],
        [Paragraph(f"<b>Asset Description:</b> {jobcard['asset_description']}", meta_style)],
        [Paragraph(f"<b>Location:</b> {jobcard['location']}", meta_style)],
    ], colWidths=[usable_width * 0.48])

    
    left_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    right_table = Table([
        [Paragraph(f"<b>Actioned By:</b> {jobcard['actioned_by']}", meta_style)],
        [Paragraph(f"<b>Date Actioned:</b> {jobcard['date_actioned']}", meta_style)],
        [Paragraph(f"<b>Root Cause:</b> {jobcard['root_cause']}", meta_style)],
        [Paragraph(f"<b>Status:</b> {jobcard['status']}", meta_style)],
    ], colWidths=[usable_width * 0.48])

    
    right_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 70),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    container = Table(
        [[left_table, right_table]],
        colWidths=[usable_width * 0.5, usable_width * 0.48]
    )

    container.setStyle(TableStyle([
        # ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    return [container, Spacer(1, 10)]
