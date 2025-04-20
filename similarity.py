import pandas as pd
import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from preprocessing import preprocess_text
from database import engine
from sqlalchemy import text

def calculate_similarity():
    query_resumes = "SELECT * FROM resumes;"
    query_jobs = "SELECT * FROM job_posts;"
    
    df_resumes = pd.read_sql(query_resumes, engine)
    df_jobs = pd.read_sql(query_jobs, engine)

    if df_resumes.empty or df_jobs.empty:
        print("No resumes or jobs available for matching.")
        return
    
    df_combined = pd.merge(
        df_resumes[['resume_id', 'job_id', 'extracted_text', 'skills_extracted', 'experience', 'education']],
        df_jobs[['job_id', 'description', 'skills_required', 'experience_required', 'education_required']],
        on='job_id', how='inner'
    )

    # Preprocess text
    df_combined['cleaned_resume_text'] = df_combined['extracted_text'].fillna("").apply(preprocess_text)
    df_combined['cleaned_job_desc'] = df_combined['description'].fillna("").apply(preprocess_text)

    # TF-IDF Vectorization
    vectorizer = TfidfVectorizer()
    combined_corpus = df_combined['cleaned_resume_text'].tolist() + df_combined['cleaned_job_desc'].tolist()
    vectorizer.fit(combined_corpus)

    resume_tfidf = vectorizer.transform(df_combined['cleaned_resume_text'])
    job_tfidf = vectorizer.transform(df_combined['cleaned_job_desc'])

    df_combined['similarity_score'] = cosine_similarity(resume_tfidf, job_tfidf).diagonal() * 100

    # Jaccard Similarity for Skills
    def jaccard_similarity(list1, list2):
        set1 = set(str(list1).split(', '))
        set2 = set(str(list2).split(', '))
        return len(set1 & set2) / len(set1 | set2) if set1 and set2 else 0

    # Experience & Education Matching
    def match_experience(exp_resume, exp_job):
        num_resume = int(re.findall(r'\d+', str(exp_resume))[0]) if re.findall(r'\d+', str(exp_resume)) else 0
        num_job = int(re.findall(r'\d+', str(exp_job))[0]) if re.findall(r'\d+', str(exp_job)) else 0
        return 1 if num_resume >= num_job else 0

    def match_education(edu_resume, edu_job):
        return 1 if str(edu_resume).lower() in str(edu_job).lower() else 0

    df_combined['skills_similarity'] = df_combined.apply(lambda row: jaccard_similarity(row['skills_extracted'], row['skills_required']), axis=1)
    df_combined['experience_match'] = df_combined.apply(lambda row: match_experience(row['experience'], row['experience_required']), axis=1)
    df_combined['education_match'] = df_combined.apply(lambda row: match_education(row['education'], row['education_required']), axis=1)

    # Final Matching Score Calculation
    df_combined['matching_score'] = (
        (df_combined['similarity_score'] *  0.4) +
        (df_combined['skills_similarity'] * 0.3) +
        (df_combined['experience_match'] * 0.2) +
        (df_combined['education_match'] * 0.1)
    ).round(2)

    # Scale to percentage range (0 to 100)
    df_combined['matching_score'] = (df_combined['matching_score'] * 10).round(2)

    # Ensure the matching score is within the 0-100 range
    df_combined['matching_score'] = df_combined['matching_score'].clip(0, 96)

    # Rank Resumes for Each Jobx
    df_combined['rank'] = df_combined.groupby('job_id')['matching_score'].rank(method='first', ascending=False).astype(int)

    # Delete previous scores for these job_ids to prevent duplicate entries
    job_ids = df_combined['job_id'].unique().tolist()
    delete_query = text(f"DELETE FROM resume_scores WHERE job_id IN ({','.join(map(str, job_ids))});")
    with engine.connect() as conn:
        conn.execute(delete_query)
        conn.commit()

    # Store updated scores in Database
    df_combined[['resume_id', 'job_id', 'matching_score', 'rank']].to_sql('resume_scores', engine, if_exists='append', index=False)

    print("Scores and ranks updated successfully!")
    # Inspect first few rows of combined data to see individual scores
    print(df_combined[['resume_id', 'job_id', 'similarity_score', 'skills_similarity', 'experience_match', 'education_match', 'matching_score']].head())

