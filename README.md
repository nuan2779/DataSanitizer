# DataSanitizer

A browser-based CSV/XLSX profiling and cleaning demo built with FastAPI, Pandas,
scikit-learn and vanilla JavaScript.

## Team

- Nguyễn Hữu Luân
- Đào Trung Phúc
- Hoàng Hải Văn

## Setup (Windows PowerShell, Python 3.11)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force -Path '.\data\raw', '.\data\processed' | Out-Null
```

Run in separate terminal windows from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

```powershell
.\.venv\Scripts\python.exe -m http.server 5500 -d frontend
```

- Web interface: http://127.0.0.1:5500/index.html
- API documentation: http://127.0.0.1:8000/docs

## API contract

- `POST /api/upload`: multipart field `file`, returns `file_id`.
- `GET /api/profile/{file_id}`: dataset summary.
- `GET /api/profile/{file_id}/{col_name}`: column statistics.
- `POST /api/clean`: submit `file_id` and **ordered** `pipeline` steps from the UI;
  older four-option requests are still supported.
- `GET /api/download/{file_id}?file_format=csv` (or `json`).

Example clean request (the order matters):

```json
{
  "file_id": "00000000-0000-0000-0000-000000000001",
  "pipeline": [
    {"step_type":"standardize_nulls", "config":{}},
    {"step_type":"missing_values", "config":{"columns":["Age"], "strategy":"median"}},
    {"step_type":"encoding", "config":{"columns":["City"], "method":"one_hot"}}
  ]
}
```

The `/api/clean` response includes `audit_summary` with row/column counts, actual
logged steps, and history, plus `original_data` and `processed_data` metadata.
The steps available in the UI are `standardize_nulls`, `clean_numeric`,
`missing_values`, `outlier`, `encoding`, `scaling`, and `round`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
.\.venv\Scripts\python.exe test_adapter_currency.py
```

`tests/test_frontend_pipeline_contract.py` tests that the UI payload actually
runs the chosen steps (not merely returning HTTP 200).

## Project structure

```text
backend/
  main.py              FastAPI app and CORS
  schemas.py           Pydantic request models
  routers/             Upload / Profile / Clean / Download
  services/
    adapter.py         Legacy four-option cleaning adapter
    pipeline_runner.py Ordered pipeline + validation + safe currency conversion
    cleaner.py         Data processing engine
    profiler.py        Dataset and column profiling
frontend/
  index.html
  assets/css/
  assets/js/
tests/
data/raw/              Uploads; not committed
data/processed/        Processed datasets; not committed
```

## Important limits

- This is a local, educational prototype, **not** a multi-user production system.
  It does not implement authentication, authorization, data retention or session isolation.
- Currency conversion accepts non-ambiguous US-style number separators such as
  `$1,200.50` and `1,500 đ`. Ambiguous locale formats are rejected rather than
  silently guessed. The ordered UI pipeline converts currency only when the
  user adds a `clean_numeric` step for the relevant column(s).
- Data processing depends on step order. Select numeric columns for mean, median,
  interpolation, outlier processing and scaling. One-Hot may change the number
  of columns. Rows with genuine outliers may legitimately be dropped.
- The original uploaded file remains in `data/raw` on the local machine. Do not
  use the demo to upload confidential information.
