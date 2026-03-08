import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import load_env

load_env()

def build_db_url():
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"

@st.cache_resource
def get_engine():
    return create_engine(
        build_db_url(),
        pool_pre_ping=True,
        future=True
    )

@st.cache_resource
def get_session_factory():
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        future=True
    )

def get_session():
    SessionLocal = get_session_factory()
    return SessionLocal()