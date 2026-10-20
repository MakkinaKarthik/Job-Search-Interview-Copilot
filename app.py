
import re
import sqlite3
from pathlib import Path
from datetime import date

import streamlit as st


# ==================================================
# 1. CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="CareerPilot | Job Search Copilot",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path(__file__).parent / "jobs.db"

SKILLS = [
    "python", "sql", "linux", "ubuntu", "git", "github",
    "azure", "aws", "docker", "kubernetes", "jenkins",
    "ansible", "bash", "terraform", "ci/cd", "networking",
    "troubleshooting", "flask", "streamlit", "mysql",
    "communication", "problem solving",
]

STATUSES = [
    "Interested", "Applied", "Interview", "Offer", "Rejected"
]


# ==================================================
# 2. PROFESSIONAL UI STYLING
# ==================================================

st.markdown("""
<style>
.stApp {
    background-color: #f5f7fc;
    color: #172033;
}

.block-container {
    max-width: 1450px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    color: #18213b;
    letter-spacing: -0.5px;
}

h1 {
    font-weight: 800;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #151b35, #28205b);
}

[data-testid="stSidebar"] * {
    color: #f8fafc;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e5e9f2;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 18px rgba(30, 41, 59, 0.04);
}

[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: #5145cd !important;
    font-weight: 800;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: white;
    border-color: #e5e9f2;
    border-radius: 15px;
}

[data-testid="stForm"] {
    background: white;
    border: 1px solid #e5e9f2;
    border-radius: 16px;
    padding: 22px;
}

.stButton > button,
.stFormSubmitButton > button {
    background: #5546d7;
    color: white;
    border: none;
    border-radius: 10px;
    min-height: 42px;
    font-weight: 650;
    transition: 0.2s ease;
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background: #4334bd;
    color: white;
    border: none;
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    border-radius: 10px;
    border-color: #dce2ef;
    background: white;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    border-bottom: 1px solid #e1e6f0;
}

.stTabs [data-baseweb="tab"] {
    padding: 12px 14px;
    font-weight: 600;
}

[data-testid="stAlert"] {
    border-radius: 12px;
}

hr {
    border-color: #e4e8f1;
}

@media (max-width: 768px) {
    .block-container {
        padding: 1rem;
    }

    h1 {
        font-size: 1.8rem !important;
    }

    [data-testid="stMetric"] {
        padding: 12px;
    }
}
</style>
""", unsafe_allow_html=True)


# ==================================================
# 3. DATABASE
# ==================================================

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
        """, (
            company, title, link, str(applied_date), status, notes
        ))


def get_jobs():
    with connect_db() as conn:
        return conn.execute("""
            SELECT * FROM jobs
            ORDER BY applied_date DESC, id DESC
        """).fetchall()


def update_status(job_id, status):
    with connect_db() as conn:
        conn.execute(
            "UPDATE jobs SET status = ? WHERE id = ?",
            (status, job_id),
        )


def delete_job(job_id):
    with connect_db() as conn:
        conn.execute(
            "DELETE FROM jobs WHERE id = ?",
            (job_id,),
        )


initialize_db()


# ==================================================
# 4. RESUME MATCHING
# ==================================================

def extract_skills(text):
    text = text.lower()
    found = []

    for skill in SKILLS:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"

        if re.search(pattern, text):
            found.append(skill)

    return sorted(found)


# ==================================================
# 5. INTERVIEW QUESTIONS
# ==================================================

def generate_questions(role, skills, count):
    questions = [
        f"Explain your understanding of the {role} role.",
        "Tell me about a technical problem you solved.",
        "Describe a mistake you made and what you learned.",
        "Why are you interested in this position?",
        "Explain one project you have built.",
        "How do you troubleshoot an unfamiliar problem?",
        "How do you prioritize multiple tasks?",
        "What would you like to learn in your first 90 days?",
    ]

    for skill in skills:
        questions.append(
            f"Explain {skill} and give a practical example of its use."
        )

    return questions[:count]


# ==================================================
# 6. SIDEBAR
# ==================================================

with st.sidebar:
    st.markdown("# CareerPilot")
    st.caption("YOUR PERSONAL CAREER WORKSPACE")
    st.divider()

    st.markdown("### 🚀 Your career journey")
    st.write(
        "Keep your applications organized, discover skill gaps, "
        "and prepare for interviews."
    )

    st.divider()
    st.markdown("### Quick overview")

    sidebar_jobs = get_jobs()

    st.write(f"📌 Saved jobs: {len(sidebar_jobs)}")
    st.write(
        "🎤 Interviews: "
        f"{sum(j['status'] == 'Interview' for j in sidebar_jobs)}"
    )
    st.write(
        "🏆 Offers: "
        f"{sum(j['status'] == 'Offer' for j in sidebar_jobs)}"
    )

    st.divider()
    st.caption("Built with Python and Streamlit")


# ==================================================
# 7. HERO SECTION - NATIVE STREAMLIT
# No HTML tags are used for the heading or description.
# ==================================================

st.caption("YOUR PERSONAL CAREER WORKSPACE")
st.title("Land your next opportunity.")
st.write(
    "Track applications, discover skill gaps, and prepare "
    "for interviews, all in one place."
)

st.divider()


# ==================================================
# 8. NAVIGATION
# ==================================================

dashboard_tab, add_tab, resume_tab, interview_tab = st.tabs([
    "📊 Dashboard",
    "➕ Add Job",
    "🧠 Resume Analyzer",
    "🎤 Interview Studio",
])


# ==================================================
# 9. DASHBOARD
# ==================================================

with dashboard_tab:
    jobs = get_jobs()

    st.subheader("Your job search overview")
    st.caption("A quick look at your career progress.")

    total = len(jobs)
    applied = sum(j["status"] == "Applied" for j in jobs)
    interviews = sum(j["status"] == "Interview" for j in jobs)
    offers = sum(j["status"] == "Offer" for j in jobs)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total opportunities", total)
    c2.metric("Applications sent", applied)
    c3.metric("Interviews", interviews)
    c4.metric("Offers", offers)

    st.write("")
    st.subheader("Application progress")

    if total:
        processed = sum(
            j["status"] in ["Applied", "Interview", "Offer", "Rejected"]
            for j in jobs
        )
        progress = processed / total

        st.progress(
            progress,
            text=f"{round(progress * 100)}% of saved jobs processed",
        )
    else:
        st.info(
            "Welcome! Add your first opportunity to start "
            "building your job search dashboard."
        )

    st.write("")
    st.subheader("Your opportunities")

    if not jobs:
        st.markdown(
            "Start by adding a job in the **Add Job** tab."
        )
    else:
        for job in jobs:
            with st.container(border=True):
                left, middle, right = st.columns([3, 2, 1])

                with left:
                    st.markdown(f"### {job['title']}")
                    st.write(f"🏢 {job['company']}")
                    st.caption(
                        f"Application date: {job['applied_date']} "
                        f"| Reference #{job['id']}"
                    )

                    if job["link"]:
                        st.markdown(
                            f"[View job posting]({job['link']})"
                        )

                    if job["notes"]:
                        st.caption(job["notes"])

                with middle:
                    current = (
                        STATUSES.index(job["status"])
                        if job["status"] in STATUSES else 0
                    )

                    new_status = st.selectbox(
                        "Application status",
                        STATUSES,
                        index=current,
                        key=f"status_{job['id']}",
                    )

                    if new_status != job["status"]:
                        update_status(job["id"], new_status)
                        st.rerun()

                with right:
                    st.write("")
                    if st.button(
                        "Delete",
                        key=f"delete_{job['id']}",
                        use_container_width=True,
                    ):
                        delete_job(job["id"])
                        st.rerun()


# ==================================================
# 10. ADD JOB
# ==================================================

with add_tab:
    st.subheader("Add a new opportunity")
    st.write(
        "Save the important details now so you can track "
        "the application later."
    )

    with st.form("add_job_form"):
        company = st.text_input(
            "Company name *",
            placeholder="e.g. Microsoft",
        )

        title = st.text_input(
            "Job title *",
            placeholder="e.g. Associate DevOps Engineer",
        )

        link = st.text_input(
            "Job posting URL",
            placeholder="https://company.com/careers/job",
        )

        col1, col2 = st.columns(2)

        with col1:
            applied_date = st.date_input(
                "Application date",
                value=date.today(),
            )

        with col2:
            status = st.selectbox(
                "Current status",
                STATUSES,
            )

        notes = st.text_area(
            "Notes",
            placeholder="Skills to revise, recruiter details, follow-up...",
        )

        submitted = st.form_submit_button(
            "Save application",
            use_container_width=True,
        )

        if submitted:
            if not company.strip() or not title.strip():
                st.error("Company name and job title are required.")

            elif link and not link.startswith(("https://", "http://")):
                st.error("Enter a valid URL beginning with http:// or https://.")

            else:
                add_job(
                    company.strip(),
                    title.strip(),
                    link.strip(),
                    applied_date,
                    status,
                    notes.strip(),
                )
                st.success("Application saved successfully!")
                st.rerun()


# ==================================================
# 11. RESUME ANALYZER
# ==================================================

with resume_tab:
    st.subheader("Resume Analyzer")
    st.write(
        "Compare your resume against a job description "
        "to identify relevant skill keywords."
    )

    st.info(
        "This version uses keyword matching, not an AI model. "
        "The score is not a hiring probability or an ATS score."
    )

    resume = st.text_area(
        "Paste your resume text",
        height=200,
        placeholder="Your skills, projects, education, and experience...",
    )

    description = st.text_area(
        "Paste the job description",
        height=200,
        placeholder="Required skills, responsibilities, qualifications...",
    )

    if st.button("Analyze resume", use_container_width=True):
        if not resume.strip() or not description.strip():
            st.warning("Please enter both text fields.")
        else:
            resume_skills = set(extract_skills(resume))
            required_skills = set(extract_skills(description))

            matched = sorted(resume_skills & required_skills)
            missing = sorted(required_skills - resume_skills)

            if not required_skills:
                st.warning(
                    "No supported skills were found in the job description."
                )
            else:
                score = round(
                    100 * len(matched) / len(required_skills)
                )

                st.divider()
                st.subheader("Your analysis")

                a, b, c = st.columns(3)
                a.metric("Keyword overlap", f"{score}%")
                b.metric("Matching skills", len(matched))
                c.metric("Skills to review", len(missing))

                st.progress(score / 100)

                left, right = st.columns(2)

                with left:
                    st.markdown("#### ✅ Matching skills")
                    if matched:
                        for skill in matched:
                            st.write(f"• {skill.title()}")
                    else:
                        st.write("No matching keywords found.")

                with right:
                    st.markdown("#### 📚 Skills to review")
                    if missing:
                        for skill in missing:
                            st.write(f"• {skill.title()}")
                    else:
                        st.write("No missing supported keywords.")

                st.caption(
                    "Only add a skill to your resume if you genuinely "
                    "have that knowledge or experience."
                )


# ==================================================
# 12. INTERVIEW STUDIO
# ==================================================

with interview_tab:
    st.subheader("Interview Studio")
    st.write(
        "Create a practice session for your target role."
    )

    role = st.text_input(
        "Target job role",
        value="Associate DevOps Engineer",
    )

    chosen_skills = st.multiselect(
        "Topics to practice",
        SKILLS,
        default=[
            "linux", "git", "docker", "kubernetes", "jenkins"
        ],
    )

    count = st.slider(
        "Number of questions",
        min_value=5,
        max_value=15,
        value=10,
    )

    if st.button(
        "Generate questions",
        use_container_width=True,
    ):
        if not role.strip():
            st.warning("Please enter a target role.")
        else:
            questions = generate_questions(
                role.strip(),
                chosen_skills,
                count,
            )

            st.divider()
            st.subheader("Your practice session")

            for i, question in enumerate(questions, start=1):
                with st.container(border=True):
                    st.markdown(f"**Question {i}**")
                    st.write(question)

                    st.text_area(
                        "Write your practice answer",
                        key=f"answer_{i}_{role.strip()}",
                        placeholder="Write your answer here...",
                        height=100,
                    )

            st.info(
                "Practice explaining your answer aloud and use "
                "real examples from your own projects."
            )


# ==================================================
# 13. FOOTER
# ==================================================

st.divider()

st.caption(
    "CareerPilot · Organize your search. Practice with purpose."
)
