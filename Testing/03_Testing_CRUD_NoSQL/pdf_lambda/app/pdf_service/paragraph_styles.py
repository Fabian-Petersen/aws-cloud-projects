from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT

def meta_style(styles):
    return ParagraphStyle(
        name="MetaLine",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=3
    )

def right_small_style(styles):
    return ParagraphStyle(
        name="RightSmall",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_RIGHT
    )
