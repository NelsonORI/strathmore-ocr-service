from groq import Groq
import json
import os
import re

def generate_flashcards(extracted_text: str, metadata: dict, confidence_score: float) -> dict:
    """
    Send extracted OCR text to Groq API and get back structured Q&A flashcard pairs.
    """
    try:
        client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

        prompt = f"""
You are an expert academic flashcard generator for university students.

You have been given the extracted text from a past exam paper with the following details:
- Unit Code: {metadata.get('unit_code')}
- Unit Name: {metadata.get('unit_name')}
- Lecturer: {metadata.get('lecturer')}
- Academic Year: {metadata.get('academic_year')}
- Semester: {metadata.get('semester')}
- Exam Type: {metadata.get('exam_type')}

Your task is to generate clear, concise, and accurate Q&A flashcard pairs from the exam paper text below.

Rules:
1. Extract every distinct question or concept from the text
2. Each flashcard must have a clear question and a complete, accurate answer
3. Questions should be standalone and self-explanatory
4. Answers should be thorough but concise
5. Ignore page numbers, headers, footers, and irrelevant formatting text
6. Generate between 10 and 40 flashcards depending on the content
7. Return ONLY a valid JSON array — no extra text, no markdown, no explanation

Return this exact format:
[
  {{
    "question": "What is normalisation in database design?",
    "answer": "Normalisation is the process of organising a database to reduce redundancy and improve data integrity by dividing large tables into smaller ones and defining relationships between them."
  }}
]

Exam paper text:
{extracted_text}
"""

        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {
                    'role': 'system',
                    'content': 'You are an expert academic flashcard generator. You always return only valid JSON arrays with no extra text or markdown.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        response_text = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'^```\s*',     '', response_text)
        response_text = re.sub(r'\s*```$',     '', response_text)
        response_text = response_text.strip()

        flashcards_raw = json.loads(response_text)

        # Attach confidence score to each card
        flashcards = [
            {
                'question':         card['question'],
                'answer':           card['answer'],
                'confidence_score': confidence_score,
            }
            for card in flashcards_raw
            if 'question' in card and 'answer' in card
        ]

        return {
            'success':    True,
            'flashcards': flashcards,
        }

    except json.JSONDecodeError as e:
        return {
            'success': False,
            'error':   f'Groq returned invalid JSON: {str(e)}',
        }

    except Exception as e:
        return {
            'success': False,
            'error':   str(e),
        }