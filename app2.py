import streamlit as st
import requests
import os
import pdfplumber
import docx
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import csv

# ------------------ Azure AI ------------------
ENDPOINT = "https://hire-smart-mvp-resource.cognitiveservices.azure.com/openai/deployments/recruit-ai-gpt4/chat/completions?api-version=2025-01-01-preview"
API_KEY = "E9SGGXsfrRlyY4YsnFH7Qv0VjqHHRehRF3AVHyXpaUgYBvSzD9MWJQQJ99BJACHYHv6XJ3w3AAAAACOGGAHM"
HEADERS = {"Content-Type": "application/json", "api-key": API_KEY}

# ------------------ SMTP Email (Gmail) ------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "linkjune224@gmail.com"
EMAIL_PASSWORD = "ofwm lhxh cibp focw"  # App password

# ------------------ Utility Functions ------------------
def read_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def read_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def call_ai(prompt):
    try:
        body = {"messages":[{"role":"user","content":prompt}], "temperature":0.7, "max_tokens":600}
        response = requests.post(ENDPOINT, headers=HEADERS, json=body)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error calling AI: {str(e)}"

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)

# ------------------ Streamlit Frontend ------------------
st.set_page_config(page_title="AI Recruitment Assistant", layout="wide")
st.title("🚀 AI Recruitment Assistant")

# --- Initialize session state ---
for key in ["screened","ai_result","candidate_email","candidate_name","decision","interview_datetime"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ------------------ Candidate Screening ------------------
st.header("1️⃣ Candidate Screening")
col1, col2 = st.columns(2)
with col1:
    jd_file = st.file_uploader("Upload Job Description (DOCX)", type=["docx"])
with col2:
    resume_file = st.file_uploader("Upload Candidate Resume (DOCX or PDF)", type=["docx","pdf"])

st.session_state.candidate_name = st.text_input("Candidate Name")
st.session_state.candidate_email = st.text_input("Candidate Email")

if st.button("Screen Candidate"):
    if not jd_file or not resume_file or not st.session_state.candidate_email or not st.session_state.candidate_name:
        st.error("Please provide all required inputs: Name, Email, JD, and Resume.")
    else:
        jd_path = f"temp_jd.{jd_file.name.split('.')[-1]}"
        resume_path = f"temp_resume.{resume_file.name.split('.')[-1]}"
        with open(jd_path, "wb") as f:
            f.write(jd_file.getbuffer())
        with open(resume_path, "wb") as f:
            f.write(resume_file.getbuffer())

        st.info("Analyzing candidate...please wait")
        try:
            jd_text = read_docx(jd_path) if jd_path.endswith(".docx") else ""
            resume_text = ""
            if resume_path.endswith(".docx"):
                resume_text = read_docx(resume_path)
            elif resume_path.endswith(".pdf"):
                resume_text = read_pdf(resume_path)
            else:
                st.error("Resume must be DOCX or PDF")

            prompt = f"""
            You are an expert recruitment AI assistant.
            Compare candidate resume with job description.
            Give match score 0-100, 3 strengths, 3 weaknesses with proper line formatting.

            Resume:
            {resume_text}

            Job Description:
            {jd_text}
            """
            st.session_state.ai_result = call_ai(prompt)
            st.session_state.screened = True
        except Exception as e:
            st.error(f"Error analyzing candidate: {str(e)}")
        finally:
            if os.path.exists(jd_path):
                os.remove(jd_path)
            if os.path.exists(resume_path):
                os.remove(resume_path)

# Show AI analysis result
if st.session_state.screened:
    st.subheader("AI Screening Result")
    st.text_area("Evaluation Remarks", st.session_state.ai_result, height=300)

# ------------------ Recruiter Decision ------------------
if st.session_state.screened:
    st.header("2️⃣ Recruiter Decision")
    st.session_state.decision = st.radio("Decision:", ("Accept", "Reject"))

    if st.session_state.decision == "Accept":
        # Date + Hour/Minute selection
        interview_date = st.date_input(
            "Select Interview Date",
            datetime.now().date() + timedelta(days=1)
        )
        col1, col2 = st.columns(2)
        with col1:
            interview_hour = st.selectbox("Hour", list(range(0,24)), index=datetime.now().hour)
        with col2:
            interview_minute = st.selectbox("Minute", [0,15,30,45], index=(datetime.now().minute//15))

        st.session_state.interview_datetime = datetime.combine(interview_date, datetime.min.time()) + timedelta(hours=interview_hour, minutes=interview_minute)
        st.markdown(f"**Selected Interview:** {st.session_state.interview_datetime.strftime('%Y-%m-%d %H:%M')}")

    if st.button("Send Email / Schedule Interview"):
        if st.session_state.decision == "Accept" and not st.session_state.interview_datetime:
            st.error("Please select interview date and time.")
        else:
            if st.session_state.decision == "Accept":
                email_subject = "Interview Invitation"
                booking_link = f"https://outlook.office.com/bookwithme/user/531488e2b8b04506a16c3b4c0aa36f22@hypernymbiz.com/meetingtype/SVRwCe7HMUGxuT6WGxi68g2?start={st.session_state.interview_datetime.isoformat()}"
                email_body = f"""
                Dear {st.session_state.candidate_name},<br><br>
                Congratulations! You have been shortlisted for an interview.<br><br>
                Interview Date & Time: {st.session_state.interview_datetime.strftime('%Y-%m-%d %H:%M')}<br>
                Duration: 30 minutes<br>
                Schedule here: <a href="{booking_link}">Book Interview</a><br><br>
                <b>AI Evaluation Remarks:</b><br>{st.session_state.ai_result.replace('\n','<br>')}<br><br>
                Best Regards,<br>Recruitment Team
                """
            else:
                # Simple rejection email
                email_subject = "Application Update"
                email_body = f"""
                Dear {st.session_state.candidate_name},<br><br>
                Thank you for your application. After careful evaluation, we regret to inform you that you have not been selected for the role.<br><br>
                Best Regards,<br>Recruitment Team
                """

            sent, msg = send_email(st.session_state.candidate_email, email_subject, email_body)
            if sent:
                st.success(f"✅ Email sent successfully: {email_subject}")
            else:
                st.error(f"❌ Email sending failed: {msg}")

            # Save to CSV
            csv_file = "candidate_evaluation.csv"
            file_exists = os.path.isfile(csv_file)
            with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Name","Email","Decision","Interview DateTime","AI Evaluation"])
                writer.writerow([
                    st.session_state.candidate_name,
                    st.session_state.candidate_email,
                    st.session_state.decision,
                    st.session_state.interview_datetime.strftime('%Y-%m-%d %H:%M') if st.session_state.interview_datetime else "",
                    st.session_state.ai_result.replace('\n',' | ')
                ])

# ------------------ Refresh Button ------------------
if st.button("🔄 Refresh Page"):
    for key in st.session_state.keys():
        st.session_state[key] = None
