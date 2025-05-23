from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from similarity import calculate_similarity
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import psycopg2
import os
from config import Config
from models import Company, JobPost, JobPostStatus, Resume, ResumeScore
from werkzeug.utils import secure_filename
from drive_auth import upload_to_drive
from pdf_extractor import extract_text_from_pdf, extract_skills, extract_experience, extract_education
from database import get_connection
import requests
from flask import Response
import re
from io import BytesIO
from flask import send_file
from datetime import datetime
from sqlalchemy import or_
from extensions import db
from sqlalchemy import func, desc
from collections import Counter
import nltk

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.secret_key = os.getenv("SECRET_KEY")
app.config.from_object(Config)

print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])
# # Initialize database
db.init_app(app)

migrate = Migrate(app, db)

@app.route('/media/<path:filename>')
def media_files(filename):
    return send_from_directory('media', filename)

@app.route('/')
def landing_page():
    return render_template('landing_page.html',)

@app.route('/all-job-posts', methods=['GET'])
def all_job_posts():
    query = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of jobs per page

    if query:
        jobs_query = JobPost.query.join(Company).filter(
            or_(
                JobPost.job_title.ilike(f"%{query}%"),
                Company.company_name.ilike(f"%{query}%")
            )
        ).order_by(JobPost.created_at.desc())
    else:
        jobs_query = JobPost.query.order_by(JobPost.created_at.desc())

    jobs = jobs_query.paginate(page=page, per_page=per_page)
    current_time = datetime.now().date()

    return render_template('all_posts.html', jobs=jobs, current_time=current_time, query=query)

@app.route('/about')
def about():
    # Get all job categories
    job_posts = JobPost.query.all()
    categories = [job.job_category for job in job_posts]
    print(job_posts)
    print(categories)
    # Count each category
    category_counts = Counter(categories)
    print(category_counts)
    # Prepare data for the chart
    labels = list(category_counts.keys())
    values = list(category_counts.values())

    return render_template('about.html', labels=labels, values=values)

# Loaded environment variables
load_dotenv()

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        # Email content
        email_body = f"Name: {name}\nEmail: {email}\nSubject: {subject}\n\nMessage:\n{message}"

        # Retrieve credentials from .env
        sender_email = os.getenv("EMAIL_USER")
        sender_password = os.getenv("EMAIL_PASS")
        receiver_email = os.getenv("RECEIVER_EMAIL")

        msg = MIMEText(email_body)
        msg["Subject"] = f"Contact Form: {subject}"
        msg["From"] = sender_email
        msg["To"] = receiver_email

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            server.quit()
            flash(("Message sent successfully! We will get back to you soon."))
        except Exception as e:
            flash(("Failed to send message. Please try again later."))

        return redirect(url_for("contact"))

    return render_template("contact.html")

# SignUp Route
UPLOAD_FOLDER_LOGO = 'media/uploads/logos/'  # Folder to store images
if not os.path.exists(UPLOAD_FOLDER_LOGO):
    os.makedirs(UPLOAD_FOLDER_LOGO)
ALLOWED_EXTENSIONS_LOGO = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER_LOGO'] = UPLOAD_FOLDER_LOGO

# Function to check allowed file extensions
def allowed_logo_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_LOGO

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_name = request.form['company_name']
        email = request.form['email']
        password = request.form['password']
        location = request.form['location']
        
        company_logo = request.files.get('company_logo')
        logo_filename = None

        existing_company = Company.query.filter((Company.email == email) | (Company.company_name == company_name)).first()
        if existing_company:
            flash("Company name or email already exists!", "danger")
            return redirect(url_for('signup'))
        
        # filename = company_logo.filename.strip()  # Remove leading/trailing spaces
        # print(f"Trimmed filename: '{filename}'")  # Debug line to show trimmed filename

        # print(f"Company logo: {company_logo}")  # Debug line
        # print(f"Company filename: {company_logo.filename}")  # Debug line
        # print(f"Allowed logo file check: {allowed_logo_file(company_logo.filename)}")  # Debug line

        if company_logo and allowed_logo_file(company_logo.filename):
            # print(f"Inside: Company logo: {company_logo}")  # Debug line
            filename = secure_filename(company_logo.filename)
            unique_filename = f"{company_name}_{filename}"
            logo_path = os.path.join(app.config['UPLOAD_FOLDER_LOGO'], unique_filename)
            # save the uploaded image
            company_logo.save(logo_path)
            # store on a database
            logo_filename = unique_filename
        else:
            # print(f"Else: Company logo: {company_logo}")  # Debug line
            logo_filename = 'media/uploads/logos/company_default_img.png'

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        new_company = Company(
            company_name=company_name,
            email=email,
            password=hashed_password,
            location=location,
            company_logo=logo_filename
        )
        db.session.add(new_company)
        db.session.commit()

        flash ("Company registered successfully!", "success")
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

    # Fetch the total number of job posts
    total_job_posts = JobPost.query.filter_by(company_id=company_id).count()

    # Fetch the total number of applications
    total_applications = Resume.query.filter(Resume.job_id.in_(
        db.session.query(JobPost.job_id).filter_by(company_id=company_id)
    )).count()

    # Fetch the number of active job posts
    active_job_posts = JobPost.query.filter_by(company_id=company_id, status='active').count()

    # Fetch the number of shortlisted candidates (Assuming a threshold score of 80)
    shortlisted_candidates = db.session.query(Resume).join(ResumeScore).filter(
        Resume.job_id.in_(
            db.session.query(JobPost.job_id).filter_by(company_id=company_id)
        ),
        ResumeScore.matching_score >= 80).count()

    # Fetch the number of applicants per job post
    applicants_per_job = db.session.query(
        JobPost.job_title, db.func.count(Resume.resume_id)
    ).join(Resume, JobPost.job_id == Resume.job_id).filter(JobPost.company_id == company_id).group_by(JobPost.job_title).all()
    
    job_titles = [job[0] for job in applicants_per_job]
    applicant_counts = [job[1] for job in applicants_per_job]

    # Fetch the top-performing job posts (sorted by applicant count)
    top_performing_jobs = db.session.query(
        JobPost.job_title, 
        db.func.count(Resume.resume_id).label("applicant_count"),
        db.func.coalesce(db.func.max(ResumeScore.matching_score), 0).label("highest_score")
    ).join(Resume, JobPost.job_id == Resume.job_id).outerjoin(
        ResumeScore, Resume.resume_id == ResumeScore.resume_id
    ).filter(JobPost.company_id == company_id).group_by(JobPost.job_title).order_by(
        db.desc("applicant_count")
    ).limit(5).all()  # Limit to top 5 performing job posts

    # Fetch the top 5 best-matched candidates for each job post
    top_matched_candidates = db.session.query(
        Resume.resume_id,
        Resume.applicant_name,
        JobPost.job_title,
        ResumeScore.matching_score,
        Resume.experience, 
        Resume.resume_file
    ).join(ResumeScore, Resume.resume_id == ResumeScore.resume_id).join(
        JobPost, Resume.job_id == JobPost.job_id
    ).filter(
        JobPost.company_id == company_id,
        ResumeScore.matching_score > 50
    ).filter(JobPost.company_id == company_id).order_by(
        db.desc(ResumeScore.matching_score)
    ).limit(5).all()  # Limit to top 5 candidates

    # Applicants by Job Category (new query)
    applicants_by_category = db.session.query(
        JobPost.job_category,
        db.func.count(Resume.resume_id).label('applicant_count')
    ).join(Resume, JobPost.job_id == Resume.job_id).filter(JobPost.company_id == company_id).group_by(JobPost.job_category).all()

    # Extract categories and applicant counts for the pie chart
    categories = [item.job_category for item in applicants_by_category]
    applicant_counts_category = [item.applicant_count for item in applicants_by_category]

    return render_template('company_dashboard.html', 
                           company=company, 
                           jobs=jobs, 
                           total_job_posts=total_job_posts,
                           total_applications=total_applications,
                           active_job_posts=active_job_posts,
                           shortlisted_candidates=shortlisted_candidates,
                           job_titles=job_titles,
                           applicant_counts=applicant_counts,
                           top_performing_jobs=top_performing_jobs,
                           top_matched_candidates=top_matched_candidates,
                           categories=categories,
                           applicant_counts_category=applicant_counts_category
                           )

# View specific Job posts details on landing page or home page
@app.route('/job-details/<int:job_id>', methods=['GET'])
def job_details(job_id):
    jobs = JobPost.query.get_or_404(job_id)

    # Increment the view count
    jobs.views += 1
    db.session.commit() 

    return render_template('view_job_details.html', jobs=jobs)

# display all companies on the landing page
@app.route('/companies')
def list_companies():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 6

    query = db.session.query(
        Company,
        func.count(JobPost.job_id).label('job_count')
    ).outerjoin(JobPost, Company.company_id == JobPost.company_id) \
    .group_by(Company.company_id) \
    .order_by(desc('job_count'))

    if search_query:
        query = query.filter(Company.company_name.ilike(f'%{search_query}%'))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    companies = pagination.items

    return render_template(
        'companies.html',
        companies=companies,
        pagination=pagination,
        query=search_query
    )

# showing the companies all posts
@app.route('/company/<int:company_id>')
def company_details(company_id):
    page = request.args.get('page', 1, type=int)
    company = Company.query.get_or_404(company_id)
    jobs = JobPost.query.filter_by(company_id=company_id).order_by(JobPost.created_at.desc()).paginate(page=page, per_page=5)
    current_time = datetime.now().date()
    return render_template('company_details.html', company=company, jobs=jobs, current_time=current_time)

@app.route('/company_posts', methods=['GET'])
def company_posts():
    if 'company_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))
    
    company_id = session['company_id']
    company = Company.query.get(company_id)

    query = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    per_page = 5  # You can change this based on your preference

    if query:
        jobs = JobPost.query.join(Company).filter(
            JobPost.company_id == company_id,
            JobPost.job_title.ilike(f"%{query}%")
        ).order_by(JobPost.created_at.desc()).paginate(page=page, per_page=per_page)
    else:
        jobs = JobPost.query.filter_by(company_id=company_id).order_by(JobPost.created_at.desc()).paginate(page=page, per_page=per_page)

    current_time = datetime.now().date()
    return render_template('company_jobPosts.html', company=company, jobs=jobs, current_time=current_time)

# update the company job post
@app.route('/update_job/<int:job_id>', methods=['GET', 'POST'])
def update_job_post(job_id):
    if 'company_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))

    job = JobPost.query.get_or_404(job_id)

    # Ensure the logged-in company owns this job
    if job.company_id != session['company_id']:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('company_posts'))

    if request.method == 'POST':
        job.job_title = request.form['job_title']
        job.job_type = request.form['job_type']
        job.experience_required = request.form['experience_required']
        job.skills_required = request.form['skills_required']
        job.status = request.form['status']

        db.session.commit()
        flash("Job post updated successfully!", "success")
        return redirect(url_for('company_posts'))

    return render_template('update_job.html', job=job)

# View Job posts details
@app.route('/post_details/<int:job_id>', methods=['GET'])
def post_details(job_id):
    if 'company_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))
    
    company_id = session['company_id']
    jobs = JobPost.query.filter_by(job_id=job_id, company_id=company_id).first()

    return render_template('view_jobPosts.html', jobs=jobs)

# Job Post Route
@app.route('/post-job', methods=['GET', 'POST'])
def post_job():
    if 'company_id' not in session:
        flash("Please log in to post a job.", "danger")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        job_title = request.form['job_title']
        job_category = request.form['job_category']
        description = request.form['description']
        skills_required = request.form['skills_required']
        experience_required = request.form['experience_required']
        education_required = request.form['education_required']
        job_type = request.form['job_type']
        closing_date = request.form['closing_date']
        
        if closing_date:
            closing_date = datetime.strptime(closing_date, '%Y-%m-%d') 

        new_job = JobPost(
            company_id=session['company_id'],
            job_title=job_title,
            job_category=job_category,
            description=description,
            skills_required=skills_required,
            experience_required=experience_required,
            education_required=education_required,
            job_type=job_type,
            closing_date=closing_date,
            status=JobPostStatus.active
        )
        
        db.session.add(new_job)
        db.session.commit()
        
        flash("Job posted successfully!", "success")
        return redirect(url_for('dashboard'))
    
    return render_template('post_job.html')

# View all applicants who have applied for a job on specific job post posted by company
@app.route('/view_applicants/<int:job_id>')
def view_applicants(job_id):
    # Get the page number from the query string (default to 1 if not provided)
    page = request.args.get('page', 1, type=int)
    
    # Define the number of applicants to show per page
    per_page = 10
    offset = (page - 1) * per_page

    # Query to fetch the job title and applicants' data with pagination
    query = """
    SELECT j.job_title, r.applicant_name, r.email, rs.matching_score, rs.rank, r.resume_file
    FROM resumes r
    JOIN resume_scores rs ON rs.resume_id = r.resume_id
    JOIN job_posts j ON rs.job_id = j.job_id
    WHERE rs.job_id = %s
    ORDER BY rs.rank ASC
    LIMIT %s OFFSET %s;
    """
    
    conn = get_connection()  # Get a connection from your function
    cursor = conn.cursor()
    cursor.execute(query, (job_id, per_page, offset))
    result = cursor.fetchall()

    # Extract job title and applicants' data
    job_title = result[0][0] if result else 'No Job Title'

    applicants = [
        {
            "name": row[1],
            "email": row[2],
            "score": row[3],
            "rank": row[4],
            "resume_link": row[5],
            "score_label": (
                            "Excellent" if row[3] >= 80 else
                            "Good" if row[3] >= 70 else
                            "Average" if row[3] >= 50 else
                            "Poor"
                        )
        }
        for row in result
    ]
    
    # Count total applicants for pagination info
    count_query = """
    SELECT COUNT(*) FROM resumes r
    JOIN resume_scores rs ON rs.resume_id = r.resume_id
    WHERE rs.job_id = %s;
    """
    cursor.execute(count_query, (job_id,))
    total_applicants = cursor.fetchone()[0]
    total_pages = (total_applicants // per_page) + (1 if total_applicants % per_page > 0 else 0)

    return render_template(
        'view_applicants.html',
        applicants=applicants,
        job_id=job_id,
        job_title=job_title,
        pagination={
            'page': page,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1,
            'next_num': page + 1
        }
    )

# Apply for Job Route
UPLOAD_FOLDER_RESUME = 'media/uploads/resume'
ALLOWED_EXTENSIONS_RESUME = {'pdf'}
app.config['UPLOAD_FOLDER_RESUME'] = UPLOAD_FOLDER_RESUME

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_RESUME

from flask import jsonify

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply_for_job(job_id):
    job = JobPost.query.get(job_id)
    if not job:
        flash("Job not found", "danger")
        return redirect(url_for('all_job_posts'))

    if request.method == 'POST':
        try:
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
                file_path = os.path.join(app.config['UPLOAD_FOLDER_RESUME'], filename)

                if not os.path.exists(app.config['UPLOAD_FOLDER_RESUME']):
                    os.makedirs(app.config['UPLOAD_FOLDER_RESUME'])

                resume.save(file_path)

                # Upload to Google Drive
                drive_link = upload_to_drive(file_path, filename)

                # Resume parsing
                extracted_text = extract_text_from_pdf(file_path)
                skills = extract_skills(extracted_text)
                experience = extract_experience(extracted_text)
                education = extract_education(extracted_text)

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

                calculate_similarity()

                flash('Resume submitted and extracted successfully! Scores updated.', 'success')
                return redirect(url_for('all_job_posts'))

            flash('Invalid file format. Only PDFs are allowed.', 'danger')
            return redirect(request.url)

        except Exception as e:
            print(f"Error occurred: {e}")  # You can also use `logging.error(...)`
            return "Internal Server Error: " + str(e), 500

    return render_template('apply_for_job.html', job=job)


@app.route('/calculate_scores', methods=['GET'])
def calculate_scores():
    calculate_similarity()
    return jsonify({"message": "Matching scores calculated successfully!"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)