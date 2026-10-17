import pandas as pd
from typing import Dict, Any, List

def generate_profile(df: pd.DataFrame, file_id: str, filename: str,
                     t0p_dirty_limit: int = 10) -> Dict[str, Any]:
    '''
    Quét toàn bộ dataframe và tạo bản báo cáo:
    - Tổng dòng, tổng cột
    - Mỗi cột: kiểu dữ liệu, số ô null, %null, số giá trị unique, và 5 giá trị mẫu
    '''
    total_rows = len(df)
    total_columns = len(df.columns)

    columns_summary: List[Dict[str, Any]] = []

    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        null_pct = round((null_count / total_rows * 100), 2) if total_rows > 0 else 0.0

        samples = df[col].dropna().unique()[:5].tolist()

        columns_summary.append({
            "name": str(col),
            "dtype": str(df[col].dtype),
            "null_count": null_count,
            "null_percentage": null_pct,
            "unique_count": int(df[col].nunique()),
            "sample_values": [str(x) for x in samples]
        })
    columns_summary.sort(key=lambda x: x["null_percentage"], reverse = True)

    return {
    "file_id": file_id,
    "filename": filename,
    "total_rows": total_rows,
    "total_columns": total_columns,
    "columns": columns_summary
    }

def profile_single_column(df: pd.DataFrame, col_name: str) -> Dict[str, Any]:
    #khi người dùng muốn xem1 cột cụ thể

    if col_name not in df.columns:
        return {"error": f"Cột '{col_name}' không tồn tại không dữ liệu"}

    series = df[col_name]
    total_rows = len(df)
    null_count = int(series.isnull().sum())

    info: Dict[str, Any] = {
        "column_name": col_name,
        "dtype": str(series.dtype),
        "total_rows": total_rows,
        "null_count": null_count,
        "null_percentage": round((null_count / total_rows * 100), 2) if total_rows > 0 else 0.0,
        "unique_count": int(series.nunique())
    }

    if pd.api.types.is_numeric_dtype(series):
        clean_series = series.dropna()
        q1= float(clean_series.quantile(0.25)) if not clean_series.empty else 0.0
        q3 = float(clean_series.quantile(0.75)) if not clean_series.empty else 0.0        
        iqr = q3 - q1

        info["statistics"] = {
            "mean": round(float(clean_series.mean()), 2) if not clean_series.empty else None,
            "median": round(float(clean_series.median()), 2) if not clean_series.empty else None,
            "min": float(clean_series.min()) if not clean_series.empty else None,
            "max": float(clean_series.max()) if not clean_series.empty else None,
            "outlier_count": int(((clean_series < q1 - 1.5 * iqr) | (clean_series > q3 + 1.5 * iqr)).sum())}
    return info