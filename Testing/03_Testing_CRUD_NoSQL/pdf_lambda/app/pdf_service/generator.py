import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate
from pdf_service.header import build_header
from pdf_service.job_info import build_job_info
from pdf_service.description import build_description
from pdf_service.services import build_services
from pdf_service.findings import build_findings
from pdf_service.work_completed import build_work_completed
from pdf_service.paragraph_styles import meta_style
from pdf_service.signature import build_signature

class PDFGenerator:
    def __init__(self, output_dir=None):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(self.base_dir, "assets")
        self.output_dir = output_dir or self.base_dir

    def _footer(self, canvas, doc):
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(
            A4[0] / 2,
            20,
            f"Generated on {datetime.now():%Y-%m-%d %H:%M}"
        )

    def _build_doc(self, filename):
        path = os.path.join(self.output_dir, filename)
        self.doc = SimpleDocTemplate(
            path,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        return path

    def _usable_width(self):
        return A4[0] - self.doc.leftMargin - self.doc.rightMargin

    def create_pdf(self, jobcard: dict, filename: str):
        path = self._build_doc(filename)
        styles = getSampleStyleSheet()
        meta_styles = meta_style(styles)

        story = []
        usable_width = self._usable_width()

        story += build_header(styles, usable_width, self.assets_dir)
        story += build_job_info(jobcard, usable_width, meta_styles)
        story += build_description(jobcard, styles)
        story += build_services(jobcard, styles)
        story += build_findings(jobcard, styles)
        story += build_work_completed(jobcard, styles)
        story += build_signature(styles, self.assets_dir)

        self.doc.build(
            story,
            onFirstPage=self._footer,
            onLaterPages=self._footer
        )

        return path








#     def create_pdf(self, jobcard: dict, filename: str):
#         path = os.path.join(self.output_dir, filename)

#         doc = SimpleDocTemplate(
#             path,
#             pagesize=A4,
#             rightMargin=40,
#             leftMargin=40,
#             topMargin=40,
#             bottomMargin=40
#         )

#         styles = getSampleStyleSheet()

#         story = []

#         # --- Logo ---
#         logo_path = os.path.join(
#             os.path.dirname(__file__),
#             "assets",
#             "atlantic_meat_logo.webp"
#         )

#         if os.path.exists(logo_path):
#             logo = Image(logo_path, width=100, height=50)
#             # story.append(logo)

#         title = Paragraph(
#             "Maintenance Job Card",
#             styles["Title"]
#         )

#         # Calculate usable width
#         usable_width = A4[0] - doc.leftMargin - doc.rightMargin
#         # $ --- Header ---
#         header_table = Table(
#             [[logo, title]],
#             colWidths=[100, usable_width - 110],
#             rowHeights=[65]
#         )

#         header_table.setStyle(TableStyle([
#             # Background color (light yellow)
#             ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fcb53b")),

#             # Alignment
#             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
#             ("ALIGN", (1, 0), (1, 0), "CENTER"),

#             # Padding
#             ("LEFTPADDING", (0, 0), (0, 0), 10),
#             ("RIGHTPADDING", (0, 0), (-1, -1), 10),
#             ("TOPPADDING", (0, 0), (-1, -1), 10),
#             ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
#         ]))

#         story.append(header_table)
#         story.append(Spacer(1, 15))

#         # --- Title ---
#         # story.append(Paragraph("Maintenance Job Card", styles["Title"]))
#         # story.append(Spacer(1, 10))
#         meta_style = ParagraphStyle( 
#             name="MetaLine", 
#             parent=styles["Normal"], 
#             fontSize=10, spaceAfter=3 
#         )

#         # $ --- Request Information ---
#         story.append(Paragraph(f"<b>Job Card No:</b> {jobcard['job_card_no']}", meta_style))
#         story.append(Paragraph(f"<b>Asset ID:</b> {jobcard['asset_id']}", meta_style))
        
#         story.append(Spacer(1, 10))
        
#         # $ --- Job Info ---
#         meta_style = ParagraphStyle(
#         name="MetaLine",
#         parent=styles["Normal"],
#         fontSize=10,
#         spaceAfter=3
#         )

#         # --- Request Details ---
#         left_table = Table(
#             [
#                 [Paragraph(f"<b>Requested By:</b> {jobcard['requested_by']}", meta_style)],
#                 [Paragraph(f"<b>Date Requested:</b> {jobcard['date']}", meta_style)],
#                 [Paragraph(f"<b>Asset Desription:</b> {jobcard['asset_description']}", meta_style)],
#                 [Paragraph(f"<b>Location:</b> {jobcard['location']}", meta_style)],
#             ],
#             colWidths=[usable_width * 0.48],
#             hAlign="LEFT"
#         )

#         left_table.setStyle(TableStyle([
#             ("ALIGN", (0, 0), (-1, -1), "LEFT"),
#             ("VALIGN", (0, 0), (-1, -1), "TOP"),
#             ("LEFTPADDING", (0, 0), (-1, -1), 0),
#             ("RIGHTPADDING", (0, 0), (-1, -1), 0),
#         ]))
        
#         # left_column = [
#         #     Paragraph(f"<b>Requested By:</b> {jobcard['requested_by']}", meta_style),
#         #     Paragraph(f"<b>Date Requested:</b> {jobcard['date']}", meta_style),
#         #     Paragraph(f"<b>Asset Desription:</b> {jobcard['asset_description']}", meta_style),
#         #     Paragraph(f"<b>Location:</b> {jobcard['location']}", meta_style),
#         # ]

#         right_table = Table(
#             [
#                 [Paragraph(f"<b>Actioned By:</b> {jobcard['actioned_by']}", meta_style)],
#                 [Paragraph(f"<b>Date Actioned:</b> {jobcard['date_actioned']}", meta_style)],
#                 [Paragraph(f"<b>Root Cause:</b> {jobcard['root_cause']}", meta_style)],
#                 [Paragraph(f"<b>Status:</b> {jobcard['status']}", meta_style)],
#             ],
#             colWidths=[usable_width * 0.48],
#             hAlign="RIGHT"
#         )

#         right_table.setStyle(TableStyle([
#             ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
#             ("VALIGN", (0, 0), (-1, -1), "TOP"),
#             ("LEFTPADDING", (0, 0), (-1, -1), 70),
#             ("RIGHTPADDING", (0, 0), (-1, -1), 0),
#         ]))

#         container_table = Table(
#             [[left_table, right_table]],
#             colWidths=[usable_width * 0.5, usable_width * 0.48],
#             hAlign="LEFT"
#         )

#         container_table.setStyle(TableStyle([
#             ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
#             ("VALIGN", (0, 0), (-1, -1), "TOP"),
#             ("LEFTPADDING", (0, 0), (-1, -1), 0),
#             ("RIGHTPADDING", (0, 0), (-1, -1), 0),
#         ]))

#         story.append(container_table)
#         story.append(Spacer(1, 8))

#         # $ --- Job Action Details ---
#         # right_column = [
#         #     Paragraph(f"<b>Actioned By:</b> {jobcard['actioned_by']}", meta_style),
#         #     Paragraph(f"<b>Date Actioned:</b> {jobcard['date_actioned']}", meta_style),
#         #     Paragraph(f"<b>Root Cause:</b> {jobcard['root_cause']}", meta_style),
#         #     Paragraph(f"<b>Status:</b> {jobcard['status']}", meta_style),
#         # ]

#         # meta_table = Table(
#         #     list(zip(left_column, right_column)),
#         #     colWidths=[usable_width / 2, usable_width / 2],
#         #     hAlign="LEFT"
#         # )

#         # meta_table.setStyle(TableStyle([
#         #     ("VALIGN", (0, 0), (-1, -1), "TOP"),
#         #     ("LEFTPADDING", (0, 0), (-1, -1), 0),
#         #     ("RIGHTPADDING", (0, 0), (-1, -1), 0),
#         #     ("TOPPADDING", (0, 0), (-1, -1), 2),
#         #     ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
#         # ]))

#         # story.append(meta_table)
#         story.append(Spacer(1, 8))

#         # $ --- Description ---
#         story.append(Paragraph("<b>Job Description</b>", styles["Heading3"]))
#         story.append(Paragraph(jobcard["description"], styles["Normal"]))
#         story.append(Spacer(1, 10))


# # $ ===================================== parts table ========================================  
#         # $ --- Parts Used Table ---
#         story.append(Paragraph("<b>Parts Used</b>", styles["Heading3"]))

#         table_data = [
#             ["Part Name", "Quantity", "Price (R)"]
#         ]

#         parts_total = 0.0

#         def zar(amount):
#             return f"R {amount:,.2f}"
        
#         for part in jobcard["parts_used"]:
#             qty = int(part.get("qty", 1))
#             cost = float(part.get("cost", 0))
#             line_total = qty * cost
#             parts_total += line_total

#             table_data.append([
#                 part["name"],
#                 str(qty),
#                 zar(line_total)
#             ])

#         table = Table(table_data, colWidths=[350, 50, 106])

#         table.setStyle(TableStyle([
#             ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
#             ("GRID", (0, 0), (-1, -1), 1, colors.black),

#             # Header
#             ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),

#             # Alignments
#             ("ALIGN", (1, 1), (1, -1), "CENTER"),
#             ("ALIGN", (2, 1), (2, -1), "RIGHT"),
#             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
#         ]))
        
#         story.append(table)

#         story.append(Spacer(1, 10))

#         subtotal_style = ParagraphStyle(
#         name="TotalRight",
#         parent=styles["Normal"],
#         fontSize=9,
#         alignment=TA_RIGHT
#         )

#         story.append(
#             Paragraph(
#             f"Subtotal : <b>{zar(parts_total)}</b>",
#             subtotal_style
#             )
#         )

# # $ ===================================== services table ========================================

#         KM_RATE = 4.50
#         HOUR_RATE = 350.00  # adjust if needed

#         kilometers = float(jobcard.get("kilometers", 0))
#         hours_on_site = float(jobcard.get("hours_on_site", 0))

#         services_table_data = [
#             ["Service", "Qty", "Price (R)"]
#         ]

#         km_cost = kilometers * KM_RATE
#         hour_cost = hours_on_site * HOUR_RATE

#         services_table_data.append([
#             "Travel (Kilometers)",
#             f"{kilometers:.1f}",
#             zar(km_cost)
#         ])

#         services_table_data.append([
#             "Labour (Hours on site)",
#             f"{hours_on_site:.1f}",
#             zar(hour_cost)
#         ])

#         services_total = km_cost + hour_cost

#         services_table = Table(
#             services_table_data,
#             colWidths=[350, 50, 106]
#         )

#         services_table.setStyle(TableStyle([
#             ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
#             ("GRID", (0, 0), (-1, -1), 1, colors.black),

#             ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),

#             ("ALIGN", (1, 1), (1, -1), "CENTER"),
#             ("ALIGN", (2, 1), (2, -1), "RIGHT"),
#             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
#         ]))

#         story.append(Paragraph("<b>Labour & Travel Costs</b>", styles["Heading3"]))
        
#         # story.append(Spacer(1, 10))
#         story.append(services_table)

#         job_total = parts_total + services_total

#         story.append(Spacer(1, 12))

#         # services_total_style = ParagraphStyle(
#         #     name="JobTotalRight",
#         #     parent=styles["Normal"],
#         #     fontSize=10,
#         #     alignment=TA_RIGHT
#         # )

#         story.append(
#             Paragraph(
#                 f"SubTotal : <b>{zar(services_total)}</b>",
#                 subtotal_style
#             )
#         )


# # $ ====================================== Total Cost ===============================
#         story.append(Spacer(1, 15))

#         job_total_style = ParagraphStyle(
#             name="JobTotalRight",
#             parent=styles["Normal"],
#             fontSize=12,
#             alignment=TA_RIGHT
#         )

#         story.append(
#             Paragraph(
#                 f"<b>TOTAL : </b> <b>{zar(job_total)}</b>",
#                 job_total_style
#             )
#         )

#         # 🔹 Horizontal line
#         # story.append(Spacer(1, 6))
#         # story.append(HRFlowable(
#         #     width="100%",
#         #     thickness=1,
#         #     color=colors.lightgrey,
#         #     spaceBefore=10,
#         #     spaceAfter=10
#         # ))

#         # $ --- Findings ---
#         story.append(Paragraph("<b>Findings</b>", styles["Heading3"]))
#         story.append(Paragraph(jobcard["findings"], styles["Normal"]))
#         story.append(Spacer(1, 10))

#         # $ --- Works Completed ---
#         story.append(Paragraph("<b>Works Completed</b>", styles["Heading3"]))
#         story.append(Paragraph(jobcard["works_completed"], styles["Normal"]))
#         story.append(Spacer(1, 10))


#         # $ --- signature ---
#         # Push content towards bottom of page
#         story.append(Spacer(1, 10))

#         signature_path = os.path.join(
#             os.path.dirname(__file__),
#             "assets",
#             "signature.png"
#         )

#         if os.path.exists(signature_path):
#             signature_img = Image(signature_path, width=120, height=50)
#         else:
#             signature_img = Spacer(1, 10)

#         signature_label = Paragraph(
#             "<b>Customer Signature</b>",
#             styles["Normal"]
#         )

#         signature_table = Table(
#             [
#                 [signature_img],
#                 [""],                    # space before line
#                 [""],                    # horizontal line row
#                 [signature_label],
#             ],
#             colWidths=[160],
#             rowHeights=[55, 6, 1, 18],
#             hAlign="LEFT"
#         )

#         signature_table.setStyle(TableStyle([
#             # ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
#             # Align left
#             ("ALIGN", (0, 0), (-1, -1), "LEFT"),
#             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

#             # Horizontal line
#             ("LINEBELOW", (0, 2), (0, 2), 1, colors.lightgrey),

#             # Padding
#             ("LEFTPADDING", (0, 0), (-1, -1), 0),
#             ("RIGHTPADDING", (0, 0), (-1, -1), 0),
#             ("TOPPADDING", (0, 0), (-1, -1), 2),
#             ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
#         ]))

#         story.append(signature_table)

#         # --- Build ---
#         doc.build(
#             story,
#             onFirstPage=self._footer,
#             onLaterPages=self._footer
#         )

#         return path