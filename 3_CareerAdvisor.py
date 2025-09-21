# pages/3_CareerAdvisor.py
import streamlit as st
import requests
from datetime import datetime
import plotly.graph_objects as go

FASTAPI_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Career Advisor", layout="wide")
st.title("🧭 Career Advisor")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Please login first on the Login page.")
    st.stop()

skills = st.text_area("Enter skills (comma separated)", value="Python, SQL")
if st.button("Get Advice"):
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    r = requests.post(f"{FASTAPI_URL}/advise", json={"user_skills": skills}, headers=headers)
    if r.status_code == 200:
        data = r.json()
        st.session_state["latest_advice"] = data
    else:
        st.error("API error")

if "latest_advice" in st.session_state:
    adv = st.session_state["latest_advice"]
    st.subheader("Top Careers")
    for idx, c in enumerate(adv["top_careers"], start=1):
        st.markdown(f"### {idx}. {c['career']} — {c['match_score']}%")
        st.write("Matched:", ", ".join(c["matched_skills"]) or "None")
        st.write("Missing:", ", ".join(c["missing_skills"]) or "None")
        fig = go.Figure(data=[go.Pie(labels=["Matched","Missing"], values=[len(c["matched_skills"]), len(c["missing_skills"])])])
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
    st.subheader("Tips")
    st.info(adv.get("personalized_tips", ""))

    # Save button
    if st.button("Save Recommendation"):
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}
        title = f"Advice {datetime.utcnow().isoformat()}"
        resp = requests.post(f"{FASTAPI_URL}/save", json={"title": title, "payload": adv}, headers=headers)
        if resp.status_code == 201:
            st.success("Saved")
        else:
            st.error("Save failed")
    if st.button("Export PDF (server)"):
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}
        resp = requests.post(f"{FASTAPI_URL}/export_pdf", json=st.session_state["latest_advice"], headers=headers, stream=True)
        if resp.status_code == 200:
            st.download_button("Download Report", data=resp.content, file_name="career_report.pdf", mime="application/pdf")
        else:
            st.error("Export failed")
