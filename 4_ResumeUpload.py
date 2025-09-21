# pages/4_ResumeUpload.py
import streamlit as st
import requests

FASTAPI_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Resume Upload")
st.title("📄 Resume Upload & Skill Extraction")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Please login first.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

uploaded = st.file_uploader("Upload your resume (PDF)", type=["pdf"])
if uploaded:
    files = {"file": ("resume.pdf", uploaded.read(), "application/pdf")}

    # --- Extract skills ---
    resp = requests.post(f"{FASTAPI_URL}/upload_resume", files=files, headers=headers)
    if resp.status_code == 200:
        out = resp.json()
        st.subheader("Extracted Skills")
        st.write(out.get("extracted_skills", []))
        st.subheader("Text Snippet")
        st.code(out.get("extracted_text_snippet", ""))

        # --- Analyze extracted skills directly ---
        if st.button("Analyze Extracted Skills"):
            skills = ", ".join(out.get("extracted_skills", []))
            r = requests.post(f"{FASTAPI_URL}/advise", json={"user_skills": skills}, headers=headers)
            if r.status_code == 200:
                st.session_state["latest_advice"] = r.json()
                st.success("Analysis complete — go to Career Advisor page to view")

        # --- Resume Enhancement ---
        st.subheader("✨ Resume Enhancement Suggestions")
        enh = requests.post(f"{FASTAPI_URL}/resume_enhance", files=files, headers=headers)
        if enh.status_code == 200:
            suggestions = enh.json().get("suggestions", [])
            if suggestions:
                for s in suggestions:
                    st.warning(f"⚡ {s}")
            else:
                st.success("✅ Your resume looks strong!")

            # Save resume enhancement to history (for badges)
            if st.button("Save Resume Analysis"):
                save_payload = {
                    "title": "Resume Analysis",
                    "payload": {"suggestions": suggestions, "skills": out.get("extracted_skills", [])}
                }
                r = requests.post(f"{FASTAPI_URL}/save", json=save_payload, headers=headers)
                if r.status_code == 201:
                    st.success("Resume analysis saved! (Check Dashboard for badges)")
                else:
                    st.error("Could not save analysis")

            # --- Export Enhanced Resume PDF ---
            if st.button("Export Enhanced Resume (PDF)"):
                pdf_payload = {
                    "title": "Enhanced Resume",
                    "skills": out.get("extracted_skills", []),
                    "suggestions": suggestions
                }
                r = requests.post(f"{FASTAPI_URL}/export_pdf", json=pdf_payload, headers=headers, stream=True)
                if r.status_code == 200:
                    st.download_button(
                        "📥 Download Enhanced Resume",
                        data=r.content,
                        file_name="enhanced_resume.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("Could not generate PDF")
        else:
            st.error("Resume enhancement failed")
