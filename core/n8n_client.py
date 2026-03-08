import os
import requests
import streamlit as st
from core.config import load_env

load_env()

def update_case_status(case_id, new_status, note=""):
    try:
        url = os.getenv("N8N_WEBHOOK_URL")

        payload = {
            "case_id": case_id,
            "new_status": new_status,
            "note": note
        }

        res = requests.post(
            url,
            json=payload,
            timeout=10
        )

        st.write("POST URL:", url)
        st.write("Payload:", payload)
        st.write("status_code:", res.status_code)
        st.write("response text:", res.text)

        return res.status_code == 200

    except Exception as e:
        st.error(f"เรียก n8n ไม่ได้: {e}")
        return False