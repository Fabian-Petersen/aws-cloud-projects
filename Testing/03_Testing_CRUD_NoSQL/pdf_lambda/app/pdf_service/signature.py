import os
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image

def build_signature(styles, assets_dir):
    story = []

    story.append(Spacer(1, 10))

    signature_path = os.path.join(assets_dir, "signature.png")
    signature_img = (
        Image(signature_path, width=120, height=50)
        if os.path.exists(signature_path)
        else Spacer(1, 10)
    )

    signature_label = Paragraph(
        "<b>Customer Signature</b>",
        styles["Normal"]
    )

    signature_table = Table(
        [
            [signature_img],
            [""],     # spacing row
            [""],     # line row
            [signature_label],
        ],
        colWidths=[160],
        rowHeights=[55, 6, 1, 18],
        hAlign="LEFT"
    )

    signature_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 2), (0, 2), 1, colors.lightgrey),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    story.append(signature_table)
    return story
