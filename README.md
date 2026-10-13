# Job Search & Interview Copilot

A Python web application for managing job applications,
comparing resume keywords with job descriptions, and
generating interview practice questions.

## Features

- Job application tracking with SQLite
- Application status management
- Resume and job description keyword comparison
- Role-specific interview practice questions
- Dashboard for application progress

## Tech Stack

Python, Streamlit, SQLite, Git, GitHub

## Run Locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py

## Run the application locally

Make sure you are inside the project folder and your virtual environment is activated.

```bash
python -m pip install -r requirements.txt
python -m py_compile app.py
streamlit run app.py
