from reportlab.lib import colors
from datetime import datetime
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from xml.sax.saxutils import escape
from decimal import Decimal, InvalidOperation


def zar(amount):
    """Format a numeric value as South African Rand, or return blank if invalid."""
    try:
        value = Decimal(str(amount))
        if not value.is_finite():
            return ""
        return f"R {value:,.2f}"
    except (InvalidOperation, TypeError, ValueError):
        return ""


def _normalise_cost_items(items):
    """Convert supported item shapes to safe description/cost table rows."""
    if not isinstance(items, (list, tuple)):
        return []

    rows = []
    for item in items:
        if isinstance(item, dict):
            description = (
                item.get("description")
                or item.get("name")
                or item.get("item")
                or item.get("contractor")
                or ""
            )
            cost = item.get("cost")
            if cost is None:
                cost = item.get("price")
            if cost is None:
                cost = item.get("amount")
        elif item is None or isinstance(item, (list, tuple, set)):
            continue
        else:
            description = item
            cost = None

        description = str(description or "").strip()
        formatted_cost = zar(cost) if cost is not None else ""
        if description or formatted_cost:
            rows.append((description, formatted_cost))
    return rows


def add_itemised_cost_table(title, items, total, styles, usable_width):
    """Build a consistently styled, page-safe table for an itemised cost list."""
    rows = _normalise_cost_items(items)
    if not rows:
        return []

    body_style = ParagraphStyle(
        name=f"{title}CostBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
    )
    right_style = ParagraphStyle(
        name=f"{title}CostRight",
        parent=body_style,
        alignment=TA_RIGHT,
    )

    table_data = [[
        Paragraph("<b>Description</b>", body_style),
        Paragraph("<b>Cost</b>", right_style),
    ]]
    for description, formatted_cost in rows:
        table_data.append([
            Paragraph(escape(description), body_style),
            Paragraph(escape(formatted_cost), right_style),
        ])

    formatted_total = zar(total)
    if formatted_total:
        table_data.append([
            Paragraph("<b>Total</b>", body_style),
            Paragraph(f"<b>{escape(formatted_total)}</b>", right_style),
        ])

    table = Table(
        table_data,
        colWidths=[usable_width * 0.72, usable_width * 0.28],
        repeatRows=1,
        splitByRow=1,
        splitInRow=0,
        hAlign="LEFT",
    )
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if formatted_total:
        style_commands.extend([
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f2f2f2")),
            ("LINEABOVE", (0, -1), (-1, -1), 1.25, colors.black),
        ])
    table.setStyle(TableStyle(style_commands))

    return [
        Spacer(1, 8),
        Paragraph(f"<b>{escape(title)}</b>", styles["Heading3"]),
        table,
    ]


def build_services(jobcard, styles, usable_width=506):
    story = []

    cost_sections = (
        ("Parts", "parts", "total_cost_parts"),
        ("Sundries", "sundries", "total_cost_sundries"),
        ("Contractor", "contractor", "total_cost_contractor"),
    )
    for title, items_field, total_field in cost_sections:
        items = jobcard.get(items_field) or []
        if items_field == "contractor" and not isinstance(items, (list, tuple)):
            items = [items]
        story.extend(add_itemised_cost_table(
            title,
            items,
            jobcard.get(total_field),
            styles,
            usable_width,
        ))

    right_small = ParagraphStyle(
        name="RightSmall",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_RIGHT
    )

    # ---------------- Services ----------------
    KM_RATE = 4.50
    HOUR_RATE = 350.00

    try:
        kilometers = float(jobcard.get("total_km") or 0)
    except (TypeError, ValueError):
        kilometers = 0.0

    start = datetime.fromisoformat(jobcard["start_time"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(jobcard["end_time"].replace("Z", "+00:00"))

    hours = (end - start).total_seconds() / 3600
    print('hours on site:', hours)
    hours = round(hours, 2)

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

    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Labour & Travel Costs</b>", styles["Heading3"]))
    story.append(services_table)

    story.append(Spacer(1, 5))
    story.append(
        Paragraph(f"SubTotal : <b>{zar(services_total)}</b>", right_small)
    )

    # ---------------- Grand Total ----------------
    additional_costs = 0.0
    for _, _, total_field in cost_sections:
        try:
            additional_costs += float(jobcard.get(total_field) or 0)
        except (TypeError, ValueError):
            continue
    job_total = additional_costs + services_total

    job_total_style = ParagraphStyle(
        name="JobTotal",
        parent=styles["Normal"],
        fontSize=12,
        alignment=TA_RIGHT
    )

    story.extend([
        Spacer(1, 8),
        Paragraph(f"<b>TOTAL : </b> <b>{zar(job_total)}</b>", job_total_style)
    ])

    return story

