from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import mm

def draw_signature(canvas, doc, signature_table):
    width, height = signature_table.wrap(doc.width, doc.bottomMargin)

    x = doc.leftMargin
    y = doc.bottomMargin - height - 5 * mm

    signature_table.drawOn(canvas, x, y)