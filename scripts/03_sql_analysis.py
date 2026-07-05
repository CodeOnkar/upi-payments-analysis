"""
Step 3: Load cleaned data into SQLite and run policy-relevant SQL queries.

Input:  data/upi_cleaned.csv
Output: data/upi.db (SQLite database)
        printed results for each query, with a plain-language explanation

Why SQLite: it's a single portable file, needs no server setup, and is a
standard way to demonstrate SQL skills on top of a pandas dataframe -- exactly
the kind of lightweight tool a policy analyst would use for ad-hoc queries.
"""

import sqlite3
import pandas as pd

CSV_PATH = "data/upi_cleaned.csv"
DB_PATH = "data/upi.db"
TABLE = "upi_transactions"


def run_query(conn, title, why, sql):
    print("=" * 90)
    print(f"QUERY: {title}")
    print(f"WHY IT MATTERS: {why}")
    print("-" * 90)
    result = pd.read_sql_query(sql, conn)
    print(result.to_string(index=False))
    print()
    return result


# --- Load cleaned CSV into SQLite ---
df = pd.read_csv(CSV_PATH, parse_dates=["date"])
conn = sqlite3.connect(DB_PATH)
df.to_sql(TABLE, conn, if_exists="replace", index=False)
print(f"Loaded {len(df)} rows into '{TABLE}' table in {DB_PATH}")
print()

# ============================================================
# Q1: Yearly totals -- volume, value, and average banks live
# ============================================================
run_query(
    conn,
    "Q1: Yearly totals (volume, value) and average banks live per year",
    "This is the most basic policy rollup: how big did UPI get, year by year? "
    "Annual totals smooth out monthly noise and are the natural unit for "
    "year-on-year comparisons in a policy brief.",
    f"""
    SELECT
        strftime('%Y', date) AS year,
        ROUND(SUM(volume_mn), 2)        AS total_volume_mn,
        ROUND(SUM(value_cr), 2)         AS total_value_cr,
        ROUND(AVG(banks_live), 1)       AS avg_banks_live
    FROM {TABLE}
    GROUP BY year
    ORDER BY year;
    """,
)

# ============================================================
# Q2: Highest month-over-month growth month (excluding early launch phase)
# ============================================================
run_query(
    conn,
    "Q2: Top 5 months by month-over-month (MoM) growth, from 2018 onward",
    "Identifies specific months where transaction value jumped sharply. "
    "Restricting to 2018+ avoids the 2016-17 launch-phase distortion (huge % "
    "growth off a near-zero base, which isn't a meaningful policy signal).",
    f"""
    SELECT date, value_cr, ROUND(mom_growth_pct, 1) AS mom_growth_pct
    FROM {TABLE}
    WHERE date >= '2018-01-01' AND mom_growth_pct IS NOT NULL
    ORDER BY mom_growth_pct DESC
    LIMIT 5;
    """,
)

# ============================================================
# Q3: Year-wise ranking by total transaction value
# ============================================================
run_query(
    conn,
    "Q3: Years ranked by total annual transaction value",
    "A simple ranking makes it immediately obvious which years drove the "
    "most rupee-value growth -- useful for framing 'UPI's biggest year' in "
    "a policy narrative.",
    f"""
    SELECT
        strftime('%Y', date) AS year,
        ROUND(SUM(value_cr), 2) AS total_value_cr,
        RANK() OVER (ORDER BY SUM(value_cr) DESC) AS value_rank
    FROM {TABLE}
    GROUP BY year
    ORDER BY value_rank;
    """,
)

# ============================================================
# Q4: Correlation between banks live and transaction volume
# ============================================================
run_query(
    conn,
    "Q4: Correlation between 'banks live on UPI' and transaction volume",
    "Tests whether UPI's growth was driven by network effects -- i.e. does "
    "volume rise as more banks join the network? SQLite has no built-in "
    "CORR() function, so we compute Pearson's r manually using the standard "
    "formula: cov(x,y) / (stdev(x) * stdev(y)). A value near +1 supports "
    "the 'more banks -> more usage' network-effect hypothesis, relevant to "
    "regulators deciding whether to keep onboarding more banks/payment apps.",
    f"""
    WITH stats AS (
        SELECT
            AVG(banks_live) AS mean_x,
            AVG(volume_mn)  AS mean_y
        FROM {TABLE}
    )
    SELECT
        ROUND(
            SUM((banks_live - mean_x) * (volume_mn - mean_y)) /
            (SQRT(SUM((banks_live - mean_x) * (banks_live - mean_x))) *
             SQRT(SUM((volume_mn  - mean_y) * (volume_mn  - mean_y))))
        , 4) AS pearson_correlation
    FROM {TABLE}, stats;
    """,
)

# ============================================================
# Q5: Average ticket size trend by year
# ============================================================
run_query(
    conn,
    "Q5: Average transaction ticket size (Rs per transaction), by year",
    "Financial inclusion angle: a falling or stable average ticket size "
    "while volume grows suggests UPI is increasingly used for small, "
    "everyday payments (not just big-ticket transfers) -- a sign of usage "
    "spreading to ordinary retail/person-to-person payments, not just "
    "high-value use cases.",
    f"""
    SELECT
        strftime('%Y', date) AS year,
        ROUND(SUM(value_cr) * 1e7 / (SUM(volume_mn) * 1e6), 2) AS avg_ticket_size_inr
    FROM {TABLE}
    WHERE volume_mn > 0
    GROUP BY year
    ORDER BY year;
    """,
)

# ============================================================
# Q6: Months where volume grew but banks_live stayed flat (or vice versa)
# ============================================================
run_query(
    conn,
    "Q6: Monthly change in banks_live vs. monthly % change in volume",
    "Separates two distinct growth drivers: new banks joining the network "
    "vs. existing users transacting more. If volume keeps growing in months "
    "with zero new banks, that shows organic demand growth, not just supply-side "
    "network expansion -- an important distinction for a policy diagnosis of "
    "*why* UPI grew.",
    f"""
    SELECT
        date,
        banks_live,
        banks_live - LAG(banks_live) OVER (ORDER BY date) AS new_banks_this_month,
        ROUND(mom_growth_pct, 1) AS value_mom_growth_pct
    FROM {TABLE}
    WHERE date >= '2019-01-01'
    ORDER BY date
    LIMIT 12;
    """,
)

# ============================================================
# Q7: Best and worst calendar month-of-year for growth (seasonality check)
# ============================================================
run_query(
    conn,
    "Q7: Average MoM growth % by calendar month (seasonality check)",
    "Checks whether certain months (e.g. festive season: Oct-Nov, or "
    "financial year-end: Mar) systematically show stronger growth. This "
    "matters for policy timing -- e.g. planning digital-payments awareness "
    "campaigns or infrastructure scaling ahead of predictably high-demand months.",
    f"""
    SELECT
        strftime('%m', date) AS calendar_month,
        ROUND(AVG(mom_growth_pct), 2) AS avg_mom_growth_pct,
        COUNT(*) AS n_months
    FROM {TABLE}
    WHERE date >= '2018-01-01' AND mom_growth_pct IS NOT NULL
    GROUP BY calendar_month
    ORDER BY avg_mom_growth_pct DESC;
    """,
)

# ============================================================
# Q8: COVID period impact -- 2020 vs 2019 same-month comparison
# ============================================================
run_query(
    conn,
    "Q8: 2020 vs 2019 transaction value, month by month (COVID impact)",
    "Directly measures COVID's effect by comparing each 2020 month to the "
    "same month in 2019 (avoids seasonal noise). Confirms whether the "
    "March/April 2020 lockdown caused an actual year-on-year contraction, "
    "not just a dip from the previous month.",
    f"""
    SELECT
        strftime('%m', a.date) AS calendar_month,
        a.value_cr AS value_2020,
        b.value_cr AS value_2019,
        ROUND((a.value_cr - b.value_cr) / b.value_cr * 100, 1) AS pct_change_yoy
    FROM {TABLE} a
    JOIN {TABLE} b
        ON strftime('%m', a.date) = strftime('%m', b.date)
        AND strftime('%Y', a.date) = '2020'
        AND strftime('%Y', b.date) = '2019'
    ORDER BY calendar_month;
    """,
)

# ============================================================
# Q9: Cumulative transaction value over time (running total)
# ============================================================
run_query(
    conn,
    "Q9: Cumulative UPI transaction value since launch (running total)",
    "Shows the total economic value that has flowed through UPI rails "
    "cumulatively -- a headline number regulators/policymakers often cite "
    "to communicate overall scale and impact to the public.",
    f"""
    SELECT
        date,
        value_cr,
        ROUND(SUM(value_cr) OVER (ORDER BY date), 2) AS cumulative_value_cr
    FROM {TABLE}
    ORDER BY date DESC
    LIMIT 5;
    """,
)

# ============================================================
# Q10: Banks-live growth vs value growth -- full network expansion timeline
# ============================================================
run_query(
    conn,
    "Q10: Banks live at year-end vs. total annual value (network expansion timeline)",
    "A compact year-end snapshot combining network size (banks live) and "
    "usage scale (annual value) in one table -- the kind of summary table "
    "that would go directly into a policy brief appendix.",
    f"""
    SELECT
        strftime('%Y', date) AS year,
        MAX(banks_live) AS banks_live_at_year_end,
        ROUND(SUM(value_cr), 0) AS total_annual_value_cr
    FROM {TABLE}
    GROUP BY year
    ORDER BY year;
    """,
)

conn.close()
print("Done. Database saved at", DB_PATH)
