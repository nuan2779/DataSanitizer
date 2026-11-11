@echo off
title DataSanitizer Launcher
echo ========================================================
echo       KHOI DONG HE THONG DATASANITIZER 2.0
echo ========================================================
echo.
echo 1. Dang khoi dong Backend FastAPI tai cong 8000...
start "DataSanitizer Backend (Port 8000)" cmd /k "python -m uvicorn backend.main:app --reload --port 8000"

echo 2. Dang khoi dong Frontend Web tai cong 5500...
start "DataSanitizer Frontend (Port 5500)" cmd /k "python -m http.server 5500 -d frontend"

echo 3. Cho 2 giay de server san sang...
timeout /t 2 /nobreak > nul

echo 4. Dang mo trinh duyet toi http://127.0.0.1:5500...
start http://127.0.0.1:5500

echo.
echo ========================================================
echo He thong da khoi dong thanh cong!
echo - Web App: http://127.0.0.1:5500
echo - API Docs (Swagger): http://127.0.0.1:8000/docs
echo (Khong tat 2 cua so console Backend & Frontend de giu ket noi)
echo ========================================================
pause
