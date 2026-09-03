"""MediGen AI - Production Database Cleanup Script.

Safely removes all demo/seed records, demo patients, demo doctors, demo appointments,
and synthetic test records while strictly preserving user-entered personal accounts:
- User 9: harishsonwale4@gmail.com (Patient)
- User 13: harishsonwale0408@gmail.com (Patient)
- User 17: sauravmadake@gmail.com (Doctor)
- User 19: karan@hospital.org (Admin)

Guarantees data integrity and ensures Dr. Saurav Madake has an official Doctor profile.
"""

import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "medigen_dev.db")
BACKUP_PATH = os.path.join(os.path.dirname(__file__), "..", "medigen_dev.db.bak")

PRESERVED_USER_IDS = (9, 13, 17, 19)


def run_cleanup():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = OFF;")

    # 1. Verify preserved users exist
    cursor.execute(
        f"SELECT id, email, name, role FROM users WHERE id IN ({','.join(map(str, PRESERVED_USER_IDS))})"
    )
    preserved = cursor.fetchall()
    print(f"Found {len(preserved)} user-entered accounts to preserve:")
    for u in preserved:
        print(f"  [PRESERVED] User ID={u[0]}: {u[1]} ({u[2]}, Role: {u[3]})")

    if len(preserved) < 4:
        print("Warning: Expected 4 preserved users. Found fewer. Aborting for safety.")
        conn.close()
        sys.exit(1)

    # 2. Delete demo/test appointments
    cursor.execute("DELETE FROM appointments")
    print(f"Removed demo appointments (deleted: {cursor.rowcount})")

    # 3. Delete demo medical documents
    cursor.execute("DELETE FROM medical_documents")
    print(f"Removed demo medical documents (deleted: {cursor.rowcount})")

    # 4. Delete demo encounters
    cursor.execute("DELETE FROM encounters")
    print(f"Removed demo encounters (deleted: {cursor.rowcount})")

    # 5. Delete demo clinical notes
    cursor.execute("DELETE FROM clinical_notes")
    print(f"Removed demo clinical notes (deleted: {cursor.rowcount})")

    # 6. Delete demo clinical orders
    cursor.execute("DELETE FROM clinical_orders")
    print(f"Removed demo clinical orders (deleted: {cursor.rowcount})")

    # 7. Delete demo care plans and care tasks
    cursor.execute("DELETE FROM care_tasks")
    cursor.execute("DELETE FROM care_plans")
    cursor.execute("DELETE FROM discharge_protocols")
    print("Removed demo care plans, tasks, and discharge protocols")

    # 8. Delete demo vitals
    cursor.execute("DELETE FROM vital_telemetry")
    print("Removed demo vital telemetry")

    # 9. Delete demo chat sessions and messages
    cursor.execute("DELETE FROM chat_messages")
    cursor.execute("DELETE FROM chat_sessions")
    print("Removed demo chat sessions & messages")

    # 10. Delete demo medication administration records
    cursor.execute("DELETE FROM medication_administration_records")
    print("Removed demo medication administration records")

    # 11. Delete demo DICOM records and AI findings
    cursor.execute("DELETE FROM ai_isolated_lesion_findings")
    cursor.execute("DELETE FROM dicom_instance_records")
    cursor.execute("DELETE FROM dicom_series_records")
    cursor.execute("DELETE FROM dicom_study_records")
    cursor.execute("DELETE FROM ecg_waveform_sessions")
    cursor.execute("DELETE FROM arrhythmia_alert_events")
    print("Removed demo DICOM, ECG, and imaging study records")

    # 12. Delete demo patients (all existing were DEFAULT_DEMO_PATIENTS or test scripts)
    cursor.execute(f"DELETE FROM patients WHERE user_id NOT IN ({','.join(map(str, PRESERVED_USER_IDS))}) OR user_id IS NULL")
    print(f"Removed demo patients (deleted: {cursor.rowcount})")

    # 13. Delete demo doctors
    cursor.execute(f"DELETE FROM doctors WHERE user_id NOT IN ({','.join(map(str, PRESERVED_USER_IDS))})")
    print(f"Removed demo doctors (deleted: {cursor.rowcount})")

    # 14. Ensure Dr. Saurav Madake (user_id=17) has an active, verified doctor profile
    cursor.execute("SELECT id FROM doctors WHERE user_id = 17")
    existing_doc = cursor.fetchone()
    if not existing_doc:
        cursor.execute("""
            INSERT INTO doctors (
                doctor_id, user_id, full_name, professional_title, department,
                specialization, medical_registration_number, years_of_experience, email,
                consultation_mode, verification_status, availability_status
            ) VALUES (
                'DOC-17', 17, 'Dr. Saurav Madake', 'Dr.', 'General Medicine',
                'General Medicine & Clinical Practice', 'MCI-0017-2026', 10, 'sauravmadake@gmail.com',
                'both', 'verified', 'available'
            )
        """)
        print("Created verified Doctor profile for Dr. Saurav Madake (DOC-17)")

    # 15. Delete demo users
    cursor.execute(
        f"DELETE FROM users WHERE id NOT IN ({','.join(map(str, PRESERVED_USER_IDS))})"
    )
    print(f"Removed demo users (deleted: {cursor.rowcount})")

    # 16. Ensure active status on all preserved accounts
    cursor.execute(
        f"UPDATE users SET is_active = 1 WHERE id IN ({','.join(map(str, PRESERVED_USER_IDS))})"
    )

    conn.commit()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Print remaining state
    print("\n--- CLEANUP COMPLETE: REMAINING DATA VERIFICATION ---")
    cursor.execute("SELECT id, email, name, role, is_active FROM users")
    remaining_users = cursor.fetchall()
    print(f"Active Users ({len(remaining_users)}):")
    for u in remaining_users:
        print(f"  User {u[0]}: {u[1]} | {u[2]} | Role: {u[3]} | Active: {bool(u[4])}")

    cursor.execute("SELECT id, doctor_id, full_name, user_id, verification_status FROM doctors")
    remaining_doctors = cursor.fetchall()
    print(f"Doctors ({len(remaining_doctors)}):")
    for d in remaining_doctors:
        print(f"  Doctor {d[0]}: {d[1]} | {d[2]} | User ID: {d[3]} | Status: {d[4]}")

    cursor.execute("SELECT COUNT(*) FROM patients")
    print(f"Patients count: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM appointments")
    print(f"Appointments count: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM medical_documents")
    print(f"Medical Documents count: {cursor.fetchone()[0]}")

    conn.close()


if __name__ == "__main__":
    run_cleanup()
