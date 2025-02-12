from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from config import Config
from models import db, Company, JobPost, JobPostStatus

app = Flask(__name__)

# Load configuration from config.py file
app.config.from_object(Config)

# Initialize database
db.init_app(app)

migrate = Migrate(app, db)

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

# Logout Route
@app.route('/logout')
def logout():
    session.pop('company_id', None)
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))

# Company Dashboard
@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))

    company_id = session['company_id']
    company = Company.query.get(company_id)
    jobs = JobPost.query.filter_by(company_id=session['company_id']).all()

    return render_template('company_dashboard.html', company=company, jobs=jobs)

# Job Post Route
@app.route('/post-job', methods=['GET', 'POST'])
def post_job():
    if 'company_id' not in session:
        flash("Please log in to post a job.", "danger")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        job_title = request.form['job_title']
        description = request.form['description']
        skills_required = request.form['skills_required']
        experience_required = request.form['experience_required']
        education_required = request.form['education_required']
        job_type = request.form['job_type']
        
        new_job = JobPost(
            company_id=session['company_id'],
            job_title=job_title,
            description=description,
            skills_required=skills_required,
            experience_required=experience_required,
            education_required=education_required,
            job_type=job_type,
            status=JobPostStatus.active
        )
        
        db.session.add(new_job)
        db.session.commit()
        
        flash("Job posted successfully!", "success")
        return redirect(url_for('dashboard'))
    
    return render_template('post_job.html')

if __name__ == "__main__":
    app.run(debug=True)
