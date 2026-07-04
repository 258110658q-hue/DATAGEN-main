"""Hugging Face Spaces 入口 — 重定向到 frontend/streamlit_app.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runpy
runpy.run_path(os.path.join("frontend", "streamlit_app.py"))
