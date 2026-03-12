from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
DB_PATH = DATA_DIR / "tkhasosi_staging.db"

DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = "tkhasosi-dev-key"

DEGREE_TYPES = [
    "diploma",
    "bachelor",
    "higher_diploma",
    "master",
    "phd",
    "other",
]

PROGRAM_OPTION_TYPES = [
    ("major", "تخصص رئيسي"),
    ("minor", "تخصص فرعي"),
    ("integrated_minor", "تخصص فرعي مدمج"),
]

LANGUAGES = [
    "arabic",
    "english",
    "both",
    "other",
]

CURRENCIES = ["NIS", "JOD", "USD"]

UNIVERSITY_TYPES = [
    "public",
    "private",
    "government",
    "community",
    "technical",
    "other",
]

MAJOR_CATEGORIES = [
    ("Engineering", "الهندسة"),
    ("Medical & Health", "الطب والعلوم الصحية"),
    ("Information Technology", "تكنولوجيا المعلومات"),
    ("Business & Economics", "الأعمال والاقتصاد"),
    ("Arts & Humanities", "الآداب والعلوم الإنسانية"),
    ("Education", "التربية"),
    ("Science", "العلوم"),
    ("Law & Political Science", "القانون والعلوم السياسية"),
    ("Media & Communication", "الإعلام والاتصال"),
    ("Sports & Physical Education", "الرياضة والتربية الرياضية"),
]

TAWJIHI_STREAMS = [
    {"en": "All", "ar": "الكل"},
    {"en": "Scientific", "ar": "علمي"},
    {"en": "Literary", "ar": "الأدبي"},
    {"en": "Sharia", "ar": "الشرعي"},
    {"en": "Entrepreneurship and Business", "ar": "الريادة والأعمال"},
    {"en": "Agricultural", "ar": "الزراعي"},
    {"en": "Industrial", "ar": "الصناعي"},
    {"en": "Hotel and Home Economics", "ar": "الفندقي و الاقتصاد المنزلي"},
    {"en": "Information Technology (IT)", "ar": "تكنولوجيا المعلومات"},

]

PRESEEDED_UNIVERSITIES = [
    (
        "Birzeit University",
        "جامعة بيرزيت",
        "Birzeit, Ramallah",
        "بيرزيت، رام الله",
        "https://www.birzeit.edu",
        "public",
    ),
    (
        "An-Najah National University",
        "جامعة النجاح الوطنية",
        "Nablus",
        "نابلس",
        "https://www.najah.edu",
        "public",
    ),
    (
        "Bethlehem University",
        "جامعة بيت لحم",
        "Bethlehem",
        "بيت لحم",
        "https://www.bethlehem.edu",
        "private",
    ),
    (
        "Hebron University",
        "جامعة الخليل",
        "Hebron",
        "الخليل",
        "https://www.hebron.edu",
        "public",
    ),
    (
        "Palestine Polytechnic University",
        "جامعة بوليتكنك فلسطين",
        "Hebron",
        "الخليل",
        "https://www.ppu.edu",
        "public",
    ),
    (
        "Al-Quds University",
        "جامعة القدس",
        "Jerusalem / Abu Dis",
        "القدس / أبو ديس",
        "https://www.alquds.edu",
        "public",
    ),
    (
        "Arab American University",
        "الجامعة العربية الأمريكية",
        "Jenin / Ramallah",
        "جنين / رام الله",
        "https://www.aaup.edu",
        "private",
    ),
    (
        "Palestine Technical University - Kadoorie",
        "جامعة فلسطين التقنية - خضوري",
        "Tulkarm",
        "طولكرم",
        "https://www.ptuk.edu.ps",
        "public",
    ),
]


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize(text: str | None) -> str:
    return " ".join((text or "").strip().lower().split())


def parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None

def get_program_option_type_ar(value: str | None) -> str:
    mapping = {
        "major": "تخصص رئيسي",
        "minor": "تخصص فرعي",
        "integrated_minor": "تخصص فرعي مدمج",
    }
    return mapping.get((value or "").strip(), "")

def parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.create_function("normalize", 1, normalize)
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def ensure_column(db: sqlite3.Connection, table_name: str, column_name: str, column_def: str) -> None:
    existing = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_names = {row[1] for row in existing}
    if column_name not in existing_names:
        db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def init_db() -> None:
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS universities (
            university_id INTEGER PRIMARY KEY AUTOINCREMENT,
            university_name_en TEXT NOT NULL,
            university_name_ar TEXT NOT NULL,
            city_en TEXT,
            city_ar TEXT,
            official_website TEXT,
            description_en TEXT,
            description_ar TEXT,
            logo_path TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            university_type TEXT CHECK (university_type IN ('public', 'private', 'government', 'community', 'technical', 'other')),
            founded_year INTEGER,
            student_count INTEGER,
            global_ranking INTEGER,
            local_ranking INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS majors (
            major_id INTEGER PRIMARY KEY AUTOINCREMENT,
            university_id INTEGER NOT NULL,
            faculty_name_en TEXT,
            faculty_name_ar TEXT,
            major_name_en TEXT NOT NULL,
            major_name_ar TEXT NOT NULL,
            degree_type TEXT CHECK (degree_type IN ('diploma', 'bachelor', 'higher_diploma', 'master', 'phd', 'other')),
            program_option_type TEXT NOT NULL DEFAULT 'major' CHECK (program_option_type IN ('major', 'minor', 'integrated_minor')),
            program_option_type_ar TEXT,
            duration_years REAL,
            total_hour_credits REAL,
            language_of_study TEXT CHECK (language_of_study IN ('arabic', 'english', 'both', 'other')),
            study_plan_link TEXT,
            major_description_en TEXT,
            major_description_ar TEXT,
            career_opportunities_en TEXT,
            career_opportunities_ar TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (university_id) REFERENCES universities(university_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS major_cutoffs (
        cutoff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        major_id INTEGER NOT NULL,
        tawjihi_stream_en TEXT,
        tawjihi_stream_ar TEXT,
        cutoff_average REAL CHECK (cutoff_average >= 0 AND cutoff_average <= 100),
        regular_credit_hour_price REAL CHECK (regular_credit_hour_price >= 0),
        parallel_admission_cutoff REAL CHECK (parallel_admission_cutoff >= 0 AND parallel_admission_cutoff <= 100),
        parallel_credit_hour_price REAL CHECK (parallel_credit_hour_price >= 0),
        currency TEXT NOT NULL DEFAULT 'NIS' CHECK (currency IN ('NIS', 'USD', 'JOD')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (major_id) REFERENCES majors(major_id) ON DELETE CASCADE
    );
        CREATE TABLE IF NOT EXISTS major_categories (
            major_category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            major_id INTEGER NOT NULL,
            category_en TEXT NOT NULL,
            category_ar TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (major_id) REFERENCES majors(major_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS roles (
            role_id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS admin_users (
            admin_user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            phone TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS admin_user_roles (
            admin_user_role_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_user_id) REFERENCES admin_users(admin_user_id) ON DELETE CASCADE,
            FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ads (
            ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_en TEXT NOT NULL,
            title_ar TEXT NOT NULL,
            description_en TEXT,
            description_ar TEXT,
            image_path TEXT,
            target_url TEXT,
            advertiser_name TEXT,
            ad_type TEXT CHECK (ad_type IN ('image', 'banner', 'popup', 'sponsored_card')),
            placement TEXT,
            priority INTEGER DEFAULT 0,
            start_date TEXT,
            end_date TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by_admin_user_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(admin_user_id) ON DELETE SET NULL
        );
        """
    )

    ensure_column(db, "universities", "founded_year", "INTEGER")
    ensure_column(db, "universities", "student_count", "INTEGER")
    ensure_column(db, "universities", "global_ranking", "INTEGER")
    ensure_column(db, "universities", "local_ranking", "INTEGER")
    ensure_column(db, "universities", "updated_at", "TEXT")

    ensure_column(db, "majors", "total_hour_credits", "REAL")
    ensure_column(db, "majors", "study_plan_link", "TEXT")
    ensure_column(db, "majors", "program_option_type", "TEXT NOT NULL DEFAULT 'major'")
    ensure_column(db, "majors", "program_option_type_ar", "TEXT")
    ensure_column(db, "majors", "updated_at", "TEXT")

    ensure_column(db, "major_cutoffs", "regular_credit_hour_price", "REAL")
    ensure_column(db, "major_cutoffs", "first_semester_year1_tuition", "REAL")
    ensure_column(db, "major_cutoffs", "parallel_admission_cutoff", "REAL")
    ensure_column(db, "major_cutoffs", "parallel_credit_hour_price", "REAL")
    ensure_column(db, "major_cutoffs", "currency", "TEXT")
    ensure_column(db, "major_cutoffs", "updated_at", "TEXT")

    db.execute("""
        UPDATE majors
        SET program_option_type_ar = CASE program_option_type
            WHEN 'major' THEN 'تخصص رئيسي'
            WHEN 'minor' THEN 'تخصص فرعي'
            WHEN 'integrated_minor' THEN 'تخصص فرعي مدمج'
            ELSE program_option_type_ar
        END
        WHERE program_option_type_ar IS NULL OR program_option_type_ar = ''
    """)

    count = cur.execute("SELECT COUNT(*) FROM universities").fetchone()[0]
    if count == 0:
        now = now_iso()
        cur.executemany(
            """
            INSERT INTO universities (
                university_name_en, university_name_ar, city_en, city_ar,
                official_website, university_type, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(u[0], u[1], u[2], u[3], u[4], u[5], now, now) for u in PRESEEDED_UNIVERSITIES],
        )

    role_count = cur.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
    if role_count == 0:
        cur.executemany(
            "INSERT INTO roles (role_name) VALUES (?)",
            [
                ("super_admin",),
                ("admin",),
                ("data_entry",),
                ("editor",),
                ("advertiser",),
                ("analyst",),
            ],
        )

    db.commit()
    db.close()

def get_universities() -> list[sqlite3.Row]:
    return get_db().execute(
        "SELECT * FROM universities ORDER BY university_name_en ASC"
    ).fetchall()


def get_selected_university() -> sqlite3.Row | None:
    university_id = session.get("current_university_id")
    if not university_id:
        return None
    return get_db().execute(
        "SELECT * FROM universities WHERE university_id = ?",
        (university_id,),
    ).fetchone()


def get_existing_faculties(university_id: int | None) -> list[sqlite3.Row]:
    if not university_id:
        return []
    return get_db().execute(
        """
        SELECT DISTINCT faculty_name_en, faculty_name_ar
        FROM majors
        WHERE university_id = ? AND COALESCE(faculty_name_en, '') != ''
        ORDER BY faculty_name_en ASC
        """,
        (university_id,),
    ).fetchall()


def get_major_categories(major_id: int) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT * FROM major_categories
        WHERE major_id = ?
        ORDER BY major_category_id
        """,
        (major_id,),
    ).fetchall()


def get_major_category_keys(major_id: int) -> set[str]:
    rows = get_db().execute(
        "SELECT category_en FROM major_categories WHERE major_id = ?",
        (major_id,),
    ).fetchall()
    return {row[0] for row in rows}


def collect_selected_categories(form: Any) -> list[dict[str, str]]:
    selected = set(form.getlist("major_categories[]"))
    rows: list[dict[str, str]] = []

    for en, ar in MAJOR_CATEGORIES:
        if en in selected:
            rows.append({"category_en": en, "category_ar": ar})

    return rows


def collect_cutoff_rows(form: Any) -> list[dict[str, Any]]:
    streams_en = form.getlist("cutoff_stream_en[]")
    streams_ar = form.getlist("cutoff_stream_ar[]")
    regular_cutoff = form.getlist("cutoff_average[]")
    regular_price = form.getlist("regular_credit_hour_price[]")
    first_semester_tuition = form.getlist("first_semester_year1_tuition[]")
    parallel_cutoff = form.getlist("parallel_admission_cutoff[]")
    parallel_price = form.getlist("parallel_credit_hour_price[]")
    currencies = form.getlist("cutoff_currency[]")

    rows: list[dict[str, Any]] = []
    total = max(
        len(streams_en),
        len(streams_ar),
        len(regular_cutoff),
        len(regular_price),
        len(first_semester_tuition),
        len(parallel_cutoff),
        len(parallel_price),
        len(currencies),
    )

    for i in range(total):
        stream_en = (streams_en[i] if i < len(streams_en) else "").strip()
        stream_ar = (streams_ar[i] if i < len(streams_ar) else "").strip()
        cutoff_average = parse_float(regular_cutoff[i] if i < len(regular_cutoff) else "")
        regular_credit_hour_price = parse_float(regular_price[i] if i < len(regular_price) else "")
        first_semester_year1_tuition = parse_float(first_semester_tuition[i] if i < len(first_semester_tuition) else "")
        parallel_admission_cutoff = parse_float(parallel_cutoff[i] if i < len(parallel_cutoff) else "")
        parallel_credit_hour_price = parse_float(parallel_price[i] if i < len(parallel_price) else "")
        currency = (currencies[i] if i < len(currencies) else "").strip()

        if (
            not stream_en
            and not stream_ar
            and cutoff_average is None
            and regular_credit_hour_price is None
            and first_semester_year1_tuition is None
            and parallel_admission_cutoff is None
            and parallel_credit_hour_price is None
            and not currency
        ):
            continue

        rows.append(
            {
                "tawjihi_stream_en": stream_en,
                "tawjihi_stream_ar": stream_ar,
                "cutoff_average": cutoff_average,
                "regular_credit_hour_price": regular_credit_hour_price,
                "first_semester_year1_tuition": first_semester_year1_tuition,
                "parallel_admission_cutoff": parallel_admission_cutoff,
                "parallel_credit_hour_price": parallel_credit_hour_price,
                "currency": currency,
            }
        )

    return rows

@app.route("/")
def index() -> str:
    db = get_db()
    q = (request.args.get("q") or "").strip()
    selected_university = get_selected_university()

    if q:
        majors = db.execute(
            """
            SELECT m.*, u.university_name_en, u.university_name_ar,
                   GROUP_CONCAT(mc.category_en, ', ') AS category_names_en,
                   GROUP_CONCAT(mc.category_ar, '، ') AS category_names_ar
            FROM majors m
            JOIN universities u ON u.university_id = m.university_id
            LEFT JOIN major_categories mc ON mc.major_id = m.major_id
            WHERE m.major_name_en LIKE ?
               OR m.major_name_ar LIKE ?
               OR m.faculty_name_en LIKE ?
               OR m.faculty_name_ar LIKE ?
               OR u.university_name_en LIKE ?
               OR u.university_name_ar LIKE ?
            GROUP BY m.major_id
            ORDER BY m.created_at DESC
            """,
            tuple([f"%{q}%"] * 6),
        ).fetchall()
    elif selected_university:
        majors = db.execute(
            """
            SELECT m.*, u.university_name_en, u.university_name_ar,
                   GROUP_CONCAT(mc.category_en, ', ') AS category_names_en,
                   GROUP_CONCAT(mc.category_ar, '، ') AS category_names_ar
            FROM majors m
            JOIN universities u ON u.university_id = m.university_id
            LEFT JOIN major_categories mc ON mc.major_id = m.major_id
            WHERE m.university_id = ?
            GROUP BY m.major_id
            ORDER BY m.created_at DESC
            LIMIT 50
            """,
            (selected_university["university_id"],),
        ).fetchall()
    else:
        majors = db.execute(
            """
            SELECT m.*, u.university_name_en, u.university_name_ar,
                   GROUP_CONCAT(mc.category_en, ', ') AS category_names_en,
                   GROUP_CONCAT(mc.category_ar, '، ') AS category_names_ar
            FROM majors m
            JOIN universities u ON u.university_id = m.university_id
            LEFT JOIN major_categories mc ON mc.major_id = m.major_id
            GROUP BY m.major_id
            ORDER BY m.created_at DESC
            LIMIT 50
            """
        ).fetchall()

    recent_majors = db.execute(
        """
        SELECT m.major_id, m.major_name_en, m.major_name_ar, m.faculty_name_en,
               u.university_name_en, u.university_name_ar, m.created_at,
               GROUP_CONCAT(mc.category_en, ', ') AS category_names_en,
               GROUP_CONCAT(mc.category_ar, '، ') AS category_names_ar
        FROM majors m
        JOIN universities u ON u.university_id = m.university_id
        LEFT JOIN major_categories mc ON mc.major_id = m.major_id
        GROUP BY m.major_id
        ORDER BY m.created_at DESC
        LIMIT 8
        """
    ).fetchall()

    return render_template(
        "index.html",
        universities=get_universities(),
        selected_university=selected_university,
        majors=majors,
        recent_majors=recent_majors,
        query=q,
    )


@app.post("/set-current-university")
def set_current_university() -> Any:
    university_id = request.form.get("university_id", type=int)
    if university_id:
        session["current_university_id"] = university_id
    else:
        session.pop("current_university_id", None)
    return redirect(url_for("index"))

@app.route("/university/new", methods=["GET", "POST"])
def university_new() -> Any:
    if request.method == "POST":
        form = request.form
        db = get_db()
        now = now_iso()
        db.execute(
            """
            INSERT INTO universities (
                university_name_en, university_name_ar, city_en, city_ar,
                official_website, description_en, description_ar, logo_path,
                contact_email, contact_phone,
                university_type, founded_year, student_count, global_ranking, local_ranking, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                form.get("university_name_en", "").strip(),
                form.get("university_name_ar", "").strip(),
                form.get("city_en", "").strip(),
                form.get("city_ar", "").strip(),
                form.get("official_website", "").strip(),
                form.get("description_en", "").strip(),
                form.get("description_ar", "").strip(),
                form.get("logo_path", "").strip(),
                form.get("contact_email", "").strip(),
                form.get("contact_phone", "").strip(),
                form.get("university_type", "").strip(),
                parse_int(form.get("founded_year")),
                parse_int(form.get("student_count")),
                parse_int(form.get("global_ranking")),
                parse_int(form.get("local_ranking")),
                now,
                now,
            ),
        )
        db.commit()
        new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        session["current_university_id"] = new_id
        flash("University created.")
        return redirect(url_for("major_new"))

    return render_template(
        "university_form.html",
        university=None,
        university_types=UNIVERSITY_TYPES,
    )
@app.route("/university/<int:university_id>/edit", methods=["GET", "POST"])
def university_edit(university_id: int) -> Any:
    db = get_db()
    university = db.execute(
        "SELECT * FROM universities WHERE university_id = ?",
        (university_id,),
    ).fetchone()

    if not university:
        flash("University not found.")
        return redirect(url_for("index"))

    if request.method == "POST":
        form = request.form
        db.execute(
            """
            UPDATE universities SET
                university_name_en = ?,
                university_name_ar = ?,
                city_en = ?,
                city_ar = ?,
                official_website = ?,
                description_en = ?,
                description_ar = ?,
                logo_path = ?,
                contact_email = ?,
                contact_phone = ?,
                university_type = ?,
                founded_year = ?,
                student_count = ?,
                global_ranking = ?,
                local_ranking = ?,
                updated_at = ?
            WHERE university_id = ?
            """,
            (
                form.get("university_name_en", "").strip(),
                form.get("university_name_ar", "").strip(),
                form.get("city_en", "").strip(),
                form.get("city_ar", "").strip(),
                form.get("official_website", "").strip(),
                form.get("description_en", "").strip(),
                form.get("description_ar", "").strip(),
                form.get("logo_path", "").strip(),
                form.get("contact_email", "").strip(),
                form.get("contact_phone", "").strip(),
                form.get("university_type", "").strip(),
                parse_int(form.get("founded_year")),
                parse_int(form.get("student_count")),
                parse_int(form.get("global_ranking")),
                parse_int(form.get("local_ranking")),
                now_iso(),
                university_id,
            ),
        )
        db.commit()
        session["current_university_id"] = university_id
        flash("University updated.")
        return redirect(url_for("index"))

    return render_template(
        "university_form.html",
        university=university,
        university_types=UNIVERSITY_TYPES,
    )
@app.route("/major/new", methods=["GET", "POST"])
def major_new() -> Any:
    db = get_db()
    universities = get_universities()
    selected_university = get_selected_university()
    sticky = session.get("major_defaults", {})

    if request.method == "POST":
        form = request.form
        university_id = form.get("university_id", type=int)

        if university_id:
            session["current_university_id"] = university_id

        major_name_en = form.get("major_name_en", "").strip()
        major_name_ar = form.get("major_name_ar", "").strip()
        faculty_name_en = form.get("faculty_name_en", "").strip()
        faculty_name_ar = form.get("faculty_name_ar", "").strip()
        program_option_type = form.get("program_option_type", "major").strip()
        program_option_type_ar = get_program_option_type_ar(program_option_type)

        existing = db.execute(
            """
            SELECT m.major_id, m.major_name_en, m.major_name_ar
            FROM majors m
            WHERE m.university_id = ?
              AND normalize(COALESCE(m.faculty_name_en, '')) = normalize(?)
              AND (
                    normalize(m.major_name_en) = normalize(?)
                 OR normalize(m.major_name_ar) = normalize(?)
              )
            """,
            (university_id, faculty_name_en, major_name_en, major_name_ar),
        ).fetchall()

        if existing:
            flash("Warning: a similar major already exists in this university and faculty.", "warning")

        now = now_iso()
        db.execute(
            """
            INSERT INTO majors (
                university_id, faculty_name_en, faculty_name_ar,
                major_name_en, major_name_ar, degree_type,
                program_option_type, program_option_type_ar,
                duration_years, language_of_study, total_hour_credits, study_plan_link,
                major_description_en, major_description_ar,
                career_opportunities_en, career_opportunities_ar, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                university_id,
                faculty_name_en,
                faculty_name_ar,
                major_name_en,
                major_name_ar,
                form.get("degree_type", "").strip(),
                program_option_type,
                program_option_type_ar,
                parse_float(form.get("duration_years")),
                form.get("language_of_study", "").strip(),
                parse_float(form.get("total_hour_credits")),
                form.get("study_plan_link", "").strip(),
                form.get("major_description_en", "").strip(),
                form.get("major_description_ar", "").strip(),
                form.get("career_opportunities_en", "").strip(),
                form.get("career_opportunities_ar", "").strip(),
                now,
                now,
            ),
        )

        major_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        for category in collect_selected_categories(form):
            db.execute(
                """
                INSERT INTO major_categories (
                    major_id, category_en, category_ar, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    major_id,
                    category["category_en"],
                    category["category_ar"],
                    now_iso(),
                ),
            )

        for row in collect_cutoff_rows(form):
            db.execute(
                """
                INSERT INTO major_cutoffs (major_id, tawjihi_stream_en, tawjihi_stream_ar,
                                           cutoff_average, regular_credit_hour_price, first_semester_year1_tuition,
                                           parallel_admission_cutoff, parallel_credit_hour_price,
                                           currency, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    major_id,
                    row["tawjihi_stream_en"],
                    row["tawjihi_stream_ar"],
                    row["cutoff_average"],
                    row["regular_credit_hour_price"],
                    row["first_semester_year1_tuition"],
                    row["parallel_admission_cutoff"],
                    row["parallel_credit_hour_price"],
                    row["currency"],
                    now_iso(),
                    now_iso(),
                ),
            )

        db.commit()

        session["major_defaults"] = {
            "faculty_name_en": faculty_name_en,
            "faculty_name_ar": faculty_name_ar,
            "degree_type": form.get("degree_type", "").strip(),
            "program_option_type": program_option_type,
            "duration_years": form.get("duration_years", "").strip(),
            "language_of_study": form.get("language_of_study", "").strip(),
            "study_plan_link": form.get("study_plan_link", "").strip(),
            "total_hour_credits": form.get("total_hour_credits", "").strip(),
            "regular_credit_hour_price": form.getlist("regular_credit_hour_price[]")[0] if form.getlist(
                "regular_credit_hour_price[]") else "",
            "first_semester_year1_tuition": form.getlist("first_semester_year1_tuition[]")[0] if form.getlist(
                "first_semester_year1_tuition[]") else "",
            "parallel_credit_hour_price": form.getlist("parallel_credit_hour_price[]")[0] if form.getlist(
                "parallel_credit_hour_price[]") else "",
            "cutoff_currency": form.getlist("cutoff_currency[]")[0] if form.getlist("cutoff_currency[]") else "JOD",
            "major_categories": form.getlist("major_categories[]"),
        }

        flash("Major created.")
        return redirect(url_for("major_edit", major_id=major_id))

    default_cutoffs = [
        {
            "tawjihi_stream_en": "All",
            "tawjihi_stream_ar": "الكل",
            "cutoff_average": "",
            "regular_credit_hour_price": sticky.get("regular_credit_hour_price", ""),
            "first_semester_year1_tuition": sticky.get("first_semester_year1_tuition", ""),
            "parallel_admission_cutoff": "",
            "parallel_credit_hour_price": sticky.get("parallel_credit_hour_price", ""),
            "currency": sticky.get("cutoff_currency", "JOD"),
        }
    ]

    return render_template(
        "major_form.html",
        major=None,
        cutoffs=default_cutoffs,
        universities=universities,
        selected_university=selected_university,
        faculties=get_existing_faculties(selected_university["university_id"] if selected_university else None),
        degree_types=DEGREE_TYPES,
        program_option_types=PROGRAM_OPTION_TYPES,
        languages=LANGUAGES,
        currencies=CURRENCIES,
        streams=TAWJIHI_STREAMS,
        sticky=sticky,
        major_categories=MAJOR_CATEGORIES,
        selected_categories=set(sticky.get("major_categories", [])),
    )

@app.route("/major/<int:major_id>/edit", methods=["GET", "POST"])
def major_edit(major_id: int) -> Any:
    db = get_db()
    major = db.execute("SELECT * FROM majors WHERE major_id = ?", (major_id,)).fetchone()

    if not major:
        flash("Major not found.")
        return redirect(url_for("index"))

    if request.method == "POST":
        form = request.form
        university_id = form.get("university_id", type=int)

        if university_id:
            session["current_university_id"] = university_id

        program_option_type = form.get("program_option_type", "major").strip()
        program_option_type_ar = get_program_option_type_ar(program_option_type)

        db.execute(
            """
            UPDATE majors SET
                university_id = ?,
                faculty_name_en = ?,
                faculty_name_ar = ?,
                major_name_en = ?,
                major_name_ar = ?,
                degree_type = ?,
                program_option_type = ?,
                program_option_type_ar = ?,
                duration_years = ?,
                language_of_study = ?,
                total_hour_credits = ?,
                study_plan_link = ?,
                major_description_en = ?,
                major_description_ar = ?,
                career_opportunities_en = ?,
                career_opportunities_ar = ?,
                updated_at = ?
            WHERE major_id = ?
            """,
            (
                university_id,
                form.get("faculty_name_en", "").strip(),
                form.get("faculty_name_ar", "").strip(),
                form.get("major_name_en", "").strip(),
                form.get("major_name_ar", "").strip(),
                form.get("degree_type", "").strip(),
                program_option_type,
                program_option_type_ar,
                parse_float(form.get("duration_years")),
                form.get("language_of_study", "").strip(),
                parse_float(form.get("total_hour_credits")),
                form.get("study_plan_link", "").strip(),
                form.get("major_description_en", "").strip(),
                form.get("major_description_ar", "").strip(),
                form.get("career_opportunities_en", "").strip(),
                form.get("career_opportunities_ar", "").strip(),
                now_iso(),
                major_id,
            ),
        )

        db.execute("DELETE FROM major_categories WHERE major_id = ?", (major_id,))

        for category in collect_selected_categories(form):
            db.execute(
                """
                INSERT INTO major_categories (
                    major_id, category_en, category_ar, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    major_id,
                    category["category_en"],
                    category["category_ar"],
                    now_iso(),
                ),
            )

        db.execute("DELETE FROM major_cutoffs WHERE major_id = ?", (major_id,))

        for row in collect_cutoff_rows(form):
            db.execute(
                """
                INSERT INTO major_cutoffs (major_id, tawjihi_stream_en, tawjihi_stream_ar,
                                           cutoff_average, regular_credit_hour_price, first_semester_year1_tuition,
                                           parallel_admission_cutoff, parallel_credit_hour_price,
                                           currency, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    major_id,
                    row["tawjihi_stream_en"],
                    row["tawjihi_stream_ar"],
                    row["cutoff_average"],
                    row["regular_credit_hour_price"],
                    row["first_semester_year1_tuition"],
                    row["parallel_admission_cutoff"],
                    row["parallel_credit_hour_price"],
                    row["currency"],
                    now_iso(),
                    now_iso(),
                ),
            )

        db.commit()
        flash("Major updated.")
        return redirect(url_for("major_edit", major_id=major_id))

    cutoffs = db.execute(
        """
        SELECT * FROM major_cutoffs
        WHERE major_id = ?
        ORDER BY cutoff_id
        """,
        (major_id,),
    ).fetchall()

    if not cutoffs:
        cutoffs = [
            {
                "tawjihi_stream_en": "All",
                "tawjihi_stream_ar": "الكل",
                "cutoff_average": "",
                "regular_credit_hour_price": "",
                "first_semester_year1_tuition": "",
                "parallel_admission_cutoff": "",
                "parallel_credit_hour_price": "",
                "currency": "JOD",
            }
        ]

    return render_template(
        "major_form.html",
        major=major,
        cutoffs=cutoffs,
        universities=get_universities(),
        selected_university=db.execute(
            "SELECT * FROM universities WHERE university_id = ?",
            (major["university_id"],),
        ).fetchone(),
        faculties=get_existing_faculties(major["university_id"]),
        degree_types=DEGREE_TYPES,
        program_option_types=PROGRAM_OPTION_TYPES,
        languages=LANGUAGES,
        currencies=CURRENCIES,
        streams=TAWJIHI_STREAMS,
        sticky=session.get("major_defaults", {}),
        major_categories=MAJOR_CATEGORIES,
        selected_categories=get_major_category_keys(major_id),
    )


@app.route("/export/json")
def export_json() -> Any:
    db = get_db()
    universities = [
        dict(row)
        for row in db.execute("SELECT * FROM universities ORDER BY university_id").fetchall()
    ]

    majors = []
    for row in db.execute("SELECT * FROM majors ORDER BY major_id").fetchall():
        major = dict(row)
        categories = [
            dict(c)
            for c in db.execute(
                "SELECT * FROM major_categories WHERE major_id = ? ORDER BY major_category_id",
                (row["major_id"],),
            ).fetchall()
        ]
        cutoffs = [
            dict(c)
            for c in db.execute(
                "SELECT * FROM major_cutoffs WHERE major_id = ? ORDER BY cutoff_id",
                (row["major_id"],),
            ).fetchall()
        ]
        major["categories"] = categories
        major["cutoffs"] = cutoffs
        majors.append(major)

    payload = {"universities": universities, "majors": majors}
    path = EXPORT_DIR / "tkhasosi_export.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return send_file(path, as_attachment=True)


@app.route("/export/csv")
def export_csv() -> Any:
    db = get_db()

    universities = [
        dict(row)
        for row in db.execute("SELECT * FROM universities ORDER BY university_id").fetchall()
    ]
    majors = [
        dict(row)
        for row in db.execute("SELECT * FROM majors ORDER BY major_id").fetchall()
    ]
    categories = [
        dict(row)
        for row in db.execute("SELECT * FROM major_categories ORDER BY major_category_id").fetchall()
    ]
    cutoffs = [
        dict(row)
        for row in db.execute("SELECT * FROM major_cutoffs ORDER BY cutoff_id").fetchall()
    ]

    def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    u_path = EXPORT_DIR / "universities.csv"
    m_path = EXPORT_DIR / "majors.csv"
    cat_path = EXPORT_DIR / "major_categories.csv"
    c_path = EXPORT_DIR / "major_cutoffs.csv"

    write_csv(u_path, universities)
    write_csv(m_path, majors)
    write_csv(cat_path, categories)
    write_csv(c_path, cutoffs)

    return send_file(m_path, as_attachment=True)


@app.route("/export/sql")
def export_sql() -> Any:
    db = get_db()
    path = EXPORT_DIR / "tkhasosi_insert_export.sql"
    lines: list[str] = []

    for table in ("universities", "majors", "major_categories", "major_cutoffs"):
        for row in db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall():
            cols = row.keys()
            vals = []
            for c in cols:
                v = row[c]
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                else:
                    vals.append("'" + str(v).replace("'", "''") + "'")
            lines.append(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(vals)});"
            )

    path.write_text("\n".join(lines), encoding="utf-8")
    return send_file(path, as_attachment=True)


@app.context_processor
def inject_globals() -> dict[str, Any]:
    return {
        "current_university": get_selected_university(),
        "current_year": datetime.now().year,
    }


init_db()

if __name__ == "__main__":
    app.run(debug=True)