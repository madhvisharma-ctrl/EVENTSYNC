"""
EventSync Demo Data Seeder

Creates demo data for the hackathon:

- Departments
- Admin
- Teachers
- Subjects
- Academic lectures
- Events
- Event coordinators
- Event ↔ lecture mappings

IMPORTANT:
Student accounts are NOT seeded here.

Students create their own accounts through the registration page.
"""

from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from database.db import get_connection


# ================================================================
# DEMO CREDENTIALS
# ================================================================

ADMIN_EMAIL = "admin@eventsync.demo"
ADMIN_PASSWORD = "EventSync@123"

TEACHER_PASSWORD = "EventSync@123"

TEACHERS = [
    {
        "name": "Neha Kapoor",
        "email": "neha.kapoor@eventsync.demo",
        "department": "CSE",
    },
    {
        "name": "Amit Sharma",
        "email": "amit.sharma@eventsync.demo",
        "department": "CSE",
    },
    {
        "name": "Priya Mehta",
        "email": "priya.mehta@eventsync.demo",
        "department": "ECE",
    },
]


# ================================================================
# DEPARTMENTS
# ================================================================

DEPARTMENTS = [
    ("CSE", "Computer Science and Engineering"),
    ("ECE", "Electronics and Communication Engineering"),
    ("ME", "Mechanical Engineering"),
    ("CE", "Civil Engineering"),
    ("EE", "Electrical Engineering"),
    ("IT", "Information Technology"),
    ("BBA", "Bachelor of Business Administration"),
    ("BCA", "Bachelor of Computer Applications"),
    ("OTHER", "Other"),
]


# ================================================================
# SUBJECTS
# ================================================================

SUBJECTS = [
    (
        "CS301",
        "Data Structures and Algorithms",
        "CSE",
        3,
        4,
    ),
    (
        "CS302",
        "Object Oriented Programming",
        "CSE",
        3,
        4,
    ),
    (
        "CS303",
        "Artificial Intelligence",
        "CSE",
        6,
        4,
    ),
    (
        "CS304",
        "Database Management Systems",
        "CSE",
        4,
        4,
    ),
    (
        "EC301",
        "Digital Electronics",
        "ECE",
        3,
        4,
    ),
]


# ================================================================
# EVENT DEFINITIONS
# ================================================================

EVENTS = [
    {
        "name": "TechNova 2026",
        "category": "Technical",
        "type": "Hackathon",
        "days_from_today": 2,
        "start": "09:00",
        "end": "17:00",
        "venue": "Innovation Lab",
        "description": (
            "A technical hackathon where students build innovative "
            "technology solutions for real-world problems."
        ),
        "created_by": "admin@eventsync.demo",
        "main_coordinator": "neha.kapoor@eventsync.demo",
        "mapped_subject": "CS301",
    },
    {
        "name": "CodeSprint Challenge",
        "category": "Competitions",
        "type": "Coding Competition",
        "days_from_today": 4,
        "start": "10:00",
        "end": "15:00",
        "venue": "Computer Lab 1",
        "description": (
            "Competitive programming challenge covering algorithms, "
            "problem solving and coding skills."
        ),
        "created_by": "admin@eventsync.demo",
        "main_coordinator": "amit.sharma@eventsync.demo",
        "mapped_subject": "CS302",
    },
    {
        "name": "AI & Future Tech Summit",
        "category": "Research & Innovation",
        "type": "AI-ML Workshop",
        "days_from_today": 6,
        "start": "10:00",
        "end": "16:00",
        "venue": "Seminar Hall",
        "description": (
            "Research and innovation summit focused on artificial "
            "intelligence, machine learning and emerging technologies."
        ),
        "created_by": "admin@eventsync.demo",
        "main_coordinator": "priya.mehta@eventsync.demo",
        "mapped_subject": "CS303",
    },
    {
        "name": "Annual Cultural Fest",
        "category": "College Fest",
        "type": "Annual Fest",
        "days_from_today": 8,
        "start": "11:00",
        "end": "20:00",
        "venue": "Main Auditorium",
        "description": (
            "Annual college cultural celebration featuring music, "
            "dance, drama and creative competitions."
        ),
        "created_by": "admin@eventsync.demo",
        "main_coordinator": "neha.kapoor@eventsync.demo",
        "mapped_subject": "CS304",
    },
    {
        "name": "Career Guidance Session",
        "category": "Placement & Career",
        "type": "Career Guidance",
        "days_from_today": 10,
        "start": "11:00",
        "end": "14:00",
        "venue": "Conference Hall",
        "description": (
            "Career guidance session covering placements, internships, "
            "resume preparation and interview readiness."
        ),
        "created_by": "admin@eventsync.demo",
        "main_coordinator": "amit.sharma@eventsync.demo",
        "mapped_subject": "CS304",
    },
    {
        "name": "Inter-College Sports Meet",
        "category": "Sports",
        "type": "Sports Meet",
        "days_from_today": 12,
        "start": "08:00",
        "end": "18:00",
        "venue": "College Sports Ground",
        "description": (
            "Inter-college sports event featuring athletics, cricket, "
            "football and indoor games."
        ),
        "created_by": "admin@eventsync.demo",
        "main_coordinator": "priya.mehta@eventsync.demo",
        "mapped_subject": "EC301",
    },
]


# ================================================================
# HELPERS
# ================================================================

def get_department_id(connection, code):
    row = connection.execute(
        """
        SELECT id
        FROM departments
        WHERE code = ?
        """,
        (code,),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f"Department '{code}' was not found."
        )

    return row["id"]


def get_user_id(connection, email):
    row = connection.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f"User '{email}' was not found."
        )

    return row["id"]


def get_subject_id(connection, subject_code):
    row = connection.execute(
        """
        SELECT id
        FROM subjects
        WHERE subject_code = ?
        """,
        (subject_code,),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f"Subject '{subject_code}' was not found."
        )

    return row["id"]


# ================================================================
# DEPARTMENT SEEDING
# ================================================================

def seed_departments(connection):
    for code, name in DEPARTMENTS:
        connection.execute(
            """
            INSERT OR IGNORE INTO departments (
                code,
                name
            )
            VALUES (?, ?)
            """,
            (code, name),
        )


# ================================================================
# ADMIN SEEDING
# ================================================================

def seed_admin(connection):
    department_id = get_department_id(
        connection,
        "OTHER",
    )

    connection.execute(
        """
        INSERT INTO users (
            name,
            email,
            password_hash,
            role,
            department_id,
            is_active
        )
        VALUES (?, ?, ?, 'admin', ?, 1)

        ON CONFLICT(email)
        DO UPDATE SET
            name = excluded.name,
            password_hash = excluded.password_hash,
            role = 'admin',
            department_id = excluded.department_id,
            is_active = 1
        """,
        (
            "EventSync Administrator",
            ADMIN_EMAIL,
            generate_password_hash(ADMIN_PASSWORD),
            department_id,
        ),
    )


# ================================================================
# TEACHER SEEDING
# ================================================================

def seed_teachers(connection):
    for teacher in TEACHERS:

        department_id = get_department_id(
            connection,
            teacher["department"],
        )

        connection.execute(
            """
            INSERT INTO users (
                name,
                email,
                password_hash,
                role,
                department_id,
                is_active
            )
            VALUES (?, ?, ?, 'teacher', ?, 1)

            ON CONFLICT(email)
            DO UPDATE SET
                name = excluded.name,
                password_hash = excluded.password_hash,
                role = 'teacher',
                department_id = excluded.department_id,
                is_active = 1
            """,
            (
                teacher["name"],
                teacher["email"],
                generate_password_hash(TEACHER_PASSWORD),
                department_id,
            ),
        )


# ================================================================
# SUBJECT SEEDING
# ================================================================

def seed_subjects(connection):
    for (
        subject_code,
        subject_name,
        department_code,
        semester,
        credits,
    ) in SUBJECTS:

        department_id = get_department_id(
            connection,
            department_code,
        )

        connection.execute(
            """
            INSERT INTO subjects (
                subject_code,
                subject_name,
                department_id,
                semester,
                credits,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, 1)

            ON CONFLICT(subject_code)
            DO UPDATE SET
                subject_name = excluded.subject_name,
                department_id = excluded.department_id,
                semester = excluded.semester,
                credits = excluded.credits,
                is_active = 1
            """,
            (
                subject_code,
                subject_name,
                department_id,
                semester,
                credits,
            ),
        )


# ================================================================
# LECTURE SEEDING
# ================================================================

def seed_lectures(connection):
    today = date.today()

    lecture_data = [
        {
            "teacher": "neha.kapoor@eventsync.demo",
            "subject": "CS301",
            "department": "CSE",
            "semester": 3,
            "section": "A",
            "date": today,
            "start": "09:00",
            "end": "10:00",
            "room": "CSE-201",
        },
        {
            "teacher": "amit.sharma@eventsync.demo",
            "subject": "CS302",
            "department": "CSE",
            "semester": 3,
            "section": "A",
            "date": today,
            "start": "10:00",
            "end": "11:00",
            "room": "CSE-202",
        },
        {
            "teacher": "neha.kapoor@eventsync.demo",
            "subject": "CS304",
            "department": "CSE",
            "semester": 4,
            "section": "A",
            "date": today + timedelta(days=1),
            "start": "09:00",
            "end": "10:00",
            "room": "CSE-203",
        },
        {
            "teacher": "amit.sharma@eventsync.demo",
            "subject": "CS303",
            "department": "CSE",
            "semester": 6,
            "section": "A",
            "date": today + timedelta(days=1),
            "start": "11:00",
            "end": "12:00",
            "room": "AI-Lab",
        },
        {
            "teacher": "priya.mehta@eventsync.demo",
            "subject": "EC301",
            "department": "ECE",
            "semester": 3,
            "section": "A",
            "date": today + timedelta(days=2),
            "start": "10:00",
            "end": "11:00",
            "room": "ECE-101",
        },
    ]

    for lecture in lecture_data:

        teacher_id = get_user_id(
            connection,
            lecture["teacher"],
        )

        subject_id = get_subject_id(
            connection,
            lecture["subject"],
        )

        department_id = get_department_id(
            connection,
            lecture["department"],
        )

        connection.execute(
            """
            INSERT INTO lectures (
                teacher_id,
                subject_id,
                department_id,
                semester,
                section,
                lecture_date,
                start_time,
                end_time,
                room,
                is_active
            )
            SELECT
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                1
            WHERE NOT EXISTS (
                SELECT 1
                FROM lectures
                WHERE teacher_id = ?
                  AND subject_id = ?
                  AND lecture_date = ?
                  AND start_time = ?
                  AND end_time = ?
                  AND room = ?
            )
            """,
            (
                teacher_id,
                subject_id,
                department_id,
                lecture["semester"],
                lecture["section"],
                lecture["date"].isoformat(),
                lecture["start"],
                lecture["end"],
                lecture["room"],
                teacher_id,
                subject_id,
                lecture["date"].isoformat(),
                lecture["start"],
                lecture["end"],
                lecture["room"],
            ),
        )


# ================================================================
# EVENT SEEDING
# ================================================================

def seed_events(connection):
    today = date.today()

    for event in EVENTS:

        created_by = get_user_id(
            connection,
            event["created_by"],
        )

        event_date = (
            today + timedelta(
                days=event["days_from_today"]
            )
        ).isoformat()

        existing = connection.execute(
            """
            SELECT id
            FROM events
            WHERE event_name = ?
            """,
            (event["name"],),
        ).fetchone()

        if existing:
            event_id = existing["id"]

            connection.execute(
                """
                UPDATE events
                SET
                    event_category = ?,
                    event_type = ?,
                    event_date = ?,
                    start_time = ?,
                    end_time = ?,
                    venue = ?,
                    description = ?,
                    created_by = ?
                WHERE id = ?
                """,
                (
                    event["category"],
                    event["type"],
                    event_date,
                    event["start"],
                    event["end"],
                    event["venue"],
                    event["description"],
                    created_by,
                    event_id,
                ),
            )

        else:
            cursor = connection.execute(
                """
                INSERT INTO events (
                    event_name,
                    event_category,
                    event_type,
                    event_date,
                    start_time,
                    end_time,
                    venue,
                    description,
                    created_by,
                    status
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, 'upcoming'
                )
                """,
                (
                    event["name"],
                    event["category"],
                    event["type"],
                    event_date,
                    event["start"],
                    event["end"],
                    event["venue"],
                    event["description"],
                    created_by,
                ),
            )

            event_id = cursor.lastrowid

        # --------------------------------------------------------
        # MAIN COORDINATOR
        # --------------------------------------------------------

        coordinator_id = get_user_id(
            connection,
            event["main_coordinator"],
        )

        connection.execute(
            """
            INSERT INTO event_coordinators (
                event_id,
                user_id,
                coordinator_role
            )
            VALUES (?, ?, 'main_coordinator')

            ON CONFLICT(event_id, user_id)
            DO UPDATE SET
                coordinator_role = 'main_coordinator'
            """,
            (
                event_id,
                coordinator_id,
            ),
        )

        # --------------------------------------------------------
        # EVENT ↔ LECTURE MAPPING
        # --------------------------------------------------------

        subject_id = get_subject_id(
            connection,
            event["mapped_subject"],
        )

        lecture = connection.execute(
            """
            SELECT id
            FROM lectures
            WHERE subject_id = ?
            ORDER BY lecture_date ASC
            LIMIT 1
            """,
            (subject_id,),
        ).fetchone()

        if lecture:

            connection.execute(
                """
                INSERT OR IGNORE INTO event_lecture_mapping (
                    event_id,
                    lecture_id
                )
                VALUES (?, ?)
                """,
                (
                    event_id,
                    lecture["id"],
                ),
            )


# ================================================================
# MAIN
# ================================================================

def seed_demo_data():
    connection = get_connection()

    try:
        print()
        print("=" * 70)
        print(" EVENTSYNC DEMO DATA SEEDING")
        print("=" * 70)

        # --------------------------------------------------------
        # DEPARTMENTS
        # --------------------------------------------------------

        print("Seeding departments...")
        seed_departments(connection)

        # --------------------------------------------------------
        # ADMIN
        # --------------------------------------------------------

        print("Seeding admin...")
        seed_admin(connection)

        # --------------------------------------------------------
        # TEACHERS
        # --------------------------------------------------------

        print("Seeding teachers...")
        seed_teachers(connection)

        # --------------------------------------------------------
        # SUBJECTS
        # --------------------------------------------------------

        print("Seeding subjects...")
        seed_subjects(connection)

        # --------------------------------------------------------
        # LECTURES
        # --------------------------------------------------------

        print("Seeding academic lectures...")
        seed_lectures(connection)

        # --------------------------------------------------------
        # EVENTS
        # --------------------------------------------------------

        print("Seeding events...")
        seed_events(connection)

        connection.commit()

        print()
        print("=" * 70)
        print(" DEMO DATA SEEDED SUCCESSFULLY")
        print("=" * 70)
        print()
        print("ADMIN")
        print(f"  Email    : {ADMIN_EMAIL}")
        print(f"  Password : {ADMIN_PASSWORD}")
        print()
        print("TEACHERS")
        print("  Email    : neha.kapoor@eventsync.demo")
        print("  Password : EventSync@123")
        print()
        print("  Email    : amit.sharma@eventsync.demo")
        print("  Password : EventSync@123")
        print()
        print("  Email    : priya.mehta@eventsync.demo")
        print("  Password : EventSync@123")
        print()
        print("STUDENTS")
        print("  No demo student accounts created.")
        print("  Students register through the EventSync registration page.")
        print()
        print("EVENT CATEGORIES")
        print("  Technical")
        print("  Competitions")
        print("  Research & Innovation")
        print("  College Fest")
        print("  Placement & Career")
        print("  Sports")
        print()
        print("=" * 70)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ================================================================
# RUN
# ================================================================

if __name__ == "__main__":
    seed_demo_data()