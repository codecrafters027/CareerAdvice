# pages/5_Settings.py
import streamlit as st

st.set_page_config(page_title="Settings")
st.title("⚙️ Settings")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Not signed in.")
else:
    st.write(f"Signed in as: {st.session_state.get('email')}")
    if st.button("Sign out"):
        st.session_state["token"] = None
        st.session_state["email"] = None
        st.success("Signed out")
