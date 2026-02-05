import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate
from pdf_service.header import build_header
from pdf_service.document import build_doc, usable_width
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
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(
            A4[0] / 2,
            20,
            f"Generated on {datetime.now():%d-%m-%Y %H:%M}"
        )

    def create_pdf(self, jobcard: dict, filename: str):
        self.doc, path = build_doc(self.output_dir, filename)
        styles = getSampleStyleSheet()
        meta_styles = meta_style(styles)

        story = []
        width = usable_width(self.doc)

        story += build_header(styles, width, self.assets_dir)
        story += build_job_info(jobcard, width, meta_styles)
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