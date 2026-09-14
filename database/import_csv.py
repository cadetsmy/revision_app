"""
import_csv.py
--------------
Imports one chapter's questions CSV into the Supabase (Postgres) database.

Usage:
    python import_csv.py <csv_path> --subject "Biology" --board "CBSE" --class 10 --chapter "Life Processes"

What it does, step by step:
  1. Connects to your Supabase Postgres database using DATABASE_URL from a .env file.
  2. Gets-or-creates the subject row (matched by name + board + class).
  3. Gets-or-creates the chapter row under that subject (matched by name).
  4. For every CSV row:
       - Gets-or-creates the topic under that chapter (from the CSV 'topic' column).
       - Gets-or-creates the concept under that topic (from the CSV 'concept' column).
       - Inserts the question under that concept.
  5. Prints a summary of what was created/found and how many questions were inserted.

Expected CSV columns (order doesn't matter, names must match exactly):
    question_text, option_a, option_b, option_c, option_d,
    correct_answer, explanation, topic, concept,
    difficulty, source_type, source_note

Setup (once):
    pip install psycopg2-binary python-dotenv
    Create a .env file (never commit it) in the same folder with:
        DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres
    (Get this from Supabase: Project Settings > Database > Connection string > URI)
"""

import argparse
import csv
import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()

REQUIRED_COLUMNS = [
    "question_text", "option_a", "option_b", "option_c", "option_d",
    "correct_answer", "explanation", "topic", "concept",
    "difficulty", "source_type", "source_note",
]


def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        sys.exit(
            "ERROR: DATABASE_URL not found. Create a .env file next to this "
            "script with:\n  DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres"
        )
    return psycopg2.connect(db_url)


def get_or_create(cur, table, match_cols, match_vals, insert_cols=None, insert_vals=None):
    """
    Generic get-or-create helper.
    match_cols/match_vals: columns+values used to find an existing row.
    insert_cols/insert_vals: full set of columns+values used if we need to insert.
    Returns the row's id.
    """
    where_clause = " AND ".join(f"{c} = %s" for c in match_cols)
    cur.execute(f"SELECT id FROM {table} WHERE {where_clause}", match_vals)
    row = cur.fetchone()
    if row:
        return row[0]

    insert_cols = insert_cols or match_cols
    insert_vals = insert_vals or match_vals
    cols_sql = ", ".join(insert_cols)
    placeholders = ", ".join(["%s"] * len(insert_vals))
    cur.execute(
        f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders}) RETURNING id",
        insert_vals,
    )
    return cur.fetchone()[0]


def validate_headers(fieldnames):
    missing = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
    if missing:
        sys.exit(
            f"ERROR: CSV is missing required column(s): {missing}\n"
            f"Found columns: {fieldnames}"
        )


def main():
    parser = argparse.ArgumentParser(description="Import a chapter's questions CSV into Supabase.")
    parser.add_argument("csv_path", help="Path to the questions CSV file")
    parser.add_argument("--subject", required=True, help="Subject name, e.g. Biology")
    parser.add_argument("--board", required=True, help="Board, e.g. CBSE")
    parser.add_argument("--class", dest="class_", required=True, type=int, help="Class/grade, e.g. 10")
    parser.add_argument("--chapter", required=True, help="Chapter name, e.g. 'Life Processes'")
    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        sys.exit(f"ERROR: file not found: {args.csv_path}")

    with open(args.csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        validate_headers(reader.fieldnames)
        rows = list(reader)

    if not rows:
        sys.exit("ERROR: CSV has no data rows.")

    conn = get_connection()
    cur = conn.cursor()

    try:
        subject_id = get_or_create(
            cur, "subjects",
            match_cols=["name", "board", "class"],
            match_vals=[args.subject, args.board, args.class_],
        )
        chapter_id = get_or_create(
            cur, "chapters",
            match_cols=["name", "subject_id"],
            match_vals=[args.chapter, subject_id],
        )

        topic_cache = {}
        concept_cache = {}
        inserted = 0

        for i, row in enumerate(rows, start=2):  # start=2 because row 1 is the header
            topic_name = row["topic"].strip()
            concept_name = row["concept"].strip()

            if not topic_name or not concept_name:
                print(f"  Skipping row {i}: missing topic or concept")
                continue

            topic_key = (chapter_id, topic_name)
            if topic_key not in topic_cache:
                topic_cache[topic_key] = get_or_create(
                    cur, "topics",
                    match_cols=["name", "chapter_id"],
                    match_vals=[topic_name, chapter_id],
                )
            topic_id = topic_cache[topic_key]

            concept_key = (topic_id, concept_name)
            if concept_key not in concept_cache:
                concept_cache[concept_key] = get_or_create(
                    cur, "concepts",
                    match_cols=["name", "topic_id"],
                    match_vals=[concept_name, topic_id],
                )
            concept_id = concept_cache[concept_key]

            cur.execute(
                """
                INSERT INTO questions (
                    concept_id, question_text, option_a, option_b, option_c, option_d,
                    correct_answer, explanation, difficulty, source_type, source_note
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    concept_id,
                    row["question_text"].strip(),
                    row["option_a"].strip(),
                    row["option_b"].strip(),
                    row["option_c"].strip(),
                    row["option_d"].strip(),
                    row["correct_answer"].strip(),
                    row["explanation"].strip(),
                    row["difficulty"].strip() or None,
                    row["source_type"].strip() or None,
                    row["source_note"].strip() or None,
                ],
            )
            inserted += 1

        conn.commit()
        print(f"Subject id: {subject_id} ({args.subject}, {args.board}, class {args.class_})")
        print(f"Chapter id: {chapter_id} ({args.chapter})")
        print(f"Topics used: {len(topic_cache)} | Concepts used: {len(concept_cache)}")
        print(f"Questions inserted: {inserted} / {len(rows)}")

    except Exception as e:
        conn.rollback()
        print(f"ERROR during import, rolled back all changes: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
