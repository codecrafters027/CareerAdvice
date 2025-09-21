# pages/1_Login.py
import streamlit as st
import requests

FASTAPI_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Login", layout="centered")
st.title("🔐 Login / Register")

if "token" not in st.session_state:
    st.session_state["token"] = None
if "user_email" not in st.session_state:   # 👈 renamed to avoid conflict
    st.session_state["user_email"] = None

tab = st.radio("Action", ["Login", "Register"])

# Widget inputs (use unique keys)
email = st.text_input("Email", key="login_email")
password = st.text_input("Password", type="password", key="login_password")

if st.button("Submit"):
    if tab == "Register":
        try:
            r = requests.post(f"{FASTAPI_URL}/register", json={"email": email, "password": password})
            if r.status_code == 201:
                st.success("Registered — now login")
            else:
                st.error(r.json().get("detail", r.text))
        except Exception as e:
            st.error(f"Error: {e}")
    else:  # Login
        try:
            r = requests.post(f"{FASTAPI_URL}/token", data={"username": email, "password": password})
            if r.status_code == 200:
                token = r.json()["access_token"]
                st.session_state["token"] = token
                st.session_state["user_email"] = email   # 👈 store separately
                st.success("Logged in")
            else:
                st.error("Login failed")
        except Exception as e:
            st.error(f"Error: {e}")
