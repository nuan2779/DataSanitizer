import pandas as pd 
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.preprocessing import LabelEncoder, StandardScaler, MinMaxScaler, OneHotEncoder

class DataCleaner:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        # Lưu lại kích thước ban đầu
        self.initial_shape = df.shape
        # Danh sách từng hành động đã thực hiện
        self.audit_log: List[Dict[str, Any]] = []
        # Cơ chế phân tách Train/Test chống Data Leakage
        self.train_df: Optional[pd.DataFrame] = None
        self.test_df: Optional[pd.DataFrame] = None
        self.is_split: bool = False
        self.split_ratio: float = 0.2
        self.random_state: int = 42

    def split_train_test(self, test_size: float = 0.2, random_state: int = 42):
        """
        Phân tách tập dữ liệu thành Train và Test độc lập để chống rò rỉ dữ liệu (Data Leakage).
        Các bước Encoding và Scaling sau bước này sẽ chỉ FIT trên tập Train và TRANSFORM sang tập Test.
        """
        from sklearn.model_selection import train_test_split
        self.is_split = True
        self.split_ratio = float(test_size)
        self.random_state = int(random_state)
        self.train_df, self.test_df = train_test_split(
            self.df, test_size=self.split_ratio, random_state=self.random_state
        )
        self.train_df = self.train_df.copy()
        self.test_df = self.test_df.copy()
        self._log(
            "split_train_test",
            f"Đã phân tách Train ({len(self.train_df)} dòng) và Test ({len(self.test_df)} dòng) với tỷ lệ Test {int(self.split_ratio * 100)}% (chống Data Leakage)",
            {
                "train_rows": len(self.train_df),
                "test_rows": len(self.test_df),
                "test_size": self.split_ratio,
                "random_state": self.random_state
            }
        )
        return self

    def get_split_data(self) -> Dict[str, Optional[pd.DataFrame]]:
        """Trả về 2 DataFrame Train và Test sau khi làm sạch."""
        return {
            "train": self.train_df,
            "test": self.test_df,
            "is_split": self.is_split
        }

    # ghi chép log và xuất báo cáo
    def _log(self, action: str, description: str, details: Optional[Dict[str,Any]] = None):
        self.audit_log.append({
            "step": len(self.audit_log) + 1,
            "action": action,
            "description": description,
            "details": details or {}
        })

    def get_audit_summary(self) -> Dict[str, Any]:
        # Xuất bản báo cáo
        rows_diff = self.initial_shape[0] - len(self.df)
        cols_diff = len(self.df.columns) - self.initial_shape[1]
        summary = {
            "initial_rows": self.initial_shape[0],
            "final_rows": len(self.df),
            "rows_removed": rows_diff,
            "initial_columns": self.initial_shape[1],
            "final_columns": len(self.df.columns),
            "columns_added_or_removed": cols_diff,
            "total_steps": len(self.audit_log),
            "history": self.audit_log,
            "is_split": self.is_split
        }
        if self.is_split and self.train_df is not None and self.test_df is not None:
            summary["train_rows"] = len(self.train_df)
            summary["test_rows"] = len(self.test_df)
            summary["split_ratio"] = self.split_ratio
        return summary

    # Xử lí giá trị thiếu
    def handle_missing_values(
            self,
            columns: Optional[List[str]] = None,
            strategy: str = "mean",
            fill_value: Any = None
    ):
        target_cols = columns if columns else self.df.columns.tolist()

        if strategy in ("drop_row", "drop_rows", "drop"):
            self.df = self.df.dropna(subset=target_cols)
            if self.is_split and self.train_df is not None and self.test_df is not None:
                self.train_df = self.train_df.dropna(subset=target_cols)
                self.test_df = self.test_df.dropna(subset=target_cols)

        elif strategy in ("drop_col", "drop_cols"):
            self.df = self.df.drop(columns=target_cols)
            if self.is_split and self.train_df is not None and self.test_df is not None:
                self.train_df = self.train_df.drop(columns=target_cols)
                self.test_df = self.test_df.drop(columns=target_cols)

        elif strategy == "mean":
            for col in target_cols:
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    val = self.train_df[col].mean() if self.is_split and self.train_df is not None else self.df[col].mean()
                    self.df[col] = self.df[col].fillna(val)
                    if self.is_split and self.train_df is not None and self.test_df is not None:
                        self.train_df[col] = self.train_df[col].fillna(val)
                        self.test_df[col] = self.test_df[col].fillna(val)

        elif strategy == "median":
            for col in target_cols:
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    val = self.train_df[col].median() if self.is_split and self.train_df is not None else self.df[col].median()
                    self.df[col] = self.df[col].fillna(val)
                    if self.is_split and self.train_df is not None and self.test_df is not None:
                        self.train_df[col] = self.train_df[col].fillna(val)
                        self.test_df[col] = self.test_df[col].fillna(val)

        elif strategy == "mode":
            for col in target_cols:
                source = self.train_df[col] if self.is_split and self.train_df is not None else self.df[col]
                mode_val = source.mode()
                if not mode_val.empty:
                    val = mode_val[0]
                    self.df[col] = self.df[col].fillna(val)
                    if self.is_split and self.train_df is not None and self.test_df is not None:
                        self.train_df[col] = self.train_df[col].fillna(val)
                        self.test_df[col] = self.test_df[col].fillna(val)

        elif strategy == "interpolate":
            for col in target_cols:
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    self.df[col] = self.df[col].interpolate(method="linear")
                    if self.is_split and self.train_df is not None and self.test_df is not None:
                        self.train_df[col] = self.train_df[col].interpolate(method="linear")
                        self.test_df[col] = self.test_df[col].interpolate(method="linear")

        elif strategy == "constant" and fill_value is not None:
            self.df[target_cols] = self.df[target_cols].fillna(fill_value)
            if self.is_split and self.train_df is not None and self.test_df is not None:
                self.train_df[target_cols] = self.train_df[target_cols].fillna(fill_value)
                self.test_df[target_cols] = self.test_df[target_cols].fillna(fill_value)

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
        rows_before = len(self.df)

        for col in columns:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                continue

            # Khi da chia train/test: Thong so thong ke (Q1, Q3, Mean, Std) phai hoc tu tap Train!
            stat_df = self.train_df if (self.is_split and self.train_df is not None) else self.df

            if method == "iqr":
                q1 = stat_df[col].quantile(0.25)
                q3 = stat_df[col].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - threshold * iqr
                upper = q3 + threshold * iqr
            elif method == "z_score":
                mean = stat_df[col].mean()
                std = stat_df[col].std()
                if std == 0:
                    continue
                lower = mean - threshold * std
                upper = mean + threshold * std
            else:
                continue

            if handling == "remove":
                condition = ((self.df[col] >= lower) & (self.df[col] <= upper)) | self.df[col].isna()
                self.df = self.df[condition]
                if self.is_split and self.train_df is not None and self.test_df is not None:
                    c_train = ((self.train_df[col] >= lower) & (self.train_df[col] <= upper)) | self.train_df[col].isna()
                    c_test = ((self.test_df[col] >= lower) & (self.test_df[col] <= upper)) | self.test_df[col].isna()
                    self.train_df = self.train_df[c_train]
                    self.test_df = self.test_df[c_test]
            elif handling == "cap":
                self.df[col] = np.clip(self.df[col], lower, upper)
                if self.is_split and self.train_df is not None and self.test_df is not None:
                    self.train_df[col] = np.clip(self.train_df[col], lower, upper)
                    self.test_df[col] = np.clip(self.test_df[col], lower, upper)

        rows_removed = rows_before - len(self.df)
        self._log("outlier", f"Đã loại bỏ {rows_removed} dòng ngoại lai ở các cột: {columns}")
        return self

    # Mã hóa phân loại (Co che Anti Data Leakage)
    def encode_categorical(self, columns: List[str], method: str = "label"):
        if self.is_split and self.train_df is not None and self.test_df is not None:
            # CHE DO ML: FIT tren Train, TRANSFORM sang Test
            for col in columns:
                if col not in self.train_df.columns:
                    continue
                if method == "label":
                    # Tu dien hoc tu tap Train
                    unique_train = self.train_df[col].dropna().astype(str).unique()
                    val_to_idx = {val: idx for idx, val in enumerate(sorted(unique_train))}
                    
                    self.train_df[col] = self.train_df[col].astype(str).map(val_to_idx).fillna(-1).astype(int)
                    # Test dung lai tu dien; nhan la unseen duoc gan -1
                    self.test_df[col] = self.test_df[col].astype(str).map(val_to_idx).fillna(-1).astype(int)

                elif method == "one_hot":
                    ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
                    train_col_data = self.train_df[[col]].astype(str)
                    test_col_data = self.test_df[[col]].astype(str)

                    ohe_train = ohe.fit_transform(train_col_data)
                    ohe_test = ohe.transform(test_col_data)

                    categories = ohe.categories_[0]
                    col_names = [f"{col}_{cat}" for cat in categories]
                    if len(col_names) > 1:
                        col_names = col_names[1:]
                        ohe_train = ohe_train[:, 1:]
                        ohe_test = ohe_test[:, 1:]

                    df_ohe_train = pd.DataFrame(ohe_train, columns=col_names, index=self.train_df.index)
                    df_ohe_test = pd.DataFrame(ohe_test, columns=col_names, index=self.test_df.index)

                    self.train_df = pd.concat([self.train_df.drop(columns=[col]), df_ohe_train], axis=1)
                    self.test_df = pd.concat([self.test_df.drop(columns=[col]), df_ohe_test], axis=1)

            # Dong bo self.df
            self.df = pd.concat([self.train_df, self.test_df], axis=0)
            self._log("encoding", f"Đã mã hóa phân loại độc lập Train/Test chống Data Leakage (phương pháp '{method}') cho các cột: {columns}")
            return self

        # CHE DO EDA: Ma hoa tren toan bo bang nhu cu
        for col in columns:
            if col not in self.df.columns:
                continue
            if method == "label":
                le = LabelEncoder()
                self.df[col] = le.fit_transform(self.df[col].astype(str))
            elif method == "one_hot":
                self.df = pd.get_dummies(self.df, columns=[col], prefix=col, drop_first=True)

        self._log("encoding", f"Đã mã hóa phân loại (phương pháp '{method}') cho các cột: {columns}")
        return self

    # Chuẩn hóa dữ liệu (Co che Anti Data Leakage)
    def scale_features(self, columns: List[str], method: str = "standard"):
        valid_cols = [c for c in columns if c in self.df.columns and pd.api.types.is_numeric_dtype(self.df[c])]
        if not valid_cols:
            return self

        if self.is_split and self.train_df is not None and self.test_df is not None:
            # FIT tren Train, TRANSFORM sang Test
            scaler = StandardScaler() if method == "standard" else MinMaxScaler()
            self.train_df[valid_cols] = scaler.fit_transform(self.train_df[valid_cols])
            self.test_df[valid_cols] = scaler.transform(self.test_df[valid_cols])
            self.df = pd.concat([self.train_df, self.test_df], axis=0)
            self._log("scaling", f"Đã chuẩn hóa thang đo độc lập Train/Test chống Data Leakage (phương pháp '{method}') cho các cột: {valid_cols}")
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
        if self.is_split and self.train_df is not None and self.test_df is not None:
            self.train_df = self.train_df.replace(junk_null_markers, np.nan)
            self.test_df = self.test_df.replace(junk_null_markers, np.nan)
        nulls_after = int(self.df.isnull().sum().sum())
        junk_count = nulls_after - nulls_before

        self._log("standardize_nulls", f"Đã chuẩn hóa {junk_count} ô chứa các ký tự rác thành chuẩn")
        return self

    def drop_duplicates(self, subset: Optional[List[str]] = None, keep: str = "first"):
        rows_before = len(self.df)
        self.df = self.df.drop_duplicates(subset=subset, keep=keep)
        if self.is_split and self.train_df is not None and self.test_df is not None:
            self.train_df = self.train_df.drop_duplicates(subset=subset, keep=keep)
            self.test_df = self.test_df.drop_duplicates(subset=subset, keep=keep)
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
                if self.is_split and self.train_df is not None and self.test_df is not None:
                    c_train = self.train_df[col].astype(str).str.strip().str.replace(r"[^\d.]", "", regex=True)
                    c_test = self.test_df[col].astype(str).str.strip().str.replace(r"[^\d.]", "", regex=True)
                    self.train_df[col] = pd.to_numeric(c_train, errors="coerce")
                    self.test_df[col] = pd.to_numeric(c_test, errors="coerce")
        self._log("clean_numeric", f"Đã bóc tách ký tự tiền tệ và ép kiểu số cho các cột: {columns}")
        return self

    # Làm tròn số
    def round_feature(self, columns: List[str], decimals: int = 0, to_integer: bool = False):
        for col in columns:
            if col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[col]):
                self.df[col] = self.df[col].round(decimals)
                if to_integer and self.df[col].isnull().sum() == 0:
                    self.df[col] = self.df[col].astype(int)
                if self.is_split and self.train_df is not None and self.test_df is not None:
                    self.train_df[col] = self.train_df[col].round(decimals)
                    self.test_df[col] = self.test_df[col].round(decimals)
                    if to_integer and self.train_df[col].isnull().sum() == 0:
                        self.train_df[col] = self.train_df[col].astype(int)
                    if to_integer and self.test_df[col].isnull().sum() == 0:
                        self.test_df[col] = self.test_df[col].astype(int)
        self._log("round", f"Đã làm tròn về {decimals} chữ số thập phân cho các cột: {columns}")
        return self

    # Tối ưu hóa dung lượng
    def optimize_memory(self):
        start_mem = self.df.memory_usage(deep=True).sum() / (1024 ** 2)
        for col in self.df.columns:
            col_type = self.df[col].dtype
            if pd.api.types.is_integer_dtype(col_type):
                c_min = self.df[col].min()
                c_max = self.df[col].max()
                if c_min >= np.iinfo(np.int8).min and c_max <= np.iinfo(np.int8).max:
                    self.df[col] = self.df[col].astype(np.int8)
                elif c_min >= np.iinfo(np.int16).min and c_max <= np.iinfo(np.int16).max:
                    self.df[col] = self.df[col].astype(np.int16)
                elif c_min >= np.iinfo(np.int32).min and c_max <= np.iinfo(np.int32).max:
                    self.df[col] = self.df[col].astype(np.int32)
            elif pd.api.types.is_float_dtype(col_type):
                self.df[col] = self.df[col].astype(np.float32)
            elif col_type == "object":
                num_unique = self.df[col].nunique()
                num_total = len(self.df[col])
                if num_total > 0 and (num_unique / num_total) < 0.5:
                    self.df[col] = self.df[col].astype("category")

        end_mem = self.df.memory_usage(deep=True).sum() / (1024 ** 2)
        reduction = ((start_mem - end_mem) / start_mem * 100) if start_mem > 0 else 0.0

        self._log(
            "optimize_memory",
            f"Đã tối ưu RAM: giảm từ {start_mem:.2f} MB xuống {end_mem:.2f} MB (tiết kiệm {reduction:.1f}% RAM)."
        )
        return self

    # Thực thi pipeline
    def execute_pipeline(self, pipeline_steps: List[Dict[str, Any]], is_ml_mode: bool = False, test_size: float = 0.2, random_state: int = 42) -> pd.DataFrame:
        if is_ml_mode and not self.is_split:
            self.split_train_test(test_size=test_size, random_state=random_state)

        for step in pipeline_steps:
            step_type = step.get("step_type")
            config = step.get("config", {})

            if step_type == "missing_values":
                self.handle_missing_values(
                    columns=config.get("columns"),
                    strategy=config.get("strategy", "mean"),
                    fill_value=config.get("fill_value")
                )
            elif step_type == "outlier":
                self.handle_outliers(
                    columns=config.get("columns", []),
                    method=config.get("method", "iqr"),
                    threshold=float(config.get("threshold", 1.5)),
                    handling=config.get("handling", "remove")
                )
            elif step_type == "encoding":
                self.encode_categorical(
                    columns=config.get("columns", []),
                    method=config.get("method", "label")            
                )
            elif step_type == "scaling":
                self.scale_features(
                    columns=config.get("columns", []),
                    method=config.get("method", "standard")
                )
            elif step_type == "standardize_nulls":
                self.standardize_nulls()
            elif step_type == "clean_numeric":
                self.clean_and_cast_numeric(
                    columns=config.get("columns", [])
                )
            elif step_type == "round":
                self.round_feature(
                    columns=config.get("columns", []),
                    decimals=int(config.get("decimals", 0)),
                    to_integer=bool(config.get("to_integer", False))
                )
            elif step_type == "drop_duplicates":
                self.drop_duplicates(
                    subset=config.get("subset"),
                    keep=config.get("keep", "first")
                )
            elif step_type == "optimize_memory":
                self.optimize_memory()

        return self.df
