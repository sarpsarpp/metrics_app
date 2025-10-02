#!/bin/bash
# Startup script for Composite Fundamentals app

cd "$(dirname "$0")"

echo "Starting Composite Fundamentals app..."
streamlit run app.py
