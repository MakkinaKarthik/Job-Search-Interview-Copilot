
import re
import sqlite3
from pathlib import Path
from datetime import date

import streamlit as st

DB_PATH = Path(__file__).parent / "jobs.db"

st.set_page_config(
    page_title="Job Search Copilot",
    page_icon="🎯",
    layout="wide",
)

SKILLS = [
    "python", "sql", "linux", "ubuntu", "git", "github",
    "azure", "aws", "docker", "kubernetes", "jenkins",
    "ansible", "bash", "terraform", "ci/cd", "networking",
    "troubleshooting", "flask", "streamlit", "mysql",
    "communication", "problem solving"
]


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT,
                applied_date TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT DEFAULT ''
            )
        """)


def add_job(company, title, link, applied_date, status, notes):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO jobs
            (company, title, link, applied_date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (company, title, link, str(applied_date), status, notes))


def get_jobs():
    with connect_db() as conn:
        return conn.execute(
            "SELECT * FROM jobs ORDER BY applied_date DESC, id DESC"
        ).fetchall()


def update_status(job_id, status):
    with connect_db() as conn:
        conn.execute(
            "UPDATE jobs SET status = ? WHERE id = ?",
            (status, job_id)
        )


def delete_job(job_id):
    with connect_db() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


def extract_skills(text):
    text = text.lower()
    found = []

    for skill in SKILLS:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        if re.search(pattern, text):
            found.append(skill)

    return sorted(found)


def generate_questions(role, skills, count):
    questions = [
        f"Explain your understanding of the {role} role.",
        "Tell me about a technical problem you solved.",
        "Describe a mistake you made and how you learned from it.",
        "Why are you interested in this position?",
        "Explain one project you have built and your contribution.",
        "How do you troubleshoot a problem you have never seen before?",
        "How do you prioritize tasks when several are urgent?",
        "What would you like to learn in your first 90 days?"
    ]

    for skill in skills:
        questions.append(
            f"Explain {skill} and describe a practical example of using it."
        )

    return questions[:count]


initialize_db()

st.title("🎯 Job Search & Interview Copilot")
st.caption("Track opportunities. Identify skill gaps. Prepare with confidence.")

tab_dashboard, tab_add, tab_analyze, tab_interview = st.tabs([
    "📊 Dashboard",
    "➕ Add Job",
    "🧠 Resume Match",
    "🎤 Interview Prep"
])

jobs = get_jobs()

with tab_dashboard:
    st.subheader("Your job search overview")

    total = len(jobs)
    interviews = sum(j["status"] == "Interview" for j in jobs)
    offers = sum(j["status"] == "Offer" for j in jobs)
    applied = sum(j["status"] == "Applied" for j in jobs)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total applications", total)
    c2.metric("Applied", applied)
    c3.metric("Interviews", interviews)
    c4.metric("Offers", offers)

    st.subheader("Manage your applications")

    if not jobs:
        st.info("No jobs saved yet. Open Add Job to create your first entry.")
    else:
        for job in jobs:
            with st.container(border=True):
                left, middle, right = st.columns([3, 2, 1])

                with left:
                    st.markdown(f"**{job['title']}**")
                    st.write(job["company"])
                    st.caption(
                        f"Applied: {job['applied_date']} | ID: {job['id']}"
                    )
                    if job["link"]:
                        st.markdown(f"[Open job posting]({job['link']})")
                    if job["notes"]:
                        st.caption(job["notes"])

                with middle:
                    statuses = [
                        "Interested", "Applied", "Interview",
                        "Offer", "Rejected"
                    ]
                    current = (
                        statuses.index(job["status"])
                        if job["status"] in statuses else 0
                    )
                    new_status = st.selectbox(
                        "Status",
                        statuses,
                        index=current,
                        key=f"status_{job['id']}"
                    )
                    if new_status != job["status"]:
                        update_status(job["id"], new_status)
                        st.rerun()

                with right:
                    if st.button("Delete", key=f"delete_{job['id']}"):
                        delete_job(job["id"])
                        st.rerun()

with tab_add:
    st.subheader("Save a job opportunity")

    with st.form("add_job_form"):
        company = st.text_input("Company name *")
        title = st.text_input("Job title *")
        link = st.text_input("Job posting URL (optional)")
        applied_date = st.date_input(
            "Application date", value=date.today()
        )
        status = st.selectbox(
            "Current status",
            ["Interested", "Applied", "Interview", "Offer", "Rejected"]
        )
        notes = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("Save job")

        if submitted:
            if not company.strip() or not title.strip():
                st.error("Company name and job title are required.")
            elif link and not link.startswith(("https://", "http://")):
                st.error("Enter a valid URL beginning with http:// or https://.")
            else:
                add_job(
                    company.strip(), title.strip(), link.strip(),
                    applied_date, status, notes.strip()
                )
                st.success("Job saved successfully.")
                st.rerun()

with tab_analyze:
    st.subheader("Compare your resume with a job description")
    st.caption(
        "This is a basic keyword comparison, not an AI assessment "
        "or a guaranteed measure of job fit."
    )

    resume = st.text_area(
        "Paste resume text",
        height=200,
        placeholder="Paste your skills, projects, and experience here."
    )
    description = st.text_area(
        "Paste job description",
        height=200,
        placeholder="Paste the responsibilities and required skills here."
    )

    if st.button("Analyze skill match"):
        if not resume.strip() or not description.strip():
            st.warning("Please enter both your resume and the job description.")
        else:
            resume_skills = set(extract_skills(resume))
            required_skills = set(extract_skills(description))
            matched = sorted(resume_skills & required_skills)
            missing = sorted(required_skills - resume_skills)

            if required_skills:
                score = round(100 * len(matched) / len(required_skills))
                st.metric("Keyword overlap", f"{score}%")
            else:
                st.info(
                    "No supported skills were found. Add more skills "
                    "to the SKILLS list in app.py if needed."
                )

            a, b = st.columns(2)
            a.markdown("**Matching skills**")
            a.write(", ".join(matched) if matched else "No matches found.")
            b.markdown("**Skills to review**")
            b.write(", ".join(missing) if missing else "No missing keywords.")

            st.caption(
                "A missing keyword does not prove you lack a skill. "
                "Only add skills to your resume when they reflect your "
                "actual knowledge or experience."
            )

with tab_interview:
    st.subheader("Generate practice interview questions")

    role = st.text_input(
        "Target role", value="Associate DevOps Engineer"
    )
    chosen_skills = st.multiselect(
        "Topics to practice",
        SKILLS,
        default=["linux", "git", "docker", "kubernetes", "jenkins"]
    )
    count = st.slider("Number of questions", 5, 15, 10)

    if st.button("Generate questions"):
        questions = generate_questions(role, chosen_skills, count)
        for index, question in enumerate(questions, start=1):
            st.markdown(f"**{index}.** {question}")

st.divider()
st.caption(
    "Job Search Copilot | Personal project | "
    "Verify job details and keep your resume information private."
)
