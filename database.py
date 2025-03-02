from sqlalchemy import create_engine
import psycopg2

host = "localhost"
user = "postgres"
password = "testing"
dbname = "AI_Resume_Scanner"
port = 5432

DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
engine = create_engine(DATABASE_URL)

def get_connection():
    return psycopg2.connect(host=host, user=user, password=password, dbname=dbname, port=port)
