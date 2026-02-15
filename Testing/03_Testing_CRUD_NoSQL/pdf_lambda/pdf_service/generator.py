# $ This code generate a pdf in bytes and put in s3 bucket

import os
from datetime import datetime
from io import BytesIO
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
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(self.base_dir, "assets")

    def _footer(self, canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(
            A4[0] / 2,
            20,
            f"Generated on {datetime.now():%d-%m-%Y %H:%M}"
        )

    def create_pdf(self, jobcard: dict) -> bytes:
        if not isinstance(jobcard, dict):
            raise ValueError("jobcard must be a dict")
        
        buffer = BytesIO()

        doc = build_doc(buffer)
        styles = getSampleStyleSheet()
        meta_styles = meta_style(styles)

        story = []
        width = usable_width(doc)

        story += build_header(styles, width, self.assets_dir)
        story += build_job_info(jobcard, width, meta_styles)
        story += build_description(jobcard, styles)
        story += build_services(jobcard, styles)
        story += build_findings(jobcard, styles)
        story += build_work_completed(jobcard, styles)
        story += build_signature(styles, self.assets_dir)

        doc.build(
            story,
            onFirstPage=self._footer,
            onLaterPages=self._footer
        )
        buffer.seek(0)
        return buffer.getvalue()