from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from datetime import datetime, timezone, timedelta

    ## Change the date format in the database to readible for humans
def to_human_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string)
    ## Convert to Cape Town time (UTC+2)
    dt = dt.astimezone(timezone(timedelta(hours=2)))
    return dt.strftime("%d %b %Y, %H:%M")

def build_job_info(jobcard, usable_width, meta_style):
    jobCreated = to_human_date(jobcard['jobCreated'])
    actionCreated = to_human_date(jobcard['actionCreated'])

    left_table = Table([
        [Paragraph(f"<b>Requested By:</b> {jobcard.get('requested_by', '')}", meta_style)],
        [Paragraph(f"<b>Date Requested:</b> {jobCreated}", meta_style)],
        [Paragraph(f"<b>Asset Description:</b> {jobcard['equipment']}", meta_style)],
        [Paragraph(f"<b>Location:</b> {jobcard['location']}", meta_style)],
    ], colWidths=[usable_width * 0.48])

    
    left_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    right_table = Table([
        [Paragraph(f"<b>Actioned By:</b> {jobcard.get('actioned_by', '')}", meta_style)],
        [Paragraph(f"<b>Date Actioned:</b> {actionCreated}", meta_style)],
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
