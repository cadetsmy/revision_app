-- ============================================================
-- Revision App Database Schema
-- ============================================================
-- Order matters: parent tables are created before child tables
-- that reference them via foreign keys.
--
-- Priority chain (blocks CSV import today):
--   subjects -> chapters -> topics -> concepts -> questions
--
-- Supporting tables (draftable, don't block import):
--   students, question_attempts, tests, test_attempts, study_sessions
-- ============================================================


-- ============================================================
-- 1. SUBJECTS
-- ============================================================
CREATE TABLE subjects (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  board TEXT NOT NULL,
  class INT NOT NULL
);

-- ============================================================
-- 2. CHAPTERS
-- ============================================================
CREATE TABLE chapters (
  id SERIAL PRIMARY KEY,
  subject_id INT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  name TEXT NOT NULL
);

-- ============================================================
-- 3. TOPICS
-- ============================================================
CREATE TABLE topics (
  id SERIAL PRIMARY KEY,
  chapter_id INT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  name TEXT NOT NULL
);

-- ============================================================
-- 4. CONCEPTS
-- ============================================================
CREATE TABLE concepts (
  id SERIAL PRIMARY KEY,
  topic_id INT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  name TEXT NOT NULL
);

-- ============================================================
-- 5. QUESTIONS
-- ============================================================
CREATE TABLE questions (
  id SERIAL PRIMARY KEY,
  concept_id INT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  question_text TEXT NOT NULL,
  option_a TEXT,
  option_b TEXT,
  option_c TEXT,
  option_d TEXT,
  correct_answer TEXT NOT NULL,
  explanation TEXT,
  difficulty TEXT,       -- e.g. 'easy' | 'medium' | 'hard'
  source_type TEXT,      -- e.g. 'textbook' | 'past_paper' | 'custom'
  source_note TEXT
);

-- ============================================================
-- 6. STUDENTS
-- ============================================================
CREATE TABLE students (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE,
  board TEXT,
  class INT,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- ============================================================
-- 7. QUESTION_ATTEMPTS
-- ============================================================
-- One row per time a student answers a single question.
CREATE TABLE question_attempts (
  id SERIAL PRIMARY KEY,
  student_id INT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  question_id INT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  selected_answer TEXT,
  is_correct BOOLEAN,
  time_taken_seconds INT,
  attempted_at TIMESTAMP NOT NULL DEFAULT now()
);

-- ============================================================
-- 8. TESTS
-- ============================================================
-- A test is a named, reusable set of questions built for a subject.
CREATE TABLE tests (
  id SERIAL PRIMARY KEY,
  subject_id INT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  total_questions INT,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- ============================================================
-- 9. TEST_ATTEMPTS
-- ============================================================
-- One row per time a student takes a given test.
CREATE TABLE test_attempts (
  id SERIAL PRIMARY KEY,
  test_id INT NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
  student_id INT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  score INT,
  total_questions INT,
  started_at TIMESTAMP NOT NULL DEFAULT now(),
  completed_at TIMESTAMP
);

-- ============================================================
-- 10. STUDY_SESSIONS
-- ============================================================
-- Tracks a block of time a student spends studying a subject.
CREATE TABLE study_sessions (
  id SERIAL PRIMARY KEY,
  student_id INT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  subject_id INT REFERENCES subjects(id) ON DELETE SET NULL,
  started_at TIMESTAMP NOT NULL DEFAULT now(),
  ended_at TIMESTAMP,
  duration_minutes INT,
  notes TEXT
);
