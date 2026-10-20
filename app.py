
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from pypdf import PdfReader
from google import genai


# =========================================================
# 1. CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "jobs.db"

STATUSES = [
    "Interested",
    "Applied",
    "Interview",
    "Offer",
    "Rejected",
]

SKILLS = [
    "python", "sql", "linux", "ubuntu", "git", "github",
    "azure", "aws", "docker", "kubernetes", "jenkins",
    "ansible", "bash", "terraform", "ci/cd", "networking",
    "troubleshooting", "flask", "streamlit", "mysql",
    "communication", "problem solving",
]

st.set_page_config(
    page_title="CareerPilot | Job Search Copilot",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# 2. CUSTOM STYLING
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f7f8fc;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }

    .hero {
        background: linear-gradient(120deg, #172554, #334b91);
        color: white;
        padding: 32px;
        border-radius: 18px;
        margin-bottom: 25px;
    }

    .hero-label {
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 2px;
        color: #bfdbfe;
        margin-bottom: 10px;
    }

    .hero h1 {
        color: white;
        font-size: clamp(28px, 4vw, 42px);
        margin: 0 0 10px 0;
    }

    .hero p {
        color: #e2e8f0;
        font-size: 16px;
        margin-bottom: 0;
    }

    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5e7eb;
        padding: 16px;
        border-radius: 12px;
    }

    div[data-testid="stForm"] {
        background: white;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 3. DATABASE FUNCTIONS
# =========================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def init_database():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                job_url TEXT,
                location TEXT,
                status TEXT NOT NULL DEFAULT 'Interested',
                applied_date TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Migrate older databases if these columns are missing.
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
        }

        if "company" not in columns:
            conn.execute(
                "ALTER TABLE jobs ADD COLUMN company TEXT NOT NULL DEFAULT ''"
            )

        if "role" not in columns:
            conn.execute(
                "ALTER TABLE jobs ADD COLUMN role TEXT NOT NULL DEFAULT ''"
            )

        for column in [
            "job_url", "location", "status", "applied_date", "notes",
        ]:
            if column not in columns:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {column} TEXT")

        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
        }

        # Copy values from older schema column names when available.
        if "title" in columns:
            conn.execute(
                """
                UPDATE jobs SET role = title
                WHERE (role IS NULL OR role = '') AND title IS NOT NULL
                """
            )

        if "job_title" in columns:
            conn.execute(
                """
                UPDATE jobs SET role = job_title
                WHERE (role IS NULL OR role = '')
                AND job_title IS NOT NULL
                """
            )

        if "company_name" in columns:
            conn.execute(
                """
                UPDATE jobs SET company = company_name
                WHERE (company IS NULL OR company = '')
                AND company_name IS NOT NULL
                """
            )


def add_job(company, role, job_url, location, status, applied_date, notes):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO jobs
            (company, role, job_url, location, status, applied_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company.strip(),
                role.strip(),
                job_url.strip(),
                location.strip(),
                status,
                str(applied_date) if applied_date else "",
                notes.strip(),
            ),
        )


def get_jobs():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, company, role, job_url, location,
                   status, applied_date, notes
            FROM jobs
            ORDER BY id DESC
            """
        ).fetchall()


def edit_job(
    job_id, company, role, job_url, location,
    status, applied_date, notes,
):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET company = ?, role = ?, job_url = ?, location = ?,
                status = ?, applied_date = ?, notes = ?
            WHERE id = ?
            """,
            (
                company.strip(),
                role.strip(),
                job_url.strip(),
                location.strip(),
                status,
                str(applied_date) if applied_date else "",
                notes.strip(),
                job_id,
            ),
        )


def update_job_status(job_id, status):
    with get_connection() as conn:
        conn.execute(
            "UPDATE jobs SET status = ? WHERE id = ?",
            (status, job_id),
        )


def delete_job(job_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


init_database()


# =========================================================
# 4. RESUME ANALYZER FUNCTIONS
# =========================================================

def extract_pdf_text(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )
    except Exception as exc:
        st.error(f"Could not read the PDF: {exc}")
        return ""


def extract_skills(text):
    text_lower = text.lower()
    found = []

    for skill in SKILLS:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        if re.search(pattern, text_lower):
            found.append(skill)

    return found


# =========================================================
# 5. GEMINI AI FUNCTION
# =========================================================

def ask_gemini(prompt):
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        api_key = ""

    if not api_key:
        return (
            "Gemini API key is not configured.\n\n"
            "Create `.streamlit/secrets.toml` and add:\n\n"
            'GEMINI_API_KEY = "your_api_key_here"\n\n'
            "Restart the application after configuring it."
        )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )

        return response.text or "The AI did not return any text."

    except Exception as exc:
        return (
            "The AI request failed. Check your API key, model availability, "
            f"network connection, and usage limits.\n\nDetails: {exc}"
        )


# =========================================================
# 6. SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("## 🎯 CareerPilot")
    st.caption("Your personal career workspace")
    st.divider()

    st.markdown("### Your workflow")
    st.write("1. Track job applications")
    st.write("2. Analyze your resume")
    st.write("3. Practice interviews")

    st.divider()
    st.caption("Built with Python, Streamlit and SQLite")


# =========================================================
# 7. HERO
# =========================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-label">YOUR PERSONAL CAREER WORKSPACE</div>
        <h1>Land your next opportunity.</h1>
        <p>
            Track applications, discover skill gaps, and prepare for
            interviews, all in one place.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 8. NAVIGATION TABS
# =========================================================

dashboard_tab, add_tab, resume_tab, interview_tab = st.tabs(
    [
        "📊 Dashboard",
        "➕ Add Job",
        "📄 Resume Analyzer",
        "🤖 Interview Studio",
    ]
)


# =========================================================
# 9. DASHBOARD
# =========================================================

with dashboard_tab:
    st.subheader("Your job search overview")

    jobs = get_jobs()

    total_jobs = len(jobs)
    interested_count = sum(1 for job in jobs if job[5] == "Interested")
    applied_count = sum(1 for job in jobs if job[5] == "Applied")
    interview_count = sum(1 for job in jobs if job[5] == "Interview")
    offer_count = sum(1 for job in jobs if job[5] == "Offer")
    rejected_count = sum(1 for job in jobs if job[5] == "Rejected")

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric("Total jobs", total_jobs)
    metric2.metric("Applied", applied_count)
    metric3.metric("Interviews", interview_count)
    metric4.metric("Offers", offer_count)

    with st.expander("View all status counts"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Interested", interested_count)
        c2.metric("Rejected", rejected_count)
        c3.metric(
            "Interview rate",
            f"{interview_count / total_jobs * 100:.1f}%"
            if total_jobs else "0%",
        )

    st.divider()
    st.subheader("Manage applications")

    search_text = st.text_input(
        "🔍 Search by company or job title",
        placeholder="For example, Python Developer or Microsoft",
        key="job_search",
    )

    status_filter = st.selectbox(
        "Filter by application status",
        ["All"] + STATUSES,
        key="job_status_filter",
    )

    filtered_jobs = [
        job for job in jobs
        if (
            search_text.strip().lower() in (job[1] or "").lower()
            or search_text.strip().lower() in (job[2] or "").lower()
        )
        and (
            status_filter == "All" or job[5] == status_filter
        )
    ]

    st.caption(
        f"Showing {len(filtered_jobs)} of {total_jobs} job applications"
    )

    if not filtered_jobs:
        if not jobs:
            st.info(
                "You haven't added any jobs yet. "
                "Open the Add Job tab to record your first opportunity."
            )
        else:
            st.info("No jobs match your search or selected status.")

    for job in filtered_jobs:
        (
            job_id, company, role, job_url, location,
            status, applied_date, notes,
        ) = job

        with st.container(border=True):
            left, middle, right = st.columns([3, 2, 1])

            with left:
                st.markdown(f"**{role or 'Untitled role'}**")
                st.write(company or "Unknown company")

                if location:
                    st.caption(f"📍 {location}")

                if applied_date:
                    st.caption(f"Application date: {applied_date}")

                if notes:
                    st.caption(f"Notes: {notes}")

            with middle:
                st.caption("Application status")

                new_status = st.selectbox(
                    "Update status",
                    STATUSES,
                    index=(
                        STATUSES.index(status)
                        if status in STATUSES else 0
                    ),
                    key=f"status_{job_id}",
                    label_visibility="collapsed",
                )

                if new_status != status:
                    update_job_status(job_id, new_status)
                    st.rerun()

            with right:
                if job_url and job_url.strip():
                    clean_url = job_url.strip()

                    if clean_url.startswith(("https://", "http://")):
                        st.link_button(
                            "🔗 Open Job",
                            clean_url,
                            use_container_width=True,
                        )
                    else:
                        st.warning("Invalid job URL")
                else:
                    st.caption("No job link added")

                if st.button(
                    "🗑️ Delete",
                    key=f"delete_{job_id}",
                    use_container_width=True,
                ):
                    st.session_state[f"confirm_delete_{job_id}"] = True

            # Ask for confirmation before deleting a record.
            if st.session_state.get(f"confirm_delete_{job_id}", False):
                st.warning(
                    f"Delete the application for {company}, {role}? "
                    "This cannot be undone."
                )

                confirm_col, cancel_col = st.columns(2)

                with confirm_col:
                    if st.button(
                        "Confirm delete",
                        key=f"confirm_{job_id}",
                        type="primary",
                    ):
                        delete_job(job_id)
                        st.session_state.pop(
                            f"confirm_delete_{job_id}", None
                        )
                        st.rerun()

                with cancel_col:
                    if st.button(
                        "Cancel",
                        key=f"cancel_{job_id}",
                    ):
                        st.session_state.pop(
                            f"confirm_delete_{job_id}", None
                        )
                        st.rerun()

            # Edit existing application details.
            with st.expander("✏️ Edit job details"):
                try:
                    parsed_date = (
                        date.fromisoformat(applied_date)
                        if applied_date else date.today()
                    )
                except ValueError:
                    parsed_date = date.today()

                with st.form(f"edit_job_form_{job_id}"):
                    edit_company = st.text_input(
                        "Company name",
                        value=company or "",
                        key=f"edit_company_{job_id}",
                    )

                    edit_role = st.text_input(
                        "Job title / role",
                        value=role or "",
                        key=f"edit_role_{job_id}",
                    )

                    edit_url = st.text_input(
                        "Job posting URL",
                        value=job_url or "",
                        key=f"edit_url_{job_id}",
                    )

                    edit_location = st.text_input(
                        "Location",
                        value=location or "",
                        key=f"edit_location_{job_id}",
                    )

                    edit_status = st.selectbox(
                        "Application status",
                        STATUSES,
                        index=(
                            STATUSES.index(status)
                            if status in STATUSES else 0
                        ),
                        key=f"edit_status_{job_id}",
                    )

                    edit_date = st.date_input(
                        "Application date",
                        value=parsed_date,
                        key=f"edit_date_{job_id}",
                    )

                    edit_notes = st.text_area(
                        "Notes",
                        value=notes or "",
                        key=f"edit_notes_{job_id}",
                    )

                    save_edit = st.form_submit_button(
                        "Save changes",
                        use_container_width=True,
                    )

                    if save_edit:
                        if not edit_company.strip() or not edit_role.strip():
                            st.error(
                                "Company name and job title are required."
                            )
                        elif edit_url.strip() and not edit_url.strip().startswith(
                            ("https://", "http://")
                        ):
                            st.error(
                                "Enter a valid job URL beginning with "
                                "http:// or https://, or leave it blank."
                            )
                        else:
                            edit_job(
                                job_id,
                                edit_company,
                                edit_role,
                                edit_url,
                                edit_location,
                                edit_status,
                                edit_date,
                                edit_notes,
                            )
                            st.success("Job application updated.")
                            st.rerun()


# =========================================================
# 10. ADD JOB
# =========================================================

with add_tab:
    st.subheader("Add a job opportunity")
    st.write("Keep your job search organized in one place.")

    with st.form("add_job_form", clear_on_submit=True):
        company = st.text_input("Company name *")
        role = st.text_input("Job title / role *")
        job_url = st.text_input("Job posting URL")
        location = st.text_input("Location")
        status = st.selectbox("Application status", STATUSES)
        applied_date = st.date_input(
            "Application date",
            value=date.today(),
        )
        notes = st.text_area(
            "Notes",
            placeholder=(
                "Recruiter details, skills required, "
                "follow-up reminders..."
            ),
        )

        submitted = st.form_submit_button(
            "Save job application",
            use_container_width=True,
        )

        if submitted:
            if not company.strip() or not role.strip():
                st.error(
                    "Please enter both the company name and job title."
                )
            elif job_url.strip() and not job_url.strip().startswith(
                ("https://", "http://")
            ):
                st.error(
                    "Enter a valid job URL beginning with http:// "
                    "or https://, or leave it blank."
                )
            else:
                add_job(
                    company,
                    role,
                    job_url,
                    location,
                    status,
                    applied_date,
                    notes,
                )
                st.success("Job application saved successfully.")
                st.rerun()


# =========================================================
# 11. RESUME ANALYZER
# =========================================================

with resume_tab:
    st.subheader("Resume Analyzer")
    st.write(
        "Upload your resume and compare your skills with a job description."
    )

    uploaded_resume = st.file_uploader(
        "Upload your resume in PDF format",
        type=["pdf"],
        key="resume_upload",
    )

    job_description = st.text_area(
        "Paste the job description",
        height=220,
        placeholder="Paste the complete job description here...",
    )

    if st.button("Analyze resume", key="analyze_resume"):
        if uploaded_resume is None:
            st.warning("Please upload a PDF resume first.")
        elif not job_description.strip():
            st.warning("Please paste a job description first.")
        else:
            resume_text = extract_pdf_text(uploaded_resume)

            if not resume_text.strip():
                st.error(
                    "No readable text was found. "
                    "If this is a scanned PDF, you may need OCR."
                )
            else:
                resume_skills = set(extract_skills(resume_text))
                required_skills = set(extract_skills(job_description))

                matched = sorted(resume_skills & required_skills)
                missing = sorted(required_skills - resume_skills)

                st.markdown("### Analysis results")

                col1, col2, col3 = st.columns(3)
                col1.metric("Skills in resume", len(resume_skills))
                col2.metric("Matched skills", len(matched))
                col3.metric("Potential skill gaps", len(missing))

                if matched:
                    st.markdown("#### ✅ Matching skills")
                    st.write(", ".join(matched))

                if missing:
                    st.markdown("#### 📚 Skills to work on")
                    st.write(", ".join(missing))
                else:
                    st.success(
                        "All detected skills from the job description "
                        "also appear in your resume."
                    )

                with st.expander("View extracted resume text"):
                    st.text(resume_text[:12000])

                if st.button("Get AI resume feedback"):
                    prompt = f"""
                    Act as a practical resume reviewer for an entry-level
                    candidate.

                    Compare the resume with the job description.
                    Give honest, specific feedback in these sections:
                    1. Strong matches
                    2. Missing skills
                    3. Resume improvements
                    4. Suggested projects or learning priorities
                    5. Three concrete next steps

                    Do not invent qualifications or experience.

                    RESUME:
                    {resume_text[:12000]}

                    JOB DESCRIPTION:
                    {job_description[:10000]}
                    """

                    with st.spinner("Reviewing your resume..."):
                        feedback = ask_gemini(prompt)

                    st.markdown("### AI feedback")
                    st.markdown(feedback)


# =========================================================
# 12. INTERVIEW STUDIO
# =========================================================

with interview_tab:
    st.subheader("AI Interview Studio")
    st.write(
        "Generate practice questions and receive feedback on your answers."
    )

    target_role = st.text_input(
        "Target job role",
        placeholder="For example, Associate DevOps Engineer",
    )

    experience_level = st.selectbox(
        "Experience level",
        ["Fresher", "Entry-level", "Intermediate"],
    )

    interview_type = st.selectbox(
        "Interview type",
        [
            "Technical",
            "HR",
            "Scenario-based",
            "Mixed",
        ],
    )

    if st.button(
        "Generate interview questions",
        use_container_width=True,
    ):
        if not target_role.strip():
            st.warning("Please enter a target job role.")
        else:
            prompt = f"""
            Act as an experienced interviewer.

            Create 10 interview practice questions for:
            Role: {target_role}
            Experience level: {experience_level}
            Interview type: {interview_type}

            Include a balanced set appropriate for the selected type.
            Number the questions clearly.
            For technical or scenario-based interviews, include practical
            troubleshooting questions where relevant.
            Do not provide answers yet.
            """

            with st.spinner("Generating interview questions..."):
                questions = ask_gemini(prompt)

            st.session_state["interview_questions"] = questions

    if st.session_state.get("interview_questions"):
        st.markdown("### Practice questions")
        st.markdown(st.session_state["interview_questions"])

        st.divider()
        st.markdown("### Practice your answer")

        question_to_practice = st.text_area(
            "Paste one question",
            placeholder="Select a question from the list above...",
        )

        practice_answer = st.text_area(
            "Your answer",
            height=200,
            placeholder="Write your answer as if you were in an interview...",
        )

        if st.button("Review my answer"):
            if not question_to_practice.strip() or not practice_answer.strip():
                st.warning(
                    "Enter both the interview question and your answer."
                )
            else:
                prompt = f"""
                Act as a supportive but honest interview coach.

                Job role: {target_role}
                Experience level: {experience_level}

                Interview question:
                {question_to_practice}

                Candidate answer:
                {practice_answer}

                Evaluate the answer in these sections:
                1. What was good
                2. What needs improvement
                3. Technical or factual gaps
                4. A stronger sample answer appropriate for the candidate's
                   experience level
                5. One practical tip for the next attempt

                Do not claim that the candidate has experience they did
                not mention. Keep the feedback specific and constructive.
                """

                with st.spinner("Reviewing your answer..."):
                    feedback = ask_gemini(prompt)

                st.markdown("### Interview feedback")
                st.markdown(feedback)


# =========================================================
# 13. FOOTER
# =========================================================

st.divider()

st.caption(
    "CareerPilot | Job Search and Interview Copilot | "
    "Built with Python, Streamlit, SQLite and Gemini"
)
