"""
generate_chapter_csv.py
-----------------------
Generates educational MCQ questions using the Gemini API
and saves them in the CSV format required by import_csv.py.

Example:
    python generate_chapter_csv.py \
        --board CBSE \
        --class 10 \
        --subject Physics \
        --chapter "Light" \
        --num-questions 30 \
        --out light.csv
"""

import argparse
import csv
import json
import os
import sys
import time

from dotenv import load_dotenv
from google import genai


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    sys.exit(
        "ERROR: GEMINI_API_KEY not found.\n"
        "Create a .env file in the same folder with:\n\n"
        "GEMINI_API_KEY=your_api_key_here"
    )


client = genai.Client(api_key=API_KEY)

# Use a fast model suitable for generating structured questions.
MODEL = "gemini-3.8-flash"


# ---------------------------------------------------------
# CSV columns required by import_csv.py
# ---------------------------------------------------------

CSV_COLUMNS = [
    "question_text",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_answer",
    "explanation",
    "topic",
    "concept",
    "difficulty",
    "source_type",
    "source_note",
]


# ---------------------------------------------------------
# Prompt
# ---------------------------------------------------------

def build_prompt(board, class_name, subject, chapter, num_questions):

    return f"""
You are an expert school-level question paper creator.

Generate exactly {num_questions} high-quality multiple-choice questions
for the following curriculum:

Board: {board}
Class: {class_name}
Subject: {subject}
Chapter: {chapter}

Requirements:

1. Follow the {board} Class {class_name} curriculum.
2. Questions must be relevant to the specified chapter.
3. Cover different concepts within the chapter.
4. Avoid duplicate or near-duplicate questions.
5. Use exactly four options: A, B, C and D.
6. Only one option must be correct.
7. The correct_answer field must contain ONLY:
   A, B, C, or D
8. Include a short explanation of why the answer is correct.
9. Assign each question a difficulty:
   easy, medium, or hard.
10. Every question must have a topic and concept.
11. Do not invent topics that are unrelated to the chapter.
12. Questions should be appropriate for school examinations.
13. Avoid ambiguous questions.
14. Do not use markdown.
15. Do not include numbering outside the JSON data.
16. Return ONLY valid JSON.

Return exactly this structure:

{{
  "questions": [
    {{
      "question_text": "Question here",
      "option_a": "Option A",
      "option_b": "Option B",
      "option_c": "Option C",
      "option_d": "Option D",
      "correct_answer": "A",
      "explanation": "Short explanation.",
      "topic": "Topic name",
      "concept": "Concept name",
      "difficulty": "easy",
      "source_type": "AI-generated",
      "source_note": "Generated for {board} Class {class_name} {subject} - {chapter}"
    }}
  ]
}}

Important:
- Return exactly {num_questions} questions.
- Return valid JSON only.
"""


# ---------------------------------------------------------
# Clean Gemini response
# ---------------------------------------------------------

def clean_response(text):

    text = text.strip()

    # Remove markdown code fences if Gemini adds them.
    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    return text


# ---------------------------------------------------------
# Validate questions
# ---------------------------------------------------------

def validate_questions(questions, expected_count):

    if not isinstance(questions, list):
        raise ValueError("Gemini response does not contain a question list.")

    if len(questions) != expected_count:
        raise ValueError(
            f"Expected {expected_count} questions, "
            f"but Gemini returned {len(questions)}."
        )

    valid_answers = {"A", "B", "C", "D"}
    valid_difficulties = {"easy", "medium", "hard"}

    required = [
        "question_text",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_answer",
        "explanation",
        "topic",
        "concept",
        "difficulty",
        "source_type",
        "source_note",
    ]

    seen_questions = set()

    for i, q in enumerate(questions, start=1):

        if not isinstance(q, dict):
            raise ValueError(f"Question {i} is not an object.")

        # Check required fields
        for field in required:
            if field not in q:
                raise ValueError(
                    f"Question {i} is missing field: {field}"
                )

            if not str(q[field]).strip():
                raise ValueError(
                    f"Question {i} has an empty field: {field}"
                )

        # Validate correct answer
        answer = str(q["correct_answer"]).strip().upper()

        if answer not in valid_answers:
            raise ValueError(
                f"Question {i} has invalid correct_answer: {answer}"
            )

        q["correct_answer"] = answer

        # Validate difficulty
        difficulty = str(q["difficulty"]).strip().lower()

        if difficulty not in valid_difficulties:
            raise ValueError(
                f"Question {i} has invalid difficulty: {difficulty}"
            )

        q["difficulty"] = difficulty

        # Detect duplicate questions
        question_key = (
            str(q["question_text"]).strip().lower()
        )

        if question_key in seen_questions:
            raise ValueError(
                f"Duplicate question detected: {q['question_text']}"
            )

        seen_questions.add(question_key)


# ---------------------------------------------------------
# Generate questions
# ---------------------------------------------------------

def generate_questions(
    board,
    class_name,
    subject,
    chapter,
    num_questions
):

    prompt = build_prompt(
        board,
        class_name,
        subject,
        chapter,
        num_questions
    )

    print()
    print("Generating questions with Gemini...")
    print(f"Board:    {board}")
    print(f"Class:    {class_name}")
    print(f"Subject:  {subject}")
    print(f"Chapter:  {chapter}")
    print(f"Questions: {num_questions}")
    print()

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "temperature": 0.4,
            "response_mime_type": "application/json",
        },
    )

    text = clean_response(response.text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print("Gemini returned invalid JSON.")
        print()
        print(text)
        raise e

    questions = data.get("questions")

    validate_questions(
        questions,
        num_questions
    )

    return questions


# ---------------------------------------------------------
# Save CSV
# ---------------------------------------------------------

def save_csv(questions, output_path):

    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=CSV_COLUMNS
        )

        writer.writeheader()

        for q in questions:
            writer.writerow({
                column: str(q[column]).strip()
                for column in CSV_COLUMNS
            })


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Generate chapter MCQs using Gemini."
    )

    parser.add_argument(
        "--board",
        required=True,
        help="Board, e.g. CBSE"
    )

    parser.add_argument(
        "--class",
        dest="class_",
        required=True,
        help="Class/grade, e.g. 10"
    )

    parser.add_argument(
        "--subject",
        required=True,
        help="Subject, e.g. Physics"
    )

    parser.add_argument(
        "--chapter",
        required=True,
        help="Chapter name, e.g. Light"
    )

    parser.add_argument(
        "--num-questions",
        type=int,
        required=True,
        help="Number of questions to generate"
    )

    parser.add_argument(
        "--out",
        required=True,
        help="Output CSV filename"
    )

    args = parser.parse_args()

    if args.num_questions <= 0:
        sys.exit("ERROR: --num-questions must be greater than 0.")

    if args.num_questions > 100:
        sys.exit(
            "ERROR: Please generate no more than 100 questions "
            "per request."
        )

    try:

        questions = generate_questions(
            board=args.board,
            class_name=args.class_,
            subject=args.subject,
            chapter=args.chapter,
            num_questions=args.num_questions
        )

        save_csv(
            questions,
            args.out
        )

        print()
        print("=" * 60)
        print("SUCCESS")
        print("=" * 60)
        print(f"Generated: {len(questions)} questions")
        print(f"Saved to:  {args.out}")
        print()
        print("Next step:")
        print()
        print(
            f'python import_csv.py "{args.out}" '
            f'--subject "{args.subject}" '
            f'--board "{args.board}" '
            f'--class {args.class_} '
            f'--chapter "{args.chapter}"'
        )
        print()

    except Exception as e:

        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)
        print(str(e))
        print()

        sys.exit(1)


if __name__ == "__main__":
    main()