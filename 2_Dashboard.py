# pages/2_Dashboard.py
import streamlit as st
import requests
import plotly.express as px
import pandas as pd

FASTAPI_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Dashboard", layout="wide")
st.title("📊 Dashboard")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Please login first.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

# --- Saved Recommendations History ---
r = requests.get(f"{FASTAPI_URL}/history", headers=headers)
if r.status_code == 200:
    hist = r.json().get("history", [])
    if hist:
        st.subheader("Saved Recommendations")
        for it in hist:
            st.markdown(f"**{it['title']}** — {it['created_at']}")
            top = it["data"].get("top_careers", [])
            if top:
                st.write(f"Top: {top[0]['career']} — {top[0]['match_score']}%")
            st.markdown("---")

        # Histogram of match scores
        scores = [h["data"]["top_careers"][0]["match_score"] for h in hist if h["data"].get("top_careers")]
        fig = px.histogram(scores, nbins=8, title="Saved Top Match Scores")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No saved recommendations yet.")
else:
    st.error("Could not fetch history.")

# --- Badges ---
b = requests.get(f"{FASTAPI_URL}/badges", headers=headers)
if b.status_code == 200:
    badges = b.json().get("badges", [])
    st.subheader("🏅 Badges")
    if badges:
        for bd in badges:
            st.success(f"{bd['name']} — earned at {bd['earned_at']}")
    else:
        st.info("No badges yet. Save a recommendation to earn badges.")

# --- Job Trends ---
st.subheader("📈 Job Trends")
q = st.text_input("Check job trend for (skill/career)", value="Data Scientist")
if st.button("Get Job Trends"):
    jt = requests.get(f"{FASTAPI_URL}/job_trends", params={"q": q})
    if jt.status_code == 200:
        trend = jt.json()["trend"]
        df = pd.DataFrame(trend)
        st.line_chart(df.set_index("date"))

# --- Quiz Scores ---
st.subheader("📝 Quiz Performance")
quiz_scores = requests.get(f"{FASTAPI_URL}/history", headers=headers)  # reuse? or create /quiz_history later
# If you add /quiz_history endpoint in api.py, replace above with that.
try:
    qh = requests.get(f"{FASTAPI_URL}/quiz_scores", headers=headers)
    if qh.status_code == 200:
        data = qh.json().get("scores", [])
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df)
            fig2 = px.bar(df, x="created_at", y="score", color="career", title="Quiz Scores Over Time")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No quiz attempts yet.")
except:
    st.info("Quiz scores not available (check API).")

# --- Career Comparison ---
st.subheader("⚖️ Compare Careers")
c1 = st.selectbox("Career 1", list(headers) if 'career_db' in globals() else ["Data Scientist","Web Developer","AI Engineer","Product Manager"], key="c1")
c2 = st.selectbox("Career 2", ["Web Developer","AI Engineer","Product Manager","Data Scientist"], key="c2")

if st.button("Compare"):
    comp = requests.get(f"{FASTAPI_URL}/compare_careers", params={"c1": c1, "c2": c2}, headers=headers)
    if comp.status_code == 200:
        data = comp.json()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"### {data['career1']['name']}")
            st.write("Required Skills:", ", ".join(data['career1']['required_skills']))
            st.write("Roadmap:", " → ".join(data['career1']['roadmap']))
            st.info(f"Salary Estimate: {data['salary_estimates'][c1]}")
        with col2:
            st.markdown(f"### {data['career2']['name']}")
            st.write("Required Skills:", ", ".join(data['career2']['required_skills']))
            st.write("Roadmap:", " → ".join(data['career2']['roadmap']))
            st.info(f"Salary Estimate: {data['salary_estimates'][c2]}")
    else:
        st.error("Could not fetch comparison")
