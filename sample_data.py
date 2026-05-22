from __future__ import annotations

from datetime import date, timedelta

import pandas as pd


CITIES = ["Grand Rapids", "Holland", "Muskegon", "Kalamazoo", "Saginaw", "Traverse City"]
TENANTS = [
    "Byron Center Showroom",
    "Grand Rapids Metro",
    "Northern Michigan",
    "Tri-Cities Market",
]
INDUSTRIES = [
    "Wet Area Remodel",
    "Aging-in-Place",
    "Jacuzzi Dealer",
    "Homeowner Remodel",
    "Veteran Accessibility",
]
PRODUCTS = [
    "Jacuzzi Bathtub",
    "Walk-In Shower",
    "Tub-to-Shower Conversion",
    "Shower-to-Tub Conversion",
    "Senior Safety Remodel",
]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]


def _dimension(index: int) -> dict[str, str]:
    return {
        "City": CITIES[index % len(CITIES)],
        "Tenant": TENANTS[index % len(TENANTS)],
        "Industry": INDUSTRIES[index % len(INDUSTRIES)],
        "Product": PRODUCTS[index % len(PRODUCTS)],
    }


def demo_deals() -> pd.DataFrame:
    today = date.today()
    stages = [
        "Qualification",
        "Proposal/Price Quote",
        "Negotiation/Review",
        "Closed Won",
        "Closed Lost",
        "Needs Analysis",
        "Value Proposition",
        "Closed Won",
    ]
    owners = ["Camilo", "Laura", "Daniela", "Sofia", "Mateo", "Isabella"]
    rows = []
    for index in range(24):
        rows.append(
            {
                **_dimension(index),
                "Deal_Name": f"{PRODUCTS[index % len(PRODUCTS)]} project {index + 1}",
                "Stage": stages[index % len(stages)],
                "Amount": 8500 + (index * 4300) + ((index % 4) * 2200),
                "Closing_Date": today + timedelta(days=(index * 5) - 30),
                "Account_Name": TENANTS[index % len(TENANTS)],
                "Owner": owners[index % len(owners)],
            }
        )
    return pd.DataFrame(rows)


def demo_leads() -> pd.DataFrame:
    today = date.today()
    statuses = ["Contacted", "Not Contacted", "Qualified", "Junk Lead", "Nurturing"]
    rows = []
    for index in range(36):
        rows.append(
            {
                **_dimension(index),
                "Company": f"{CITIES[index % len(CITIES)]} homeowner {index + 1}",
                "Lead_Status": statuses[index % len(statuses)],
                "Lead_Source": ["Website Form", "Phone Call", "Showroom", "Event", "Referral"][index % 5],
                "Created_Time": today - timedelta(days=index * 2),
                "Owner": ["Camilo", "Laura", "Daniela", "Sofia"][index % 4],
            }
        )
    return pd.DataFrame(rows)


def demo_recruiter_performance() -> pd.DataFrame:
    recruiters = ["Ana Torres", "Miguel Rios", "Valeria Gomez", "Santiago Mora", "Nina Patel"]
    roles = [
        "In-House Installer",
        "Design Consultant",
        "Appointment Setter",
        "Project Coordinator",
        "Service Technician",
    ]
    rows = []
    for index in range(30):
        candidates = 72 + (index * 9) % 95
        interviews = int(candidates * (0.27 + (index % 4) * 0.03))
        offers = int(interviews * (0.22 + (index % 3) * 0.04))
        hires = max(1, int(offers * (0.48 + (index % 4) * 0.05)))
        rows.append(
            {
                **_dimension(index),
                "Recruiter": recruiters[index % len(recruiters)],
                "Role": roles[index % len(roles)],
                "Open_Roles": 3 + index % 9,
                "Candidates": candidates,
                "Interviews": interviews,
                "Offers": offers,
                "Hires": hires,
                "Avg_Days_To_Hire": 18 + index % 17,
                "Quality_Score": 78 + index % 20,
            }
        )
    return pd.DataFrame(rows)


def demo_call_center_performance() -> pd.DataFrame:
    teams = ["Inbound Leads", "Outbound Follow-Up", "Showroom", "Install Support", "Warranty Care"]
    rows = []
    for index in range(30):
        calls = 720 + (index * 137) % 1650
        answered = int(calls * (0.71 + (index % 5) * 0.045))
        answered = min(answered, calls)
        city_factor = CITIES.index(CITIES[index % len(CITIES)]) + 1
        agents = 8 + city_factor * 2 + (index % 5) * 3 + int(calls / 420)
        rows.append(
            {
                **_dimension(index),
                "Team": teams[index % len(teams)],
                "Agents": agents,
                "Calls": calls,
                "Answered": answered,
                "Missed": calls - answered,
                "Avg_Handle_Time": round(4.2 + (index % 9) * 0.65, 1),
                "SLA": 78 + index % 19,
                "CSAT": round(3.8 + (index % 12) * 0.1, 1),
                "Conversions": 34 + (index * 7) % 160,
            }
        )
    return pd.DataFrame(rows)


def demo_sales_performance() -> pd.DataFrame:
    reps = ["Laura Pena", "Daniel Ortiz", "Camilo Ruiz", "Paula Mejia", "Ava Chen", "Noah Smith"]
    rows = []
    for index in range(36):
        pipeline = 52000 + (index * 12500) % 230000
        closed_won = int(pipeline * (0.22 + (index % 5) * 0.035))
        deals_won = 3 + index % 14
        rows.append(
            {
                **_dimension(index),
                "Rep": reps[index % len(reps)],
                "Pipeline": pipeline,
                "Closed_Won": closed_won,
                "Deals_Won": deals_won,
                "Win_Rate": 24 + index % 21,
                "Avg_Deal_Size": int(closed_won / deals_won),
                "Forecast": int(pipeline * (0.45 + (index % 4) * 0.06)),
            }
        )
    return pd.DataFrame(rows)


def demo_marketing_performance() -> pd.DataFrame:
    channels = ["Paid Search", "Social Ads", "Email", "Home Shows", "Organic", "Referrals"]
    rows = []
    for index in range(36):
        spend = 3200 + (index * 1450) % 26000
        leads = 120 + (index * 41) % 720
        mql = int(leads * (0.31 + (index % 5) * 0.035))
        sql = int(mql * (0.34 + (index % 4) * 0.04))
        revenue = int(spend * (2.6 + (index % 7) * 0.42))
        rows.append(
            {
                **_dimension(index),
                "Channel": channels[index % len(channels)],
                "Spend": spend,
                "Leads": leads,
                "MQL": mql,
                "SQL": sql,
                "CAC": int(spend / max(sql, 1)),
                "Revenue": revenue,
            }
        )
    return pd.DataFrame(rows)


def demo_gross_revenue_monthly() -> pd.DataFrame:
    rows = []
    for tenant_index, tenant in enumerate(TENANTS):
        for month_index, month in enumerate(MONTHS):
            index = tenant_index * len(MONTHS) + month_index
            gross = 118000 + (tenant_index * 42000) + (month_index * 18500)
            rows.append(
                {
                    **_dimension(index),
                    "Month": month,
                    "Gross_Revenue": gross,
                    "Net_Revenue": int(gross * (0.86 + (month_index % 3) * 0.015)),
                    "Refunds": int(gross * (0.035 + (tenant_index % 2) * 0.008)),
                    "New": int(gross * 0.26),
                    "Expansion": int(gross * 0.18),
                    "Recurring": int(gross * 0.56),
                }
            )
    return pd.DataFrame(rows)


def demo_gross_revenue_segments() -> pd.DataFrame:
    segments = ["Bathtubs", "Showers", "Conversions", "Senior Safety"]
    rows = []
    for index, industry in enumerate(INDUSTRIES * 2):
        rows.append(
            {
                **_dimension(index),
                "Segment": segments[index % len(segments)],
                "Region": ["West Michigan", "Northern Michigan", "Tri-Cities"][index % 3],
                "Revenue": 165000 + (index * 59000) % 620000,
                "Margin": 34 + index % 20,
            }
        )
    return pd.DataFrame(rows)
