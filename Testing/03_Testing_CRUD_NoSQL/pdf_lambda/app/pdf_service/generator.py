from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import (getSampleStyleSheet, ParagraphStyle)
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable,
)

from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime
import os


class PDFGenerator:
    # output_dir="/tmp"
    def __init__(self, output_dir=None):
        # Directory where this file lives
        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(__file__))

        self.output_dir = output_dir

    def _footer(self, canvas, doc):
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(
            A4[0] / 2,
            20,
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )


    def create_pdf(self, jobcard: dict, filename: str):
        path = os.path.join(self.output_dir, filename)

        doc = SimpleDocTemplate(
            path,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()

        story = []

        # --- Logo ---
        logo_path = os.path.join(
            os.path.dirname(__file__),
            "assets",
            "atlantic_meat_logo.webp"
        )

        if os.path.exists(logo_path):
            logo = Image(logo_path, width=100, height=50)
            # story.append(logo)

        title = Paragraph(
            "",
            styles["Title"]
        )

        # Calculate usable width
        usable_width = A4[0] - doc.leftMargin - doc.rightMargin

        header_table = Table(
            [[logo, title]],
            colWidths=[100, usable_width - 110],
            rowHeights=[65]
        )

        header_table.setStyle(TableStyle([
            # Background color (light yellow)
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fcb53b")),

            # Alignment
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),

            # Padding
            ("LEFTPADDING", (0, 0), (0, 0), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))

        story.append(header_table)

        story.append(Spacer(1, 15))

        # --- Title ---
    
        story.append(Paragraph("Maintenance Job Card", styles["Title"]))
        story.append(Spacer(1, 10))

        # --- Job Info ---

        meta_style = ParagraphStyle(
        name="MetaLine",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=3
        )
        story.append(Paragraph(f"<b>Job Card No:</b> {jobcard['job_card_no']}", meta_style))
        story.append(Paragraph(f"<b>Requested By:</b> {jobcard['requested_by']}", meta_style))
        story.append(Paragraph(f"<b>Date:</b> {jobcard['date']}", meta_style))
        story.append(Paragraph(f"<b>Location:</b> {jobcard['location']}", meta_style))
        story.append(Spacer(1, 5))

        # --- Description ---
        story.append(Paragraph("<b>Job Description</b>", styles["Heading3"]))
        story.append(Paragraph(jobcard["description"], styles["Normal"]))
        story.append(Spacer(1, 10))


# $ ===================================== parts table ========================================  
        # --- Parts Used Table ---
        story.append(Paragraph("<b>Parts Used</b>", styles["Heading3"]))

        table_data = [
            ["Part Name", "Quantity", "Price (R)"]
        ]

        parts_total = 0.0

        def zar(amount):
            return f"R {amount:,.2f}"
        
        for part in jobcard["parts_used"]:
            qty = int(part.get("qty", 1))
            cost = float(part.get("cost", 0))
            line_total = qty * cost
            parts_total += line_total

            table_data.append([
                part["name"],
                str(qty),
                zar(line_total)
            ])

        table = Table(table_data, colWidths=[350, 50, 106])

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),

            # Header
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),

            # Alignments
            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        
        story.append(table)

        story.append(Spacer(1, 10))

        subtotal_style = ParagraphStyle(
        name="TotalRight",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_RIGHT
        )

        story.append(
            Paragraph(
            f"Subtotal : <b>{zar(parts_total)}</b>",
            subtotal_style
            )
        )

# $ ===================================== services table ========================================

        KM_RATE = 4.50
        HOUR_RATE = 350.00  # adjust if needed

        kilometers = float(jobcard.get("kilometers", 0))
        hours_on_site = float(jobcard.get("hours_on_site", 0))

        services_table_data = [
            ["Service", "Qty", "Price (R)"]
        ]

        km_cost = kilometers * KM_RATE
        hour_cost = hours_on_site * HOUR_RATE

        services_table_data.append([
            "Travel (Kilometers)",
            f"{kilometers:.1f}",
            zar(km_cost)
        ])

        services_table_data.append([
            "Labour (Hours on site)",
            f"{hours_on_site:.1f}",
            zar(hour_cost)
        ])

        services_total = km_cost + hour_cost

        services_table = Table(
            services_table_data,
            colWidths=[350, 50, 106]
        )

        services_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),

            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),

            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        story.append(Paragraph("<b>Labour & Travel Costs</b>", styles["Heading3"]))
        
        # story.append(Spacer(1, 10))
        story.append(services_table)

        job_total = parts_total + services_total

        story.append(Spacer(1, 12))

        # services_total_style = ParagraphStyle(
        #     name="JobTotalRight",
        #     parent=styles["Normal"],
        #     fontSize=10,
        #     alignment=TA_RIGHT
        # )

        story.append(
            Paragraph(
                f"SubTotal : <b>{zar(services_total)}</b>",
                subtotal_style
            )
        )


# $ ====================================== Total Cost ===============================
        story.append(Spacer(1, 15))

        job_total_style = ParagraphStyle(
            name="JobTotalRight",
            parent=styles["Normal"],
            fontSize=12,
            alignment=TA_RIGHT
        )

        story.append(
            Paragraph(
                f"<b>TOTAL : </b> <b>{zar(job_total)}</b>",
                job_total_style
            )
        )

        # 🔹 Horizontal line
        story.append(Spacer(1, 6))
        story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.lightgrey,
            spaceBefore=10,
            spaceAfter=10
        ))

        # --- Comments ---
        story.append(Paragraph("<b>Comments</b>", styles["Heading3"]))
        story.append(Paragraph(jobcard["comments"], styles["Normal"]))
        story.append(Spacer(1, 10))

        # --- Build ---
        doc.build(
            story,
            onFirstPage=self._footer,
            onLaterPages=self._footer
        )

        return path