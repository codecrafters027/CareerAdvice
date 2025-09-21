# pages/7_Interview.py
import streamlit as st
import requests

FASTAPI_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Mock Interview", layout="wide")
st.title("🎤 Mock Interview Simulator")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Please login first.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

career = st.selectbox("Choose career for interview:", ["Data Scientist", "Web Developer", "AI Engineer", "Product Manager"])
if st.button("Get Questions"):
    r = requests.get(f"{FASTAPI_URL}/interview_questions", params={"career": career}, headers=headers)
    if r.status_code == 200:
        st.session_state["interview_qs"] = r.json()["questions"]
    else:
        st.error("Could not fetch interview questions")

if "interview_qs" in st.session_state:
    st.subheader(f"Mock Interview for {career}")
    answers = []
    for idx, q in enumerate(st.session_state["interview_qs"]):
        ans = st.text_area(f"Q{idx+1}: {q}", key=f"ans{idx}")
        answers.append(ans)

    if st.button("Submit Answers"):
        resp = requests.post(f"{FASTAPI_URL}/interview_feedback",
                             params={"career": career},
                             json={"answers": answers},
                             headers=headers)
        if resp.status_code == 200:
            feedback = resp.json()["feedback"]
            st.subheader("Feedback")
            for fb in feedback:
                st.write(f"Answer: {fb['answer']}")
                st.success(f"Keywords matched: {', '.join(fb['keywords_matched']) or 'None'}")
        else:
            st.error("Error getting feedback")
