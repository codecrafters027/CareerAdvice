# pages/6_Quiz.py
import streamlit as st
import requests

FASTAPI_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Skill Quiz", layout="wide")
st.title("📝 Skill Quiz")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Please login first.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

# --- Select Career ---
career = st.selectbox("Choose a career/skill for quiz:", ["Python", "SQL", "Data Scientist", "Web Developer"])
num_qs = st.slider("How many questions do you want?", 1, 5, 3)

if st.button("Get Quiz"):
    try:
        r = requests.get(
            f"{FASTAPI_URL}/quiz_questions",
            params={"career": career, "limit": num_qs},
            headers=headers
        )
        if r.status_code == 200:
            st.session_state["quiz_data"] = r.json()
            st.session_state["quiz_answers"] = {}
        else:
            st.error(r.json().get("detail", "Could not fetch quiz"))
    except Exception as e:
        st.error(f"Error fetching quiz: {e}")

# --- Render Quiz ---
if "quiz_data" in st.session_state:
    quiz = st.session_state["quiz_data"]
    answers = {}

    st.subheader(f"Quiz on {quiz['career']}")
    for idx, q in enumerate(quiz["questions"]):
        answers[str(idx)] = st.radio(
            q["q"], 
            q["options"], 
            key=f"q{idx}"
        )

    if st.button("Submit Quiz"):
        try:
            resp = requests.post(
                f"{FASTAPI_URL}/submit_quiz",
                json={"career": quiz["career"], "answers": answers},
                headers=headers
            )
            if resp.status_code == 200:
                res = resp.json()
                st.success(f"✅ You scored {res['score']} / {res['total']}")
            else:
                st.error(resp.json().get("detail", "Error submitting quiz"))
        except Exception as e:
            st.error(f"Error submitting answers: {e}")
