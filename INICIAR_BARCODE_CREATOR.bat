@echo off
title BARCODE-CREATOR - WHTP203E
cd /d "%~dp0"
py -m streamlit run app_barcode_creator.py
pause
