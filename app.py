from flask import Flask, render_template, request, redirect, url_for, flash, session
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
def landing_page():
    return render_template('landing_page.html')

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

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        company = Company.query.filter_by(email=email).first()
        
        if company and check_password_hash(company.password, password):
            session['company_id'] = company.company_id
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials!", "danger")
            return redirect(url_for('login'))
    
    return render_template('login.html')

# Company Dashboard
@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))

    company_id = session['company_id']
    company = Company.query.get(company_id)

    return render_template('company_dashboard.html', company=company)

if __name__ == "__main__":
    app.run(debug=True)
