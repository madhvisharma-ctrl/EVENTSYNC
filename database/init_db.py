"""
EventSync Database Initializer

Creates the complete SQLite schema for:

- Students
- Teachers
- Admins
- Departments
- Subjects
- Academic lectures
- College events
- Event coordinators
- Event registrations
- Dynamic QR tokens
- Face verification
- Event verification
- Teacher notifications
- Manual academic attendance
- Event-to-lecture mapping
"""

from database.db import get_connection, DATABASE_PATH


# ================================================================
# DATABASE INITIALIZATION
# ================================================================

def create_database():
    """
    Create all EventSync database tables and indexes.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ========================================================
        # DEPARTMENTS
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                code TEXT NOT NULL UNIQUE,

                name TEXT NOT NULL UNIQUE,

                is_active INTEGER NOT NULL DEFAULT 1,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ========================================================
        # USERS
        #
        # Roles:
        #   student
        #   teacher
        #   admin
        #
        # There is NO separate coordinator account.
        # Coordinator is an event assignment.
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                email TEXT NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                role TEXT NOT NULL
                    CHECK (
                        role IN (
                            'student',
                            'teacher',
                            'admin'
                        )
                    ),

                department_id INTEGER,

                semester INTEGER,

                section TEXT,

                roll_no TEXT UNIQUE,

                face_image_path TEXT,

                is_active INTEGER NOT NULL DEFAULT 1,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (department_id)
                    REFERENCES departments(id)
                    ON DELETE SET NULL
            )
            """
        )

        # ========================================================
        # SUBJECTS
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                subject_code TEXT NOT NULL UNIQUE,

                subject_name TEXT NOT NULL,

                department_id INTEGER,

                semester INTEGER,

                credits INTEGER NOT NULL DEFAULT 3,

                is_active INTEGER NOT NULL DEFAULT 1,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (department_id)
                    REFERENCES departments(id)
                    ON DELETE SET NULL
            )
            """
        )

        # ========================================================
        # ACADEMIC LECTURES
        #
        # Teachers use these records for manual attendance.
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lectures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                teacher_id INTEGER NOT NULL,

                subject_id INTEGER NOT NULL,

                department_id INTEGER,

                semester INTEGER,

                section TEXT,

                lecture_date TEXT NOT NULL,

                start_time TEXT NOT NULL,

                end_time TEXT NOT NULL,

                room TEXT,

                is_active INTEGER NOT NULL DEFAULT 1,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (teacher_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (subject_id)
                    REFERENCES subjects(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (department_id)
                    REFERENCES departments(id)
                    ON DELETE SET NULL
            )
            """
        )

        # ========================================================
        # EVENTS
        #
        # Categories can include:
        # Technical
        # Sports
        # Cultural
        # Placement & Career
        # Competitions
        # Research & Innovation
        # College Fest
        # Other
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                event_name TEXT NOT NULL,

                event_category TEXT NOT NULL,

                event_type TEXT NOT NULL,

                event_date TEXT NOT NULL,

                start_time TEXT NOT NULL,

                end_time TEXT NOT NULL,

                venue TEXT NOT NULL,

                description TEXT,

                created_by INTEGER NOT NULL,

                status TEXT NOT NULL DEFAULT 'upcoming'
                    CHECK (
                        status IN (
                            'draft',
                            'upcoming',
                            'live',
                            'completed',
                            'cancelled'
                        )
                    ),

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (created_by)
                    REFERENCES users(id)
                    ON DELETE RESTRICT
            )
            """
        )

        # ========================================================
        # EVENT COORDINATORS
        #
        # Teacher:
        #   main_coordinator
        #
        # Student:
        #   student_coordinator
        #
        # These are assignments, NOT separate accounts.
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS event_coordinators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                event_id INTEGER NOT NULL,

                user_id INTEGER NOT NULL,

                coordinator_role TEXT NOT NULL
                    CHECK (
                        coordinator_role IN (
                            'main_coordinator',
                            'student_coordinator'
                        )
                    ),

                assigned_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    event_id,
                    user_id
                ),

                FOREIGN KEY (event_id)
                    REFERENCES events(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )

        # ========================================================
        # EVENT REGISTRATIONS
        #
        # Student chooses:
        #   Participant
        #   Student Coordinator
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS event_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                event_id INTEGER NOT NULL,

                student_id INTEGER NOT NULL,

                participation_role TEXT NOT NULL
                    CHECK (
                        participation_role IN (
                            'participant',
                            'student_coordinator'
                        )
                    ),

                status TEXT NOT NULL DEFAULT 'registered'
                    CHECK (
                        status IN (
                            'registered',
                            'cancelled',
                            'attended'
                        )
                    ),

                registered_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    event_id,
                    student_id
                ),

                FOREIGN KEY (event_id)
                    REFERENCES events(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (student_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )

        # ========================================================
        # EVENT ↔ LECTURE MAPPING
        #
        # Allows admin to map an event to an academic lecture.
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS event_lecture_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                event_id INTEGER NOT NULL,

                lecture_id INTEGER NOT NULL,

                mapped_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    event_id,
                    lecture_id
                ),

                FOREIGN KEY (event_id)
                    REFERENCES events(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (lecture_id)
                    REFERENCES lectures(id)
                    ON DELETE CASCADE
            )
            """
        )

        # ========================================================
        # DYNAMIC QR TOKENS
        #
        # QR tokens are short-lived.
        #
        # Student must scan an active token during the event.
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS qr_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                event_id INTEGER NOT NULL,

                token TEXT NOT NULL UNIQUE,

                generated_by INTEGER NOT NULL,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                expires_at TEXT NOT NULL,

                is_active INTEGER NOT NULL DEFAULT 1,

                FOREIGN KEY (event_id)
                    REFERENCES events(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (generated_by)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )

        # ========================================================
        # EVENT VERIFICATIONS
        #
        # Final verification requires:
        #
        # Registered student
        # + valid event
        # + valid QR
        # + face verification
        # + valid time
        #
        # = VERIFIED
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS event_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                event_id INTEGER NOT NULL,

                student_id INTEGER NOT NULL,

                qr_token_id INTEGER,

                qr_verified INTEGER NOT NULL DEFAULT 0,

                face_verified INTEGER NOT NULL DEFAULT 0,

                verification_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (
                        verification_status IN (
                            'pending',
                            'failed',
                            'verified'
                        )
                    ),

                confidence REAL,

                verified_at TEXT,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    event_id,
                    student_id
                ),

                FOREIGN KEY (event_id)
                    REFERENCES events(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (student_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (qr_token_id)
                    REFERENCES qr_tokens(id)
                    ON DELETE SET NULL
            )
            """
        )

        # ========================================================
        # NOTIFICATIONS
        #
        # Teacher receives verification notifications containing:
        # Student name
        # Roll number
        # Event
        # Verification status
        # Verification time
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                event_id INTEGER,

                student_id INTEGER,

                title TEXT NOT NULL,

                message TEXT NOT NULL,

                notification_type TEXT NOT NULL
                    DEFAULT 'info',

                is_read INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (event_id)
                    REFERENCES events(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (student_id)
                    REFERENCES users(id)
                    ON DELETE SET NULL
            )
            """
        )

        # ========================================================
        # MANUAL ACADEMIC ATTENDANCE
        #
        # IMPORTANT:
        #
        # EventSync verification DOES NOT automatically mark
        # academic attendance.
        #
        # Teacher manually marks:
        #   present
        #   absent
        #   late
        # ========================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                lecture_id INTEGER NOT NULL,

                student_id INTEGER NOT NULL,

                attendance_status TEXT NOT NULL
                    DEFAULT 'present'
                    CHECK (
                        attendance_status IN (
                            'present',
                            'absent',
                            'late'
                        )
                    ),

                marked_by INTEGER NOT NULL,

                marked_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    lecture_id,
                    student_id
                ),

                FOREIGN KEY (lecture_id)
                    REFERENCES lectures(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (student_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (marked_by)
                    REFERENCES users(id)
                    ON DELETE RESTRICT
            )
            """
        )

        # ========================================================
        # INDEXES
        # ========================================================

        index_statements = [

            """
            CREATE INDEX IF NOT EXISTS
            idx_users_role
            ON users(role)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_users_department
            ON users(department_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_users_roll_no
            ON users(roll_no)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_subject_department
            ON subjects(department_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_lectures_teacher
            ON lectures(teacher_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_lectures_date
            ON lectures(lecture_date)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_events_date
            ON events(event_date)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_events_status
            ON events(status)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_event_coordinators_event
            ON event_coordinators(event_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_event_coordinators_user
            ON event_coordinators(user_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_event_registrations_event
            ON event_registrations(event_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_event_registrations_student
            ON event_registrations(student_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_qr_tokens_event
            ON qr_tokens(event_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_qr_tokens_expiry
            ON qr_tokens(expires_at)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_verifications_event
            ON event_verifications(event_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_verifications_student
            ON event_verifications(student_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_notifications_user
            ON notifications(user_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_attendance_lecture
            ON attendance(lecture_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_attendance_student
            ON attendance(student_id)
            """
        ]

        for statement in index_statements:
            cursor.execute(statement)

        # ========================================================
        # COMMIT
        # ========================================================

        connection.commit()

        print()
        print("=" * 70)
        print(" EVENTSYNC DATABASE INITIALIZED SUCCESSFULLY")
        print("=" * 70)
        print()
        print(f"Database:")
        print(f"  {DATABASE_PATH}")
        print()
        print("Core architecture:")
        print("  ✓ Student accounts created through registration")
        print("  ✓ Teacher accounts")
        print("  ✓ Admin accounts")
        print("  ✓ Event coordinator = assignment")
        print("  ✓ Academic teacher = timetable responsibility")
        print("  ✓ Dynamic QR verification")
        print("  ✓ Face verification")
        print("  ✓ Teacher notifications")
        print("  ✓ Manual academic attendance")
        print("  ✓ Event ↔ lecture mapping")
        print()
        print("=" * 70)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ================================================================
# MAIN
# ================================================================

if __name__ == "__main__":
    create_database()