"""
generate_data.py
Generates a realistic synthetic Ghanaian bank loan portfolio dataset
for credit monitoring analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

np.random.seed(42)
random.seed(42)

N = 500

ghanaian_names = [
    "Kwame Asante", "Ama Owusu", "Kofi Mensah", "Akosua Boateng",
    "Yaw Darko", "Abena Frimpong", "Kojo Antwi", "Efua Osei",
    "Kwabena Acheampong", "Adwoa Adjei", "Nana Sarpong", "Akua Amponsah",
    "Fiifi Koomson", "Esi Tetteh", "Kwesi Appiah", "Maame Amoah",
    "Kofi Agyeman", "Ama Bonsu", "Yaw Quartey", "Akosua Quaye",
    "Emmanuel Boateng", "Grace Mensah", "Daniel Asante", "Rebecca Ofori"
]
sectors = ["Retail Trade", "Agriculture", "Manufacturing", "Services",
           "Real Estate", "Transport", "Healthcare", "Education", "Construction"]
branches = ["Accra Main", "Kumasi", "Takoradi", "Tema", "Cape Coast", "Tamale"]
loan_types = ["Term Loan", "Overdraft", "Mortgage", "SME Loan", "Agricultural Loan"]
relationship_managers = ["R. Asante", "K. Mensah", "A. Owusu", "Y. Darko", "E. Frimpong"]

start = datetime(2021, 1, 1)
end   = datetime(2024, 12, 31)

rows = []
for i in range(1, N + 1):
    origination   = start + timedelta(days=random.randint(0, (end - start).days))
    term_months   = random.choice([12, 24, 36, 48, 60])
    maturity      = origination + timedelta(days=term_months * 30)
    principal     = round(random.choice([
        np.random.normal(50000, 15000),
        np.random.normal(200000, 60000),
        np.random.normal(500000, 150000)
    ]), -3)
    principal = max(10000, principal)

    # Days past due drives classification
    dpd = max(0, int(np.random.exponential(30)))
    if   dpd == 0:       classification = "Current"
    elif dpd <= 30:      classification = "Watch"
    elif dpd <= 90:      classification = "Substandard"
    elif dpd <= 180:     classification = "Doubtful"
    else:                classification = "Loss"

    provision_rates = {"Current": 0.01, "Watch": 0.05,
                       "Substandard": 0.25, "Doubtful": 0.50, "Loss": 1.00}
    provision_rate  = provision_rates[classification]

    outstanding   = round(principal * random.uniform(0.30, 0.98), 2)
    collateral    = round(principal * random.uniform(0.5, 1.8), 2)
    provision_amt = round(outstanding * provision_rate, 2)
    coverage_pct  = round((collateral / outstanding) * 100, 1) if outstanding > 0 else 0
    remediation   = round(outstanding * random.uniform(0.1, 0.6), 2) if classification != "Current" else 0

    last_payment  = origination + timedelta(days=random.randint(30, (datetime(2025, 4, 1) - origination).days))
    sector        = random.choice(sectors)
    branch        = random.choice(branches)
    loan_type     = random.choice(loan_types)
    rm            = random.choice(relationship_managers)
    borrower      = random.choice(ghanaian_names)

    rows.append({
        "loan_id":              f"LN{i:05d}",
        "borrower_name":        borrower,
        "sector":               sector,
        "branch":               branch,
        "loan_type":            loan_type,
        "relationship_manager": rm,
        "origination_date":     origination.strftime("%Y-%m-%d"),
        "maturity_date":        maturity.strftime("%Y-%m-%d"),
        "principal_ghs":        principal,
        "outstanding_ghs":      outstanding,
        "collateral_value_ghs": collateral,
        "days_past_due":        dpd,
        "classification":       classification,
        "provision_rate":       provision_rate,
        "provision_amount_ghs": provision_amt,
        "collateral_coverage_pct": coverage_pct,
        "last_payment_date":    last_payment.strftime("%Y-%m-%d"),
        "remediation_value_ghs": remediation,
        "review_completed":     random.choice([True, True, True, False]),
        "improvement_target_ghs": round(remediation * random.uniform(0.4, 0.9), 2)
    })

df = pd.DataFrame(rows)
df.to_csv("data/loan_portfolio.csv", index=False)
print(f"Generated {len(df)} loan records")
print(df["classification"].value_counts())
print(f"\nTotal Portfolio (GHS): {df['outstanding_ghs'].sum():,.0f}")
print(f"Total NPL (GHS):       {df[df['classification'].isin(['Substandard','Doubtful','Loss'])]['outstanding_ghs'].sum():,.0f}")
