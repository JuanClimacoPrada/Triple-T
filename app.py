"""Entrada de la interfaz conversacional principal de Triple-T."""
import streamlit as st
from ui_chat import mostrar_chat

st.set_page_config(page_title="Triple-T | Análisis crediticio", layout="wide", initial_sidebar_state="auto")
mostrar_chat()
