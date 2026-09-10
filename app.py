from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_file,
    flash,
    g
)

import os
import csv
import re
import sqlite3
import textwrap
import zlib
from datetime import datetime
from io import BytesIO, StringIO
from functools import wraps

import sqlite3
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from jinja2 import ChoiceLoader, FileSystemLoader, PrefixLoader

# PostgreSQL support
try:
    import psycopg2
    from psycopg2 import sql
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

from config import Config
from university_data import (
    MASTER_UNIVERSITIES_DATA,
    seed_master_universities,
    seed_student_prerequisites_for_university,
    compute_student_alerts
)


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app = Flask(__name__)
app.config.from_object(Config)

# The project keeps its templates in a flat directory while routes use
# student/... and counselor/... template names.  Map both namespaces to the
# shared template directory so the same paths work locally and on Vercel.
_templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
app.jinja_loader = ChoiceLoader([
    FileSystemLoader(_templates_dir),
    PrefixLoader({
        "student": FileSystemLoader(_templates_dir),
        "counselor": FileSystemLoader(_templates_dir),
    }),
])

BASE_DIR = app.config["BASE_DIR"]
app.secret_key = app.config["SECRET_KEY"]
app.config["DB_PATH"] = Config.DB_PATH

UPLOAD_FOLDER = app.config["UPLOAD_FOLDER"]
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

_target_logo = os.path.join(BASE_DIR, "static", "logo.png")
_target_students = os.path.join(BASE_DIR, "static", "nest-students.jpg")


def allowed_file(filename, custom_allowed=None):
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    allowed = custom_allowed or app.config.get("ALLOWED_EXTENSIONS", Config.ALLOWED_EXTENSIONS)
    return ext in allowed


# ============================================================
# DATABASE CONNECTION
# ============================================================

class SparkConnection:
    def __init__(self, connection, db_type="sqlite"):
        self._connection = connection
        self._closed = False
        self._db_type = db_type

    def cursor(self):
        return self._connection.cursor()

    def execute(self, query, params=None):
        cursor = self.cursor()
        # Handle parameter differences between SQLite and PostgreSQL
        if self._db_type == "postgresql" and params:
            # PostgreSQL uses %s placeholders
            cursor.execute(query, params)
        else:
            # SQLite uses ? placeholders
            cursor.execute(query, params or ())
        return cursor

    def commit(self):
        if not self._closed:
            self._connection.commit()

    def rollback(self):
        if not self._closed:
            self._connection.rollback()

    def close(self):
        if not self._closed:
            self._connection.close()
            self._closed = True


def get_db():
    if "db" not in g:
        try:
            database_url = app.config.get("DATABASE_URL")
            db_type = getattr(Config, 'DB_TYPE', 'sqlite')
            
            if database_url and db_type == "postgresql" and POSTGRESQL_AVAILABLE:
                # Use PostgreSQL
                raw_conn = psycopg2.connect(database_url)
                raw_conn.autocommit = False
                g.db = SparkConnection(raw_conn, db_type="postgresql")
            else:
                # Use SQLite
                db_path = app.config.get("DB_PATH", os.path.join(BASE_DIR, "spark.db"))
                raw_conn = sqlite3.connect(db_path)
                raw_conn.row_factory = sqlite3.Row
                g.db = SparkConnection(raw_conn, db_type="sqlite")
        except Exception as e:
            print(f"Database connection error: {e}")
            # For SQLite, try to create database if it doesn't exist
            if not database_url or db_type == "sqlite":
                ensure_db_exists()
                # Try again
                db_path = app.config.get("DB_PATH", os.path.join(BASE_DIR, "spark.db"))
                raw_conn = sqlite3.connect(db_path)
                raw_conn.row_factory = sqlite3.Row
                g.db = SparkConnection(raw_conn, db_type="sqlite")
            else:
                raise
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def student_record_csv(conn, student_id):
    """Create a portable complete-record export for a student."""
    output = StringIO()
    writer = csv.writer(output)
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if student is None:
        return None
    writer.writerow(["SPARK Student Record"])
    writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")])
    writer.writerow([])
    writer.writerow(["Student profile"])
    for key, value in dict(student).items():
        writer.writerow([key.replace("_", " ").title(), value or ""])

    exports = {
        "Academic records": ("academics", ("subject", "marks", "grade", "exam_name", "created_at")),
        "Test scores": ("test_scores", ("test_name", "score", "test_date", "status")),
        "Milestones": ("milestones", ("title", "target_date", "status")),
        "Universities": ("universities", ("university_name", "country", "degree", "application_type", "deadline", "status")),
        "Activities": ("activities", ("activity_name", "category", "description", "achievement")),
        "Essays": ("essays", ("essay_prompt", "university", "draft_status", "deadline")),
        "Deadlines": ("deadlines", ("action", "due_date", "category", "status")),
        "Prerequisites": ("prerequisites", ("requirement", "completed", "notes")),
        "Readiness checklist": ("readiness_checklist", ("item_key", "completed", "updated_at")),
        "Documents": ("documents", ("document_name", "file_name", "uploaded_at")),
    }
    for heading, (table, columns) in exports.items():
        writer.writerow([])
        writer.writerow([heading])
        writer.writerow([column.replace("_", " ").title() for column in columns])
        order_by = "updated_at DESC" if table == "readiness_checklist" else "id DESC"
        rows = conn.execute(f"SELECT {', '.join(columns)} FROM {table} WHERE student_id = ? ORDER BY {order_by}", (student_id,)).fetchall()
        writer.writerows([[row[column] if row[column] is not None else "" for column in columns] for row in rows])
    return output.getvalue()


def get_full_student_data(conn, student_id):
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if student is None:
        return None
    student_dict = dict(student)
    
    def fetch_all(query, args=()):
        return [dict(r) for r in conn.execute(query, args).fetchall()]

    return {
        'student': student_dict,
        'academics': fetch_all("SELECT * FROM academics WHERE student_id = ? ORDER BY id DESC", (student_id,)),
        'test_scores': fetch_all("SELECT * FROM test_scores WHERE student_id = ? ORDER BY id DESC", (student_id,)),
        'milestones': fetch_all("SELECT * FROM milestones WHERE student_id = ? ORDER BY id DESC", (student_id,)),
        'universities': fetch_all("SELECT * FROM universities WHERE student_id = ? ORDER BY id DESC", (student_id,)),
        'activities': fetch_all("SELECT * FROM activities WHERE student_id = ? ORDER BY id DESC", (student_id,)),
        'essays': fetch_all("SELECT * FROM essays WHERE student_id = ? ORDER BY id DESC", (student_id,)),
        'deadlines': fetch_all("SELECT * FROM deadlines WHERE student_id = ? ORDER BY id DESC", (student_id,)),
        'prerequisites': fetch_all("SELECT * FROM prerequisites WHERE student_id = ? ORDER BY id DESC", (student_id,)),
        'readiness_checklist': fetch_all("SELECT * FROM readiness_checklist WHERE student_id = ? ORDER BY updated_at DESC", (student_id,)),
        'documents': fetch_all("SELECT * FROM documents WHERE student_id = ? ORDER BY id DESC", (student_id,)),
    }


class SparkInteractivePDFEngine:
    def __init__(self, data, options=None):
        self.data = data
        self.options = options or {}
        self.theme = self.options.get('theme', 'navy')
        self.enable_checklist = self.options.get('interactive_checklist', True)
        self.enable_notes = self.options.get('fillable_notes', True)
        self.enable_links = self.options.get('clickable_links', True)
        self.sections_filter = self.options.get('sections', None)

        palettes = {
            'navy': {
                'primary': (0.043, 0.204, 0.459),      # #0B3475
                'primary_dark': (0.031, 0.161, 0.341), # #082957
                'secondary': (1.0, 0.608, 0.102),     # #FF9B1A
                'accent': (0.914, 0.294, 0.141),        # #E94B24
                'gold': (0.910, 0.788, 0.471),          # #E8C978
                'bg_card': (1.0, 0.976, 0.910),         # #FFF9E8
                'bg_subtle': (1.0, 0.953, 0.839),       # #FFF3D6
                'text_main': (0.043, 0.204, 0.459),     # #0B3475
                'text_muted': (0.325, 0.420, 0.557),    # #536B8E
                'border': (0.910, 0.788, 0.471),        # #E8C978
                'white': (1.0, 1.0, 1.0),
                'row_alt': (0.98, 0.96, 0.92)
            },
            'emerald': {
                'primary': (0.023, 0.373, 0.275),      # #065F46
                'primary_dark': (0.016, 0.286, 0.208),
                'secondary': (0.063, 0.725, 0.506),
                'accent': (0.961, 0.620, 0.043),
                'gold': (0.651, 0.890, 0.631),
                'bg_card': (0.941, 0.980, 0.953),
                'bg_subtle': (0.871, 0.953, 0.902),
                'text_main': (0.023, 0.373, 0.275),
                'text_muted': (0.282, 0.467, 0.384),
                'border': (0.651, 0.890, 0.631),
                'white': (1.0, 1.0, 1.0),
                'row_alt': (0.92, 0.96, 0.94)
            },
            'sunset': {
                'primary': (0.486, 0.176, 0.071),      # #7C2D12
                'primary_dark': (0.365, 0.118, 0.047),
                'secondary': (0.961, 0.459, 0.118),
                'accent': (0.886, 0.149, 0.149),
                'gold': (0.992, 0.796, 0.431),
                'bg_card': (0.996, 0.953, 0.914),
                'bg_subtle': (0.996, 0.902, 0.816),
                'text_main': (0.486, 0.176, 0.071),
                'text_muted': (0.604, 0.365, 0.282),
                'border': (0.992, 0.796, 0.431),
                'white': (1.0, 1.0, 1.0),
                'row_alt': (0.98, 0.93, 0.88)
            }
        }
        self.colors = palettes.get(self.theme, palettes['navy'])
        
        self.pages_commands = []
        self.page_annots = []
        self.acro_fields = []
        self.outlines = []
        self.current_page_index = -1
        self.y_cursor = 730

    def pdf_text(self, val):
        if val is None:
            return ""
        val_str = str(val)
        return val_str.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1", "replace").decode("latin-1")

    def add_page(self):
        self.pages_commands.append([])
        self.page_annots.append([])
        self.current_page_index += 1
        cmds = self.pages_commands[self.current_page_index]

        c_p = self.colors['primary']
        c_s = self.colors['secondary']
        c_w = self.colors['white']
        c_gold = self.colors['gold']

        if self.current_page_index == 0:
            cmds.append(f"{c_p[0]:.3f} {c_p[1]:.3f} {c_p[2]:.3f} rg 36 735 540 40 re f")
            cmds.append(f"{c_s[0]:.3f} {c_s[1]:.3f} {c_s[2]:.3f} rg 36 731 540 4 re f")
            cmds.append(f"BT /F2 15 Tf {c_w[0]:.3f} {c_w[1]:.3f} {c_w[2]:.3f} rg 48 752 Td (SPARK STUDENT DEVELOPMENT RECORD) Tj ET")
            cmds.append(f"BT /F1 8 Tf {c_gold[0]:.3f} {c_gold[1]:.3f} {c_gold[2]:.3f} rg 48 741 Td (THE NEST SCHOOL - OFFICIAL ACADEMIC PORTFOLIO) Tj ET")
            
            date_str = datetime.now().strftime("%B %d, %Y")
            cmds.append(f"BT /F1 9 Tf {c_w[0]:.3f} {c_w[1]:.3f} {c_w[2]:.3f} rg 460 748 Td ({self.pdf_text(date_str)}) Tj ET")
            self.y_cursor = 710
        else:
            cmds.append(f"{c_p[0]:.3f} {c_p[1]:.3f} {c_p[2]:.3f} rg 36 760 540 22 re f")
            cmds.append(f"{c_s[0]:.3f} {c_s[1]:.3f} {c_s[2]:.3f} rg 36 757 540 3 re f")
            st_name = self.data.get('student', {}).get('full_name', 'Student')
            cmds.append(f"BT /F2 9 Tf {c_w[0]:.3f} {c_w[1]:.3f} {c_w[2]:.3f} rg 48 766 Td (SPARK Student Record - {self.pdf_text(st_name)}) Tj ET")
            self.y_cursor = 740

    def check_overflow(self, height):
        if self.y_cursor - height < 45:
            self.add_page()

    def draw_rect(self, x, y, w, h, fill_color=None, stroke_color=None, line_width=1):
        cmds = self.pages_commands[self.current_page_index]
        if fill_color and stroke_color:
            cmds.append(f"{fill_color[0]:.3f} {fill_color[1]:.3f} {fill_color[2]:.3f} rg {stroke_color[0]:.3f} {stroke_color[1]:.3f} {stroke_color[2]:.3f} RG {line_width} w {x:.2f} {y:.2f} {w:.2f} {h:.2f} re B")
        elif fill_color:
            cmds.append(f"{fill_color[0]:.3f} {fill_color[1]:.3f} {fill_color[2]:.3f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
        elif stroke_color:
            cmds.append(f"{stroke_color[0]:.3f} {stroke_color[1]:.3f} {stroke_color[2]:.3f} RG {line_width} w {x:.2f} {y:.2f} {w:.2f} {h:.2f} re s")

    def draw_text(self, text, x, y, font="/F1", size=10, color=None):
        cmds = self.pages_commands[self.current_page_index]
        col = color or self.colors['text_main']
        escaped = self.pdf_text(text)
        cmds.append(f"BT {font} {size} Tf {col[0]:.3f} {col[1]:.3f} {col[2]:.3f} rg {x:.2f} {y:.2f} Td ({escaped}) Tj ET")

    def draw_section_pill(self, title):
        self.check_overflow(35)
        self.y_cursor -= 28
        c_p = self.colors['primary']
        c_w = self.colors['white']
        self.draw_rect(36, self.y_cursor, 540, 22, fill_color=c_p)
        self.draw_text(title, 48, self.y_cursor + 6, font="/F2", size=11, color=c_w)
        self.add_outline_item(title, self.current_page_index, self.y_cursor + 22)
        self.y_cursor -= 10

    def add_outline_item(self, title, page_idx, y):
        self.outlines.append({'title': title, 'page_index': page_idx, 'y': y})

    def add_uri_link(self, x, y, w, h, url):
        if not self.enable_links:
            return
        self.page_annots[self.current_page_index].append({
            'type': 'link',
            'rect': (x, y, w, h),
            'url': url
        })

    def add_checkbox(self, x, y, w, h, field_name, is_checked):
        c_stroke = self.colors['border']
        c_fill = self.colors['white']
        self.draw_rect(x, y, w, h, fill_color=c_fill, stroke_color=c_stroke, line_width=1)
        if is_checked:
            c_sec = self.colors['secondary']
            cmds = self.pages_commands[self.current_page_index]
            cmds.append(f"{c_sec[0]:.3f} {c_sec[1]:.3f} {c_sec[2]:.3f} rg {x+2:.2f} {y+2:.2f} {w-4:.2f} {h-4:.2f} re f")

        if self.enable_checklist:
            self.page_annots[self.current_page_index].append({
                'type': 'checkbox',
                'rect': (x, y, w, h),
                'field_name': field_name,
                'checked': is_checked
            })

    def add_textfield(self, x, y, w, h, field_name, default_value):
        c_stroke = self.colors['border']
        c_fill = self.colors['bg_card']
        self.draw_rect(x, y, w, h, fill_color=c_fill, stroke_color=c_stroke, line_width=1)

        if self.enable_notes:
            self.page_annots[self.current_page_index].append({
                'type': 'textfield',
                'rect': (x, y, w, h),
                'field_name': field_name,
                'value': default_value
            })
        else:
            self.draw_text(default_value[:90] + "...", x + 6, y + h - 14, font="/F3", size=9, color=self.colors['text_muted'])

    def should_include(self, sec_name):
        if not self.sections_filter:
            return True
        return sec_name in self.sections_filter

    def build_document(self):
        self.add_page()
        st = self.data.get('student', {})

        self.check_overflow(105)
        self.y_cursor -= 95
        c_card = self.colors['bg_card']
        c_border = self.colors['border']
        c_main = self.colors['text_main']
        c_muted = self.colors['text_muted']
        c_sec = self.colors['secondary']

        self.draw_rect(36, self.y_cursor, 540, 95, fill_color=c_card, stroke_color=c_border, line_width=1.5)

        full_name = st.get('full_name') or 'Student Record'
        st_id = st.get('student_id') or f"SPK-{st.get('id', 1001):05d}"
        email = st.get('email') or 'student@school.edu'
        phone = st.get('phone') or 'Not provided'
        grade = f"Grade {st.get('grade') or 11}"
        department = st.get('department') or 'General Academic Track'
        readiness_score = float(st.get('readiness_score') or 72.0)
        academic_average = float(st.get('academic_average') or 85.0)

        self.draw_text(full_name, 52, self.y_cursor + 70, font="/F2", size=15, color=c_main)
        self.draw_text(f"{grade}  |  ID: {st_id}  |  Track: {department}", 52, self.y_cursor + 54, font="/F1", size=10, color=c_muted)
        
        self.draw_text(f"Email: {email}", 52, self.y_cursor + 36, font="/F1", size=9, color=c_main)
        self.add_uri_link(85, self.y_cursor + 34, 180, 12, f"mailto:{email}")

        self.draw_text(f"Phone: {phone}", 280, self.y_cursor + 36, font="/F1", size=9, color=c_muted)
        
        portal_url = "http://127.0.0.1:5000/"
        self.draw_text("SPARK Student Portal: http://127.0.0.1:5000/", 52, self.y_cursor + 16, font="/F3", size=9, color=c_sec)
        self.add_uri_link(160, self.y_cursor + 14, 160, 12, portal_url)

        self.check_overflow(70)
        self.y_cursor -= 65
        kpi_w = 126
        gap = 12

        metrics = [
            ("Readiness Score", f"{readiness_score:.1f}%", True, readiness_score),
            ("Academic Average", f"{academic_average:.1f}%", False, None),
            ("Colleges Saved", str(len(self.data.get('universities', []))), False, None),
            ("Impact Activities", str(len(self.data.get('activities', []))), False, None),
        ]

        for i, (m_label, m_val, has_bar, p_val) in enumerate(metrics):
            kx = 36 + i * (kpi_w + gap)
            ky = self.y_cursor
            self.draw_rect(kx, ky, kpi_w, 55, fill_color=self.colors['bg_subtle'], stroke_color=c_border, line_width=1)
            self.draw_text(m_label, kx + 8, ky + 40, font="/F1", size=8, color=c_muted)
            self.draw_text(m_val, kx + 8, ky + 20, font="/F2", size=14, color=c_main)

            if has_bar:
                self.draw_rect(kx + 8, ky + 8, kpi_w - 16, 6, fill_color=(0.85, 0.85, 0.85))
                bar_w = max(2, (kpi_w - 16) * (p_val / 100.0))
                self.draw_rect(kx + 8, ky + 8, bar_w, 6, fill_color=c_sec)

        if self.should_include('academics'):
            self.draw_section_pill("ACADEMIC PERFORMANCE & TEST SCORES")

            academics = self.data.get('academics', [])
            if academics:
                self.check_overflow(25)
                self.y_cursor -= 18
                self.draw_rect(36, self.y_cursor, 540, 18, fill_color=self.colors['bg_subtle'])
                self.draw_text("Subject", 48, self.y_cursor + 5, font="/F2", size=9, color=c_main)
                self.draw_text("Marks (%)", 220, self.y_cursor + 5, font="/F2", size=9, color=c_main)
                self.draw_text("Grade", 340, self.y_cursor + 5, font="/F2", size=9, color=c_main)
                self.draw_text("Exam / Level", 440, self.y_cursor + 5, font="/F2", size=9, color=c_main)

                for idx, item in enumerate(academics[:8]):
                    self.check_overflow(18)
                    self.y_cursor -= 16
                    bg_col = self.colors['row_alt'] if idx % 2 == 1 else self.colors['white']
                    self.draw_rect(36, self.y_cursor, 540, 16, fill_color=bg_col)

                    subj = str(item.get('subject') or 'N/A')
                    marks = f"{item.get('marks', 0):.1f}%" if item.get('marks') is not None else '-'
                    grd = str(item.get('grade') or '-')
                    exam = str(item.get('exam_name') or 'Internal Assessment')

                    self.draw_text(subj, 48, self.y_cursor + 4, font="/F1", size=9, color=c_main)
                    self.draw_text(marks, 220, self.y_cursor + 4, font="/F1", size=9, color=c_main)
                    self.draw_text(grd, 340, self.y_cursor + 4, font="/F1", size=9, color=c_main)
                    self.draw_text(exam, 440, self.y_cursor + 4, font="/F1", size=8, color=c_muted)
            else:
                self.y_cursor -= 15
                self.draw_text("No academic records logged yet.", 48, self.y_cursor, font="/F3", size=9, color=c_muted)

        if self.should_include('test_scores'):
            test_scores = self.data.get('test_scores', [])
            if test_scores:
                self.y_cursor -= 10
                self.check_overflow(25)
                self.y_cursor -= 18
                self.draw_rect(36, self.y_cursor, 540, 18, fill_color=self.colors['bg_subtle'])
                self.draw_text("Standardized Test", 48, self.y_cursor + 5, font="/F2", size=9, color=c_main)
                self.draw_text("Score", 240, self.y_cursor + 5, font="/F2", size=9, color=c_main)
                self.draw_text("Test Date", 360, self.y_cursor + 5, font="/F2", size=9, color=c_main)
                self.draw_text("Status", 470, self.y_cursor + 5, font="/F2", size=9, color=c_main)

                for idx, ts in enumerate(test_scores[:5]):
                    self.check_overflow(18)
                    self.y_cursor -= 16
                    bg_col = self.colors['row_alt'] if idx % 2 == 1 else self.colors['white']
                    self.draw_rect(36, self.y_cursor, 540, 16, fill_color=bg_col)

                    t_name = str(ts.get('test_name') or 'SAT/ACT')
                    t_score = str(ts.get('score') or 'Pending')
                    t_date = str(ts.get('test_date') or '-')
                    t_status = str(ts.get('status') or 'Planned')

                    self.draw_text(t_name, 48, self.y_cursor + 4, font="/F1", size=9, color=c_main)
                    self.draw_text(t_score, 240, self.y_cursor + 4, font="/F2", size=9, color=c_main)
                    self.draw_text(t_date, 360, self.y_cursor + 4, font="/F1", size=8, color=c_muted)
                    self.draw_text(t_status, 470, self.y_cursor + 4, font="/F1", size=8, color=c_main)

        if self.should_include('universities'):
            self.draw_section_pill("TARGET UNIVERSITIES & APPLICATION STATUS")

            universities = self.data.get('universities', [])
            if universities:
                self.check_overflow(25)
                self.y_cursor -= 18
                self.draw_rect(36, self.y_cursor, 540, 18, fill_color=self.colors['bg_subtle'])
                self.draw_text("University / College", 48, self.y_cursor + 5, font="/F2", size=9, color=c_main)
                self.draw_text("Country / Degree", 220, self.y_cursor + 5, font="/F2", size=9, color=c_main)
                self.draw_text("Category", 360, self.y_cursor + 5, font="/F2", size=9, color=c_main)
                self.draw_text("Deadline & Status", 450, self.y_cursor + 5, font="/F2", size=9, color=c_main)

                for idx, u in enumerate(universities[:8]):
                    self.check_overflow(18)
                    self.y_cursor -= 16
                    bg_col = self.colors['row_alt'] if idx % 2 == 1 else self.colors['white']
                    self.draw_rect(36, self.y_cursor, 540, 16, fill_color=bg_col)

                    u_name = str(u.get('university_name') or 'University')
                    u_cnt = f"{u.get('country') or 'US'} ({u.get('degree') or 'B.S.'})"
                    u_type = str(u.get('application_type') or 'Match')
                    u_status = str(u.get('status') or 'Researching')

                    self.draw_text(u_name, 48, self.y_cursor + 4, font="/F2", size=9, color=c_main)
                    u_search_url = f"https://www.google.com/search?q={self.pdf_text(u_name)}+university"
                    self.add_uri_link(48, self.y_cursor + 2, 160, 12, u_search_url)

                    self.draw_text(u_cnt, 220, self.y_cursor + 4, font="/F1", size=8, color=c_muted)
                    self.draw_text(u_type, 360, self.y_cursor + 4, font="/F1", size=8, color=c_main)
                    self.draw_text(u_status, 450, self.y_cursor + 4, font="/F1", size=8, color=c_main)
            else:
                self.y_cursor -= 15
                self.draw_text("No target colleges added yet.", 48, self.y_cursor, font="/F3", size=9, color=c_muted)

        if self.should_include('activities'):
            self.draw_section_pill("EXTRACURRICULAR ACTIVITIES & LEADERSHIP")

            activities = self.data.get('activities', [])
            if activities:
                self.check_overflow(25)
                self.y_cursor -= 18
                self.draw_rect(36, self.y_cursor, 540, 18, fill_color=self.colors['bg_subtle'])
                self.draw_text("Activity / Organization", 48, self.y_cursor + 5, font="/F2", size=9, color=c_main)
                self.draw_text("Category", 220, self.y_cursor + 5, font="/F2", size=9, color=c_main)
                self.draw_text("Key Achievement & Role", 350, self.y_cursor + 5, font="/F2", size=9, color=c_main)

                for idx, act in enumerate(activities[:6]):
                    self.check_overflow(18)
                    self.y_cursor -= 16
                    bg_col = self.colors['row_alt'] if idx % 2 == 1 else self.colors['white']
                    self.draw_rect(36, self.y_cursor, 540, 16, fill_color=bg_col)

                    a_name = str(act.get('activity_name') or 'Activity')
                    a_cat = str(act.get('category') or 'Leadership')
                    a_ach = str(act.get('achievement') or act.get('description') or 'Participant')

                    self.draw_text(a_name, 48, self.y_cursor + 4, font="/F2", size=9, color=c_main)
                    self.draw_text(a_cat, 220, self.y_cursor + 4, font="/F1", size=8, color=c_muted)
                    self.draw_text(a_ach[:45], 350, self.y_cursor + 4, font="/F1", size=8, color=c_main)
            else:
                self.y_cursor -= 15
                self.draw_text("No extracurricular activities logged yet.", 48, self.y_cursor, font="/F3", size=9, color=c_muted)

        if self.should_include('readiness_checklist'):
            self.draw_section_pill("SPARK READINESS CHECKLIST & ACTION ITEMS")

            default_items = [
                ("profile_complete", "Complete Personal Profile & Contact Details", True),
                ("academics_added", "Log Academic Transcripts & Subject Marks", True),
                ("tests_planned", "Schedule & Plan SAT / ACT / IELTS Test Dates", False),
                ("activities_logged", "Document Top 5 Extracurricular & Leadership Roles", True),
                ("colleges_shortlisted", "Build Shortlist of Reach, Match & Safety Colleges", True),
                ("recommenders_assigned", "Assign Teacher & Counselor Recommenders", False),
                ("essay_draft_started", "Draft Personal Statement & Supplemental Essays", False),
                ("financial_plan_done", "Finalize Financial Aid & Scholarship Planning", False),
            ]

            db_chk = {item['item_key']: bool(item['completed']) for item in self.data.get('readiness_checklist', [])}

            for idx, (key, label, default_completed) in enumerate(default_items):
                self.check_overflow(20)
                self.y_cursor -= 18
                is_done = db_chk.get(key, default_completed)

                self.add_checkbox(48, self.y_cursor + 1, 14, 14, f"chk_{key}", is_done)

                done_text = "[ COMPLETED ]" if is_done else "[ IN PROGRESS ]"
                txt_col = self.colors['text_main'] if is_done else self.colors['text_muted']
                self.draw_text(label, 70, self.y_cursor + 3, font="/F1", size=9, color=txt_col)
                self.draw_text(done_text, 450, self.y_cursor + 3, font="/F2", size=8, color=self.colors['secondary'] if is_done else self.colors['accent'])

        self.draw_section_pill("COUNSELOR FEEDBACK & STUDENT ACTION NOTES")

        self.check_overflow(75)
        self.y_cursor -= 70

        field_val = f"Counselor Notes for {full_name}:\n- Strong academic progress.\n- Next steps: Finalize recommendation letters and submit early college application draft."
        self.add_textfield(48, self.y_cursor, 516, 60, "Counselor_Notes_Field", field_val)

    def generate(self):
        self.build_document()

        total_pages = len(self.pages_commands)
        if total_pages == 0:
            self.add_page()
            total_pages = 1

        for idx in range(total_pages):
            cmds = self.pages_commands[idx]
            page_num_str = f"Page {idx + 1} of {total_pages}"
            c_muted = self.colors['text_muted']
            cmds.append(f"{c_muted[0]:.3f} {c_muted[1]:.3f} {c_muted[2]:.3f} RG 0.5 w 36 32 540 0 re S")
            cmds.append(f"BT /F1 8 Tf {c_muted[0]:.3f} {c_muted[1]:.3f} {c_muted[2]:.3f} rg 36 20 Td (SPARK Student Success Platform | Official Interactive Record) Tj ET")
            cmds.append(f"BT /F1 8 Tf {c_muted[0]:.3f} {c_muted[1]:.3f} {c_muted[2]:.3f} rg 510 20 Td ({self.pdf_text(page_num_str)}) Tj ET")

        font_f1 = 5
        font_f2 = 6
        font_f3 = 7
        curr_obj = 8

        page_obj_ids = []
        content_obj_ids = []

        for p_idx in range(total_pages):
            p_id = curr_obj
            c_id = curr_obj + 1
            page_obj_ids.append(p_id)
            content_obj_ids.append(c_id)
            curr_obj += 2

        annot_obj_ids_per_page = []
        all_annot_objects = {}

        for p_idx, annots in enumerate(self.page_annots):
            page_p_id = page_obj_ids[p_idx]
            p_ann_ids = []
            for item in annots:
                a_id = curr_obj
                curr_obj += 1
                p_ann_ids.append(a_id)

                if item['type'] == 'link':
                    url_esc = self.pdf_text(item['url'])
                    x1, y1, w, h = item['rect']
                    content = f"<< /Type /Annot /Subtype /Link /Rect [{x1:.2f} {y1:.2f} {x1+w:.2f} {y1+h:.2f}] /Border [0 0 0] /A << /Type /Action /S /URI /URI ({url_esc}) >> >>"
                    all_annot_objects[a_id] = content
                elif item['type'] == 'checkbox':
                    val = "/Yes" if item['checked'] else "/Off"
                    fn_esc = self.pdf_text(item['field_name'])
                    x1, y1, w, h = item['rect']
                    content = f"<< /Type /Annot /Subtype /Widget /FT /Btn /T ({fn_esc}) /V {val} /AS {val} /Rect [{x1:.2f} {y1:.2f} {x1+w:.2f} {y1+h:.2f}] /P {page_p_id} 0 R /F 4 /Flags 0 >>"
                    all_annot_objects[a_id] = content
                    self.acro_fields.append(f"{a_id} 0 R")
                elif item['type'] == 'textfield':
                    fn_esc = self.pdf_text(item['field_name'])
                    val_esc = self.pdf_text(item['value'])
                    x1, y1, w, h = item['rect']
                    content = f"<< /Type /Annot /Subtype /Widget /FT /Tx /T ({fn_esc}) /V ({val_esc}) /Rect [{x1:.2f} {y1:.2f} {x1+w:.2f} {y1+h:.2f}] /P {page_p_id} 0 R /F 4 /Ff 4096 >>"
                    all_annot_objects[a_id] = content
                    self.acro_fields.append(f"{a_id} 0 R")
            annot_obj_ids_per_page.append(p_ann_ids)

        outline_obj_ids = []
        if self.outlines:
            for o_item in self.outlines:
                o_id = curr_obj
                curr_obj += 1
                outline_obj_ids.append(o_id)

            outlines_root_content = f"<< /Type /Outlines /First {outline_obj_ids[0]} 0 R /Last {outline_obj_ids[-1]} 0 R /Count {len(outline_obj_ids)} >>"
            for o_idx, o_item in enumerate(self.outlines):
                o_id = outline_obj_ids[o_idx]
                target_p_id = page_obj_ids[o_item['page_index']]
                title_esc = self.pdf_text(o_item['title'])
                prev_ref = f"/Prev {outline_obj_ids[o_idx-1]} 0 R" if o_idx > 0 else ""
                next_ref = f"/Next {outline_obj_ids[o_idx+1]} 0 R" if o_idx < len(self.outlines)-1 else ""
                all_annot_objects[o_id] = f"<< /Title ({title_esc}) /Parent 3 0 R {prev_ref} {next_ref} /Dest [{target_p_id} 0 R /XYZ 0 {o_item['y']:.2f} 0] >>"
        else:
            outlines_root_content = "<< /Type /Outlines /Count 0 >>"

        acro_fields_str = " ".join(self.acro_fields)
        acroform_content = f"<< /Fields [{acro_fields_str}] /NeedAppearances true >>" if self.acro_fields else "<< /Fields [] >>"

        catalog_content = "<< /Type /Catalog /Pages 2 0 R /Outlines 3 0 R /AcroForm 4 0 R >>"
        kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
        pages_content = f"<< /Type /Pages /Kids [{kids_str}] /Count {total_pages} >>"

        pdf_objs = {
            1: catalog_content,
            2: pages_content,
            3: outlines_root_content,
            4: acroform_content,
            font_f1: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            font_f2: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
            font_f3: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>",
        }

        for p_idx in range(total_pages):
            p_id = page_obj_ids[p_idx]
            c_id = content_obj_ids[p_idx]

            stream_data = "\n".join(self.pages_commands[p_idx]).encode("latin-1", "replace")
            compressed_stream = zlib.compress(stream_data)

            pdf_objs[c_id] = b"<< /Length " + str(len(compressed_stream)).encode() + b" /Filter /FlateDecode >>\nstream\n" + compressed_stream + b"\nendstream"

            annots_refs = " ".join(f"{aid} 0 R" for aid in annot_obj_ids_per_page[p_idx])
            annots_str = f"/Annots [{annots_refs}]" if annots_refs else ""

            page_dict = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_f1} 0 R /F2 {font_f2} 0 R /F3 {font_f3} 0 R >> >> /Contents {c_id} 0 R {annots_str} >>"
            pdf_objs[p_id] = page_dict

        for o_id, content in all_annot_objects.items():
            pdf_objs[o_id] = content

        max_obj_id = max(pdf_objs.keys())

        doc = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0] * (max_obj_id + 1)

        for num in range(1, max_obj_id + 1):
            if num not in pdf_objs:
                continue
            offsets[num] = len(doc)
            doc.extend(f"{num} 0 obj\n".encode())
            c = pdf_objs[num]
            doc.extend(c if isinstance(c, bytes) else c.encode("latin-1"))
            doc.extend(b"\nendobj\n")

        xref_pos = len(doc)
        doc.extend(f"xref\n0 {max_obj_id + 1}\n0000000000 65535 f \n".encode())
        for num in range(1, max_obj_id + 1):
            offset = offsets[num]
            doc.extend(f"{offset:010d} 00000 n \n".encode())

        doc.extend(f"trailer\n<< /Size {max_obj_id + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode())
        return bytes(doc)


def student_record_pdf(conn, student_id, options=None):
    """Build a rich, vector-rendered, interactive PDF version of the complete student record."""
    data = get_full_student_data(conn, student_id)
    if data is None:
        return b""
    engine = SparkInteractivePDFEngine(data, options=options)
    return engine.generate()


# ============================================================
# STUDENT METRICS
# ============================================================

def recalculate_student_metrics(conn, student_id):

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (student_id,)).fetchone()

    if student is None:

        return None

    academic_row = conn.execute("""
        SELECT AVG(marks) AS avg_marks
        FROM academics
        WHERE student_id = ?
    """, (student_id,)).fetchone()

    academic_average = (
        float(academic_row["avg_marks"])
        if academic_row and academic_row["avg_marks"] is not None
        else 0.0
    )

    activity_count = conn.execute("""
        SELECT COUNT(*)
        FROM activities
        WHERE student_id = ?
    """, (student_id,)).fetchone()[0] or 0

    university_count = conn.execute("""
        SELECT COUNT(*)
        FROM universities
        WHERE student_id = ?
    """, (student_id,)).fetchone()[0] or 0

    document_count = conn.execute("""
        SELECT COUNT(*)
        FROM documents
        WHERE student_id = ?
    """, (student_id,)).fetchone()[0] or 0

    profile_fields = [
        student["full_name"],
        student["email"],
        student["phone"],
        student["date_of_birth"],
        student["department"],
        student["subjects"] if "subjects" in student.keys() else None,
        student["target_degree"] if "target_degree" in student.keys() else None,
        student["career_interest"] if "career_interest" in student.keys() else None,
        student["why_interest"] if "why_interest" in student.keys() else None,
        student["strengths"] if "strengths" in student.keys() else None,
    ]

    completed_fields = sum(
        1 for value in profile_fields
        if value not in (None, "", " ", "[]", "{}")
    )

    profile_percentage = round(
        (completed_fields / len(profile_fields)) * 100,
        1
    )

    academic_percentage = min(100.0, academic_average)

    activity_percentage = min(100.0, activity_count * 25.0)

    university_percentage = min(100.0, university_count * 20.0)

    document_percentage = min(100.0, document_count * 15.0)

    readiness_score = round(
        (
            profile_percentage +
            academic_percentage +
            activity_percentage +
            university_percentage +
            document_percentage
        ) / 5.0,
        1
    )

    conn.execute("""
        UPDATE students
        SET
            academic_average = ?,
            readiness_score = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        academic_average,
        readiness_score,
        datetime.now().isoformat(),
        student_id
    ))

    conn.commit()

    return {
        "academic_average": academic_average,
        "readiness_score": readiness_score,
        "profile_percentage": profile_percentage,
        "activity_count": activity_count,
        "university_count": university_count,
        "document_count": document_count
    }


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def ensure_db_exists():
    """Check if database exists and initialize if needed."""
    try:
        database_url = app.config.get("DATABASE_URL")
        db_type = getattr(Config, 'DB_TYPE', 'sqlite')
        
        if database_url and db_type == "postgresql" and POSTGRESQL_AVAILABLE:
            # For PostgreSQL, just try to initialize (it will handle existing tables)
            try:
                init_db()
            except Exception as e:
                print(f"PostgreSQL initialization error: {e}")
        else:
            # SQLite handling
            db_path = app.config.get("DB_PATH", os.path.join(BASE_DIR, "spark.db"))
            if not os.path.exists(db_path):
                # Create empty database file
                with open(db_path, 'w') as f:
                    pass  # Create empty file
                init_db()
    except Exception as e:
        print(f"Error in ensure_db_exists: {e}")
        # Don't fail the app if database initialization fails


def get_primary_key_sql():
    """Return appropriate primary key SQL based on database type"""
    db_type = getattr(Config, 'DB_TYPE', 'sqlite')
    if db_type == "postgresql":
        return "SERIAL PRIMARY KEY"
    else:
        return "INTEGER PRIMARY KEY AUTOINCREMENT"

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Determine database type
    db_type = getattr(Config, 'DB_TYPE', 'sqlite')
    primary_key = get_primary_key_sql()
    
    try:
        # --------------------------------------------------------
        # USERS
        # --------------------------------------------------------
        
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                id {primary_key},
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # --------------------------------------------------------
        # STUDENTS
        # --------------------------------------------------------
        
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS students (
                id {primary_key},
                user_id INTEGER,
                student_id TEXT UNIQUE,
                full_name TEXT,
                email TEXT,
                phone TEXT,
                grade TEXT,
                date_of_birth TEXT,
                department TEXT,
                subjects TEXT,
                target_degree TEXT,
                career_interest TEXT,
                why_interest TEXT,
                strengths TEXT,
                academic_average REAL DEFAULT 0,
                readiness_score REAL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        # --------------------------------------------------------
        # ACADEMICS
        # --------------------------------------------------------

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS academics (
                id {primary_key},
                student_id INTEGER,
                subject TEXT,
                marks REAL,
                grade TEXT,
                exam_name TEXT,

                created_at TEXT NOT NULL,

                FOREIGN KEY(student_id)
                    REFERENCES students(id)

            )
        """)

        # --------------------------------------------------------
        # ACTIVITIES
        # --------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activities (

                id {primary_key},

                student_id INTEGER,

                activity_name TEXT,

                category TEXT,

                description TEXT,

                achievement TEXT,

                created_at TEXT NOT NULL,

                FOREIGN KEY(student_id)
                    REFERENCES students(id)

            )
        """)

        # --------------------------------------------------------
        # UNIVERSITIES
        # --------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS universities (

                id {primary_key},

                student_id INTEGER,

                university_name TEXT,

                country TEXT,

                degree TEXT,

                application_type TEXT,

                deadline TEXT,

                status TEXT,

                created_at TEXT NOT NULL,

                FOREIGN KEY(student_id)
                    REFERENCES students(id)

            )
        """)

        # --------------------------------------------------------
        # DOCUMENTS
        # --------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (

                id {primary_key},

                student_id INTEGER,

                document_name TEXT,

                file_name TEXT,

                file_path TEXT,

                uploaded_at TEXT NOT NULL,

                FOREIGN KEY(student_id)
                    REFERENCES students(id)

            )
        """)

        # Planning records for every page in the student workspace.
        for statement in [
            f"""CREATE TABLE IF NOT EXISTS test_scores (id {primary_key}, student_id INTEGER NOT NULL, test_name TEXT NOT NULL, score TEXT, test_date TEXT, status TEXT DEFAULT 'Planned', created_at TEXT NOT NULL, FOREIGN KEY(student_id) REFERENCES students(id))""",
            f"""CREATE TABLE IF NOT EXISTS milestones (id {primary_key}, student_id INTEGER NOT NULL, title TEXT NOT NULL, target_date TEXT, status TEXT DEFAULT 'Not Started', created_at TEXT NOT NULL, FOREIGN KEY(student_id) REFERENCES students(id))""",
            f"""CREATE TABLE IF NOT EXISTS essays (id {primary_key}, student_id INTEGER NOT NULL, essay_prompt TEXT NOT NULL, university TEXT, draft_status TEXT DEFAULT 'Uploaded for Counselor Review', deadline TEXT, file_path TEXT, file_name TEXT, feedback TEXT, created_at TEXT NOT NULL, FOREIGN KEY(student_id) REFERENCES students(id))""",
            f"""CREATE TABLE IF NOT EXISTS recommenders (id {primary_key}, student_id INTEGER NOT NULL, teacher_name TEXT NOT NULL, subject TEXT, university TEXT, deadline TEXT, brag_sheet TEXT, status TEXT DEFAULT 'Requested', lor_file_path TEXT, lor_file_name TEXT, created_at TEXT NOT NULL, FOREIGN KEY(student_id) REFERENCES students(id))""",
            f"""CREATE TABLE IF NOT EXISTS deadlines (id {primary_key}, student_id INTEGER NOT NULL, action TEXT NOT NULL, due_date TEXT, category TEXT, status TEXT DEFAULT 'Pending', created_at TEXT NOT NULL, FOREIGN KEY(student_id) REFERENCES students(id))""",
            f"""CREATE TABLE IF NOT EXISTS prerequisites (id {primary_key}, student_id INTEGER NOT NULL, requirement TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(student_id) REFERENCES students(id))""",
            """CREATE TABLE IF NOT EXISTS readiness_checklist (student_id INTEGER NOT NULL, item_key TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL, PRIMARY KEY(student_id, item_key), FOREIGN KEY(student_id) REFERENCES students(id))""",
            f"""CREATE TABLE IF NOT EXISTS master_universities (id {primary_key}, name TEXT UNIQUE NOT NULL, country TEXT NOT NULL, best_fit_courses TEXT, academic_requirement TEXT, key_subjects TEXT, tests TEXT, competitive_target TEXT, application_deadline TEXT, created_at TEXT NOT NULL)""",
            f"""CREATE TABLE IF NOT EXISTS master_university_requirements (id {primary_key}, university_id INTEGER NOT NULL, requirement_name TEXT NOT NULL, category TEXT NOT NULL, description TEXT, FOREIGN KEY(university_id) REFERENCES master_universities(id))""",
            f"""CREATE TABLE IF NOT EXISTS student_prerequisites (id {primary_key}, student_id INTEGER NOT NULL, university_id INTEGER NOT NULL, requirement_name TEXT NOT NULL, category TEXT, description TEXT, completed INTEGER NOT NULL DEFAULT 0, notes TEXT, completed_at TEXT, created_at TEXT NOT NULL, FOREIGN KEY(student_id) REFERENCES students(id), FOREIGN KEY(university_id) REFERENCES universities(id) ON DELETE CASCADE)""",
            f"""CREATE TABLE IF NOT EXISTS alerts (id {primary_key}, student_id INTEGER NOT NULL, deadline_id INTEGER, item_type TEXT, severity TEXT NOT NULL, message TEXT NOT NULL, target_url TEXT, is_read INTEGER DEFAULT 0, created_at TEXT NOT NULL, FOREIGN KEY(student_id) REFERENCES students(id))"""
        ]:
            cursor.execute(statement)

        seed_master_universities(conn)


        # Migrations for existing database tables
        def get_table_columns(table_name):
            cursor.execute(f"PRAGMA table_info({table_name})")
            return [row[1] for row in cursor.fetchall()]
        
        student_cols = get_table_columns("students")
        for col in ["subjects", "target_degree", "career_interest", "why_interest", "strengths"]:
            if col not in student_cols:
                cursor.execute(f"ALTER TABLE students ADD COLUMN {col} TEXT")

        essay_cols = get_table_columns("essays")
        if "file_path" not in essay_cols:
            cursor.execute("ALTER TABLE essays ADD COLUMN file_path TEXT")
        if "file_name" not in essay_cols:
            cursor.execute("ALTER TABLE essays ADD COLUMN file_name TEXT")
        if "feedback" not in essay_cols:
            cursor.execute("ALTER TABLE essays ADD COLUMN feedback TEXT")

        rec_cols = get_table_columns("recommenders")
        if "university" not in rec_cols:
            cursor.execute("ALTER TABLE recommenders ADD COLUMN university TEXT")
        if "lor_file_path" not in rec_cols:
            cursor.execute("ALTER TABLE recommenders ADD COLUMN lor_file_path TEXT")
        if "lor_file_name" not in rec_cols:
            cursor.execute("ALTER TABLE recommenders ADD COLUMN lor_file_name TEXT")

        # --------------------------------------------------------
        # COUNSELOR NOTES
        # --------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS counselor_notes (

                id {primary_key},

                student_id INTEGER,

                counselor_id INTEGER,

                note TEXT,

                created_at TEXT NOT NULL,

                FOREIGN KEY(student_id)
                    REFERENCES students(id),

                FOREIGN KEY(counselor_id)
                    REFERENCES users(id)

            )
        """)

        # --------------------------------------------------------
        # DEFAULT COUNSELOR
        # --------------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM users
            WHERE username = ?
        """, ("counselor",))

        counselor = cursor.fetchone()

        if counselor is None:

            cursor.execute("""
                INSERT INTO users
            (
                username,
                password,
                role,
                created_at
            )

            VALUES (?, ?, ?, ?)
        """, (

            "counselor",

            generate_password_hash("counselor123"),

            "counselor",

            datetime.now().isoformat()

        ))

        # --------------------------------------------------------
        # DEFAULT STUDENT
        # --------------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM users
            WHERE username = ?
        """, ("student",))

        student_user = cursor.fetchone()

        if student_user is None:

            cursor.execute("""
                INSERT INTO users
                (
                    username,
                    password,
                    role,
                    created_at
                )

                VALUES (?, ?, ?, ?)
        """, (

            "student",

            generate_password_hash("student123"),

            "student",

            datetime.now().isoformat()

        ))

            student_user_id = cursor.lastrowid
        else:
            student_user_id = student_user["id"]

        cursor.execute("""
            INSERT INTO students
            (
                user_id,
                student_id,
                full_name,
                email,
                phone,
                grade,
                department,
                academic_average,
                readiness_score,
                created_at,
                updated_at
            )

            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM students WHERE user_id = ?)
        """, (

            student_user_id,

            "SPK-11001",

            "Demo Student",

            "student@spark.edu",

            "",

            "11",

            "Computer Science",

            92,

            86,

            datetime.now().isoformat(),

            datetime.now().isoformat(),

            student_user_id

        ))

        conn.commit()
    
    except Exception as e:
        print(f"Error during database initialization: {e}")
        conn.rollback()
        raise


@app.before_request
def ensure_database_initialized():
    """Create the ephemeral SQLite schema for every Vercel function instance."""
    if request.endpoint != "static":
        init_db()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/favicon.ico")
def favicon():

    return send_file(_target_logo, mimetype="image/png")


# ============================================================
# LOGIN PAGE
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session.clear()

            session["user_id"] = user["id"]

            session["username"] = user["username"]

            session["role"] = user["role"]

            # --------------------------------------------
            # STUDENT
            # --------------------------------------------

            if user["role"] == "student":

                return redirect(
                    url_for("student_dashboard")
                )

            # --------------------------------------------
            # COUNSELOR
            # --------------------------------------------

            if user["role"] == "counselor":

                return redirect(
                    url_for("counselor_dashboard")
                )

        flash(
            "Invalid username or password.",
            "error"
        )

    return render_template("login.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# AUTHENTICATION & ROLE DECORATORS
# ============================================================

def login_required(f=None):
    if f is None:
        return "user_id" in session

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Authentication required"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"success": False, "message": "Authentication required"}), 401
                return redirect(url_for("login"))
            if roles and session.get("role") not in roles:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"success": False, "message": "Access forbidden: insufficient role permissions"}), 403
                return "Access denied: insufficient permissions", 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/student/dashboard")
@role_required("student")
def student_dashboard():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if student is not None:

        dashboard_metrics = recalculate_student_metrics(conn, student["id"])

        activity_count = dashboard_metrics["activity_count"] if dashboard_metrics else 0
        university_count = dashboard_metrics["university_count"] if dashboard_metrics else 0
        document_count = dashboard_metrics["document_count"] if dashboard_metrics else 0
        academic_average = dashboard_metrics["academic_average"] if dashboard_metrics else (student["academic_average"] or 0)
        readiness_score = dashboard_metrics["readiness_score"] if dashboard_metrics else (student["readiness_score"] or 0)
        profile_percentage = dashboard_metrics["profile_percentage"] if dashboard_metrics else 0
        alerts = compute_student_alerts(conn, student["id"])
        universities = conn.execute("SELECT * FROM universities WHERE student_id = ? ORDER BY deadline ASC, created_at DESC", (student["id"],)).fetchall()

    else:

        activity_count = 0
        university_count = 0
        document_count = 0
        academic_average = 0
        readiness_score = 0
        profile_percentage = 0
        alerts = []
        universities = []

    return render_template(
        "student/dashboard.html",
        student=student,
        activity_count=activity_count,
        university_count=university_count,
        document_count=document_count,
        academic_average=academic_average,
        readiness_score=readiness_score,
        profile_percentage=profile_percentage,
        alerts=alerts,
        universities=universities
    )



# ============================================================
# STUDENT PROFILE
# ============================================================

@app.route("/student/profile")
@role_required("student")
def student_profile():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    return render_template(
        "student/profile.html",
        student=student
    )


# ============================================================
# ACADEMICS
# ============================================================

@app.route("/student/academics")
@role_required("student")
def academics():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    academics_data = conn.execute("""
        SELECT subject, marks, grade, exam_name, created_at
        FROM academics
        WHERE student_id = ?
        ORDER BY created_at DESC
    """, (
        student["id"],
    )).fetchall()

    return render_template(
        "student/academics.html",
        student=student,
        academics=academics_data
    )

@app.route("/student/milestones")
@role_required("student")
def milestones():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    records = conn.execute("SELECT * FROM milestones WHERE student_id = ? ORDER BY target_date ASC, created_at DESC", (student["id"],)).fetchall()

    return render_template("student/milestones.html", student=student, records=records)


# ============================================================
# UNIVERSITIES
# ============================================================

@app.route("/student/universities")
@role_required("student")
def universities():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    universities_data = conn.execute("""
        SELECT *
        FROM universities
        WHERE student_id = ?
        ORDER BY deadline ASC
    """, (
        student["id"],
    )).fetchall()

    master_unis = conn.execute("""
        SELECT *
        FROM master_universities
        ORDER BY country, name
    """).fetchall()

    return render_template(
        "student/universities.html",
        student=student,
        universities=universities_data,
        master_universities=master_unis
    )



# ============================================================
# ACTIVITIES
# ============================================================

@app.route("/student/activities")
@role_required("student")
def activities():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    activities_data = conn.execute("""
        SELECT activity_name AS name, category AS type, '' AS role, '' AS hours, '' AS weeks, COALESCE(achievement, description, '') AS impact
        FROM activities
        WHERE student_id = ?
        ORDER BY created_at DESC
    """, (
        student["id"],
    )).fetchall()

    return render_template(
        "student/activities.html",
        student=student,
        activities=activities_data
    )


# ============================================================
# ESSAYS
# ============================================================

@app.route("/student/essays")
@role_required("student")
def essays():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    records = conn.execute("SELECT * FROM essays WHERE student_id = ? ORDER BY deadline ASC, created_at DESC", (student["id"],)).fetchall()

    return render_template("student/essays.html", student=student, records=records, active_tab="essays")


# ============================================================
# RECOMMENDERS
# ============================================================

@app.route("/student/recommenders")
@role_required("student")
def recommenders():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    records = conn.execute("SELECT * FROM recommenders WHERE student_id = ? ORDER BY deadline ASC, created_at DESC", (student["id"],)).fetchall()

    return render_template("student/recommenders.html", student=student, records=records, active_tab="recommenders")


@app.route("/student/deadlines")
@role_required("student")
def deadlines():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    records = conn.execute("SELECT * FROM deadlines WHERE student_id = ? ORDER BY due_date ASC, created_at DESC", (student["id"],)).fetchall()

    return render_template("student/deadlines.html", student=student, records=records)


# ============================================================
# PREREQUISITES
# ============================================================

@app.route("/student/prerequisites")
@role_required("student")
def prerequisites():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if student is None:
        return redirect(url_for("login"))

    unis = conn.execute("SELECT * FROM universities WHERE student_id = ? ORDER BY deadline ASC", (student["id"],)).fetchall()
    
    unis_with_prereqs = []
    total_items = 0
    total_completed = 0

    for u in unis:
        u_dict = dict(u)
        master_uni = conn.execute("SELECT * FROM master_universities WHERE name = ?", (u_dict["university_name"],)).fetchone()
        master_dict = dict(master_uni) if master_uni else {}

        prereqs = conn.execute("SELECT * FROM student_prerequisites WHERE university_id = ? AND student_id = ? ORDER BY id ASC", (u["id"], student["id"])).fetchall()
        prereqs_list = [dict(p) for p in prereqs]

        if not prereqs_list:
            seed_student_prerequisites_for_university(conn, student["id"], u["id"], u_dict["university_name"], u_dict["degree"])
            prereqs = conn.execute("SELECT * FROM student_prerequisites WHERE university_id = ? AND student_id = ? ORDER BY id ASC", (u["id"], student["id"])).fetchall()
            prereqs_list = [dict(p) for p in prereqs]

        done_cnt = sum(1 for p in prereqs_list if p["completed"])
        tot_cnt = len(prereqs_list)
        pct = round((done_cnt / tot_cnt * 100)) if tot_cnt > 0 else 0

        total_items += tot_cnt
        total_completed += done_cnt

        u_dict["master"] = master_dict
        u_dict["prerequisites"] = prereqs_list
        u_dict["completed_count"] = done_cnt
        u_dict["total_count"] = tot_cnt
        u_dict["progress_pct"] = pct
        unis_with_prereqs.append(u_dict)

    overall_pct = round((total_completed / total_items * 100)) if total_items > 0 else 0
    alerts = compute_student_alerts(conn, student["id"])

    records = conn.execute("SELECT * FROM prerequisites WHERE student_id = ? ORDER BY completed ASC, created_at DESC", (student["id"],)).fetchall()
    checklist_rows = conn.execute("SELECT item_key, completed FROM readiness_checklist WHERE student_id = ?", (student["id"],)).fetchall()
    checklist = {row["item_key"]: bool(row["completed"]) for row in checklist_rows}
    
    metrics = {
        "academics_count": conn.execute("SELECT COUNT(*) FROM academics WHERE student_id = ?", (student["id"],)).fetchone()[0] or 0,
        "academics_avg": conn.execute("SELECT AVG(marks) FROM academics WHERE student_id = ?", (student["id"],)).fetchone()[0] or 0,
        "activities_count": conn.execute("SELECT COUNT(*) FROM activities WHERE student_id = ?", (student["id"],)).fetchone()[0] or 0,
        "universities_count": conn.execute("SELECT COUNT(*) FROM universities WHERE student_id = ?", (student["id"],)).fetchone()[0] or 0,
        "essays_count": conn.execute("SELECT COUNT(*) FROM essays WHERE student_id = ?", (student["id"],)).fetchone()[0] or 0,
        "recommenders_count": conn.execute("SELECT COUNT(*) FROM recommenders WHERE student_id = ?", (student["id"],)).fetchone()[0] or 0,
        "test_scores_count": conn.execute("SELECT COUNT(*) FROM test_scores WHERE student_id = ?", (student["id"],)).fetchone()[0] or 0,
        "documents_count": conn.execute("SELECT COUNT(*) FROM documents WHERE student_id = ?", (student["id"],)).fetchone()[0] or 0,
    }

    return render_template(
        "student/prerequisites.html",
        student=student,
        unis_with_prereqs=unis_with_prereqs,
        overall_progress=overall_pct,
        total_completed=total_completed,
        total_items=total_items,
        alerts=alerts,
        records=records,
        checklist=checklist,
        metrics=metrics
    )



# ============================================================
# DOCUMENTS
# ============================================================

@app.route("/student/documents")
@role_required("student")
def documents():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    documents_data = conn.execute("""
        SELECT *
        FROM documents
        WHERE student_id = ?
        ORDER BY uploaded_at DESC
    """, (
        student["id"],
    )).fetchall()

    return render_template(
        "student/documents.html",
        student=student,
        documents=documents_data
    )


# ============================================================
# COUNSELOR DASHBOARD
# ============================================================

@app.route("/counselor/students")
@role_required("counselor")
def counselor_students():

    conn = get_db()
    students = conn.execute("""
        SELECT
            s.*,
            s.full_name AS name,
            NULL AS target_country,
            s.readiness_score AS progress,
            'Active' AS status
        FROM students
        AS s
        ORDER BY full_name ASC
    """).fetchall()

    return render_template(
        "counselor/students.html",
        students=students,
        active_students=len(students)
    )


@app.route("/counselor/dashboard")
@role_required("counselor")
def counselor_dashboard():

    conn = get_db()

    students = conn.execute("""
        SELECT
            s.*,
            (SELECT COUNT(*) FROM academics a WHERE a.student_id = s.id) AS academic_count,
            (SELECT COUNT(*) FROM activities a WHERE a.student_id = s.id) AS activity_count,
            (SELECT COUNT(*) FROM universities u WHERE u.student_id = s.id) AS university_count,
            (SELECT COUNT(*) FROM documents d WHERE d.student_id = s.id) AS document_count,
            (SELECT COUNT(*) FROM test_scores t WHERE t.student_id = s.id) AS test_count,
            (SELECT COUNT(*) FROM milestones m WHERE m.student_id = s.id) AS milestone_count
        FROM students s
        ORDER BY s.full_name ASC
    """).fetchall()

    total_students = conn.execute("""
        SELECT COUNT(*)
        FROM students
    """).fetchone()[0]

    average_readiness = conn.execute("""
        SELECT AVG(readiness_score)
        FROM students
    """).fetchone()[0] or 0

    students_review = conn.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE readiness_score < 60
    """).fetchone()[0]

    document_count = conn.execute("""
        SELECT COUNT(*)
        FROM documents
    """).fetchone()[0]

    # Centralized Student - Counselor Deadline Alerts & Readiness Breakdowns
    attention_required = []
    student_readiness_breakdown = {}

    for s in students:
        s_alerts = compute_student_alerts(conn, s["id"])
        for a in s_alerts:
            a_copy = dict(a)
            a_copy["student_name"] = s["full_name"]
            a_copy["student_code"] = s["student_id"]
            a_copy["student_db_id"] = s["id"]
            attention_required.append(a_copy)

        # Per-college breakdown for student
        s_unis = conn.execute("SELECT * FROM universities WHERE student_id = ?", (s["id"],)).fetchall()
        uni_breakdowns = []
        for u in s_unis:
            prereqs = conn.execute("SELECT completed FROM student_prerequisites WHERE university_id = ? AND student_id = ?", (u["id"], s["id"])).fetchall()
            tot = len(prereqs)
            done = sum(1 for p in prereqs if p["completed"])
            pct = round(done / tot * 100) if tot > 0 else 0
            uni_breakdowns.append({
                "university_name": u["university_name"],
                "degree": u["degree"],
                "completed": done,
                "total": tot,
                "progress_pct": pct
            })
        student_readiness_breakdown[s["id"]] = uni_breakdowns

    severity_order = {"CRITICAL": 0, "URGENT": 1, "IMPORTANT": 2, "OVERDUE": 3, "REMINDER": 4, "UPCOMING": 5, "COMPLETED": 6}
    attention_required.sort(key=lambda x: severity_order.get(x["severity_level"], 99))

    return render_template(
        "counselor/dashboard.html",
        students=students,
        total_students=total_students,
        average_readiness=round(average_readiness, 1),
        students_review=students_review,
        document_count=document_count,
        attention_required=attention_required,
        student_readiness_breakdown=student_readiness_breakdown
    )


# ============================================================
# STUDENT PROFILE FOR COUNSELOR
# ============================================================

@app.route(
    "/counselor/student/<int:student_id>"
)
@role_required("counselor")
def counselor_student_profile(student_id):

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (
        student_id,
    )).fetchone()

    if student is None:
        return "Student not found", 404

    academics = conn.execute("""
        SELECT *
        FROM academics
        WHERE student_id = ?
        ORDER BY created_at DESC
    """, (
        student_id,
    )).fetchall()

    activities = conn.execute("""
        SELECT *
        FROM activities
        WHERE student_id = ?
        ORDER BY created_at DESC
    """, (
        student_id,
    )).fetchall()

    universities = conn.execute("""
        SELECT id, university_name AS name, country, degree AS course, application_type AS category, status, deadline
        FROM universities
        WHERE student_id = ?
        ORDER BY deadline ASC
    """, (
        student_id,
    )).fetchall()

    unis_with_prereqs = []
    for u in universities:
        u_dict = dict(u)
        master_uni = conn.execute("SELECT * FROM master_universities WHERE name = ?", (u_dict["name"],)).fetchone()
        master_dict = dict(master_uni) if master_uni else {}

        prereqs = conn.execute("SELECT * FROM student_prerequisites WHERE university_id = ? AND student_id = ? ORDER BY id ASC", (u_dict["id"], student_id)).fetchall()
        prereqs_list = [dict(p) for p in prereqs]

        if not prereqs_list:
            seed_student_prerequisites_for_university(conn, student_id, u_dict["id"], u_dict["name"], u_dict["course"])
            prereqs = conn.execute("SELECT * FROM student_prerequisites WHERE university_id = ? AND student_id = ? ORDER BY id ASC", (u_dict["id"], student_id)).fetchall()
            prereqs_list = [dict(p) for p in prereqs]

        done_cnt = sum(1 for p in prereqs_list if p["completed"])
        tot_cnt = len(prereqs_list)
        pct = round((done_cnt / tot_cnt * 100)) if tot_cnt > 0 else 0

        u_dict["master"] = master_dict
        u_dict["prerequisites"] = prereqs_list
        u_dict["completed_count"] = done_cnt
        u_dict["total_count"] = tot_cnt
        u_dict["progress_pct"] = pct
        unis_with_prereqs.append(u_dict)

    alerts = compute_student_alerts(conn, student_id)

    documents = conn.execute("""
        SELECT *
        FROM documents
        WHERE student_id = ?
        ORDER BY uploaded_at DESC
    """, (
        student_id,
    )).fetchall()

    essays = conn.execute("""
        SELECT *
        FROM essays
        WHERE student_id = ?
        ORDER BY created_at DESC
    """, (student_id,)).fetchall()

    recommenders = conn.execute("""
        SELECT *
        FROM recommenders
        WHERE student_id = ?
        ORDER BY created_at DESC
    """, (student_id,)).fetchall()

    planning = {
        "tests": conn.execute("SELECT test_name, score, test_date, status FROM test_scores WHERE student_id = ? ORDER BY created_at DESC", (student_id,)).fetchall(),
        "milestones": conn.execute("SELECT title, target_date, status FROM milestones WHERE student_id = ? ORDER BY created_at DESC", (student_id,)).fetchall(),
        "essays": essays,
        "recommenders": recommenders,
        "deadlines": conn.execute("SELECT action, due_date, category, status FROM deadlines WHERE student_id = ? ORDER BY created_at DESC", (student_id,)).fetchall(),
        "prerequisites": conn.execute("SELECT requirement, completed, notes FROM prerequisites WHERE student_id = ? ORDER BY created_at DESC", (student_id,)).fetchall(),
        "checklist": conn.execute("SELECT item_key, completed FROM readiness_checklist WHERE student_id = ?", (student_id,)).fetchall(),
    }

    notes = conn.execute("""
        SELECT *
        FROM counselor_notes
        WHERE student_id = ?
        ORDER BY created_at DESC
    """, (
        student_id,
    )).fetchall()

    conn.close()

    student_dict = dict(student)
    student_dict["name"] = student_dict["full_name"]
    student_dict["progress"] = student_dict["readiness_score"]

    return render_template(
        "counselor/student_view.html",
        student=student_dict,
        academics=academics,
        activities=activities,
        universities=universities,
        unis_with_prereqs=unis_with_prereqs,
        alerts=alerts,
        documents=documents,
        notes=notes,
        planning=planning,
        essays=essays,
        recommenders=recommenders
    )
# ============================================================

@app.route(
    "/api/counselor/students"
)
def api_students():

    if not login_required():

        return jsonify({
            "success": False,
            "message": "Login required"
        }), 401

    if session.get("role") != "counselor":

        return jsonify({
            "success": False,
            "message": "Counselor access required"
        }), 403

    conn = get_db()

    students = conn.execute("""
        SELECT
            id,
            student_id,
            full_name,
            email,
            grade,
            department,
            academic_average,
            readiness_score,
            created_at
        FROM students
        ORDER BY full_name
    """).fetchall()

    conn.close()

    data = []

    for student in students:

        data.append({
            "id": student["id"],
            "student_id": student["student_id"],
            "full_name": student["full_name"],
            "email": student["email"],
            "grade": student["grade"],
            "department": student["department"],
            "academic_average": student["academic_average"],
            "readiness_score": student["readiness_score"]
        })

    return jsonify({
        "success": True,
        "students": data
    })


# ============================================================
# STUDENT PROFILE API
# ============================================================

@app.route(
    "/api/student/profile",
    methods=["GET"]
)
@role_required("student")
def student_profile_api():

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if student is None:

        return jsonify({
            "success": False,
            "message": "Student record not found"
        }), 404

    return jsonify({
        "success": True,
        "student": dict(student)
    })


# ============================================================
# SAVE STUDENT PROFILE
# ============================================================

@app.route(
    "/api/student/profile",
    methods=["POST"]
)
@role_required("student")
def save_student_profile():

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "No data received"
        }), 400

    conn = get_db()

    student = conn.execute("""
        SELECT id
        FROM students
        WHERE user_id = ?
    """, (session["user_id"],)).fetchone()

    if student is None:

        return jsonify({
            "success": False,
            "message": "Student not found"
        }), 404

    conn.execute("""
        UPDATE students

        SET
            full_name = ?,
            email = ?,
            phone = ?,
            date_of_birth = ?,
            department = ?,
            subjects = ?,
            target_degree = ?,
            career_interest = ?,
            why_interest = ?,
            strengths = ?,
            updated_at = ?

        WHERE user_id = ?
    """, (

        data.get("full_name"),

        data.get("email"),

        data.get("phone"),

        data.get("date_of_birth"),

        data.get("department"),

        data.get("subjects"),

        data.get("target_degree"),

        data.get("career_interest"),

        data.get("why_interest"),

        data.get("strengths"),

        datetime.now().isoformat(),

        session["user_id"]

    ))

    conn.commit()

    recalculate_student_metrics(conn, student["id"])

    return jsonify({
        "success": True,
        "message": "Profile saved successfully"
    })


# ============================================================
# ACADEMIC DATA
# ============================================================

@app.route(
    "/api/student/academics",
    methods=["POST"]
)
@role_required("student")
def save_academic():

    data = request.get_json()

    conn = get_db()

    student = conn.execute("""
        SELECT id
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if student is None:

        return jsonify({
            "success": False,
            "message": "Student not found"
        }), 404

    conn.execute("""
        INSERT INTO academics
        (
            student_id,
            subject,
            marks,
            grade,
            exam_name,
            created_at
        )

        VALUES (?, ?, ?, ?, ?, ?)
    """, (

        student["id"],

        data.get("subject"),

        data.get("marks"),

        data.get("grade"),

        data.get("exam_name"),

        datetime.now().isoformat()

    ))

    conn.commit()

    recalculate_student_metrics(conn, student["id"])

    return jsonify({
        "success": True,
        "message": "Academic record saved"
    })


# ============================================================
# ACTIVITIES
# ============================================================

@app.route(
    "/api/student/activities",
    methods=["POST"]
)
@role_required("student")
def save_activity():

    data = request.get_json()

    conn = get_db()

    student = conn.execute("""
        SELECT id
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if student is None:

        return jsonify({
            "success": False,
            "message": "Student not found"
        }), 404

    conn.execute("""
        INSERT INTO activities
        (
            student_id,
            activity_name,
            category,
            description,
            achievement,
            created_at
        )

        VALUES (?, ?, ?, ?, ?, ?)
    """, (

        student["id"],

        data.get("activity_name"),

        data.get("category"),

        data.get("description"),

        data.get("achievement"),

        datetime.now().isoformat()

    ))

    conn.commit()

    recalculate_student_metrics(conn, student["id"])

    return jsonify({
        "success": True,
        "message": "Activity saved"
    })


# ============================================================
# UNIVERSITY
# ============================================================

@app.route(
    "/api/student/universities",
    methods=["POST"]
)
@role_required("student")
def save_university():

    data = request.get_json()

    conn = get_db()

    student = conn.execute("""
        SELECT id
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if student is None:

        return jsonify({
            "success": False,
            "message": "Student not found"
        }), 404

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO universities
        (
            student_id,
            university_name,
            country,
            degree,
            application_type,
            deadline,
            status,
            created_at
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    """, (

        student["id"],

        data.get("university_name"),

        data.get("country"),

        data.get("degree"),

        data.get("application_type"),

        data.get("deadline"),

        data.get("status", "Planning"),

        datetime.now().isoformat()

    ))

    uni_id = cursor.fetchone()[0]

    # Automatically seed college-specific prerequisites for this student & university
    seed_student_prerequisites_for_university(conn, student["id"], uni_id, data.get("university_name"), data.get("degree"))

    conn.commit()

    recalculate_student_metrics(conn, student["id"])

    return jsonify({
        "success": True,
        "message": "University saved successfully"
    })


@app.route("/api/student/universities/delete/<int:id>", methods=["DELETE", "POST"])
@role_required("student")
def delete_university(id):

    conn = get_db()

    student = conn.execute("""
        SELECT id
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if student is None:

        return jsonify({
            "success": False,
            "message": "Student not found"
        }), 404

    uni = conn.execute("""
        SELECT *
        FROM universities
        WHERE id = ? AND student_id = ?
    """, (id, student["id"])).fetchone()

    if not uni:

        return jsonify({
            "success": False,
            "message": "University not found"
        }), 404

    # Clean up associated student prerequisites without affecting master dataset
    conn.execute("DELETE FROM student_prerequisites WHERE university_id = ? AND student_id = ?", (id, student["id"]))
    conn.execute("DELETE FROM universities WHERE id = ? AND student_id = ?", (id, student["id"]))

    conn.commit()

    recalculate_student_metrics(conn, student["id"])

    return jsonify({
        "success": True,
        "message": "University deleted successfully"
    })


@app.route("/api/student/prerequisites/toggle", methods=["POST"])
@role_required("student")
def toggle_student_prerequisite():
    data = request.get_json(silent=True) or {}
    prereq_id = data.get("prerequisite_id") or data.get("id")
    completed = 1 if data.get("completed") else 0
    notes = data.get("notes")

    if not prereq_id:
        return jsonify({"success": False, "message": "Prerequisite ID is required"}), 400

    conn = get_db()
    student = conn.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],)).fetchone()
    if student is None:
        return jsonify({"success": False, "message": "Student not found"}), 404

    prereq = conn.execute("SELECT * FROM student_prerequisites WHERE id = ? AND student_id = ?", (prereq_id, student["id"])).fetchone()
    if not prereq:
        return jsonify({"success": False, "message": "Prerequisite record not found"}), 404

    now_str = datetime.now().isoformat() if completed else None

    if notes is not None:
        conn.execute("""
            UPDATE student_prerequisites
            SET completed = ?, notes = ?, completed_at = ?
            WHERE id = ? AND student_id = ?
        """, (completed, notes, now_str, prereq_id, student["id"]))
    else:
        conn.execute("""
            UPDATE student_prerequisites
            SET completed = ?, completed_at = ?
            WHERE id = ? AND student_id = ?
        """, (completed, now_str, prereq_id, student["id"]))

    conn.commit()

    # Recalculate per-university progress
    uni_prereqs = conn.execute("SELECT completed FROM student_prerequisites WHERE university_id = ? AND student_id = ?", (prereq["university_id"], student["id"])).fetchall()
    total = len(uni_prereqs)
    done = sum(1 for p in uni_prereqs if p["completed"])
    pct = round((done / total * 100)) if total > 0 else 0

    recalculate_student_metrics(conn, student["id"])

    return jsonify({
        "success": True,
        "message": "Prerequisite status updated",
        "completed": bool(completed),
        "completed_count": done,
        "total_count": total,
        "progress_pct": pct
    })


@app.route("/api/student/alerts")
@role_required("student")
def api_student_alerts():
    conn = get_db()
    student = conn.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],)).fetchone()
    if student is None:
        return jsonify({"success": False, "message": "Student not found"}), 404

    alerts = compute_student_alerts(conn, student["id"])
    return jsonify({"success": True, "alerts": alerts})


@app.route("/api/counselor/alerts")
@role_required("counselor")
def api_counselor_alerts():
    conn = get_db()
    students = conn.execute("SELECT id, full_name, student_id FROM students").fetchall()
    all_alerts = []
    for s in students:
        s_alerts = compute_student_alerts(conn, s["id"])
        for a in s_alerts:
            a_copy = dict(a)
            a_copy["student_name"] = s["full_name"]
            a_copy["student_code"] = s["student_id"]
            a_copy["student_id"] = s["id"]
            all_alerts.append(a_copy)

    severity_order = {"CRITICAL": 0, "URGENT": 1, "IMPORTANT": 2, "OVERDUE": 3, "REMINDER": 4, "UPCOMING": 5, "COMPLETED": 6}
    all_alerts.sort(key=lambda x: severity_order.get(x["severity_level"], 99))
    return jsonify({"success": True, "alerts": all_alerts})



# ============================================================
# STUDENT ESSAY & RECOMMENDER APIS
# ============================================================

@app.route("/api/student/essay", methods=["POST"])
@role_required("student")
def save_student_essay():
    is_json = request.is_json
    essay_prompt = (request.json.get("essay_prompt") if is_json else request.form.get("essay_prompt")) or ""
    university = (request.json.get("university") if is_json else request.form.get("university")) or ""
    deadline = (request.json.get("deadline") if is_json else request.form.get("deadline")) or ""
    draft_status = (request.json.get("draft_status") if is_json else request.form.get("draft_status")) or "Uploaded for Counselor Review"

    essay_prompt = str(essay_prompt).strip()
    if not essay_prompt:
        return jsonify(success=False, message="Essay prompt is required"), 400

    file = request.files.get("essay_file") if not is_json else None
    file_path = None
    file_name = None

    conn = get_db()
    student = conn.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],)).fetchone()
    if student is None:
        return jsonify(success=False, message="Student not found"), 404

    if file and file.filename:
        if not allowed_file(file.filename):
            return jsonify(success=False, message=f"Invalid file type. Allowed formats: {', '.join(sorted(app.config.get('ALLOWED_EXTENSIONS', Config.ALLOWED_EXTENSIONS)))}"), 400
        file_name = file.filename
        safe_base = secure_filename(file_name) or "essay_draft.pdf"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_name = f"essay_{student['id']}_{timestamp}_{safe_base}"
        file_path = os.path.join(UPLOAD_FOLDER, safe_name)
        file.save(file_path)

    conn.execute("""
        INSERT INTO essays (student_id, essay_prompt, university, draft_status, deadline, file_path, file_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (student["id"], essay_prompt, university, draft_status, deadline, file_path, file_name, datetime.now().isoformat()))
    conn.commit()
    recalculate_student_metrics(conn, student["id"])
    return jsonify(success=True, message="Essay draft submitted for counselor review!")


@app.route("/api/student/recommender", methods=["POST"])
@role_required("student")
def save_student_recommender():
    data = request.get_json(silent=True) or request.form
    teacher_name = str(data.get("teacher_name", "")).strip()
    subject = str(data.get("subject", "")).strip()
    university = str(data.get("university", "")).strip()
    deadline = str(data.get("deadline", "")).strip()
    brag_sheet = str(data.get("brag_sheet", "")).strip()

    if not teacher_name:
        return jsonify(success=False, message="Teacher/Staff name is required"), 400

    conn = get_db()
    student = conn.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],)).fetchone()
    if student is None:
        return jsonify(success=False, message="Student not found"), 404

    conn.execute("""
        INSERT INTO recommenders (student_id, teacher_name, subject, university, deadline, brag_sheet, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Requested', ?)
    """, (student["id"], teacher_name, subject, university, deadline, brag_sheet, datetime.now().isoformat()))
    conn.commit()
    recalculate_student_metrics(conn, student["id"])
    return jsonify(success=True, message="LOR request sent to staff!")


# ============================================================
# COUNSELOR ESSAY & LOR ACTION APIS
# ============================================================

@app.route("/api/counselor/essay/<int:essay_id>/feedback", methods=["POST"])
@role_required("counselor")
def add_essay_feedback(essay_id):
    data = request.get_json(silent=True) or request.form
    feedback = str(data.get("feedback", "")).strip()
    draft_status = str(data.get("draft_status", "Counselor Reviewed")).strip()

    conn = get_db()
    essay = conn.execute("SELECT * FROM essays WHERE id = ?", (essay_id,)).fetchone()
    if essay is None:
        return jsonify(success=False, message="Essay record not found"), 404

    conn.execute("UPDATE essays SET feedback = ?, draft_status = ? WHERE id = ?", (feedback, draft_status, essay_id))
    conn.commit()
    return jsonify(success=True, message="Counselor recommendation feedback saved!")


@app.route("/api/counselor/recommender/<int:recommender_id>/upload_lor", methods=["POST"])
@role_required("counselor")
def upload_staff_lor(recommender_id):
    file = request.files.get("lor_file")
    status = request.form.get("status", "LOR Sent by Staff")

    if not file or not file.filename:
        return jsonify(success=False, message="Please select an LOR document file to upload"), 400

    if not allowed_file(file.filename):
        return jsonify(success=False, message=f"Invalid file type. Allowed formats: {', '.join(sorted(app.config.get('ALLOWED_EXTENSIONS', Config.ALLOWED_EXTENSIONS)))}"), 400

    conn = get_db()
    recommender = conn.execute("SELECT * FROM recommenders WHERE id = ?", (recommender_id,)).fetchone()
    if recommender is None:
        return jsonify(success=False, message="Recommender request not found"), 404

    file_name = file.filename
    safe_base = secure_filename(file_name) or "official_lor.pdf"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_name = f"lor_{recommender['student_id']}_{timestamp}_{safe_base}"
    file_path = os.path.join(UPLOAD_FOLDER, safe_name)
    file.save(file_path)

    conn.execute("UPDATE recommenders SET lor_file_path = ?, lor_file_name = ?, status = ? WHERE id = ?", (file_path, file_name, status, recommender_id))
    conn.commit()
    return jsonify(success=True, message="Official LOR uploaded and sent by staff!")


# ============================================================
# FILE DOWNLOAD ENDPOINTS
# ============================================================

@app.route("/essay_draft/<int:essay_id>/download")
@login_required
def download_essay_draft(essay_id):
    conn = get_db()
    essay = conn.execute("SELECT * FROM essays WHERE id = ?", (essay_id,)).fetchone()

    if essay is None or not essay["file_path"] or not os.path.exists(essay["file_path"]):
        return "Essay draft file not found", 404

    if session.get("role") == "student":
        student = conn.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],)).fetchone()
        if student is None or student["id"] != essay["student_id"]:
            return "Access denied: You are not authorized to download this essay draft.", 403
    elif session.get("role") != "counselor":
        return "Access denied", 403

    return send_file(essay["file_path"], as_attachment=True, download_name=essay["file_name"] or "essay_draft.pdf")


@app.route("/lor/<int:recommender_id>/download")
@login_required
def download_lor(recommender_id):
    conn = get_db()
    recommender = conn.execute("SELECT * FROM recommenders WHERE id = ?", (recommender_id,)).fetchone()

    if recommender is None or not recommender["lor_file_path"] or not os.path.exists(recommender["lor_file_path"]):
        return "LOR file not found", 404

    if session.get("role") == "student":
        student = conn.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],)).fetchone()
        if student is None or student["id"] != recommender["student_id"]:
            return "Access denied: You are not authorized to download this LOR.", 403
    elif session.get("role") != "counselor":
        return "Access denied", 403

    return send_file(recommender["lor_file_path"], as_attachment=True, download_name=recommender["lor_file_name"] or "Official_LOR.pdf")


@app.route("/api/student/planning/<record_type>", methods=["POST"])
@role_required("student")
def save_planning_record(record_type):
    """Save the records created from the Tests, Journey, Essays, Deadlines and Requirements pages."""
    definitions = {
        "tests": ("test_scores", ("test_name", "score", "test_date", "status")),
        "milestones": ("milestones", ("title", "target_date", "status")),
        "essays": ("essays", ("essay_prompt", "university", "draft_status", "deadline")),
        "deadlines": ("deadlines", ("action", "due_date", "category", "status")),
        "prerequisites": ("prerequisites", ("requirement", "completed", "notes")),
    }
    definition = definitions.get(record_type)
    if definition is None:
        return jsonify(success=False, message="Unknown record type"), 404

    data = request.get_json(silent=True) or {}
    table, fields = definition
    required_field = fields[0]
    if not str(data.get(required_field, "")).strip():
        return jsonify(success=False, message=f"{required_field.replace('_', ' ').title()} is required"), 400

    conn = get_db()
    student = conn.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],)).fetchone()
    if student is None:
        return jsonify(success=False, message="Student not found"), 404

    columns = ("student_id",) + fields + ("created_at",)
    values = [student["id"]] + [data.get(field) for field in fields] + [datetime.now().isoformat()]
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", values)
    conn.commit()
    recalculate_student_metrics(conn, student["id"])
    return jsonify(success=True, message="Record saved")


@app.route("/api/student/readiness-checklist", methods=["POST"])
@role_required("student")
def save_readiness_checklist():
    data = request.get_json(silent=True) or {}
    items = data.get("items")
    if not isinstance(items, dict):
        return jsonify(success=False, message="Checklist data is required"), 400

    conn = get_db()
    student = conn.execute("SELECT id FROM students WHERE user_id = ?", (session["user_id"],)).fetchone()
    if student is None:
        return jsonify(success=False, message="Student not found"), 404
    now = datetime.now().isoformat()
    for key, completed in items.items():
        if isinstance(key, str) and len(key) <= 80:
            conn.execute("""INSERT INTO readiness_checklist (student_id, item_key, completed, updated_at)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(student_id, item_key) DO UPDATE SET completed = excluded.completed, updated_at = excluded.updated_at""",
                         (student["id"], key, int(bool(completed)), now))
    conn.commit()
    return jsonify(success=True, message="Readiness progress saved")


# ============================================================
# DOCUMENT UPLOAD
# ============================================================

@app.route(
    "/api/student/document",
    methods=["POST"]
)
@role_required("student")
def upload_document():

    file = request.files.get("file")

    document_name = request.form.get(
        "document_name",
        "Student Document"
    )

    if not file or not file.filename:

        return jsonify({
            "success": False,
            "message": "No file uploaded"
        }), 400

    if not allowed_file(file.filename):

        return jsonify({
            "success": False,
            "message": f"Invalid file type. Allowed formats: {', '.join(sorted(app.config.get('ALLOWED_EXTENSIONS', Config.ALLOWED_EXTENSIONS)))}"
        }), 400

    conn = get_db()

    student = conn.execute("""
        SELECT id
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if student is None:

        return jsonify({
            "success": False,
            "message": "Student not found"
        }), 404

    original_name = file.filename
    safe_base = secure_filename(original_name) or "document.pdf"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_name = f"{student['id']}_{timestamp}_{safe_base}"
    file_path = os.path.join(UPLOAD_FOLDER, safe_name)

    file.save(file_path)

    conn.execute("""
        INSERT INTO documents
        (
            student_id,
            document_name,
            file_name,
            file_path,
            uploaded_at
        )

        VALUES (?, ?, ?, ?, ?)
    """, (

        student["id"],

        document_name,

        original_name,

        file_path,

        datetime.now().isoformat()

    ))

    conn.commit()

    recalculate_student_metrics(conn, student["id"])

    return jsonify({
        "success": True,
        "message": "Document uploaded successfully"
    })


# ============================================================
# DOWNLOAD DOCUMENT
# ============================================================

@app.route(
    "/document/<int:document_id>/download"
)
@login_required
def download_document(document_id):

    conn = get_db()

    document = conn.execute("""
        SELECT *
        FROM documents
        WHERE id = ?
    """, (
        document_id,
    )).fetchone()

    if document is None:

        return "Document not found", 404

    # --------------------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------------------

    if session.get("role") == "student":

        student = conn.execute("""
            SELECT id
            FROM students
            WHERE user_id = ?
        """, (
            session["user_id"],
        )).fetchone()

        if (
            student is None or
            student["id"] != document["student_id"]
        ):

            return "Access denied: You are not authorized to download this document.", 403

    elif session.get("role") != "counselor":

        return "Access denied", 403

    # --------------------------------------------------------
    # SEND FILE
    # --------------------------------------------------------

    if not os.path.exists(
        document["file_path"]
    ):

        return "File not found", 404

    return send_file(
        document["file_path"],
        as_attachment=True,
        download_name=document["file_name"]
    )


# ============================================================
# COUNSELOR NOTE
# ============================================================

@app.route(
    "/api/counselor/student/<int:student_id>/note",
    methods=["POST"]
)
def add_counselor_note(student_id):

    if not login_required():

        return jsonify({
            "success": False,
            "message": "Login required"
        }), 401

    if session.get("role") != "counselor":

        return jsonify({
            "success": False,
            "message": "Counselor access required"
        }), 403

    data = request.get_json()

    note = data.get(
        "note",
        ""
    ).strip()

    if not note:

        return jsonify({
            "success": False,
            "message": "Note cannot be empty"
        }), 400

    conn = get_db()

    conn.execute("""
        INSERT INTO counselor_notes
        (
            student_id,
            counselor_id,
            note,
            created_at
        )

        VALUES (?, ?, ?, ?)
    """, (

        student_id,

        session["user_id"],

        note,

        datetime.now().isoformat()

    ))

    conn.commit()

    conn.close()

    return jsonify({
        "success": True,
        "message": "Counselor note saved"
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/student/record/download", methods=["GET", "POST"])
@role_required("student")
def download_my_student_record():
    conn = get_db()
    student = conn.execute("SELECT id, full_name FROM students WHERE user_id = ?", (session["user_id"],)).fetchone()
    if student is None:
        conn.close()
        return "Student not found", 404

    options = {}
    if request.method == "POST":
        options = request.get_json(silent=True) or {}
    else:
        options = {
            'theme': request.args.get('theme', 'navy'),
            'interactive_checklist': request.args.get('interactive_checklist', '1') == '1',
            'fillable_notes': request.args.get('fillable_notes', '1') == '1',
            'clickable_links': request.args.get('clickable_links', '1') == '1',
            'sections': request.args.get('sections', '').split(',') if request.args.get('sections') else None
        }

    is_preview = request.args.get('preview', '0') == '1' or options.get('preview', False)

    report = student_record_pdf(conn, student["id"], options=options)
    conn.close()
    safe_name = "_".join((student["full_name"] or "student").split())
    return send_file(
        BytesIO(report),
        mimetype="application/pdf",
        as_attachment=not is_preview,
        download_name=f"SPARK_{safe_name}_Interactive_Record.pdf"
    )


@app.route("/counselor/student/<int:student_id>/record/download", methods=["GET", "POST"])
@role_required("counselor")
def counselor_download_student_record(student_id):
    conn = get_db()
    student = conn.execute("SELECT full_name FROM students WHERE id = ?", (student_id,)).fetchone()
    if student is None:
        conn.close()
        return "Student not found", 404

    options = {}
    if request.method == "POST":
        options = request.get_json(silent=True) or {}
    else:
        options = {
            'theme': request.args.get('theme', 'navy'),
            'interactive_checklist': request.args.get('interactive_checklist', '1') == '1',
            'fillable_notes': request.args.get('fillable_notes', '1') == '1',
            'clickable_links': request.args.get('clickable_links', '1') == '1',
            'sections': request.args.get('sections', '').split(',') if request.args.get('sections') else None
        }

    is_preview = request.args.get('preview', '0') == '1' or options.get('preview', False)

    report = student_record_pdf(conn, student_id, options=options)
    conn.close()
    safe_name = "_".join((student["full_name"] or "student").split())
    return send_file(
        BytesIO(report),
        mimetype="application/pdf",
        as_attachment=not is_preview,
        download_name=f"SPARK_{safe_name}_Interactive_Record.pdf"
    )

@app.route("/health")
def health():
    # Ensure database exists on health check
    ensure_db_exists()
    
    db_type = "PostgreSQL" if os.environ.get("DATABASE_URL") else "SQLite"
    
    return jsonify({
        "status": "online",
        "application": "SPARK",
        "database": db_type,
        "time": datetime.now().isoformat()
    })


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

# Don't initialize database at module level for Vercel compatibility


# ============================================================
# RUN APPLICATION
# ============================================================

# Don't initialize database globally for serverless compatibility
# Database will be initialized on first request via ensure_db_exists()

if __name__ == "__main__":
    with app.app_context():
        ensure_db_exists()

    print("")
    print("============================================")
    print("        SPARK STUDENT PORTAL")
    print("============================================")
    print("")
    print("Database : PostgreSQL")
    print("Database : mywebsite")
    print("")
    print("Student Login")
    print("Username : student")
    print("Password : student123")
    print("")
    print("Counselor Login")
    print("Username : counselor")
    print("Password : counselor123")
    print("")
    print("Open:")
    print("http://127.0.0.1:5000")
    print("")
    print("============================================")

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
