from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum
import enum

# Initialize the database
db = SQLAlchemy()

# Enum for Job Post Status
class JobPostStatus(enum.Enum):
    active = "Active"
    inactive = "In-Active"

    def __str__(self):
        return self.value

# Company Model
class Company(db.Model):
    __tablename__ = 'companies'
    
    company_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False)  # Company location
    company_logo = db.Column(db.String(500), nullable=True, default='static/uploads/logo.png')
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp(), nullable=False)

    # Relationship with job_posts
    job_posts = db.relationship('JobPost', backref='company', lazy=True, cascade="all, delete-orphan")

# Job Post Model
class JobPost(db.Model):
    __tablename__ = 'job_posts'
    
    job_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.company_id'), nullable=False)
    job_title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    skills_required = db.Column(db.Text, nullable=False)
    experience_required = db.Column(db.String(100), nullable=False)
    education_required = db.Column(db.String(255), nullable=False)
    job_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp(), nullable=False)
    status = db.Column(Enum(JobPostStatus), default=JobPostStatus.active, nullable=False)
    views = db.Column(db.Integer, default=0)
    vacancy = db.Column(db.Integer, default=1)
    job_category = db.Column(db.String(100), nullable=True)
    closing_date = db.Column(db.Date, nullable=False)

    # Relationship with resumes
    resumes = db.relationship('Resume', backref='job_post', lazy=True, cascade="all, delete-orphan")

# Resume Model
class Resume(db.Model):
    __tablename__ = 'resumes'
    
    resume_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_posts.job_id'), nullable=False)
    applicant_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    resume_file = db.Column(db.String(500), nullable=False)  # Google Drive link
    extracted_text = db.Column(db.Text, nullable=False)
    skills_extracted = db.Column(db.Text, nullable=False)
    experience = db.Column(db.Text, nullable=False)
    education = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp(), nullable=False)

    # Relationship with resume_scores
    resume_scores = db.relationship('ResumeScore', backref='resume', lazy=True, cascade="all, delete-orphan")

# Resume Score Model
class ResumeScore(db.Model):
    __tablename__ = 'resume_scores'
    
    score_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.resume_id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_posts.job_id'), nullable=False)
    matching_score = db.Column(db.Float, nullable=False)
    rank = db.Column(db.Integer, nullable=False)

    # Ensure one-to-one relationship for scoring per resume per job
    __table_args__ = (
        db.UniqueConstraint('resume_id', 'job_id', name='_resume_job_uc'),
    )
