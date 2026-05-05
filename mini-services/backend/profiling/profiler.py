import pandas as pd
import numpy as np

class DataProfiler:
    def profile(self, df, table_name=""):
        result = {"table_name": table_name, "row_count": len(df), "column_count": len(df.columns), "columns": {}}
        for col in df.columns:
            result["columns"][col] = self._profile_col(df, col)
        return result

    def _profile_col(self, df, col):
        s = df[col]
        total = len(s)
        nulls = int(s.isna().sum())
        nn = s.dropna()
        unique = int(nn.nunique())
        p = {"dtype": str(s.dtype), "null_count": nulls, "null_percent": round(nulls / total * 100, 2) if total else 0, "unique_count": unique, "non_null": len(nn)}
        if pd.api.types.is_numeric_dtype(s):
            num = pd.to_numeric(nn, errors="coerce").dropna()
            if len(num) > 0:
                p.update({"min": float(num.min()), "max": float(num.max()), "mean": round(float(num.mean()), 4), "median": float(num.median()), "std": round(float(num.std()), 4) if len(num) > 1 else 0})
        else:
            vc = nn.value_counts().head(5).to_dict()
            p["top_values"] = [{str(k): int(v)} for k, v in vc.items()]
        return p

profiler = DataProfiler()
