# EventSync

EventSync is a Flask-based college event and academic attendance management system designed for a hackathon/demo environment.

It connects:

- Student event registration
- Student coordinator assignment
- Teacher event coordination
- Dynamic QR verification
- Live face verification
- Event presence verification
- Teacher notifications
- Manual academic attendance
- Admin management
- Event-to-lecture mapping

---

## 1. Core Concept

EventSync keeps two processes separate:

### Event Presence Verification

A student can verify their presence at an active event using:

1. Registered student account
2. Registered event
3. Active event
4. Valid short-lived EventSync QR token
5. Live face verification
6. Valid event date/time

Only when the required checks pass is the event presence marked as:

**EVENT PRESENCE VERIFIED**

### Academic Attendance

Academic attendance is intentionally separate.

Teachers manually mark lecture attendance.

Event verification does **not automatically mark academic lecture attendance**.

Instead, teachers can receive notifications showing which students from their academic lecture are verified at an event. The teacher can then manually mark lecture attendance according to the actual lecture situation.

---

# 2. User Roles

## Student

Students create their own accounts through registration.

A student can:

- Register an account
- Upload an optional face image
- Browse events
- Register for events
- Register as a participant
- Register as a student coordinator for an event
- View registered events
- Verify event presence
- View verification history
- View notifications
- Manage their profile
- Access coordinator workspace when assigned

Student accounts are **not pre-seeded**.

---

## Teacher

Teachers can:

- View academic lectures
- View their timetable
- Manually mark attendance
- View attendance records
- View event assignments
- Manage assigned events
- View event registrations
- View verified students
- Receive verification notifications

A teacher can simultaneously be:

- An academic teacher
- An event coordinator

These are separate responsibilities.

---

## Admin

Admin can manage the complete system:

- Users
- Departments
- Subjects
- Lectures
- Events
- Event coordinators
- Event registrations
- Event-to-lecture mappings
- Verification reports

---

# 3. Event Categories

EventSync supports:

- Technical
- Sports
- Cultural
- Placement & Career
- Competitions
- Research & Innovation
- College Fest
- Other

---

# 4. Event Coordinator Model

There is no separate coordinator account.

An existing user can be assigned as an event coordinator.

Supported coordinator roles:

### Main Coordinator

Usually a teacher.

### Student Coordinator

A registered student who chooses the student coordinator role while registering for an event.

The coordinator assignment is event-specific.

---

# 5. Event Verification Workflow

The intended workflow is:

```text
Student Account
      |
      v
Event Registration
      |
      v
Active Event
      |
      v
Dynamic QR
      |
      v
QR Validation
      |
      v
Live Face Verification
      |
      v
Time Validation
      |
      v
Event Presence Verified
      |
      v
Coordinator Notification
      |
      v
Teacher Notification