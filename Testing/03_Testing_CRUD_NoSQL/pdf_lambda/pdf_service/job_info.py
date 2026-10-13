from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from datetime import datetime, timezone, timedelta
from xml.sax.saxutils import escape

# Change the date format in the database to readible for humans


def to_human_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string)
    # Convert to Cape Town time (UTC+2)
    dt = dt.astimezone(timezone(timedelta(hours=2)))
    return dt.strftime("%d %b %Y, %H:%M")


def capitalise_value(value) -> str:
    """Return a human-readable, title-cased value without changing its source."""
    return escape(str(value or "").strip().title())


def build_job_info(jobcard, usable_width, meta_style):
    jobCreated = to_human_date(jobcard['jobCreated'])
    actionCreated = to_human_date(jobcard['actionCreated'])

    container = Table([
        [
            Paragraph(
                f"<b>Jobcard No:</b> {jobcard.get('jobcardNumber', '')}",
                meta_style,
            ),
            Paragraph(
                f"<b>Location:</b> "
                f"{capitalise_value(jobcard.get('location'))}",
                meta_style,
            ),
        ],
        [
            Paragraph(f"<b>Date Requested:</b> {jobCreated}", meta_style),
            Paragraph(f"<b>Date Actioned:</b> {actionCreated}", meta_style),
        ],
        [
            Paragraph(
                f"<b>Requested By:</b> "
                f"{capitalise_value(jobcard.get('requested_by'))}",
                meta_style,
            ),
            Paragraph(
                f"<b>Actioned By:</b> "
                f"{capitalise_value(jobcard.get('actioned_by'))}",
                meta_style,
            ),
        ],
        [
            Paragraph(
                f"<b>Asset Description:</b> {jobcard.get('equipment', '')}",
                meta_style,
            ),
            Paragraph(
                f"<b>Asset ID:</b> {jobcard.get('assetID', '')}",
                meta_style,
            ),
        ],
    ], colWidths=[usable_width * 0.5, usable_width * 0.5])

    container.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
        ("LEFTPADDING", (1, 0), (1, -1), 70),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    return [container, Spacer(1, 10)]
