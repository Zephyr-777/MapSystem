from sqlalchemy import text
from app.core.database import SessionLocal

def add_role_column():
    db = SessionLocal()
    try:
        # Check if column exists
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='role';"))
        if result.fetchone():
            print("Column 'role' already exists.")
        else:
            print("Adding column 'role' to 'users' table...")
            # Add column with default value 'guest'
            db.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'guest' NOT NULL;"))
            
            # Update existing users to have a role (though default handles new rows, let's be safe for existing ones if any)
            # Actually DEFAULT 'guest' handles it.
            
            # Make sure at least one admin exists if needed? No, just fix schema first.
            
            db.commit()
            print("Column 'role' added successfully.")
            
    except Exception as e:
        print(f"Error adding column: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_role_column()
