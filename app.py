from flask import Flask, request, jsonify
from ocr_processor import extract_text_from_pdf
from gemini_service import generate_flashcards as generate_flashcards
from dotenv import load_dotenv
import os
import traceback
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

app = Flask(__name__)

# Max upload size — 20MB
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint — Laravel can ping this to verify the service is up."""
    return jsonify({'status': 'ok'}), 200


@app.route('/process', methods=['POST'])
def process():
    """
    Main endpoint called by Laravel after a class rep uploads a PDF.
    """
    try:
        # Validate PDF is present
        if 'pdf' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400

        pdf_file = request.files['pdf']

        if pdf_file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400

        if not pdf_file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are accepted'}), 400

        # Read metadata
        metadata = {
            'unit_code':     request.form.get('unit_code', ''),
            'unit_name':     request.form.get('unit_name', ''),
            'lecturer':      request.form.get('lecturer', ''),
            'academic_year': request.form.get('academic_year', ''),
            'semester':      request.form.get('semester', ''),
            'exam_type':     request.form.get('exam_type', ''),
        }

        # Read PDF bytes
        pdf_bytes = pdf_file.read()

        # Step 1 — Run OCR
        try:
            ocr_result = extract_text_from_pdf(pdf_bytes)
        except Exception as ocr_exc:
            logger.error(f"Unhandled OCR Exception: {str(ocr_exc)}\n{traceback.format_exc()}")
            return jsonify({
                'error': 'Internal OCR engine failure',
                'debug_message': str(ocr_exc),
                'traceback': traceback.format_exc().splitlines()  # Returns traceback as a clean JSON list
            }), 500

        if not ocr_result['success']:
            return jsonify({
                'error': f"OCR failed: {ocr_result['error']}"
            }), 500

        extracted_text   = ocr_result['text']
        confidence_score = ocr_result['confidence_score']

        if not extracted_text.strip():
            return jsonify({
                'error': 'No text could be extracted from the PDF. The file may be a scanned image with poor quality.'
            }), 422

        # Step 2 — Generate flashcards with Gemini
        gemini_result = generate_flashcards(extracted_text, metadata, confidence_score)

        if not gemini_result['success']:
            # This captures the detailed error object passed from your gemini_service
            raw_error = gemini_result.get('error', 'Unknown Gemini error')
            
            # Log it on the Flask terminal side
            logger.error(f"Gemini Generation Failed. Details: {raw_error}")
            
            return jsonify({
                'error': 'Flashcard generation failed',
                'details': raw_error,  # This will pass back the full stringified API error/dictionary
                'context': {
                    'text_length': len(extracted_text),
                    'unit_code': metadata['unit_code']
                }
            }), 500

        # Step 3 — Return flashcards to Laravel
        return jsonify({
            'success':    True,
            'flashcards': gemini_result['flashcards'],
            'page_count': ocr_result['page_count'],
            'confidence': confidence_score,
        }), 200

    except Exception as e:
        # Catch-all for any weird code crashes (e.g., KeyError, AttributeError)
        tb = traceback.format_exc()
        logger.error(f"Critical unhandled exception in /process: {str(e)}\n{tb}")
        return jsonify({
            'error': 'A critical server error occurred.',
            'exception': str(e),
            'traceback': tb.splitlines()
        }), 500


@app.errorhandler(413)
def file_too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 20MB.'}), 413


if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)