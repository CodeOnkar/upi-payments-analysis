"""
Step 1: Clean the raw UPI Payments India dataset.

Raw file: 'UPI payments India.xlsx' (Kaggle: bhatnagardaksh/upipaymentsindia)
Output:   data/upi_cleaned.csv

What this script does, and why:
1. Load the raw Excel file as-is.
2. Rename columns to short, SQL-friendly snake_case names.
3. Sort by date ascending (oldest -> newest). The raw file is sorted
   newest-first, and growth/trend calculations only make sense computed
   forward in time.
4. Fix the 'volume_mn' column: one cell (Jun 2017) contains a number with a
   trailing non-breaking space (a copy-paste artifact), which forces pandas
   to treat the whole column as text. We strip it and convert to float.
5. Add derived columns used throughout the rest of the project:
      - avg_ticket_size_inr : average value per transaction, in INR
      - mom_growth_pct      : month-over-month % change in transaction value
      - yoy_growth_pct      : year-over-year % change in transaction value (vs. same month last year)
6. Save the cleaned table to data/upi_cleaned.csv
"""

import numpy as np
import pandas as pd

RAW_PATH = "UPI payments India.xlsx"
OUT_PATH = "data/upi_cleaned.csv"

# --- 1. Load raw data ---
df = pd.read_excel(RAW_PATH)

print("=== RAW DATA: shape, dtypes, first 10 rows ===")
print(df.shape)
print(df.dtypes)
print(df.head(10))
print()

# --- 2. Rename columns ---
df = df.rename(columns={
    "Month": "date",
    "No. of Banks live on UPI": "banks_live",
    "Volume (in Mn)": "volume_mn",
    "Value (in Cr.)": "value_cr",
})

# --- 3. Sort ascending by date (raw file is newest-first) ---
df = df.sort_values("date").reset_index(drop=True)

# --- 4. Fix volume_mn: strip whitespace/non-breaking spaces, cast to float ---
df["volume_mn"] = (
    df["volume_mn"]
    .astype(str)
    .str.replace("\xa0", "", regex=False)  # non-breaking space
    .str.strip()
    .astype(float)
)

# --- Sanity check: confirm no missing values remain ---
print("=== Missing values after cleaning ===")
print(df.isnull().sum())
assert df.isnull().sum().sum() == 0, "Unexpected missing values remain!"
print("No missing values. Good.")
print()

# --- 5. Derived columns ---

# Average ticket size = average value per transaction.
# value_cr is in crores (1 crore = 1,00,00,000 INR), volume_mn is in millions (1 million = 10,00,000).
# avg ticket size in INR = (value_cr * 1,00,00,000) / (volume_mn * 10,00,000)
df["avg_ticket_size_inr"] = (df["value_cr"] * 1e7) / (df["volume_mn"] * 1e6)

# Month-over-month growth %: change vs. the immediately preceding month
df["mom_growth_pct"] = df["value_cr"].pct_change() * 100

# Year-over-year growth %: change vs. the same month, 12 rows earlier
df["yoy_growth_pct"] = df["value_cr"].pct_change(periods=12) * 100

# "Growth from zero" is undefined, not infinite. Apr-Jun 2016 had value_cr == 0
# (UPI's pre-launch/ramp-up phase), so pct_change() produces +inf for the first
# non-zero month. Treat that as missing (NaN), same as other undefined growth values.
df["mom_growth_pct"] = df["mom_growth_pct"].replace([np.inf, -np.inf], np.nan)
df["yoy_growth_pct"] = df["yoy_growth_pct"].replace([np.inf, -np.inf], np.nan)

# --- 6. Save cleaned data ---
df.to_csv(OUT_PATH, index=False)

print("=== CLEANED DATA: first 10 rows ===")
print(df.head(10).to_string())
print()
print("=== CLEANED DATA: last 5 rows ===")
print(df.tail(5).to_string())
print()
print(f"Saved cleaned data to {OUT_PATH}")
print(f"Final shape: {df.shape}")
