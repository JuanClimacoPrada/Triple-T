"""Entrada de la interfaz conversacional principal de Triple-T."""
import streamlit as st
from ui_chat import mostrar_chat

st.set_page_config(page_title="Triple-T | Asistente de análisis crediticio", page_icon="💬", layout="centered", initial_sidebar_state="collapsed")
mostrar_chat()
