import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

def compute_data_quality_score(df: pd.DataFrame, initial_rows: Optional[int] = None) -> Dict[str, Any]:
    """
    Tính toán chỉ số Chất lượng & Độ vệ sinh dữ liệu (Data Quality & Hygiene Score)
    thang điểm 0 - 100 điểm, đánh giá mức độ sạch của dữ liệu sau tiền xử lý:
    
    1. Completeness (0-30 điểm): Tỷ lệ các ô dữ liệu không bị Null/NaN.
    2. Deduplication (0-20 điểm): Tỷ lệ dữ liệu không bị trùng lặp dòng (Duplicate Rows).
    3. Type Uniformity (0-25 điểm): Tỷ lệ các cột đã được chuẩn hóa số học hoặc phân loại (không lẫn chuỗi rác).
    4. Data Retention (0-25 điểm): Tỷ lệ bảo toàn số dòng hợp lý (tránh việc drop quá đà làm mất dữ liệu).
    """
    total_cells = df.size
    if total_cells == 0 or len(df) == 0:
        return {
            "overall_score": 0.0,
            "rating": "Dữ liệu rỗng",
            "badge_color": "danger",
            "breakdown": {
                "completeness_score": 0.0,
                "missing_cell_rate": 100.0,
                "deduplication_score": 0.0,
                "duplicate_rate": 0.0,
                "type_uniformity_score": 0.0,
                "numeric_or_cat_columns": 0,
                "total_columns": len(df.columns),
                "retention_score": 0.0,
                "retention_rate": 0.0
            },
            "diagnostics": {
                "zero_variance_columns": [],
                "high_cardinality_text_columns": []
            }
        }

    # 1. Completeness (30 pts)
    null_count = int(df.isnull().sum().sum())
    missing_rate = (null_count / total_cells) * 100
    completeness_score = max(0.0, 30.0 * (1.0 - (null_count / total_cells)))

    # 2. Deduplication (20 pts)
    dup_count = int(df.duplicated().sum())
    dup_rate = (dup_count / len(df)) * 100 if len(df) > 0 else 0.0
    dedup_score = max(0.0, 20.0 * (1.0 - (dup_count / len(df)))) if len(df) > 0 else 0.0

    # 3. Type Uniformity (25 pts) - tỷ lệ các cột đã là số hoặc category
    numeric_or_cat = sum(1 for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) or isinstance(df[c].dtype, pd.CategoricalDtype))
    type_uniformity_rate = (numeric_or_cat / len(df.columns)) * 100 if len(df.columns) > 0 else 0.0
    type_score = 25.0 * (numeric_or_cat / len(df.columns)) if len(df.columns) > 0 else 0.0

    # 4. Retention (25 pts) - tỷ lệ bảo toàn dòng
    if initial_rows and initial_rows > 0:
        retention_ratio = len(df) / initial_rows
        retention_score = min(25.0, 25.0 * (retention_ratio / 0.8)) if retention_ratio >= 0.8 else max(0.0, 25.0 * retention_ratio)
        retention_rate = retention_ratio * 100
    else:
        retention_score = 25.0
        retention_rate = 100.0

    overall = round(completeness_score + dedup_score + type_score + retention_score, 1)

    if overall >= 90:
        rating = "Xuất sắc (Dữ liệu cực sạch)"
        badge_color = "success"
    elif overall >= 75:
        rating = "Tốt (Đạt chuẩn phân tích & mô hình)"
        badge_color = "primary"
    elif overall >= 50:
        rating = "Trung bình (Cần làm sạch thêm)"
        badge_color = "warning"
    else:
        rating = "Kém (Dữ liệu còn nhiều ô trống/lỗi)"
        badge_color = "danger"

    # Kiểm tra chuẩn đoán bổ sung (Diagnostics)
    zero_var_cols = [c for c in df.columns if df[c].nunique() <= 1]
    high_card_text = [c for c in df.columns if df[c].dtype == "object" and df[c].nunique() > 50]

    return {
        "overall_score": overall,
        "rating": rating,
        "badge_color": badge_color,
        "breakdown": {
            "completeness_score": round(completeness_score, 1),
            "missing_cell_rate": round(missing_rate, 2),
            "deduplication_score": round(dedup_score, 1),
            "duplicate_rate": round(dup_rate, 2),
            "type_uniformity_score": round(type_score, 1),
            "numeric_or_cat_columns": numeric_or_cat,
            "total_columns": len(df.columns),
            "retention_score": round(retention_score, 1),
            "retention_rate": round(retention_rate, 1)
        },
        "diagnostics": {
            "zero_variance_columns": zero_var_cols,
            "high_cardinality_text_columns": high_card_text
        }
    }
