# HireIntel AI

**HireIntel AI** is an AI-powered Resume Screening and Job Matching web application designed to streamline the hiring process. Built for companies to efficiently manage job posts and evaluate candidate resumes using intelligent similarity scoring, HireIntel AI automates resume analysis using Machine Learning (ML), Natural Language Processing (NLP), and Deep Learning (DL) techniques.

## Features

- **Company Registration/Login**
- **Post Job Descriptions** with relevant skills, qualifications, and details
- **Resume Submission** (PDF format) by candidates — no registration required
- **AI-Powered Resume Scoring** based on similarity to job descriptions
- **Machine Learning Model** developed from scratch for accuracy and customization
- **Resumes Stored on Google Drive** for secure access
- **Company Dashboard** to view applications and AI-generated resume scores
- **Flask Backend** with RESTful APIs
- **PostgreSQL Database Integration**

## How It Works

1. **Job Posting**: A company posts a new job with a detailed description.
2. **Resume Submission**: Candidates submit their resumes in PDF format.
3. **Resume Extraction**: Text is extracted using NLP techniques.
4. **Similarity Scoring**: The AI model calculates similarity between resume content and job description using NLP and cosine similarity or vector-based approaches.
5. **Result Display**: Companies see a list of resumes scored and ranked based on relevance.

## Tech Stack

| Component        | Technology                          |
|------------------|--------------------------------------|
| Backend          | Flask (Python)                      |
| Frontend         | HTML, CSS, Bootstrap                |
| Database         | PostgreSQL                          |
| AI/ML/NLP        | scikit-learn, pandas, nltk, spaCy   |
| File Storage     | Google Drive API                    |

## AI Model

- Custom-built model trained on job descriptions and resume data
- Uses **TF-IDF**, **cosine similarity**
- Processes text via **spaCy**, **NLTK**


## Setup Instructions
1. Clone the repo
- https://github.com/nishanlimbuchemjong/AI-Resume-Scanner.git

2. Install dependencies
- pip install -r requirements.txt

3. Configure Google Drive API
- Add your credentials.json for Google Drive
- Setup OAuth scopes and access tokens

4. Run the app
- python app.py

5. Access in browser
- http://localhost:5000