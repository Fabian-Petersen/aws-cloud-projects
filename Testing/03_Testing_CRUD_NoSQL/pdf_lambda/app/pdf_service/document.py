# $ This module builds the template for the pdf document and returns the path to the document and the doc method

import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate


def build_doc(output_dir: str, filename: str):
    path = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    return doc, path


def usable_width(doc):
    return A4[0] - doc.leftMargin - doc.rightMargin