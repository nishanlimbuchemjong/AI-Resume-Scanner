from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import psycopg2
from config import Config
from models import db

app = Flask(__name__)

# Load configuration from config.py file
app.config.from_object(Config)

# Initialize database
db.init_app(app)

@app.route('/')
def index():
    return 'Welcome to AI Resume Scanner!'

if __name__ == "__main__":
    app.run(debug=True)
