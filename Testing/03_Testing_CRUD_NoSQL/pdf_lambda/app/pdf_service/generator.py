from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os


class PDFGenerator:
    # output_dir="/tmp"
    def __init__(self, output_dir=None):
        # Directory where this file lives
        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(__file__))

        self.output_dir = output_dir

    def create_pdf(self, filename="example.pdf"):
        path = os.path.join(self.output_dir, filename)
        c = canvas.Canvas(path, pagesize=A4)
        c.drawString(100, 800, "Maintenance Job Card")
        c.drawString(100, 770, "Generated with ReportLab")
        c.showPage()
        c.save()

        return path