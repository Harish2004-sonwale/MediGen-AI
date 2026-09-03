import sqlite3
import os

db_path = "medigen_dev.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Get existing columns
    cur.execute("PRAGMA table_info(patients)")
    cols = [r[1] for r in cur.fetchall()]
    print("Existing patient columns:", cols)
    
    new_cols = [
        ("blood_group", "VARCHAR(10)"),
        ("allergies", "TEXT"),
        ("health_problem", "TEXT"),
        ("previous_diagnoses", "TEXT"),
        ("current_medications", "TEXT"),
        ("assigned_doctor_id", "INTEGER"),
        ("user_id", "INTEGER"),
    ]
    
    for col_name, col_type in new_cols:
        if col_name not in cols:
            print(f"Adding column {col_name} ({col_type}) to patients table...")
            cur.execute(f"ALTER TABLE patients ADD COLUMN {col_name} {col_type}")
            
    conn.commit()
    conn.close()
    print("Database migration completed successfully!")
else:
    print("Database file medigen.db does not exist yet.")
