"""
SPARK Database Models (Flask-SQLAlchemy)
Reflects the PostgreSQL database schema used by the SPARK Student Portal.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


# =========================================================
# USER
# =========================================================

class User(db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False
    )
    # student / counselor

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    student = db.relationship(
        "Student",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan"
    )


# =========================================================
# STUDENT
# =========================================================

class Student(db.Model):

    __tablename__ = "students"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True,
        nullable=True
    )

    student_id = db.Column(
        db.String(50),
        unique=True,
        nullable=True
    )

    full_name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150)
    )

    phone = db.Column(
        db.String(30)
    )

    date_of_birth = db.Column(
        db.String(30)
    )

    department = db.Column(
        db.String(150)
    )

    grade = db.Column(
        db.String(20),
        default="Grade 11"
    )

    subjects = db.Column(
        db.Text
    )

    target_degree = db.Column(
        db.Text
    )

    career_interest = db.Column(
        db.Text
    )

    why_interest = db.Column(
        db.Text
    )

    strengths = db.Column(
        db.Text
    )

    academic_average = db.Column(
        db.Float,
        default=0.0
    )

    readiness_score = db.Column(
        db.Float,
        default=0.0
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# Alias for backward compatibility
StudentProfile = Student


# =========================================================
# ACADEMICS
# =========================================================

class Academic(db.Model):

    __tablename__ = "academics"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    subject = db.Column(
        db.String(100),
        nullable=False
    )

    marks = db.Column(
        db.Float
    )

    max_marks = db.Column(
        db.Float,
        default=100
    )

    exam_name = db.Column(
        db.String(100)
    )

    academic_year = db.Column(
        db.String(30)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# TESTS
# =========================================================

class TestScore(db.Model):

    __tablename__ = "test_scores"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    test_name = db.Column(
        db.String(50),
        nullable=False
    )

    score = db.Column(
        db.String(50)
    )

    test_date = db.Column(
        db.String(30)
    )

    status = db.Column(
        db.String(30),
        default="Planned"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# MILESTONES
# =========================================================

class Milestone(db.Model):

    __tablename__ = "milestones"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    program = db.Column(
        db.String(100)
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    status = db.Column(
        db.String(50),
        default="Not Started"
    )

    target_date = db.Column(
        db.String(30)
    )

    work_completed = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# UNIVERSITIES
# =========================================================

class University(db.Model):

    __tablename__ = "universities"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    university = db.Column(
        db.String(200),
        nullable=False
    )

    country = db.Column(
        db.String(100)
    )

    course = db.Column(
        db.String(200)
    )

    category = db.Column(
        db.String(30)
    )
    # Reach / Match / Safe

    deadline = db.Column(
        db.String(30)
    )

    annual_cost = db.Column(
        db.String(100)
    )

    scholarship = db.Column(
        db.String(100)
    )

    status = db.Column(
        db.String(50),
        default="Planning"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# ACTIVITIES
# =========================================================

class Activity(db.Model):

    __tablename__ = "activities"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    activity = db.Column(
        db.String(200),
        nullable=False
    )

    activity_type = db.Column(
        db.String(100)
    )

    role = db.Column(
        db.String(100)
    )

    hours_per_week = db.Column(
        db.Float
    )

    weeks_per_year = db.Column(
        db.Float
    )

    impact = db.Column(
        db.Text
    )

    evidence = db.Column(
        db.String(500)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# ESSAYS & RECOMMENDERS
# =========================================================

class Essay(db.Model):

    __tablename__ = "essays"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    essay_prompt = db.Column(
        db.Text
    )

    university = db.Column(
        db.String(200)
    )

    draft_status = db.Column(
        db.String(50),
        default="Not Started"
    )

    feedback = db.Column(
        db.Text
    )

    deadline = db.Column(
        db.String(30)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Recommender(db.Model):

    __tablename__ = "recommenders"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    teacher_name = db.Column(
        db.String(150)
    )

    subject = db.Column(
        db.String(100)
    )

    status = db.Column(
        db.String(50),
        default="Requested"
    )

    deadline = db.Column(
        db.String(30)
    )

    brag_sheet = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# DEADLINES
# =========================================================

class Deadline(db.Model):

    __tablename__ = "deadlines"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    due_date = db.Column(
        db.String(30)
    )

    action = db.Column(
        db.String(250),
        nullable=False
    )

    university_or_test = db.Column(
        db.String(200)
    )

    owner = db.Column(
        db.String(100)
    )

    status = db.Column(
        db.String(50),
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# PREREQUISITES
# =========================================================

class Prerequisite(db.Model):

    __tablename__ = "prerequisites"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    requirement = db.Column(
        db.String(200),
        nullable=False
    )

    completed = db.Column(
        db.Boolean,
        default=False
    )

    notes = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# DOCUMENTS
# =========================================================

class Document(db.Model):

    __tablename__ = "documents"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    document_name = db.Column(
        db.String(200),
        nullable=False
    )

    file_path = db.Column(
        db.String(500)
    )

    file_type = db.Column(
        db.String(50)
    )

    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# MASTER UNIVERSITIES
# =========================================================

class MasterUniversity(db.Model):

    __tablename__ = "master_universities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    country = db.Column(db.String(100), nullable=False)
    best_fit_courses = db.Column(db.Text)
    academic_requirement = db.Column(db.Text)
    key_subjects = db.Column(db.Text)
    tests = db.Column(db.Text)
    competitive_target = db.Column(db.Text)
    application_deadline = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MasterUniversityRequirement(db.Model):

    __tablename__ = "master_university_requirements"

    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey("master_universities.id"), nullable=False)
    requirement_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)


# =========================================================
# STUDENT PREREQUISITES & ALERTS
# =========================================================

class StudentPrerequisite(db.Model):

    __tablename__ = "student_prerequisites"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    university_id = db.Column(db.Integer, db.ForeignKey("universities.id", ondelete="CASCADE"), nullable=False)
    requirement_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    completed_at = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Alert(db.Model):

    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    deadline_id = db.Column(db.Integer)
    item_type = db.Column(db.String(50))
    severity = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    target_url = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)