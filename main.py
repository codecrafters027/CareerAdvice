# main.py
import streamlit as st

st.set_page_config(page_title="AI Career Advisor", layout="wide")
st.title("AI Career Advisor")
st.write("Use the left sidebar to navigate: Login → Career Advisor → Dashboard → Resume Upload → Settings")
st.markdown("""
**Pages**
- Login / Register -> `Login`
- Career Advisor -> `CareerAdvisor`
- Dashboard -> `Dashboard`
- Resume Upload -> `ResumeUpload`
- Settings -> `Settings`
""")
