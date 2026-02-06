import os
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image

def build_header(styles, usable_width, assets_dir):
    story = []

    logo_path = os.path.join(assets_dir, "atlantic_meat_logo.webp")
    logo = Image(logo_path, 100, 50) if os.path.exists(logo_path) else ""

    title = Paragraph("Maintenance Job Card", styles["Title"])

    table = Table(
        [[logo, title]],
        colWidths=[100, usable_width - 110],
        rowHeights=[65]
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fcb53b")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 90),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    story.extend([table, Spacer(1, 15)])
    return story
