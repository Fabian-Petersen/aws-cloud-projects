from pdf_service.generator import PDFGenerator


def handler(event, context):
    pdf = PDFGenerator()
    path = pdf.create_pdf("jobcard.pdf")

    return {
        "statusCode": 200,
        "body": {
            "message": "PDF created",
            "path": path
        }
    }

# $ Local execution only
if __name__ == "__main__":
    result = handler({}, {})
    print(result)