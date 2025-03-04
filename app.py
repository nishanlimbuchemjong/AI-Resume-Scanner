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
from database import get_connection

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

@app.route('/about')
def about():
    return render_template('about.html')

# SignUp Route
UPLOAD_FOLDER = 'static/uploads/'  # Folder to store images
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to check allowed file extensions
def allowed_logo_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_name = request.form['company_name']
        email = request.form['email']
        password = request.form['password']
        location = request.form['location']
        
        company_logo = request.files.get('company_logo')
        logo_filename = 'static/uploads/default_logo.png'

        # if company_logo and allowed_file(company_logo.filename):
        #     filename = secure_filename(company_logo.filename)
        #     logo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
        #     company_logo.save(logo_path)
        #     logo_filename = os.path.join('uploads', filename) 
        if company_logo:
            print(f"Uploaded file: {company_logo.filename}")  # Debug print statement
            if allowed_logo_file(company_logo.filename):
                filename = secure_filename(company_logo.filename)
                logo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                company_logo.save(logo_path)
                if os.path.exists(logo_path):  # Check if the file exists after saving
                    logo_filename = os.path.join('uploads', filename)
                    print(f"Logo path: {logo_filename}")  # Debug print statement
                else:
                    print("Logo file was not saved correctly.")
            else:
                logo_filename = 'static/uploads/default_logo.png'
        else:
            logo_filename = 'static/uploads/default_logo.png'

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

    return render_template('company_dashboard.html', company=company, jobs=jobs)

# View all Job posts details on landing page or home page
@app.route('/view_all_posts')
def view_all_posts():
    jobs = JobPost.query.all()
    return render_template('view_all_posts.html', jobs=jobs)

# Company Job post
@app.route('/company_posts')
def company_posts():
    if 'company_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))
    
    company_id = session['company_id']
    company = Company.query.get(company_id)
    jobs = JobPost.query.filter_by(company_id=session['company_id']).all()

    return render_template('company_jobPosts.html', company=company, jobs=jobs)

# View Job posts details
@app.route('/post_details')
def post_details():
    if 'company_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))
    
    company_id = session['company_id']
    company = Company.query.get(company_id)
    jobs = JobPost.query.filter_by(company_id=session['company_id']).all()

    return render_template('view_jobPosts.html', company=company, jobs=jobs)

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
            "resume_link": row[5]
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
