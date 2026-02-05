import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
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