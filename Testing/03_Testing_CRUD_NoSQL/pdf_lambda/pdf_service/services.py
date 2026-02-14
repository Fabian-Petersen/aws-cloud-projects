from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle


def build_services(jobcard, styles):
    story = []

    def zar(amount):
        return f"R {amount:,.2f}"

    # Remove parts as per Leon
    # ---------------- Parts ----------------
    # story.append(Paragraph("<b>Parts Used</b>", styles["Heading3"]))

    # parts_data = [["Part Name", "Quantity", "Price (R)"]]
    parts_total = 0.0

    # for part in jobcard.get("parts_used", []):
    #     qty = int(part.get("qty", 1))
    #     cost = float(part.get("cost", 0))
    #     line_total = qty * cost
    #     parts_total += line_total

    #     parts_data.append([
    #         part.get("name", ""),
    #         str(qty),
    #         zar(line_total)
    #     ])

    # parts_table = Table(parts_data, colWidths=[350, 50, 106])
    # parts_table.setStyle(TableStyle([
    #     ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    #     ("GRID", (0, 0), (-1, -1), 1, colors.black),
    #     ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
    #     ("ALIGN", (1, 1), (1, -1), "CENTER"),
    #     ("ALIGN", (2, 1), (2, -1), "RIGHT"),
    #     ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    # ]))

    # story.extend([parts_table, Spacer(1, 10)])

    right_small = ParagraphStyle(
        name="RightSmall",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_RIGHT
    )

    # story.append(
    #     Paragraph(f"Subtotal : <b>{zar(parts_total)}</b>", right_small)
    # )

    # ---------------- Services ----------------
    KM_RATE = 4.50
    HOUR_RATE = 350.00

    kilometers = float(jobcard.get("kilometers", 0))
    hours = float(jobcard.get("hours_on_site", 0))

    services_total = (kilometers * KM_RATE) + (hours * HOUR_RATE)

    services_data = [
        ["Service", "Qty", "Price (R)"],
        ["Travel (Kilometers)", f"{kilometers:.1f}", zar(kilometers * KM_RATE)],
        ["Labour (Hours on site)", f"{hours:.1f}", zar(hours * HOUR_RATE)],
    ]

    services_table = Table(services_data, colWidths=[350, 50, 106])
    services_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Labour & Travel Costs</b>", styles["Heading3"]))
    story.append(services_table)

    story.append(Spacer(1, 8))
    story.append(
        Paragraph(f"SubTotal : <b>{zar(services_total)}</b>", right_small)
    )

    # right_small = ParagraphStyle(
    #     name="RightSmall",
    #     parent=styles["Normal"],
    #     fontSize=9,
    #     alignment=TA_RIGHT
    # )

    # story.append(
    #     Paragraph(f"Subtotal : <b>{zar(parts_total)}</b>", right_small)
    # )



    # ---------------- Grand Total ----------------
    job_total = parts_total + services_total

    job_total_style = ParagraphStyle(
        name="JobTotal",
        parent=styles["Normal"],
        fontSize=12,
        alignment=TA_RIGHT
    )

    story.extend([
        Spacer(1, 15),
        Paragraph(f"<b>TOTAL : </b> <b>{zar(job_total)}</b>", job_total_style)
    ])

    return story

