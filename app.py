from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import psycopg2

app = Flask(__name__)



@app.route('/')
def index():
    return 'Welcome to AI Resume Scanner!'

if __name__ == "__main__":
    app.run(debug=True)
