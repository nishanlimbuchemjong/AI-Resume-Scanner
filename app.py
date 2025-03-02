from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from similarity import calculate_similarity
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
from config import Config
from models import db, Company, JobPost, JobPostStatus, Resume
from werkzeug.utils import secure_filename
from drive_auth import upload_to_drive
from pdf_extractor import extract_text_from_pdf, extract_skills, extract_experience, extract_education

app = Flask(__name__)

# Load configuration from config.py file
app.config.from_object(Config)

# Initialize database
db.init_app(app)

migrate = Migrate(app, db)

@app.route('/')
def landing_page():
    return render_template('landing_page.html',)

@app.route('/all-job-posts', methods=['GET'])
def all_job_posts():
    jobs = JobPost.query.all()
    return render_template('all_posts.html', jobs=jobs)

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

# Apply for Job Route
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply_for_job(job_id):
    job = JobPost.query.get(job_id)
    if not job:
        flash("Job not found", "danger")
        return redirect(url_for('all_job_posts'))

    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        resume = request.files['resume']
        applicant_name = request.form['applicant_name']
        email = request.form['email']

        if resume.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if resume and allowed_file(resume.filename):
            filename = secure_filename(resume.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Ensure upload folder exists
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            resume.save(file_path)

            # Upload to Google Drive and get the link
            drive_link = upload_to_drive(file_path, filename)

            # Extract text and structured details from the resume
            extracted_text = extract_text_from_pdf(file_path)
            skills = extract_skills(extracted_text)
            experience = extract_experience(extracted_text)
            education = extract_education(extracted_text)

            # Save extracted details in the database
            new_resume = Resume(
                job_id=job_id,
                applicant_name=applicant_name,
                email=email,
                resume_file=drive_link,
                extracted_text=extracted_text,
                skills_extracted=skills,
                experience=experience,
                education=education
            )

            db.session.add(new_resume)
            db.session.commit()

            # **Call calculate_similarity() to update rankings**
            calculate_similarity()

            flash('Resume submitted and extracted successfully! Scores updated.', 'success')
            return redirect(url_for('all_job_posts'))

        flash('Invalid file format. Only PDFs are allowed.', 'danger')
        return redirect(request.url)

    return render_template('apply_for_job.html', job=job)

@app.route('/calculate_scores', methods=['GET'])
def calculate_scores():
    calculate_similarity()
    return jsonify({"message": "Matching scores calculated successfully!"})



if __name__ == "__main__":
    app.run(debug=True)
