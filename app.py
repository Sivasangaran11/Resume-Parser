import streamlit as st
import requests
import json

# FastAPI backend URL
BACKEND_URL = "http://127.0.0.1:8000"

st.title("PDF Email Extractor")
uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    files = {"file": uploaded_file.getvalue()}
    response = requests.post(f"{BACKEND_URL}/upload/", files=files)

    if response.status_code == 200:
        data = response.json()
        st.success("File uploaded successfully!")
        st.write("Extracted Emails:")
        st.json(data["emails"])
    else:
        st.error(f"Error: {response.json()['detail']}")

# List all PDFs in the database
if st.button("List All PDFs"):
    response = requests.get(f"{BACKEND_URL}/pdf")

    if response.status_code == 200:
        data = response.json()
        st.write("All PDFs in the database:")
        st.json(data["pdfs"])
    else:
        st.error(f"Error: {response.json()['detail']}")
