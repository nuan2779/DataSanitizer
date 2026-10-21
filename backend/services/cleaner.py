import pandas as pd 
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.preprocessing import LabelEncoder, StandardScaler, MinMaxScaler

class DataCleaner:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        #Lưu lại kích thước ban đầu
        self.initial_shape = df.shape
        #Danh sách từng hành động đã thực hiện
        self.audit_log: List[Dict[str, Any]] = []

    #ghi chép log và xuất báo cáo
    def _log(self, action: str, description: str, details: Optional[Dict[str,Any]] = None):
        self.audit_log.append({
            "step": len(self.audit_log) + 1,
            "action": action,
            "description": description,
            "details": details or {}
        })
    def get_audit_summary(self) -> Dict[str, Any]:
        #Xuất bản báo cáo
        rows_diff = self.initial_shape[0] - len(self.df)
        cols_diff = len(self.df.columns) - self.initial_shape[1]
        return {
            "initial_rows": self.initial_shape[0],
            "final_rows": len(self.df),
            "rows_removed": rows_diff,
            "initial_columns": self.initial_shape[1],
            "final_columns": len(self.df.columns),
            "columns_added_or_removed": cols_diff,
            "total_steps": len(self.audit_log),
            "history": self.audit_log
        }
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
                    self.df[col] = self.df[col].fillna(self.df[col].median())
        elif strategy == "mode":
            for col in target_cols:
                mode_val = self.df[col].mode()
                if not mode_val.empty:
                    self.df[col] = self.df[col].fillna(mode_val[0])
        elif strategy == "interpolate":
            for col in target_cols:
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    # Nội suy tuyến tính
                    self.df[col] = self.df[col].interpolate(method="linear")
        elif strategy == "constant" and fill_value is not None:
            self.df[target_cols] = self.df[target_cols].fillna(fill_value)

        self._log("missing_values", f"Đã điền ô trống theo phương pháp '{strategy}' cho các cột: {target_cols}")
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
        rows_before = len(self.df)

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

        rows_removed = rows_before - len(self.df)
        self._log("outlier", f"Đã loại bỏ {rows_removed} dòng ngoại lại ở các cột: {columns}")
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
        self._log("encoding", f"Đã mã hóa phân loại (phương pháp '{method}') cho các cột: {columns}")
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
        self._log("scaling", f"Đã chuẩn hóa thang đo (phương pháp '{method}') cho các cột: {valid_cols}")
        return self
    # Chuẩn hóa dữ liệu rác
    def standardize_nulls(self):
        junk_null_markers = ["N/A", "NA", "n/a", "na", "?", "-", "none", "null", "NULL", ""]
        nulls_before = int(self.df.isnull().sum().sum())
        self.df = self.df.replace(junk_null_markers, np.nan)
        nulls_after = int(self.df.isnull().sum().sum())
        junk_count = nulls_after - nulls_before

        self._log("standardize_nulls", f"Đã chuẩn hóa {junk_count} ô chứa các ký tự rác thành chuẩn")
        return self
    def drop_duplicates(self, subset: Optional[List[str]] = None, keep: str = "first"):
        #xóa các cột trùng lặp hoàn toàn hoặc trùng trên các cột chỉ đỉnh
        rows_before = len(self.df)
        self.df = self.df.drop_duplicates(subset=subset, keep=keep)
        rows_removed = rows_before - len(self.df)

        self._log("drop_duplicates", f"Đã xóa {rows_removed} dòng trùng lặp (giữ lại bản ghi: '{keep}').")
        return self
    def clean_and_cast_numeric(self, columns: List[str]):
        for col in columns:
            if col not in self.df.columns:
                continue
            if self.df[col].dtype == "object":
                cleaned = self.df[col].astype(str).str.strip()
                cleaned = cleaned.str.replace(r"[^\d.]", "", regex=True)
                self.df[col] = pd.to_numeric(cleaned, errors="coerce")
        self._log("clean_numeric", f"Đã bóc tách ký tự tiền tệ và ép kiểu số cho các cột: {columns}")
        return self
    #Làm tròn số
    def round_feature(self, columns: List[str], decimals: int=0, to_integer: bool = False):
        for col in columns:
            if col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[col]):
                self.df[col] = self.df[col].round(decimals)
                if to_integer and self.df[col].isnull().sum() == 0:
                    self.df[col] = self.df[col].astype(int)
        self._log("round", f"Đã làm tròn về {decimals} chữ số thập phân cho các cột: {columns}")
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
                    decimals= int(config.get("decimals",0)),
                    to_integer= bool(config.get("to_integer", False))
                )
            elif step_type == "drop_duplicates":
                self.drop_duplicates(
                    subset=config.get("subset"),
                    keep=config.get("keep","first")
                    )
        return self.df