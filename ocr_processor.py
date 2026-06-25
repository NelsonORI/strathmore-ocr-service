import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io

def extract_text_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Convert each PDF page to an image and run Tesseract OCR.
    Returns extracted text and average confidence score.
    """
    try:
        # Convert PDF bytes to list of PIL images (one per page)
        pages = convert_from_bytes(pdf_bytes, dpi=300)

        full_text        = ""
        all_confidences  = []

        for page_number, page_image in enumerate(pages, start=1):
            # Get OCR data including confidence scores per word
            ocr_data = pytesseract.image_to_data(
                page_image,
                output_type=pytesseract.Output.DICT,
                lang='eng'
            )

            # Extract text and confidence scores
            page_text   = ""
            page_conf   = []

            for i, word in enumerate(ocr_data['text']):
                conf = int(ocr_data['conf'][i])
                if conf > 0 and word.strip():
                    page_text += word + " "
                    page_conf.append(conf)

            full_text += f"\n--- Page {page_number} ---\n{page_text.strip()}\n"

            if page_conf:
                all_confidences.extend(page_conf)

        # Calculate average confidence score (0-100 → 0.0-1.0)
        avg_confidence = (sum(all_confidences) / len(all_confidences) / 100) if all_confidences else 0.0

        return {
            'success':          True,
            'text':             full_text.strip(),
            'confidence_score': round(avg_confidence, 4),
            'page_count':       len(pages),
        }

    except Exception as e:
        return {
            'success': False,
            'error':   str(e),
        }