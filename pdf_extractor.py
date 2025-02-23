# import fitz  # PyMuPDF
# import spacy
# import re

# # Load spaCy model (ensure it's installed: python -m spacy download en_core_web_sm)
# nlp = spacy.load('en_core_web_sm')

# def extract_text_from_pdf(pdf_path):
#     """
#     Extract text from a PDF file.
#     """
#     doc = fitz.open(pdf_path)
#     text = ""
#     for page in doc:
#         text += page.get_text("text")
#     return text

# def extract_entities(text):
#     """
#     Extract skills, experience, and education from the resume text using NLP.
#     """
#     doc = nlp(text)
#     skills = []
#     experience = []
#     education = []

#     for ent in doc.ents:
#         if ent.label_ in ["SKILL", "ABILITY", "EXPERTISE", "Skill"]:
#             skills.append(ent.text)
#         elif ent.label_ in ["DATE", "DURATION", "EXPERIENCE", "Experience"]:
#             experience.append(ent.text)
#         elif ent.label_ in ["DEGREE", "EDUCATION", "QUALIFICATION", "Education"]:
#             education.append(ent.text)

#     return skills, experience, education

import fitz  # PyMuPDF
import re

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.
    """
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

def extract_section(text, start_keyword, end_keywords):
    """
    Extract text between a start keyword and the next section keyword.
    This version is more flexible with formatting variations and special characters.
    """
    start_pattern = r"\b" + re.escape(start_keyword) + r"\b"
    
    end_patterns = [r"\b" + re.escape(keyword) + r"\b" for keyword in end_keywords]
    
    end_pattern = '|'.join(end_patterns)
    
    pattern = rf"{start_pattern}[\s\S]*?(?={end_pattern}|$)"
    
    match = re.search(pattern, text)
    
    if match:
        section_text = match.group(0).strip()
        
        # Ensure we capture bullet points and lists properly in the skills section
        section_text = re.sub(r"([•\*\-])\s+", r"\1 ", section_text)  # Normalize spacing after bullets
        
        # Normalize line breaks and spaces
        section_text = re.sub(r"\n\s*\n", "\n", section_text).strip()
        
        # Handle ':' character properly after category titles
        section_text = re.sub(r"\s*:\s*", ": ", section_text)  # Remove unwanted spaces around colons
        
        return section_text
    return "Not Mentioned"


def extract_skills(text):
    """
    Extract skills section from resume.
    """
    return extract_section(text, "Skills", ["Education", "Experience", "Projects", "Certifications", "Languages"])

def extract_experience(text):
    """
    Extract experience section from resume.
    """
    return extract_section(text, "Experience", ["Education", "Skills", "Projects", "Certifications", "Languages"])

def extract_education(text):
    """
    Extract education section from resume.
    """
    return extract_section(text, "Education", ["Experience", "Skills", "Projects", "Certifications", "Languages"])
