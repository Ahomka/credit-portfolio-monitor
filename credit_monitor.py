"""
credit_monitor.py
====================================================
Ghana Bank Credit Portfolio Monitoring System
====================================================
Replicates core credit monitoring officer workflows:
  1. Portfolio classification & NPL ratio tracking
  2. Provision adequacy analysis
  3. Collateral coverage monitoring
  4. Sector & branch concentration risk
  5. Remediation value tracking (planned vs achieved)
  6. Automated monitoring report generation
  7. Early warning score model

Author : Portfolio Analytics
Purpose: Credit Monitoring Officer — GitHub Portfolio Project
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import warnings
warnings.filterwarnings("ignore")

# ── Colour palette (FirstBank-adjacent blues + signal colours) ──────────────
COLOURS = {
    "Current":     "#1B4F8E",
    "Watch":       "#F5A623",
    "Substandard": "#E67E22",
    "Doubtful":    "#C0392B",
    "Loss":        "#7B241C",
    "accent":      "#1B4F8E",
    "grid":        "#E8ECF0",
    "bg":          "#F7F9FC",
}
NPL_CLASSES = ["Substandard", "Doubtful", "Loss"]

def ghs(x):
    """Format number as GHS thousands."""
    return f"GHS {x/1e6:.2f}M" if abs(x) >= 1e6 else f"GHS {x/1e3:.1f}K"

def pct(x):
    return f"{x:.1f}%"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOAD & VALIDATE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("  GHANA BANK — CREDIT PORTFOLIO MONITORING REPORT")
print("  Reporting Date: April 2026")
print("=" * 65)

df = pd.read_csv("data/loan_portfolio.csv", parse_dates=["origination_date", "maturity_date", "last_payment_date"])

total_portfolio   = df["outstanding_ghs"].sum()
npl_df            = df[df["classification"].isin(NPL_CLASSES)]
total_npl         = npl_df["outstanding_ghs"].sum()
npl_ratio         = (total_npl / total_portfolio) * 100
total_provision   = df["provision_amount_ghs"].sum()
provision_coverage= (total_provision / total_npl * 100) if total_npl > 0 else 0
reviews_done      = df["review_completed"].sum()
portfolio_coverage= (reviews_done / len(df)) * 100
remediation_target= df["improvement_target_ghs"].sum()
remediation_value = df["remediation_value_ghs"].sum()
remediation_rate  = (remediation_value / remediation_target * 100) if remediation_target > 0 else 0
remediation_to_cost = remediation_value / (total_portfolio * 0.02)  # estimated staff cost proxy

print(f"\n  {'KPI':<45} {'Value':>15}")
print(f"  {'-'*62}")
print(f"  {'Total Loan Portfolio':<45} {ghs(total_portfolio):>15}")
print(f"  {'NPL Portfolio':<45} {ghs(total_npl):>15}")
print(f"  {'NPL Ratio (NPL as % of Total Loans)':<45} {pct(npl_ratio):>15}")
print(f"  {'Provision Coverage':<45} {pct(provision_coverage):>15}")
print(f"  {'Portfolio Reviews Completed':<45} {pct(portfolio_coverage):>15}")
print(f"  {'Remediation Value (Planned vs Achieved %)':<45} {pct(remediation_rate):>15}")
print(f"  {'Remediation Value to Staff Cost Ratio':<45} {remediation_to_cost:>14.1f}x")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CLASSIFICATION BREAKDOWN
# ═══════════════════════════════════════════════════════════════════════════════
cls_summary = df.groupby("classification").agg(
    Count       = ("loan_id", "count"),
    Outstanding = ("outstanding_ghs", "sum"),
    Provision   = ("provision_amount_ghs", "sum"),
    Collateral  = ("collateral_value_ghs", "sum"),
).reindex(["Current", "Watch", "Substandard", "Doubtful", "Loss"])

cls_summary = cls_summary.dropna(subset=["Outstanding"])

cls_summary["NPL_Flag"]      = cls_summary.index.isin(NPL_CLASSES)
cls_summary["Pct_Portfolio"]  = cls_summary["Outstanding"] / total_portfolio * 100
cls_summary["Coverage_Pct"]   = cls_summary["Collateral"] / cls_summary["Outstanding"] * 100

print("\n\n  CLASSIFICATION BREAKDOWN")
print(f"  {'Class':<15} {'Count':>6} {'Outstanding':>14} {'% Portfolio':>12} {'Provision':>14} {'Coll.Coverage':>14}")
print(f"  {'-'*77}")
for cls, row in cls_summary.iterrows():
    if pd.isna(row.Count):
        continue
    flag = " ⚠" if cls in NPL_CLASSES else ""
    print(f"  {cls:<15} {int(row.Count):>6} {ghs(row.Outstanding):>14} "
          f"{pct(row.Pct_Portfolio):>12} {ghs(row.Provision):>14} {pct(row.Coverage_Pct):>14}{flag}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SECTOR CONCENTRATION RISK
# ═══════════════════════════════════════════════════════════════════════════════
sector_npl = df.groupby("sector").apply(
    lambda x: pd.Series({
        "Total_Outstanding":  x["outstanding_ghs"].sum(),
        "NPL_Outstanding":    x.loc[x["classification"].isin(NPL_CLASSES), "outstanding_ghs"].sum(),
        "NPL_Ratio":          x.loc[x["classification"].isin(NPL_CLASSES), "outstanding_ghs"].sum() /
                              x["outstanding_ghs"].sum() * 100,
        "Count":              len(x),
    })
).sort_values("NPL_Ratio", ascending=False)

print("\n\n  SECTOR NPL CONCENTRATION (Top 5 by NPL Ratio)")
print(f"  {'Sector':<20} {'NPL Ratio':>10} {'NPL Exposure':>15} {'Total Loans':>12}")
print(f"  {'-'*60}")
for sec, row in sector_npl.head(5).iterrows():
    print(f"  {sec:<20} {pct(row.NPL_Ratio):>10} {ghs(row.NPL_Outstanding):>15} {ghs(row.Total_Outstanding):>12}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. EARLY WARNING SCORE MODEL
# ═══════════════════════════════════════════════════════════════════════════════
def early_warning_score(row):
    """
    Simple rules-based early warning scoring model.
    Scores 0-100. Higher = more at risk.
    Replicated from standard credit monitoring practice.
    """
    score = 0
    # DPD component (max 40 pts)
    if   row["days_past_due"] > 180: score += 40
    elif row["days_past_due"] > 90:  score += 30
    elif row["days_past_due"] > 60:  score += 20
    elif row["days_past_due"] > 30:  score += 10
    elif row["days_past_due"] > 0:   score += 5

    # Collateral coverage (max 30 pts)
    cov = row["collateral_coverage_pct"]
    if   cov < 60:  score += 30
    elif cov < 80:  score += 20
    elif cov < 100: score += 10

    # Provision rate (max 20 pts)
    score += int(row["provision_rate"] * 20)

    # Review not completed (10 pts)
    if not row["review_completed"]:
        score += 10

    return min(score, 100)

df["ews_score"] = df.apply(early_warning_score, axis=1)

# Flag high-risk accounts for immediate remediation action
high_risk = df[df["ews_score"] >= 40].sort_values("ews_score", ascending=False)

print(f"\n\n  EARLY WARNING SYSTEM — HIGH RISK ACCOUNTS (EWS Score ≥ 60)")
print(f"  Total flagged: {len(high_risk)} accounts | "
      f"Exposure: {ghs(high_risk['outstanding_ghs'].sum())}")
print(f"\n  {'Loan ID':<10} {'Borrower':<20} {'DPD':>5} {'Classification':<15} "
      f"{'Outstanding':>12} {'EWS Score':>10}")
print(f"  {'-'*76}")
for _, row in high_risk.head(10).iterrows():
    print(f"  {row.loan_id:<10} {row.borrower_name:<20} {int(row.days_past_due):>5} "
          f"{row.classification:<15} {ghs(row.outstanding_ghs):>12} {int(row.ews_score):>10}")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. DASHBOARD — 6-PANEL MONITORING REPORT
# ═══════════════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(18, 14), facecolor=COLOURS["bg"])
fig.suptitle(
    "Ghana Bank — Credit Portfolio Monitoring Dashboard\nReporting Date: April 2026",
    fontsize=16, fontweight="bold", color=COLOURS["accent"], y=0.98
)
gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)

# ── Panel 1: KPI Summary Cards ───────────────────────────────────────────────
ax0 = fig.add_subplot(gs[0, :])
ax0.set_facecolor(COLOURS["bg"])
ax0.axis("off")

kpis = [
    ("Total Portfolio",     ghs(total_portfolio),     COLOURS["accent"]),
    ("NPL Ratio",           pct(npl_ratio),            "#C0392B" if npl_ratio > 10 else "#27AE60"),
    ("Portfolio Coverage",  pct(portfolio_coverage),   "#27AE60" if portfolio_coverage > 80 else "#E67E22"),
    ("Provision Coverage",  pct(provision_coverage),   "#27AE60" if provision_coverage > 60 else "#E67E22"),
    ("Remediation Rate",    pct(remediation_rate),     "#27AE60" if remediation_rate > 70 else "#E67E22"),
    ("High-Risk Accounts",  f"{len(high_risk)}",       "#C0392B" if len(high_risk) > 100 else "#E67E22"),
]
for idx, (label, value, colour) in enumerate(kpis):
    x = 0.03 + idx * 0.163
    ax0.add_patch(mpatches.FancyBboxPatch(
        (x, 0.05), 0.15, 0.85, boxstyle="round,pad=0.02",
        facecolor="white", edgecolor=colour, linewidth=2,
        transform=ax0.transAxes
    ))
    ax0.text(x + 0.075, 0.67, value, ha="center", va="center",
             fontsize=15, fontweight="bold", color=colour, transform=ax0.transAxes)
    ax0.text(x + 0.075, 0.25, label, ha="center", va="center",
             fontsize=8.5, color="#555", transform=ax0.transAxes)

# ── Panel 2: Portfolio Classification (Pie) ──────────────────────────────────
ax1 = fig.add_subplot(gs[1, 0])
cls_vals   = cls_summary["Outstanding"]
cls_colors = [COLOURS.get(c, "#999") for c in cls_vals.index]
wedges, texts, autotexts = ax1.pie(
    cls_vals, labels=cls_vals.index, colors=cls_colors,
    autopct=lambda p: f"{p:.1f}%" if p > 3 else "",
    startangle=140, textprops={"fontsize": 8}
)
ax1.set_title("Portfolio Classification Mix", fontweight="bold",
              color=COLOURS["accent"], fontsize=10)

# ── Panel 3: NPL Ratio by Sector ─────────────────────────────────────────────
ax2 = fig.add_subplot(gs[1, 1])
ax2.set_facecolor(COLOURS["bg"])
sector_plot = sector_npl.sort_values("NPL_Ratio")
bar_colors  = ["#C0392B" if r > 20 else "#E67E22" if r > 10 else COLOURS["accent"]
               for r in sector_plot["NPL_Ratio"]]
ax2.barh(sector_plot.index, sector_plot["NPL_Ratio"],
         color=bar_colors, edgecolor="white")
ax2.axvline(x=10, color="#C0392B", linestyle="--", linewidth=1, label="10% threshold")
ax2.set_title("NPL Ratio by Sector (%)", fontweight="bold",
              color=COLOURS["accent"], fontsize=10)
ax2.set_xlabel("NPL %", fontsize=8)
ax2.tick_params(labelsize=8)
ax2.legend(fontsize=7)

# ── Panel 4: Portfolio by Branch ─────────────────────────────────────────────
ax3 = fig.add_subplot(gs[1, 2])
ax3.set_facecolor(COLOURS["bg"])
branch_data = df.groupby("branch").agg(
    Outstanding=("outstanding_ghs", "sum"),
    NPL=("outstanding_ghs", lambda x: x[df.loc[x.index, "classification"].isin(NPL_CLASSES)].sum())
).sort_values("Outstanding", ascending=True)
x_pos = range(len(branch_data))
ax3.barh(branch_data.index, branch_data["Outstanding"] / 1e6,
         color=COLOURS["accent"], label="Total", alpha=0.8)
ax3.barh(branch_data.index, branch_data["NPL"] / 1e6,
         color="#C0392B", label="NPL", alpha=0.9)
ax3.set_title("Portfolio by Branch (GHS M)", fontweight="bold",
              color=COLOURS["accent"], fontsize=10)
ax3.set_xlabel("GHS Millions", fontsize=8)
ax3.tick_params(labelsize=8)
ax3.legend(fontsize=7)

# ── Panel 5: Early Warning Score Distribution ─────────────────────────────────
ax4 = fig.add_subplot(gs[2, 0])
ax4.set_facecolor(COLOURS["bg"])
ax4.hist(df["ews_score"], bins=20, color=COLOURS["accent"], edgecolor="white", alpha=0.85)
ax4.axvline(x=40, color="#C0392B", linestyle="--", linewidth=1.5, label="High-risk threshold (40)")
ax4.set_title("Early Warning Score Distribution", fontweight="bold",
              color=COLOURS["accent"], fontsize=10)
ax4.set_xlabel("EWS Score (0-100)", fontsize=8)
ax4.set_ylabel("Number of Loans", fontsize=8)
ax4.tick_params(labelsize=8)
ax4.legend(fontsize=7)

# ── Panel 6: Remediation — Planned vs Achieved ───────────────────────────────
ax5 = fig.add_subplot(gs[2, 1])
ax5.set_facecolor(COLOURS["bg"])
rem_by_class = df[df["classification"].isin(NPL_CLASSES)].groupby("classification").agg(
    Target=("improvement_target_ghs", "sum"),
    Achieved=("remediation_value_ghs", "sum")
)
x       = np.arange(len(rem_by_class))
width   = 0.35
ax5.bar(x - width/2, rem_by_class["Target"] / 1e6, width,
        label="Target",   color=COLOURS["accent"], alpha=0.9)
ax5.bar(x + width/2, rem_by_class["Achieved"] / 1e6, width,
        label="Achieved", color="#27AE60",          alpha=0.9)
ax5.set_title("Remediation: Planned vs Achieved (GHS M)", fontweight="bold",
              color=COLOURS["accent"], fontsize=10)
ax5.set_xticks(x)
ax5.set_xticklabels(rem_by_class.index, fontsize=8)
ax5.set_ylabel("GHS Millions", fontsize=8)
ax5.legend(fontsize=7)
ax5.tick_params(labelsize=8)

# ── Panel 7: DPD Ageing Bucket ───────────────────────────────────────────────
ax6 = fig.add_subplot(gs[2, 2])
ax6.set_facecolor(COLOURS["bg"])
max_dpd = int(df["days_past_due"].max()) + 1
bins   = [0, 1, 31, 91, 181, max(max_dpd, 182)]
labels = ["Current\n(0)", "1-30\nDPD", "31-90\nDPD", "91-180\nDPD", "180+\nDPD"]
df["dpd_bucket"] = pd.cut(df["days_past_due"], bins=bins, labels=labels,
                           right=False, include_lowest=True)
dpd_exposure = df.groupby("dpd_bucket")["outstanding_ghs"].sum() / 1e6
bar_cols = ["#1B4F8E", "#F5A623", "#E67E22", "#C0392B", "#7B241C"]
ax6.bar(dpd_exposure.index, dpd_exposure.values, color=bar_cols, edgecolor="white")
ax6.set_title("Exposure by DPD Ageing Bucket (GHS M)", fontweight="bold",
              color=COLOURS["accent"], fontsize=10)
ax6.set_ylabel("GHS Millions", fontsize=8)
ax6.tick_params(labelsize=8)

plt.savefig("outputs/credit_monitoring_dashboard.png",
            dpi=150, bbox_inches="tight", facecolor=COLOURS["bg"])
plt.show()
print("\n[Dashboard saved: outputs/credit_monitoring_dashboard.png]")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. AUTOMATED MONITORING REPORT (CSV export)
# ═══════════════════════════════════════════════════════════════════════════════
report_df = df[[
    "loan_id", "borrower_name", "sector", "branch", "relationship_manager",
    "outstanding_ghs", "days_past_due", "classification",
    "collateral_coverage_pct", "provision_amount_ghs",
    "remediation_value_ghs", "improvement_target_ghs",
    "review_completed", "ews_score"
]].sort_values(["classification", "ews_score"], ascending=[True, False])

report_df.to_csv("outputs/monitoring_report_april_2026.csv", index=False)
high_risk[["loan_id","borrower_name","sector","outstanding_ghs",
           "days_past_due","classification","ews_score"]].to_csv(
    "outputs/high_risk_watchlist.csv", index=False
)

print(f"\n[Reports saved to outputs/]")
print(f"  \u2022 monitoring_report_april_2026.csv ({len(report_df)} accounts)")
print(f"  \u2022 high_risk_watchlist.csv ({len(high_risk)} flagged accounts)")
print("\n" + "=" * 65)
