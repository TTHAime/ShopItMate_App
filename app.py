import streamlit as st
from core.config import load_env

load_env()

st.set_page_config(
    page_title="Shop IT Mate Admin",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Shop IT Mate — Admin Panel")
st.write("เลือกเมนูจาก sidebar ด้านซ้าย")