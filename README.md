
## Overview
**DataSanitizer** is a web-based application designed to automate data preprocessing and cleaning tasks. In Data Science projects, data preparation often consumes up to 80% of the workflow. DataSanitizer solves this by providing an intuitive interface where users can upload raw datasets (CSV/Excel) and receive clean, model-ready data in seconds.

## Contributors
* **Nguyễn Hữu Luân** 
* **Đào Trung Phúc** 
* **Hoàng Hải Văn** 

## Core Features
The system provides a robust data processing pipeline with 4 main modules:
1. **Missing Value Treatment:** 
   - Automatically detects NaN/Null values.
   - Supports dropping rows/columns or imputing missing data using Mean, Median, Mode, or Interpolation.
2. **Outlier Detection:** 
   - Identifies and handles anomalous values using **IQR (Interquartile Range)** or **Z-Score** methods.
3. **Data Encoding & Scaling:**
   - Supports Label Encoding and One-Hot Encoding for categorical features.
   - Normalizes numerical data (Min-Max Scaler, Standard Scaler).
4. **Data Export:** Easily export the sanitized dataset to `.csv` or `.json` formats.

## Tech Stack
* **Backend:** Python, FastAPI, Uvicorn (API Routing & Server).
* **Data Engine:** Pandas, NumPy, Scikit-learn.
* **Frontend:** HTML, CSS, Vanilla JavaScript (Fetch API).

## 📁 Project Structure
```text
datasanitizer-project/
│
├── backend/
│   ├── main.py             # Main FastAPI server configuration
│   ├── routers/            # API endpoints (upload, clean, download)
│   └── services/
│       └── cleaner.py      # Pandas logic for data processing
│
├── frontend/
│   ├── index.html          # Main web interface
│   ├── style.css
│   └── script.js
│
├── data/                   # (Ignored by Git)
│   ├── raw/                # Uploaded raw files
│   └── processed/          # Sanitized output files
│
├── .gitignore
├── requirements.txt
└── README.md
