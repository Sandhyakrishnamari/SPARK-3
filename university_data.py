import re
from datetime import datetime

MASTER_UNIVERSITIES_DATA = [
    # UK Universities
    {
        "name": "Oxford",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, Biology, Biochem, CS, Economics, Physics",
        "academic_requirement": "AAA–AAA",
        "key_subjects": "Course-specific",
        "tests": "ESAT / TMUA / TARA / UCAT",
        "competitive_target": "Aim top competitive range",
        "application_deadline": "15 Oct 2027 expected"
    },
    {
        "name": "Cambridge",
        "country": "United Kingdom",
        "best_fit_courses": "Natural Sciences, CS, Economics, Engineering, Medicine",
        "academic_requirement": "AAA",
        "key_subjects": "Maths/Science",
        "tests": "ESAT / TMUA / UCAT",
        "competitive_target": "Very high",
        "application_deadline": "15 Oct 2027 expected"
    },
    {
        "name": "Imperial",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, CS, Biology, Chemistry, Physics, Engineering",
        "academic_requirement": "AAA–AAA",
        "key_subjects": "Maths/Science",
        "tests": "ESAT / TMUA / UCAT",
        "competitive_target": "Very high",
        "application_deadline": "15 Oct 2027 expected"
    },
    {
        "name": "LSE",
        "country": "United Kingdom",
        "best_fit_courses": "Economics, Finance, Data Science, Actuarial",
        "academic_requirement": "A*AA",
        "key_subjects": "Maths",
        "tests": "TMUA",
        "competitive_target": "Aim 7+",
        "application_deadline": "Jan 2028 expected"
    },
    {
        "name": "UCL",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, CS, Biology, Economics",
        "academic_requirement": "A*AA–AAA",
        "key_subjects": "Course-specific",
        "tests": "UCAT/TMUA where required",
        "competitive_target": "High",
        "application_deadline": "Jan 2028 expected"
    },
    {
        "name": "Edinburgh",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, CS, Biology, AI, Economics",
        "academic_requirement": "AAA–AAA",
        "key_subjects": "Course-specific",
        "tests": "UCAT Medicine",
        "competitive_target": "High",
        "application_deadline": "Jan 2028 expected"
    },
    {
        "name": "King's",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, Biomedical, CS, Economics",
        "academic_requirement": "A*AA–AAA",
        "key_subjects": "Bio + Chem Medicine",
        "tests": "UCAT Medicine",
        "competitive_target": "High",
        "application_deadline": "Oct 2027 Medicine"
    },
    {
        "name": "Manchester",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, Biology, CS, Physics, Economics",
        "academic_requirement": "AAA–AAB",
        "key_subjects": "Science/Maths",
        "tests": "UCAT Medicine",
        "competitive_target": "High",
        "application_deadline": "Oct Medicine / Jan others"
    },
    {
        "name": "Warwick",
        "country": "United Kingdom",
        "best_fit_courses": "Economics, CS, Maths, Physics",
        "academic_requirement": "A*AA",
        "key_subjects": "Maths",
        "tests": "TMUA selected courses",
        "competitive_target": "Aim 7+",
        "application_deadline": "Jan 2028 expected"
    },
    {
        "name": "Bristol",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, Biology, CS, Physics, Economics",
        "academic_requirement": "A*AA–AAA",
        "key_subjects": "Course-specific",
        "tests": "UCAT",
        "competitive_target": "High",
        "application_deadline": "Oct Medicine / Jan others"
    },
    {
        "name": "St Andrews",
        "country": "United Kingdom",
        "best_fit_courses": "Biology, Chemistry, Physics, Economics, CS",
        "academic_requirement": "AAA–AAB",
        "key_subjects": "Course-specific",
        "tests": "UCAT",
        "competitive_target": "High",
        "application_deadline": "Oct Medicine / Jan others"
    },
    {
        "name": "Durham",
        "country": "United Kingdom",
        "best_fit_courses": "CS, Physics, Economics, Natural Sciences",
        "academic_requirement": "A*AA",
        "key_subjects": "Maths",
        "tests": "TMUA selected courses",
        "competitive_target": "Aim 7+",
        "application_deadline": "Jan 2028 expected"
    },
    {
        "name": "Bath",
        "country": "United Kingdom",
        "best_fit_courses": "CS, Engineering, Physics, Economics",
        "academic_requirement": "A*AA–AAA",
        "key_subjects": "Maths",
        "tests": "TMUA selected courses",
        "competitive_target": "Aim 7+",
        "application_deadline": "Jan 2028 expected"
    },
    {
        "name": "Birmingham",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, Biology, Chemistry, CS",
        "academic_requirement": "AAA–AAB",
        "key_subjects": "Science",
        "tests": "UCAT",
        "competitive_target": "High",
        "application_deadline": "Oct Medicine / Jan others"
    },
    {
        "name": "Southampton",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, Biology, Chemistry, CS, Engineering",
        "academic_requirement": "A*AA–AAA",
        "key_subjects": "Maths/Science",
        "tests": "UCAT",
        "competitive_target": "High",
        "application_deadline": "Oct Medicine / Jan others"
    },
    {
        "name": "Leeds",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, Biology, CS, Economics",
        "academic_requirement": "AAA–AAB",
        "key_subjects": "Course-specific",
        "tests": "UCAT",
        "competitive_target": "High",
        "application_deadline": "Oct Medicine / Jan others"
    },
    {
        "name": "Nottingham",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, Biology, CS, Economics",
        "academic_requirement": "AAA–AAB",
        "key_subjects": "Bio/Chem Medicine",
        "tests": "UCAT",
        "competitive_target": "High",
        "application_deadline": "Oct Medicine / Jan others"
    },
    {
        "name": "Exeter",
        "country": "United Kingdom",
        "best_fit_courses": "Biology, Economics, Business, CS",
        "academic_requirement": "AAB–AAA",
        "key_subjects": "Maths Economics",
        "tests": "Course-specific",
        "competitive_target": "Standard",
        "application_deadline": "Jan 2028 expected"
    },
    {
        "name": "Glasgow",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, Life Sciences, CS, Economics",
        "academic_requirement": "AAA–AAB",
        "key_subjects": "Science",
        "tests": "UCAT",
        "competitive_target": "High",
        "application_deadline": "Oct Medicine / Jan others"
    },
    {
        "name": "Sheffield",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, CS, Physics, Biology",
        "academic_requirement": "AAA–AAB",
        "key_subjects": "Course-specific",
        "tests": "UCAT",
        "competitive_target": "High",
        "application_deadline": "Oct Medicine / Jan others"
    },
    {
        "name": "Newcastle",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, Biology, CS, Business",
        "academic_requirement": "AAA–AAB",
        "key_subjects": "Bio/Chem Medicine",
        "tests": "UCAT",
        "competitive_target": "High",
        "application_deadline": "Oct Medicine / Jan others"
    },
    {
        "name": "Lancaster",
        "country": "United Kingdom",
        "best_fit_courses": "CS, Data Science, Physics, Economics",
        "academic_requirement": "AAB–AAA",
        "key_subjects": "Maths quantitative",
        "tests": "Course-specific",
        "competitive_target": "Standard",
        "application_deadline": "Jan 2028 expected"
    },
    {
        "name": "Queen Mary London",
        "country": "United Kingdom",
        "best_fit_courses": "Medicine, CS, Economics, Business",
        "academic_requirement": "AAA–AAB",
        "key_subjects": "Course-specific",
        "tests": "UCAT",
        "competitive_target": "High",
        "application_deadline": "Oct Medicine / Jan others"
    },
    {
        "name": "York",
        "country": "United Kingdom",
        "best_fit_courses": "Biology, Chemistry, CS, Economics",
        "academic_requirement": "AAA–AAB",
        "key_subjects": "Course-specific",
        "tests": "Course-specific",
        "competitive_target": "Standard",
        "application_deadline": "Jan 2028 expected"
    },
    {
        "name": "Surrey",
        "country": "United Kingdom",
        "best_fit_courses": "Biology, CS, Business, Economics, Physics",
        "academic_requirement": "AAB–BBB",
        "key_subjects": "Course-specific",
        "tests": "Course-specific",
        "competitive_target": "Standard",
        "application_deadline": "Jan 2028 expected"
    },

    # US Universities
    {
        "name": "MIT",
        "country": "United States",
        "best_fit_courses": "CS, AI, Engineering, Physics, Biology, Economics",
        "academic_requirement": "No formal A-level requirement. Strong Maths + Physics + Chemistry highly recommended",
        "key_subjects": "Maths + Physics + Chemistry",
        "tests": "SAT 1550+ / ACT 35+",
        "competitive_target": "A*A*A minimum target; A* in Maths/Physics preferred",
        "application_deadline": "EA ~1 Nov 2027 / RD ~Jan 2028"
    },
    {
        "name": "Stanford",
        "country": "United States",
        "best_fit_courses": "CS, Biology, Engineering, Economics",
        "academic_requirement": "No fixed A-level requirement; most rigorous available curriculum expected",
        "key_subjects": "Rigorous available curriculum",
        "tests": "SAT 1500–1570+ / ACT 34–36",
        "competitive_target": "A*A*A",
        "application_deadline": "REA ~1 Nov / RD ~5 Jan"
    },
    {
        "name": "Harvard",
        "country": "United States",
        "best_fit_courses": "Biology, Economics, CS, Engineering",
        "academic_requirement": "No fixed A-level combination; rigorous breadth expected",
        "key_subjects": "Rigorous breadth expected",
        "tests": "SAT 1500+ / ACT 34+",
        "competitive_target": "A*A*A",
        "application_deadline": "REA ~1 Nov / RD ~1 Jan"
    },
    {
        "name": "Princeton",
        "country": "United States",
        "best_fit_courses": "Physics, Biology, CS, Economics",
        "academic_requirement": "No fixed A-level minimum; strongest available Maths/Science preparation",
        "key_subjects": "Strongest Maths/Science",
        "tests": "If submitting: 1500+",
        "competitive_target": "A*A*A",
        "application_deadline": "~1 Nov / ~1 Jan"
    },
    {
        "name": "Yale",
        "country": "United States",
        "best_fit_courses": "Biology, Economics, CS, Chemistry, Physics",
        "academic_requirement": "No fixed A-level minimum; rigorous programme expected",
        "key_subjects": "Rigorous programme",
        "tests": "1500+ / 34+",
        "competitive_target": "A*A*A",
        "application_deadline": "~1 Nov / ~2 Jan"
    },
    {
        "name": "Caltech",
        "country": "United States",
        "best_fit_courses": "Physics, Chemistry, Biology, CS, Engineering",
        "academic_requirement": "A-level Maths required; Physics + Chemistry required; Biology recommended",
        "key_subjects": "Maths, Physics, Chemistry",
        "tests": "SAT 1550+, Maths 780+",
        "competitive_target": "A*A*A, including A* Maths + strong Physics/Chemistry",
        "application_deadline": "~1 Nov / ~4 Jan"
    },
    {
        "name": "University of Pennsylvania",
        "country": "United States",
        "best_fit_courses": "Wharton, Economics, Biology, CS",
        "academic_requirement": "No formal A-level minimum; rigorous courses relevant to programme",
        "key_subjects": "Programme relevant courses",
        "tests": "1500+",
        "competitive_target": "A*A*A",
        "application_deadline": "ED ~1 Nov / RD ~5 Jan"
    },
    {
        "name": "Columbia",
        "country": "United States",
        "best_fit_courses": "Economics, CS, Biology, Engineering",
        "academic_requirement": "No fixed A-level requirement; rigorous academic programme",
        "key_subjects": "Rigorous academic programme",
        "tests": "1500+ if submitting",
        "competitive_target": "A*A*A",
        "application_deadline": "~1 Nov / ~1 Jan"
    },
    {
        "name": "Cornell",
        "country": "United States",
        "best_fit_courses": "Engineering, CS, Biology, Business, Economics",
        "academic_requirement": "Programme-specific preparation; Maths/Physics for engineering",
        "key_subjects": "Maths/Physics for STEM",
        "tests": "1480–1550+",
        "competitive_target": "A*A*A",
        "application_deadline": "ED ~1 Nov / RD ~2 Jan"
    },
    {
        "name": "University of Chicago",
        "country": "United States",
        "best_fit_courses": "Economics, Biology, CS, Maths",
        "academic_requirement": "No fixed A-level minimum; advanced Maths strongly useful",
        "key_subjects": "Advanced Maths",
        "tests": "1500+ if submitting",
        "competitive_target": "A*A*A",
        "application_deadline": "~1 Nov / ~5 Jan"
    },
    {
        "name": "Duke",
        "country": "United States",
        "best_fit_courses": "Biology, Economics, CS, Engineering",
        "academic_requirement": "No fixed A-level minimum; Maths/Science for STEM",
        "key_subjects": "Maths/Science for STEM",
        "tests": "1500+ / 34+ if submitting",
        "competitive_target": "A*A*A",
        "application_deadline": "~1 Nov / ~5 Jan"
    },
    {
        "name": "Johns Hopkins",
        "country": "United States",
        "best_fit_courses": "Medicine pathway, Biology, Biomedical, CS",
        "academic_requirement": "Biology + Chemistry + Maths strongly recommended for STEM/medicine pathway",
        "key_subjects": "Bio + Chem + Maths",
        "tests": "1500+ / 34+",
        "competitive_target": "A*A*A",
        "application_deadline": "~1 Nov / ~2 Jan"
    },
    {
        "name": "Northwestern",
        "country": "United States",
        "best_fit_courses": "CS, Economics, Biology, Business",
        "academic_requirement": "No fixed A-level requirement",
        "key_subjects": "Rigorous subjects",
        "tests": "1500+ / 34+ if submitting",
        "competitive_target": "A*A*A",
        "application_deadline": "~1 Nov / ~3 Jan"
    },
    {
        "name": "Carnegie Mellon",
        "country": "United States",
        "best_fit_courses": "CS, AI, Robotics, Business",
        "academic_requirement": "Maths essential for CS/AI; Physics useful",
        "key_subjects": "Maths, Physics",
        "tests": "1500+ / 34+",
        "competitive_target": "A*A*A, Maths A*",
        "application_deadline": "~1 Nov / ~5 Jan"
    },
    {
        "name": "UC Berkeley",
        "country": "United States",
        "best_fit_courses": "CS, Biology, Economics, Business",
        "academic_requirement": "No A-level minimum; rigorous preparation expected",
        "key_subjects": "Rigorous preparation",
        "tests": "Not considered",
        "competitive_target": "A*AA–A*A*A",
        "application_deadline": "30 Nov 2027 expected"
    },
    {
        "name": "UCLA",
        "country": "United States",
        "best_fit_courses": "Biology, CS, Economics, Business",
        "academic_requirement": "No A-level minimum",
        "key_subjects": "Rigorous preparation",
        "tests": "Not considered",
        "competitive_target": "A*AA–A*A*A",
        "application_deadline": "30 Nov 2027 expected"
    },
    {
        "name": "Michigan–Ann Arbor",
        "country": "United States",
        "best_fit_courses": "Engineering, CS, Biology, Economics",
        "academic_requirement": "Maths + relevant sciences for STEM",
        "key_subjects": "Maths + Sciences",
        "tests": "1450+ / 33+",
        "competitive_target": "A*AA–A*A*A",
        "application_deadline": "~1 Nov EA / Feb RD"
    },
    {
        "name": "Georgia Tech",
        "country": "United States",
        "best_fit_courses": "CS, AI, Engineering, Physics",
        "academic_requirement": "Maths + Physics strongly recommended",
        "key_subjects": "Maths + Physics",
        "tests": "1450+ / 33+",
        "competitive_target": "A*AA–A*A*A",
        "application_deadline": "~Oct/Nov EA / Jan RD"
    },
    {
        "name": "UIUC",
        "country": "United States",
        "best_fit_courses": "CS, Engineering, Biology, Economics",
        "academic_requirement": "Maths + Physics for engineering/CS",
        "key_subjects": "Maths + Physics",
        "tests": "1450+ / 33+",
        "competitive_target": "A*AA–A*A*A",
        "application_deadline": "~1 Nov EA / ~5 Jan RD"
    },
    {
        "name": "UT Austin",
        "country": "United States",
        "best_fit_courses": "CS, Engineering, Business, Biology",
        "academic_requirement": "Maths + relevant science for STEM",
        "key_subjects": "Maths + Science",
        "tests": "1450+ / 33+",
        "competitive_target": "A*AA–AAA",
        "application_deadline": "~15 Oct EA / ~1 Dec RD"
    },
    {
        "name": "University of Washington",
        "country": "United States",
        "best_fit_courses": "CS, Biology, Engineering, Economics",
        "academic_requirement": "Maths + science for STEM",
        "key_subjects": "Maths + Science",
        "tests": "Not considered",
        "competitive_target": "A*AA–AAA",
        "application_deadline": "15 Nov 2027 expected"
    },
    {
        "name": "Purdue",
        "country": "United States",
        "best_fit_courses": "Engineering, CS, Physics, Biology",
        "academic_requirement": "Maths + Physics/Chemistry",
        "key_subjects": "Maths + Physics/Chemistry",
        "tests": "1400–1450+ / 32+",
        "competitive_target": "A*AA–AAA",
        "application_deadline": "~1 Nov EA / ~15 Jan RD"
    },
    {
        "name": "USC",
        "country": "United States",
        "best_fit_courses": "CS, Business, Biology, Engineering",
        "academic_requirement": "Maths/science according to intended major",
        "key_subjects": "Maths/Science",
        "tests": "1450+ / 33+ if submitting",
        "competitive_target": "A*AA–AAA",
        "application_deadline": "~1 Nov EA/ED / ~10 Jan RD"
    },
    {
        "name": "Boston University",
        "country": "United States",
        "best_fit_courses": "Biology, Business, Economics, CS",
        "academic_requirement": "No fixed A-level minimum; relevant rigorous subjects",
        "key_subjects": "Rigorous subjects",
        "tests": "1450+ / 33+ if submitting",
        "competitive_target": "AAA–A*AA",
        "application_deadline": "~1 Nov ED / ~5 Jan RD"
    },
    {
        "name": "NYU",
        "country": "United States",
        "best_fit_courses": "Business, Economics, CS, Biology",
        "academic_requirement": "Maths strongly recommended for quantitative subjects",
        "key_subjects": "Maths",
        "tests": "1450+ / 33+ if submitting",
        "competitive_target": "AAA–A*AA",
        "application_deadline": "~1 Nov ED / ~1 Jan RD"
    }
]

def seed_master_universities(conn):
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    for uni in MASTER_UNIVERSITIES_DATA:
        cursor.execute("SELECT id FROM master_universities WHERE name = ?", (uni["name"],))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT INTO master_universities (
                    name, country, best_fit_courses, academic_requirement,
                    key_subjects, tests, competitive_target, application_deadline, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                uni["name"], uni["country"], uni["best_fit_courses"], uni["academic_requirement"],
                uni["key_subjects"], uni["tests"], uni["competitive_target"], uni["application_deadline"], now
            ))
            cursor.execute("SELECT id FROM master_universities WHERE name = ?", (uni["name"],))
            master_id = cursor.fetchone()[0]
            
            templates = [
                ("Academic requirements", "Academic", f"Target Grade: {uni['academic_requirement']} (Target: {uni['competitive_target']})"),
                ("Required subjects", "Subject", f"Key Subjects: {uni['key_subjects']}"),
                ("Required admission test", "Test", f"Test Planning: {uni['tests']}"),
                ("English proficiency", "English", "IELTS / TOEFL / Duolingo English Proficiency Verification"),
                ("Essay / personal statement", "Essay", "Personal Statement & Supplemental University Essays"),
                ("Recommendation", "Recommendation", "Academic References & Counselor Recommendation Letter"),
                ("Supporting documents", "Document", "High School Transcripts & Official Documents")
            ]
            for req_name, category, desc in templates:
                cursor.execute("""
                    INSERT INTO master_university_requirements (university_id, requirement_name, category, description)
                    VALUES (?, ?, ?, ?)
                """, (master_id, req_name, category, desc))
    conn.commit()


def seed_student_prerequisites_for_university(conn, student_id, university_record_id, uni_name, selected_course=None):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM student_prerequisites WHERE student_id = ? AND university_id = ?", (student_id, university_record_id))
    if cursor.fetchone()[0] > 0:
        return

    cursor.execute("SELECT * FROM master_universities WHERE name = ?", (uni_name,))
    master_uni = cursor.fetchone()
    
    now = datetime.now().isoformat()
    
    if master_uni:
        master_dict = dict(master_uni)
        acad_req = master_dict.get("academic_requirement", "AAA–AAA")
        comp_targ = master_dict.get("competitive_target", "High")
        key_subj = master_dict.get("key_subjects", "Course-specific")
        tests_req = master_dict.get("tests", "Standard Entry Tests")
        course_str = f" for {selected_course}" if selected_course else ""

        items = [
            ("Academic requirements", "Academic", f"Target Grade: {acad_req} | Target: {comp_targ}{course_str}"),
            ("Required subjects", "Subject", f"Key Subjects: {key_subj}"),
            ("Required admission test", "Test", f"Admission / Planning Test: {tests_req}"),
            ("English proficiency", "English", "IELTS / TOEFL / Duolingo Test Result"),
            ("Essay / personal statement", "Essay", f"Personal Statement & University Essays{course_str}"),
            ("Recommendation", "Recommendation", "Teacher & Counselor Letters of Recommendation"),
            ("Supporting documents", "Document", "Academic Transcripts & Official Documentation")
        ]
    else:
        items = [
            ("Academic requirements", "Academic", "Standard Academic Transcripts & Minimum Grade Thresholds"),
            ("Required subjects", "Subject", "Required High School Course Prerequisites"),
            ("Required admission test", "Test", "Standardized Admission Tests (SAT/ACT/UCAT/TMUA/ESAT)"),
            ("English proficiency", "English", "English Language Proficiency Test Scores"),
            ("Essay / personal statement", "Essay", "Application Personal Statement & Essays"),
            ("Recommendation", "Recommendation", "Teacher & Counselor Recommendation Letters"),
            ("Supporting documents", "Document", "Transcripts & Supporting Certificates")
        ]

    for req_name, category, desc in items:
        cursor.execute("""
            INSERT INTO student_prerequisites (
                student_id, university_id, requirement_name, category, description, completed, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (student_id, university_record_id, req_name, category, desc, False, now))
    
    conn.commit()


def parse_date_string(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    formats = ["%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%Y/%m/%d", "%d/%m/%Y", "%b %d, %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    m = re.search(r'(\d{1,2})?\s*([A-Za-z]+)\s*(\d{4})', date_str)
    if m:
        day = int(m.group(1)) if m.group(1) else 1
        month_str = m.group(2)
        year = int(m.group(3))
        for fmt in ["%b", "%B"]:
            try:
                return datetime.strptime(f"{day} {month_str} {year}", f"%d {fmt} %Y").date()
            except ValueError:
                pass
    return None


def format_alert_info(title, category, diff, is_completed, target_url):
    if is_completed:
        return {
            "title": title,
            "category": category,
            "days_remaining": diff,
            "badge_class": "badge-success",
            "severity_label": "COMPLETED",
            "severity_level": "COMPLETED",
            "message": f"{title} has been completed.",
            "target_url": target_url,
            "is_completed": True
        }
    if diff < 0:
        return {
            "title": title,
            "category": category,
            "days_remaining": diff,
            "badge_class": "badge-dark",
            "severity_label": "⚫ OVERDUE",
            "severity_level": "OVERDUE",
            "message": f"Your {title} deadline has passed.",
            "target_url": target_url,
            "is_completed": False
        }
    elif diff == 0:
        return {
            "title": title,
            "category": category,
            "days_remaining": 0,
            "badge_class": "badge-critical",
            "severity_label": "🚨 CRITICAL",
            "severity_level": "CRITICAL",
            "message": f"Your {title} deadline is today.",
            "target_url": target_url,
            "is_completed": False
        }
    elif diff == 1:
        return {
            "title": title,
            "category": category,
            "days_remaining": 1,
            "badge_class": "badge-urgent",
            "severity_label": "🔴 URGENT",
            "severity_level": "URGENT",
            "message": f"Your {title} deadline is tomorrow.",
            "target_url": target_url,
            "is_completed": False
        }
    elif 2 <= diff <= 3:
        return {
            "title": title,
            "category": category,
            "days_remaining": diff,
            "badge_class": "badge-important",
            "severity_label": "🟠 IMPORTANT",
            "severity_level": "IMPORTANT",
            "message": f"Your {title} deadline is in {diff} days.",
            "target_url": target_url,
            "is_completed": False
        }
    elif 4 <= diff <= 7:
        return {
            "title": title,
            "category": category,
            "days_remaining": diff,
            "badge_class": "badge-reminder",
            "severity_label": "🟡 REMINDER",
            "severity_level": "REMINDER",
            "message": f"Your {title} deadline is in {diff} days.",
            "target_url": target_url,
            "is_completed": False
        }
    else:
        return {
            "title": title,
            "category": category,
            "days_remaining": diff,
            "badge_class": "badge-upcoming",
            "severity_label": "🟢 UPCOMING",
            "severity_level": "UPCOMING",
            "message": f"Your {title} deadline is in {diff} days.",
            "target_url": target_url,
            "is_completed": False
        }


def compute_student_alerts(conn, student_id):
    today = datetime.now().date()
    alerts = []

    # 1. Tests from test_scores
    tests = conn.execute("SELECT * FROM test_scores WHERE student_id = ?", (student_id,)).fetchall()
    for t in tests:
        if t["test_date"]:
            d_date = parse_date_string(t["test_date"])
            if d_date:
                diff = (d_date - today).days
                is_done = (t["status"] or "").lower() in ["completed", "done", "passed"]
                alert = format_alert_info(t["test_name"], "Test", diff, is_done, "/student/academics")
                if alert:
                    alerts.append(alert)

    # 2. Universities deadlines
    unis = conn.execute("SELECT * FROM universities WHERE student_id = ?", (student_id,)).fetchall()
    for u in unis:
        if u["deadline"]:
            d_date = parse_date_string(u["deadline"])
            if d_date:
                diff = (d_date - today).days
                is_done = (u["status"] or "").lower() in ["applied", "accepted", "submitted"]
                alert = format_alert_info(f"{u['university_name']} Application", "University", diff, is_done, "/student/universities")
                if alert:
                    alerts.append(alert)

    # 3. Deadlines table entries
    deadlines = conn.execute("SELECT * FROM deadlines WHERE student_id = ?", (student_id,)).fetchall()
    for d in deadlines:
        if d["due_date"]:
            d_date = parse_date_string(d["due_date"])
            if d_date:
                diff = (d_date - today).days
                is_done = (d["status"] or "").lower() in ["completed", "done"]
                alert = format_alert_info(d["action"], d["category"] or "Action", diff, is_done, "/student/deadlines")
                if alert:
                    alerts.append(alert)

    # 4. Essays deadlines
    essays = conn.execute("SELECT * FROM essays WHERE student_id = ?", (student_id,)).fetchall()
    for e in essays:
        if e["deadline"]:
            d_date = parse_date_string(e["deadline"])
            if d_date:
                diff = (d_date - today).days
                is_done = (e["draft_status"] or "").lower() in ["approved", "completed", "finalized"]
                alert = format_alert_info(f"Essay: {e['university'] or 'College'} Draft", "Essay", diff, is_done, "/student/essays")
                if alert:
                    alerts.append(alert)

    # 5. Pending prerequisites
    prereqs = conn.execute("""
        SELECT sp.*, u.university_name 
        FROM student_prerequisites sp
        JOIN universities u ON sp.university_id = u.id
        WHERE sp.student_id = ? AND sp.completed IS FALSE
    """, (student_id,)).fetchall()
    for p in prereqs:
        alerts.append({
            "title": f"Missing Prerequisite: {p['requirement_name']}",
            "category": "Prerequisite",
            "days_remaining": None,
            "badge_class": "badge-important",
            "severity_label": "🟠 MISSING PREREQUISITE",
            "severity_level": "IMPORTANT",
            "message": f"Incomplete requirement for {p['university_name']}: {p['requirement_name']}",
            "target_url": "/student/prerequisites",
            "is_completed": False
        })

    # Sort alerts by urgency
    severity_order = {"CRITICAL": 0, "URGENT": 1, "IMPORTANT": 2, "OVERDUE": 3, "REMINDER": 4, "UPCOMING": 5, "COMPLETED": 6}
    alerts.sort(key=lambda x: severity_order.get(x["severity_level"], 99))
    return alerts
