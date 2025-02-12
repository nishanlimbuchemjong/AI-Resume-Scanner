from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from config import Config
from models import db, Company

app = Flask(__name__)

# Load configuration from config.py file
app.config.from_object(Config)

# Initialize database
db.init_app(app)

@app.route('/')
def index():
    return 'Welcome to AI Resume Scanner!'

# SignUp Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_name = request.form['company_name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        existing_company = Company.query.filter_by(email=email).first()
        if existing_company:
            flash("Company already exists!", "danger")
            return redirect(url_for('signup'))
        
        new_company = Company(company_name=company_name, email=email, password=hashed_password)
        db.session.add(new_company)
        db.session.commit()
        
        flash("Signup successful! Please log in.", "success")
        return redirect(url_for('login'))
    
    return render_template('signup.html')



if __name__ == "__main__":
    app.run(debug=True)
