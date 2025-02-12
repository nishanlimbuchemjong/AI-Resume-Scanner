from app import app
from models import db

with app.app_context():
    try:
        db.create_all()
        print("Tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")
