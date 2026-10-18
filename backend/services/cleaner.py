import pandas as pd 
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.preprocessing import LabelEncoder, StandardScaler, MinMaxScaler

class DataCleaner:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
    #Xử lí giá trị thiếu

    def handle_missing_values(
            self,
            columns: Optional[List[str]] = None,
            strategy: str = "mean",
            fill_value: Any = None
    ):
        '''
        Plan:
        - 'drop_row': Xóa các dòng có ô trống
        - 'drop_col': Xóa cả cột nếu có ô trống
        - 'mean': Điền giá trị trung bình (chỉ áp dụng cột số)
        - 'median': Điền trung vị (tốt hơn mean nếu dữ liệu bị lệch/có ngoại lai)
        - 'mode': Điền giá trị xuất hiện nhiều nhất (dùng cho cột phân loại/chữ)
        - 'constant': Điền một giá trị cố định tự chọn
        '''

        target_cols = columns if columns  else self.df.columns.tolist()

        if strategy == "drop_row":
            self.df = self.df.dropna(subset=target_cols)

        elif strategy == "drop_col":
            self.df = self.df.drop(columns=target_cols)
        elif strategy == "mean":
            for col in target_cols:
                # Kiểm tra xem cột có phải dạng số không
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    self.df[col] = self.df[col].fillna(self.df[col].mean())
        elif strategy == "median":
            for col in target_cols:
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    self.df[col] = self.df[target_cols].fillna(self.df[col].median())
        elif strategy == "mode":
            for col in target_cols:
                mode_val = self.df[col].model()
                if not mode_val.empty:
                    self.df[col] = self.df[col].fillna(mode_val[0])
        elif strategy == "interpolate":
            for col in target_cols:
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    # Nội suy tuyến tính
                    self.df[col] = self.df[col].interpolate(method="linear")
        elif strategy == "constant" and fill_value is not None:
            self.df[target_cols] = self.df[target_cols].fillna(fill_value)
        return self

    # Xử lí ngoại lai

    def handle_outliers(
            self,
            columns: List[str],
            method: str = "iqr",
            threshold: float = 1.5,
            handling: str = "remove"
    ):
        '''
        Phương pháp
        - 'iqr': Dùng khoảng tứ phân vị (Q1,Q3, IQR = Q3-Q1)
                 Lower Bound = Q1 - threshold * IQR
                 Upper Bound = Q3 + threshold * IQR
        -'Z_score': Đo đổ lệch chuẩn so với giá trị trung bình (|Z| > threshold)
                 Lower Bound = Mean - threshold * Std
                 Upper Bound = Mean + threshold * Std   
        Cách xử lý
        - remove : xóa các dòng ngoại lai
        - cap: cắt ngọn- giá trị quá lớn gần bằng trần, quá nhỏ gần bằng sàn    
        '''
        for col in columns:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                continue
            if method == "iqr":
                q1 = self.df[col].quantile(0.25)
                q3 = self.df[col].quantile(0.75)
                iqr = q3 -q1
                lower = q1 - threshold * iqr
                upper = q3 + threshold * iqr
            elif method == "z_score":
                mean = self.df[col].mean()
                std = self.df[col].std()
                if std == 0:
                    continue
                lower = mean - threshold*std
                upper = mean + threshold * std
            else:
                continue

            if handling == "remove":
                condition = ((self.df[col] >= lower) & (self.df[col] <= upper)) | self.df[col].isna()
                self.df = self.df[condition]
            elif handling == "cap":
                self.df[col] = np.clip(self.df[col], lower, upper)
        return self

    # Mã hóa phân loại
    def encode_categorical(self, columns: List[str], method: str = "label"):
        # Số hóa dữ liệu
        for col in columns:
            if col not in self.df.columns:
                continue
            if method == "label":
                le = LabelEncoder()
                #Ép kiểu sang chuỗi để tránh lỗi nếu có giá trị lẫn lội
                self.df[col] = le.fit_transform(self.df[col].astype(str))

            elif method == "one_hot":
                self.df = pd.get_dummies(self.df, columns=[col], prefix=col, drop_first=True)
        return self

    # Chuẩn hóa dữ liệu

    def scale_features(self, columns: List[str], method: str = "standard"):
        '''
        Đưa các cột về cùng 1 thang đo
        - standard : StandardScaler (Mean = 0, Variance = 1)
        - min_max: MinMaxScaler (Đưa giá trị về đoạn [0,1])
        '''

        valid_cols = [c for c in columns if c in self.df.columns and pd.api.types.is_numeric_dtype(self.df[c])]
        if not valid_cols:
            return self

        scaler = StandardScaler() if method == "standard" else MinMaxScaler()
        self.df[valid_cols] = scaler.fit_transform(self.df[valid_cols])

        return self
    # Chuẩn hóa dữ liệu rác
    def standardize_nulls(self):
        junk_null_markers = ["N/A", "NA", "n/a", "na", "?", "-", "none", "null", "NULL", ""]
        self.df = self.df.replace(junk_null_markers, np.nan)
        return self
    def clean_and_cast_numeric(self, columns: List[str]):
        for col in columns:
            if col not in self.df.columns:
                continue
            if self.df[col].dtype == "object":
                cleaned = self.df[col].astype(str).str.strip()
                cleaned = cleaned.str.replace(r"[^\d.]", "", regex=True)
                self.df[col] = pd.to_numeric(cleaned, errors="coerce")
        return self
    #Làm tròn số
    def round_feature(self, columns: List[str], decimals: int=0, to_integer: bool = False):
        for col in columns:
            if col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[col]):
                self.df[col] = self.df[col].round(decimals)
                if to_integer and self.df[col].isnull().sum() == 0:
                    self.df[col] = self.df[col].astype(int)
        return self
    # Thực thi pipeline
    def execute_pipeline(self, pipeline_steps: List[Dict[str, Any]]) -> pd.DataFrame:

        for step in pipeline_steps:
            step_type = step.get("step_type")
            config = step.get("config", {})

            if step_type == "missing_values":
                self.handle_missing_values(
                    columns = config.get("columns"),
                    strategy = config.get("strategy", "mean"),
                    fill_value = config.get("fill_value")
                )
            elif step_type == "outlier":
                self.handle_outliers(
                    columns = config.get("columns", []),
                    method = config.get("method", "iqr"),
                    threshold = float(config.get("threshold", 1.5)),
                    handling = config.get("handling", "remove")
                )
            elif step_type == "encoding":
                self.encode_categorical(
                    columns = config.get("columns", []),
                    method = config.get("method", "label")            
                )
            elif step_type == "scaling":
                self.scale_features(
                    columns = config.get("columns", []),
                    method = config.get("method", "standard")
                )
            elif step_type == "standardize_nulls":
                self.standardize_nulls()
            elif step_type == "clean_numeric":
                self.clean_and_cast_numeric(
                    columns=config.get("columns",[])
                )
            elif step_type == "round":
                self.round_feature(
                    columns = config.get("columns",[]),
                    decimals= int(config.get("decimal",0)),
                    to_integer= bool(config.get("to_integer", False))
                )
        return self.df