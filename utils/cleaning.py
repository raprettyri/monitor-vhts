import pandas as pd

def clean_text_columns(df):
    out = df.copy()
    for col in out.select_dtypes(include="object"):
        out[col] = out[col].astype(str).str.strip()
    return out
