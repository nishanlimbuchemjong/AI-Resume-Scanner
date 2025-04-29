from sqlalchemy import create_engine
import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

host = os.getenv("DB_HOST")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
dbname = os.getenv("DB_NAME")
port = int(os.getenv("DB_PORT"))

# Construct the database URL using environment variables
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
engine = create_engine(DATABASE_URL)

def get_connection():
    return psycopg2.connect(host=host, user=user, password=password, dbname=dbname, port=port)
