"""
Step 2: Exploratory analysis of UPI trends (2016-2021).

Input:  data/upi_cleaned.csv
Output: outputs/volume_trend.png, outputs/value_trend.png
        printed summary stats (total growth, peak growth month, avg YoY growth)

Why separate charts for Volume and Value instead of one dual-axis chart:
Volume (millions of transactions) and Value (crores of rupees) are on very
different scales. Dual-axis charts can visually mislead (two lines can be made
to look like they move together just by rescaling each axis independently),
so we plot them separately -- clearer and harder to misinterpret.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

df = pd.read_csv("data/upi_cleaned.csv", parse_dates=["date"])

# --- Key policy-relevant events to annotate on the timeline ---
EVENTS = [
    ("2016-11-08", "Demonetization\n(Nov 2016)"),
    ("2020-03-01", "COVID onset\n(Mar 2020)"),
]


def annotate_events(ax, y_col):
    """Draw a vertical dashed line + label for each key event."""
    for date_str, label in EVENTS:
        event_date = pd.Timestamp(date_str)
        ax.axvline(event_date, color="gray", linestyle="--", linewidth=1, alpha=0.7)
        y_max = df[y_col].max()
        ax.text(
            event_date, y_max * 0.95, label,
            rotation=0, fontsize=8, ha="left", va="top", color="dimgray",
        )


# --- Chart 1: Transaction Volume trend ---
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(df["date"], df["volume_mn"], color="#1f6feb", linewidth=2)
ax.set_title("UPI Transaction Volume, 2016-2021 (Monthly)")
ax.set_xlabel("Month")
ax.set_ylabel("Volume (in Million transactions)")
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.grid(True, alpha=0.3)
annotate_events(ax, "volume_mn")
fig.tight_layout()
fig.savefig("outputs/volume_trend.png", dpi=150)
plt.close(fig)

# --- Chart 2: Transaction Value trend ---
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(df["date"], df["value_cr"], color="#238636", linewidth=2)
ax.set_title("UPI Transaction Value, 2016-2021 (Monthly)")
ax.set_xlabel("Month")
ax.set_ylabel("Value (in Crore INR)")
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.grid(True, alpha=0.3)
annotate_events(ax, "value_cr")
fig.tight_layout()
fig.savefig("outputs/value_trend.png", dpi=150)
plt.close(fig)

# --- Chart 3: YoY growth % trend (shows adoption curve maturing over time) ---
# Start from 2018: 2017's YoY figures are computed against 2016's near-zero
# launch base and are so large (up to ~900,000%) that including them would
# compress the entire 2018-2021 story into a flat line near zero.
fig, ax = plt.subplots(figsize=(11, 5))
yoy_plot_df = df[df["date"] >= "2018-01-01"].dropna(subset=["yoy_growth_pct"])
ax.plot(yoy_plot_df["date"], yoy_plot_df["yoy_growth_pct"], color="#9333ea", linewidth=2)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_title("UPI Transaction Value: Year-over-Year Growth %, 2018-2021")
ax.set_xlabel("Month")
ax.set_ylabel("YoY Growth (%)")
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("outputs/yoy_growth_trend.png", dpi=150)
plt.close(fig)

print("Saved outputs/volume_trend.png, outputs/value_trend.png, outputs/yoy_growth_trend.png")
print()

# --- Summary statistics ---
#
# IMPORTANT: percentage growth computed from a near-zero base (2016, UPI's
# launch phase) produces huge, policy-meaningless numbers (e.g. "217 million %
# growth"). The number is technically correct but tells us nothing except that
# the starting point was tiny. We therefore report two tiers:
#   1. A one-line footnote on the raw launch-to-2021 multiple, for context.
#   2. The headline figure: full calendar-year 2017 vs full calendar-year 2021,
#      once UPI had meaningfully launched. This is the number that belongs in
#      the policy brief.

first_row = df.iloc[0]
last_row = df.iloc[-1]
base_row = df[df["value_cr"] > 0].iloc[0]  # first month with real activity (Jul-2016)

print("=== SUMMARY STATISTICS ===")
print(f"Period covered: {first_row['date'].date()} to {last_row['date'].date()}")
print()

# --- Tier 1: raw launch-to-end context (footnote only) ---
launch_multiple_value = last_row["value_cr"] / base_row["value_cr"]
launch_multiple_volume = last_row["volume_mn"] / base_row["volume_mn"]
print("[Context only -- not a headline figure]")
print(f"From first active month ({base_row['date'].date()}) to Dec-2021, "
      f"transaction value rose ~{launch_multiple_value:,.0f}x and volume ~{launch_multiple_volume:,.0f}x. "
      f"This is off a near-zero launch base, so the percentage form of this number "
      f"(hundreds of millions of %) is not policy-meaningful -- it mainly reflects how small the starting point was.")
print()

# --- Tier 2: headline figure -- full year 2017 vs full year 2021 ---
df["year"] = df["date"].dt.year
yearly = df.groupby("year")[["volume_mn", "value_cr"]].sum()

value_2017, value_2021 = yearly.loc[2017, "value_cr"], yearly.loc[2021, "value_cr"]
volume_2017, volume_2021 = yearly.loc[2017, "volume_mn"], yearly.loc[2021, "volume_mn"]
headline_value_growth = (value_2021 / value_2017 - 1) * 100
headline_volume_growth = (volume_2021 / volume_2017 - 1) * 100

print("[Headline figures -- full calendar year comparison, used in policy brief]")
print(f"Total annual transaction VALUE: Rs {value_2017:,.0f} Cr (2017) -> Rs {value_2021:,.0f} Cr (2021)")
print(f"  = {headline_value_growth:,.0f}% growth over 4 years "
      f"(~{(value_2021/value_2017):,.1f}x)")
print(f"Total annual transaction VOLUME: {volume_2017:,.0f} Mn (2017) -> {volume_2021:,.0f} Mn (2021)")
print(f"  = {headline_volume_growth:,.0f}% growth over 4 years "
      f"(~{(volume_2021/volume_2017):,.1f}x)")
print()

# --- Peak growth month ---
# Restrict to 2018 onward: by then monthly value is consistently > Rs 10,000 Cr,
# so % growth reflects a real month-to-month shift, not a small-base artifact.
mature = df[df["date"] >= "2018-01-01"]

peak_row = mature.loc[mature["mom_growth_pct"].idxmax()]
print(f"Peak MoM growth month (2018 onward, by value): {peak_row['date'].date()} "
      f"with {peak_row['mom_growth_pct']:,.1f}% growth "
      f"(value: Rs {peak_row['value_cr']:,.0f} Cr)")

avg_yoy_mature = mature["yoy_growth_pct"].mean()
print(f"Average YoY growth, 2018 onward (where defined): {avg_yoy_mature:,.1f}%")
print()
print("Note on YoY growth: we do NOT report a single 'peak YoY growth month'.")
print("The small-base distortion fades out gradually, not at one clean cutoff --")
print("even Jan-2019 (606% YoY) is still partly a base effect from early-2018.")
print("A single 'peak month' number would just surface whichever year is")
print("earliest in the comparison window, which is misleading. Instead, YoY")
print("growth is best read as a downward-trending line (see yoy_growth chart):")
print("triple-digit YoY growth in 2018-19, settling to double digits by 2021")
print("as the base matures -- itself a meaningful policy signal (adoption")
print("curve flattening from hypergrowth to steady, large-scale usage).")
