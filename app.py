from __future__ import annotations

import math
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from sample_data import (
    demo_call_center_performance,
    demo_deals,
    demo_gross_revenue_monthly,
    demo_gross_revenue_segments,
    demo_leads,
    demo_marketing_performance,
    demo_recruiter_performance,
    demo_sales_performance,
)
from zoho_client import ZohoApiError, ZohoConfig, ZohoCRMClient


st.set_page_config(
    page_title="Enterprise Dashboard",
    page_icon="📈",
    layout="wide",
)


DEAL_FIELDS = [
    "City",
    "Tenant",
    "Industry",
    "Product",
    "Deal_Name",
    "Stage",
    "Amount",
    "Closing_Date",
    "Account_Name",
    "Owner",
]
LEAD_FIELDS = [
    "City",
    "Tenant",
    "Industry",
    "Product",
    "Company",
    "Lead_Status",
    "Lead_Source",
    "Created_Time",
    "Owner",
]
DIMENSION_COLUMNS = ["City", "Tenant", "Industry", "Product"]
LOGIN_USER = "camilo.cast"
LOGIN_PASSWORD = "123456"
COMPANY_GROWTH_TARGET = 0.80


def get_secret(name: str, default: str = "") -> str:
    try:
        zoho_secrets = st.secrets.get("zoho", {})
    except Exception:
        zoho_secrets = {}
    return str(zoho_secrets.get(name, default))


def has_zoho_secrets() -> bool:
    required = ["accounts_url", "api_domain", "client_id", "client_secret", "refresh_token"]
    return all(get_secret(key) for key in required)


def normalize_lookup(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("id") or "")
    if value is None:
        return ""
    return str(value)


def records_to_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df

    for column in df.columns:
        if df[column].map(lambda item: isinstance(item, dict)).any():
            df[column] = df[column].map(normalize_lookup)
    return df


@st.cache_data(ttl=600, show_spinner=False)
def load_zoho_module(module: str, fields: list[str]) -> pd.DataFrame:
    config = ZohoConfig(
        accounts_url=get_secret("accounts_url"),
        api_domain=get_secret("api_domain"),
        client_id=get_secret("client_id"),
        client_secret=get_secret("client_secret"),
        refresh_token=get_secret("refresh_token"),
        api_version=get_secret("api_version", "v8"),
    )
    client = ZohoCRMClient(config)
    records = client.get_records(module=module, fields=fields)
    return records_to_frame(records)


def coerce_money(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def prepare_deals(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    prepared = df.copy()
    if "Amount" in prepared:
        prepared["Amount"] = coerce_money(prepared["Amount"])
    if "Closing_Date" in prepared:
        prepared["Closing_Date"] = pd.to_datetime(prepared["Closing_Date"], errors="coerce")
    return prepared


def metric_card(label: str, value: str, help_text: str | None = None) -> None:
    st.metric(label=label, value=value, help=help_text)


def money(value: float) -> str:
    return f"${value:,.0f}"


def percent(value: float) -> str:
    return f"{value:.1f}%"


def authenticate_user() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.title("Enterprise Dashboard")
    st.caption("Sign in to review performance across operations, revenue, and growth.")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")

    if submitted:
        if username == LOGIN_USER and password == LOGIN_PASSWORD:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.rerun()
        st.error("Invalid username or password.")

    st.info("Demo credentials: camilo.cast / 123456")
    return False


def render_dimension_filters(df: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
    available = [column for column in DIMENSION_COLUMNS if column in df.columns]
    if not available or df.empty:
        return df

    with st.expander("Filters", expanded=True):
        columns = st.columns(len(available))
        filtered = df.copy()
        for index, column in enumerate(available):
            options = sorted(filtered[column].dropna().astype(str).unique())
            selected = columns[index].multiselect(
                column,
                options,
                default=options,
                key=f"{key_prefix}_{column}",
            )
            if selected:
                filtered = filtered[filtered[column].astype(str).isin(selected)]
        return filtered


def plot_bar(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    height: int = 340,
) -> None:
    if df.empty or x not in df or y not in df:
        st.info("No data available for this chart.")
        return
    fig = px.bar(df, x=x, y=y, color=color, title=title)
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")


def min_max_normalize(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0)
    minimum = numeric.min()
    maximum = numeric.max()
    if maximum == minimum:
        return pd.Series([0.5] * len(numeric), index=numeric.index)
    return (numeric - minimum) / (maximum - minimum)


def linear_regression_predict(x: pd.Series, y: pd.Series, target_x: pd.Series) -> pd.Series:
    x_mean = x.mean()
    y_mean = y.mean()
    variance = ((x - x_mean) ** 2).sum()
    slope = 0 if variance == 0 else ((x - x_mean) * (y - y_mean)).sum() / variance
    intercept = y_mean - slope * x_mean
    return intercept + slope * target_x


def build_call_center_staffing_model(df: pd.DataFrame) -> pd.DataFrame:
    city = (
        df.groupby("City", as_index=False)
        .agg(
            Agents=("Agents", "sum"),
            Calls=("Calls", "sum"),
            Answered=("Answered", "sum"),
            Missed=("Missed", "sum"),
            Avg_Handle_Time=("Avg_Handle_Time", "mean"),
            SLA=("SLA", "mean"),
            CSAT=("CSAT", "mean"),
            Conversions=("Conversions", "sum"),
        )
        .sort_values("City")
    )
    city["Answer_Rate"] = city["Answered"] / city["Calls"] * 100
    city["Calls_Per_Agent"] = city["Calls"] / city["Agents"]
    city["Service_Gap"] = (92 - city["SLA"]).clip(lower=0)
    city["Growth_Target"] = f"+{int(COMPANY_GROWTH_TARGET * 100)}%"

    city["Calls_Norm"] = min_max_normalize(city["Calls"])
    city["Missed_Norm"] = min_max_normalize(city["Missed"])
    city["AHT_Norm"] = min_max_normalize(city["Avg_Handle_Time"])
    city["Conversions_Norm"] = min_max_normalize(city["Conversions"])
    city["Service_Gap_Norm"] = min_max_normalize(city["Service_Gap"])
    city["Workload_Index"] = (
        city["Calls_Norm"] * 0.40
        + city["Missed_Norm"] * 0.20
        + city["AHT_Norm"] * 0.15
        + city["Conversions_Norm"] * 0.15
        + city["Service_Gap_Norm"] * 0.10
    )

    target_workload = (city["Workload_Index"] * (1 + COMPANY_GROWTH_TARGET)).clip(upper=1.8)
    predicted = linear_regression_predict(city["Workload_Index"], city["Agents"], target_workload)
    service_buffer = 1 + (city["Service_Gap_Norm"] * 0.18)
    city["Recommended_Agents"] = (predicted * service_buffer).map(lambda value: max(1, math.ceil(value)))
    city["Agent_Gap"] = city["Recommended_Agents"] - city["Agents"]
    return city


def render_sidebar(dashboard_options: list[str]) -> tuple[bool, str]:
    if st.session_state.get("selected_dashboard") not in dashboard_options:
        st.session_state["selected_dashboard"] = dashboard_options[0]

    st.sidebar.title("Workforce Dashboards")
    st.sidebar.markdown(
        """
        <style>
        section[data-testid="stSidebar"] div[data-testid="stButton"] {
            margin: 0.18rem 0;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
            width: 100%;
            justify-content: flex-start;
            padding: 0.65rem 0.85rem;
            border-radius: 0.45rem;
            color: #2f343d;
            background: transparent;
            font-weight: 600;
            border: 1px solid transparent;
            box-shadow: none;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
            background: #f3f5f8;
            color: #111827;
            border-color: transparent;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
            background: #ef5b5b;
            color: white;
            border-color: #ef5b5b;
            box-shadow: 0 6px 18px rgba(239, 91, 91, 0.18);
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover {
            background: #e14e4e;
            color: white;
            border-color: #e14e4e;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    for option in dashboard_options:
        selected = option == st.session_state["selected_dashboard"]
        if st.sidebar.button(
            option,
            key=f"nav_{option}",
            type="primary" if selected else "secondary",
        ):
            st.session_state["selected_dashboard"] = option
            st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Settings")
    st.sidebar.caption(f"Signed in as {st.session_state.get('username', LOGIN_USER)}")
    use_demo = st.sidebar.toggle(
        "Use demo data",
        value=not has_zoho_secrets(),
        help="Turn this off after .streamlit/secrets.toml is configured.",
    )
    st.sidebar.caption("Live data is read from Zoho CRM API v8.")
    if st.sidebar.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()
    if st.sidebar.button("Sign out"):
        st.session_state.clear()
        st.rerun()
    return use_demo, st.session_state["selected_dashboard"]


def render_deals(deals: pd.DataFrame) -> None:
    st.subheader("Zoho sales")
    if deals.empty:
        st.info("No deals are available for the current filters.")
        return

    filtered = render_dimension_filters(deals, "zoho_deals")
    stage_options = sorted(deals["Stage"].dropna().unique()) if "Stage" in deals else []
    selected_stages = st.multiselect("Stages", stage_options, default=stage_options)
    if selected_stages and "Stage" in filtered:
        filtered = filtered[filtered["Stage"].isin(selected_stages)]

    total_pipeline = float(filtered.get("Amount", pd.Series(dtype=float)).sum())
    won = filtered[filtered["Stage"].eq("Closed Won")] if "Stage" in filtered else pd.DataFrame()
    open_deals = filtered[~filtered["Stage"].isin(["Closed Won", "Closed Lost"])] if "Stage" in filtered else filtered

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total pipeline", money(total_pipeline))
    with col2:
        metric_card("Open deals", str(len(open_deals)))
    with col3:
        metric_card("Closed won", money(float(won.get("Amount", pd.Series(dtype=float)).sum())))
    with col4:
        avg_ticket = total_pipeline / len(filtered) if len(filtered) else 0
        metric_card("Average ticket", money(avg_ticket))

    chart_col, table_col = st.columns([1, 1])
    with chart_col:
        if "Stage" in filtered and "Amount" in filtered:
            by_stage = filtered.groupby("Stage", as_index=False)["Amount"].sum()
            fig = px.bar(
                by_stage,
                x="Stage",
                y="Amount",
                title="Pipeline by stage",
                labels={"Stage": "Stage", "Amount": "Amount"},
            )
            fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, width="stretch")
    with table_col:
        columns = [col for col in DEAL_FIELDS if col in filtered.columns]
        st.dataframe(filtered[columns], width="stretch", hide_index=True)


def render_leads(leads: pd.DataFrame) -> None:
    st.subheader("Zoho leads")
    if leads.empty:
        st.info("No leads are available.")
        return
    leads = render_dimension_filters(leads, "zoho_leads")

    col1, col2 = st.columns([1, 2])
    with col1:
        metric_card("Total leads", str(len(leads)))
        if "Lead_Status" in leads:
            qualified = leads["Lead_Status"].astype(str).str.contains("Qualified", case=False).sum()
            metric_card("Qualified leads", str(qualified))
    with col2:
        if "Lead_Status" in leads:
            by_status = leads.groupby("Lead_Status", as_index=False).size()
            fig = px.pie(
                by_status,
                names="Lead_Status",
                values="size",
                title="Distribution by status",
            )
            fig.update_layout(height=320, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, width="stretch")

    columns = [col for col in LEAD_FIELDS if col in leads.columns]
    st.dataframe(leads[columns], width="stretch", hide_index=True)


def render_growth_dashboard(
    deals: pd.DataFrame,
    leads: pd.DataFrame,
    call_center: pd.DataFrame,
    revenue_monthly: pd.DataFrame,
) -> None:
    st.subheader("Company growth dashboard")
    st.caption("Where we are today vs where we need to be to reach 80% growth by year end.")

    staffing = build_call_center_staffing_model(call_center)
    gross_revenue = float(revenue_monthly["Gross_Revenue"].sum())
    target_revenue = gross_revenue * (1 + COMPANY_GROWTH_TARGET)
    revenue_gap = target_revenue - gross_revenue

    current_agents = int(staffing["Agents"].sum())
    required_agents = int(staffing["Recommended_Agents"].sum())
    agent_gap = required_agents - current_agents

    pipeline = float(deals.get("Amount", pd.Series(dtype=float)).sum())
    target_pipeline = pipeline * (1 + COMPANY_GROWTH_TARGET)
    pipeline_gap = target_pipeline - pipeline

    current_leads = len(leads)
    target_leads = math.ceil(current_leads * (1 + COMPANY_GROWTH_TARGET))
    lead_gap = target_leads - current_leads

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Current gross revenue", money(gross_revenue))
    with col2:
        metric_card("Year-end revenue target", money(target_revenue))
    with col3:
        metric_card("Revenue gap", money(revenue_gap))
    with col4:
        metric_card("Growth target", "+80%")

    gap_col1, gap_col2, gap_col3, gap_col4 = st.columns(4)
    with gap_col1:
        metric_card("Current agents", f"{current_agents:,}")
    with gap_col2:
        metric_card("Required agents", f"{required_agents:,}")
    with gap_col3:
        metric_card("Pipeline gap", money(pipeline_gap))
    with gap_col4:
        metric_card("Lead gap", f"{lead_gap:,}")

    progress = pd.DataFrame(
        [
            {"Metric": "Gross revenue", "Current": gross_revenue, "Target": target_revenue},
            {"Metric": "Pipeline", "Current": pipeline, "Target": target_pipeline},
            {"Metric": "Leads", "Current": current_leads, "Target": target_leads},
            {"Metric": "Agents", "Current": current_agents, "Target": required_agents},
        ]
    )
    progress["Gap"] = progress["Target"] - progress["Current"]
    progress["Progress"] = progress["Current"] / progress["Target"] * 100

    chart_col, route_col = st.columns([1.2, 1])
    with chart_col:
        progress_chart = progress.melt(
            id_vars="Metric",
            value_vars=["Current", "Target"],
            var_name="Scenario",
            value_name="Value",
        )
        fig = px.bar(
            progress_chart,
            x="Metric",
            y="Value",
            color="Scenario",
            barmode="group",
            title="Current state vs year-end target",
        )
        fig.update_layout(height=390, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    with route_col:
        staffing_by_city = staffing.sort_values("Agent_Gap", ascending=False)
        fig = px.bar(
            staffing_by_city,
            x="City",
            y="Agent_Gap",
            color="Workload_Index",
            title="Hiring gap by market",
            labels={"Agent_Gap": "Agent gap"},
        )
        fig.update_layout(height=390, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    revenue_by_tenant = revenue_monthly.groupby("Tenant", as_index=False)[
        ["Gross_Revenue", "Net_Revenue"]
    ].sum()
    city_revenue = revenue_monthly.groupby("City", as_index=False)["Gross_Revenue"].sum()
    city_revenue["Target_Revenue"] = city_revenue["Gross_Revenue"] * (1 + COMPANY_GROWTH_TARGET)
    city_revenue["Revenue_Gap"] = city_revenue["Target_Revenue"] - city_revenue["Gross_Revenue"]

    detail_col1, detail_col2 = st.columns(2)
    with detail_col1:
        fig = px.bar(
            revenue_by_tenant,
            x="Tenant",
            y=["Gross_Revenue", "Net_Revenue"],
            barmode="group",
            title="Revenue base by tenant",
        )
        fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with detail_col2:
        fig = px.scatter(
            city_revenue,
            x="Gross_Revenue",
            y="Revenue_Gap",
            size="Target_Revenue",
            color="City",
            title="Market revenue gap to +80%",
        )
        fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    action_plan = staffing[
        ["City", "Agents", "Recommended_Agents", "Agent_Gap", "Workload_Index"]
    ].merge(
        city_revenue[["City", "Gross_Revenue", "Target_Revenue", "Revenue_Gap"]],
        on="City",
        how="left",
    )
    st.dataframe(
        action_plan.sort_values(["Agent_Gap", "Revenue_Gap"], ascending=False).style.format(
            {
                "Workload_Index": "{:.2f}",
                "Gross_Revenue": "${:,.0f}",
                "Target_Revenue": "${:,.0f}",
                "Revenue_Gap": "${:,.0f}",
            }
        ),
        width="stretch",
        hide_index=True,
    )


def render_recruiter_performance(df: pd.DataFrame) -> None:
    st.subheader("Recruiter performance")
    df = render_dimension_filters(df, "recruiting")
    if df.empty:
        st.info("No recruiting records match the current filters.")
        return
    total_candidates = int(df["Candidates"].sum())
    total_hires = int(df["Hires"].sum())
    conversion = total_hires / total_candidates * 100
    avg_days = float(df["Avg_Days_To_Hire"].mean())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Candidates", f"{total_candidates:,}")
    with col2:
        metric_card("Hires", f"{total_hires:,}")
    with col3:
        metric_card("Hire conversion", percent(conversion))
    with col4:
        metric_card("Avg days to hire", f"{avg_days:.0f}")

    chart_col, table_col = st.columns([1.15, 1])
    with chart_col:
        funnel_by_recruiter = df.groupby("Recruiter", as_index=False)[
            ["Candidates", "Interviews", "Offers", "Hires"]
        ].sum()
        fig = px.bar(
            funnel_by_recruiter,
            x="Recruiter",
            y=["Candidates", "Interviews", "Offers", "Hires"],
            barmode="group",
            title="Recruiter funnel",
        )
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with table_col:
        quality_by_recruiter = (
            df.groupby("Recruiter", as_index=False)
            .agg(
                Avg_Days_To_Hire=("Avg_Days_To_Hire", "mean"),
                Quality_Score=("Quality_Score", "mean"),
                Hires=("Hires", "sum"),
                Candidates=("Candidates", "sum"),
            )
            .sort_values("Recruiter")
        )
        fig = px.scatter(
            quality_by_recruiter,
            x="Avg_Days_To_Hire",
            y="Quality_Score",
            size="Hires",
            color="Recruiter",
            hover_data=["Candidates"],
            title="Quality vs speed by recruiter",
        )
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        by_city = df.groupby("City", as_index=False)["Hires"].sum()
        plot_bar(by_city, "City", "Hires", "Hires by city")
    with sub_col2:
        by_industry = df.groupby("Industry", as_index=False)["Candidates"].sum()
        plot_bar(by_industry, "Industry", "Candidates", "Candidates by industry")
    with sub_col3:
        by_product = df.groupby("Product", as_index=False)["Open_Roles"].sum()
        plot_bar(by_product, "Product", "Open_Roles", "Open roles by product")

    st.dataframe(df, width="stretch", hide_index=True)


def render_call_center_performance(df: pd.DataFrame) -> None:
    st.subheader("Call center performance")
    st.caption("Company growth target: 80% expansion across markets.")
    df = render_dimension_filters(df, "call_center")
    if df.empty:
        st.info("No call center records match the current filters.")
        return
    answer_rate = df["Answered"].sum() / df["Calls"].sum() * 100
    avg_sla = float(df["SLA"].mean())
    avg_csat = float(df["CSAT"].mean())
    total_conversions = int(df["Conversions"].sum())
    staffing = build_call_center_staffing_model(df)
    total_agents = int(staffing["Agents"].sum())
    recommended_agents = int(staffing["Recommended_Agents"].sum())
    agent_gap = recommended_agents - total_agents

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        metric_card("Answer rate", percent(answer_rate))
    with col2:
        metric_card("Average SLA", percent(avg_sla))
    with col3:
        metric_card("Average CSAT", f"{avg_csat:.1f}/5")
    with col4:
        metric_card("Conversions", f"{total_conversions:,}")
    with col5:
        metric_card("Agents now", f"{total_agents:,}")

    target_col1, target_col2, target_col3 = st.columns(3)
    with target_col1:
        metric_card("Growth target", "+80%")
    with target_col2:
        metric_card("Recommended agents", f"{recommended_agents:,}")
    with target_col3:
        metric_card("Agent gap", f"{agent_gap:+,}")

    chart_col, table_col = st.columns([1, 1])
    with chart_col:
        call_volume_by_team = df.groupby("Team", as_index=False)[["Answered", "Missed"]].sum()
        fig = px.bar(
            call_volume_by_team,
            x="Team",
            y=["Answered", "Missed"],
            barmode="stack",
            title="Answered vs missed calls",
        )
        fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with table_col:
        service_by_team = df.groupby("Team", as_index=False)[["SLA", "CSAT"]].mean()
        fig = px.line(
            service_by_team,
            x="Team",
            y=["SLA", "CSAT"],
            markers=True,
            title="SLA and satisfaction by team",
        )
        fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        by_city = df.groupby("City", as_index=False)[["Calls", "Agents"]].sum()
        fig = px.bar(
            by_city,
            x="City",
            y=["Calls", "Agents"],
            barmode="group",
            title="Call volume and agents by city",
        )
        fig.update_layout(height=340, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with sub_col2:
        by_tenant = df.groupby("Tenant", as_index=False)["Conversions"].sum()
        plot_bar(by_tenant, "Tenant", "Conversions", "Conversions by tenant")
    with sub_col3:
        by_industry = df.groupby("Industry", as_index=False)["CSAT"].mean()
        plot_bar(by_industry, "Industry", "CSAT", "CSAT by industry")

    st.markdown("#### Staffing normalization and regression")
    model_col1, model_col2 = st.columns([1.1, 1])
    with model_col1:
        line_x = pd.Series(
            [
                float(staffing["Workload_Index"].min()),
                float(staffing["Workload_Index"].max()),
            ]
        )
        line_y = linear_regression_predict(
            staffing["Workload_Index"], staffing["Agents"], line_x
        )
        fig = px.scatter(
            staffing,
            x="Workload_Index",
            y="Agents",
            size="Calls",
            color="City",
            hover_data=[
                "Calls",
                "Missed",
                "SLA",
                "CSAT",
                "Calls_Per_Agent",
                "Recommended_Agents",
                "Agent_Gap",
            ],
            title="Regression: normalized workload vs current agents",
            labels={"Workload_Index": "Normalized workload index", "Agents": "Current agents"},
        )
        fig.add_scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            name="Regression line",
            line=dict(color="#2f343d", width=3),
        )
        fig.update_layout(height=390, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with model_col2:
        comparison = staffing.melt(
            id_vars="City",
            value_vars=["Agents", "Recommended_Agents"],
            var_name="Staffing_Type",
            value_name="Agent_Count",
        )
        fig = px.bar(
            comparison,
            x="City",
            y="Agent_Count",
            color="Staffing_Type",
            barmode="group",
            title="Current vs recommended agents by market",
        )
        fig.update_layout(height=390, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    display_columns = [
        "City",
        "Agents",
        "Recommended_Agents",
        "Agent_Gap",
        "Calls",
        "Calls_Per_Agent",
        "Answer_Rate",
        "SLA",
        "CSAT",
        "Workload_Index",
        "Growth_Target",
    ]
    st.dataframe(
        staffing[display_columns].style.format(
            {
                "Calls_Per_Agent": "{:,.1f}",
                "Answer_Rate": "{:.1f}%",
                "SLA": "{:.1f}%",
                "CSAT": "{:.1f}",
                "Workload_Index": "{:.2f}",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.dataframe(df, width="stretch", hide_index=True)


def render_sales_performance(df: pd.DataFrame) -> None:
    st.subheader("Sales performance")
    df = render_dimension_filters(df, "sales")
    if df.empty:
        st.info("No sales records match the current filters.")
        return
    total_pipeline = float(df["Pipeline"].sum())
    total_won = float(df["Closed_Won"].sum())
    weighted_win_rate = df["Closed_Won"].sum() / df["Pipeline"].sum() * 100
    forecast = float(df["Forecast"].sum())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Pipeline", money(total_pipeline))
    with col2:
        metric_card("Closed won", money(total_won))
    with col3:
        metric_card("Weighted win rate", percent(weighted_win_rate))
    with col4:
        metric_card("Forecast", money(forecast))

    chart_col, table_col = st.columns([1.1, 1])
    with chart_col:
        sales_by_rep = (
            df.groupby("Rep", as_index=False)
            .agg(
                Pipeline=("Pipeline", "sum"),
                Closed_Won=("Closed_Won", "sum"),
                Forecast=("Forecast", "sum"),
                Deals_Won=("Deals_Won", "sum"),
                Win_Rate=("Win_Rate", "mean"),
            )
            .sort_values("Rep")
        )
        sales_by_rep["Avg_Deal_Size"] = sales_by_rep["Closed_Won"] / sales_by_rep[
            "Deals_Won"
        ].clip(lower=1)
        fig = px.bar(
            sales_by_rep,
            x="Rep",
            y=["Pipeline", "Closed_Won", "Forecast"],
            barmode="group",
            title="Pipeline, closed won, and forecast",
        )
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with table_col:
        fig = px.scatter(
            sales_by_rep,
            x="Win_Rate",
            y="Avg_Deal_Size",
            size="Deals_Won",
            color="Rep",
            title="Win rate vs average ticket",
            labels={"Win_Rate": "Win rate", "Avg_Deal_Size": "Average deal size"},
        )
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        by_city = df.groupby("City", as_index=False)["Pipeline"].sum()
        plot_bar(by_city, "City", "Pipeline", "Pipeline by city")
    with sub_col2:
        by_industry = df.groupby("Industry", as_index=False)["Closed_Won"].sum()
        plot_bar(by_industry, "Industry", "Closed_Won", "Closed won by industry")
    with sub_col3:
        by_product = df.groupby("Product", as_index=False)["Forecast"].sum()
        plot_bar(by_product, "Product", "Forecast", "Forecast by product")

    st.dataframe(df, width="stretch", hide_index=True)


def render_marketing_performance(df: pd.DataFrame) -> None:
    st.subheader("Marketing performance")
    df = render_dimension_filters(df, "marketing")
    if df.empty:
        st.info("No marketing records match the current filters.")
        return
    total_spend = float(df["Spend"].sum())
    total_revenue = float(df["Revenue"].sum())
    total_leads = int(df["Leads"].sum())
    roi = (total_revenue - total_spend) / total_spend * 100

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Spend", money(total_spend))
    with col2:
        metric_card("Attributed revenue", money(total_revenue))
    with col3:
        metric_card("Leads", f"{total_leads:,}")
    with col4:
        metric_card("ROI", percent(roi))

    chart_col, table_col = st.columns([1, 1])
    with chart_col:
        marketing_by_channel = (
            df.groupby("Channel", as_index=False)
            .agg(
                Spend=("Spend", "sum"),
                Leads=("Leads", "sum"),
                MQL=("MQL", "sum"),
                SQL=("SQL", "sum"),
                Revenue=("Revenue", "sum"),
            )
            .sort_values("Channel")
        )
        marketing_by_channel["CAC"] = marketing_by_channel["Spend"] / marketing_by_channel[
            "SQL"
        ].clip(lower=1)
        funnel = marketing_by_channel.melt(
            id_vars="Channel",
            value_vars=["Leads", "MQL", "SQL"],
            var_name="Stage",
            value_name="Count",
        )
        fig = px.bar(
            funnel,
            x="Channel",
            y="Count",
            color="Stage",
            barmode="group",
            title="Marketing funnel by channel",
        )
        fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with table_col:
        fig = px.scatter(
            marketing_by_channel,
            x="Spend",
            y="Revenue",
            size="MQL",
            color="Channel",
            title="Spend vs revenue",
        )
        fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        by_city = df.groupby("City", as_index=False)["Leads"].sum()
        plot_bar(by_city, "City", "Leads", "Leads by city")
    with sub_col2:
        by_tenant = df.groupby("Tenant", as_index=False)["Revenue"].sum()
        plot_bar(by_tenant, "Tenant", "Revenue", "Revenue by tenant")
    with sub_col3:
        by_product = df.groupby("Product", as_index=False)["CAC"].mean()
        plot_bar(by_product, "Product", "CAC", "Average CAC by product")

    st.dataframe(df, width="stretch", hide_index=True)


def render_gross_revenue(monthly: pd.DataFrame, segments: pd.DataFrame) -> None:
    st.subheader("Gross revenue")
    monthly = render_dimension_filters(monthly, "gross_revenue_monthly")
    if monthly.empty:
        st.info("No revenue records match the current filters.")
        return
    shared_filters = monthly[DIMENSION_COLUMNS].drop_duplicates()
    segments = segments.merge(shared_filters, on=DIMENSION_COLUMNS, how="inner")
    gross = float(monthly["Gross_Revenue"].sum())
    net = float(monthly["Net_Revenue"].sum())
    refunds = float(monthly["Refunds"].sum())
    margin = (
        float((segments["Revenue"] * segments["Margin"]).sum() / segments["Revenue"].sum())
        if not segments.empty
        else 0
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Gross revenue", money(gross))
    with col2:
        metric_card("Net revenue", money(net))
    with col3:
        metric_card("Refunds", money(refunds))
    with col4:
        metric_card("Average margin", percent(margin))

    overview_tab, mix_tab, segment_tab, table_tab = st.tabs(
        ["Overview", "Revenue mix", "Segments", "Detail"]
    )
    with overview_tab:
        monthly_totals = monthly.groupby("Month", as_index=False)[
            ["Gross_Revenue", "Net_Revenue", "Refunds"]
        ].sum()
        fig = px.line(
            monthly_totals,
            x="Month",
            y=["Gross_Revenue", "Net_Revenue"],
            markers=True,
            color_discrete_sequence=px.colors.qualitative.Set2,
            title="Monthly revenue",
        )
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")

        split_col1, split_col2 = st.columns(2)
        with split_col1:
            by_tenant = monthly.groupby("Tenant", as_index=False)["Gross_Revenue"].sum()
            plot_bar(by_tenant, "Tenant", "Gross_Revenue", "Gross revenue by tenant")
        with split_col2:
            by_city = monthly.groupby("City", as_index=False)["Net_Revenue"].sum()
            plot_bar(by_city, "City", "Net_Revenue", "Net revenue by city")
    with mix_tab:
        mix_source = monthly.groupby("Month", as_index=False)[
            ["New", "Expansion", "Recurring"]
        ].sum()
        mix = mix_source.melt(
            id_vars="Month",
            value_vars=["New", "Expansion", "Recurring"],
            var_name="Revenue_Type",
            value_name="Revenue",
        )
        fig = px.area(
            mix,
            x="Month",
            y="Revenue",
            color="Revenue_Type",
            title="Revenue composition",
        )
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with segment_tab:
        if segments.empty:
            st.info("No segment detail is available for the current filters.")
        else:
            fig = px.sunburst(
                segments,
                path=["Region", "Segment", "Industry"],
                values="Revenue",
                color="Margin",
                title="Revenue by region, segment, and industry",
            )
            fig.update_layout(height=420, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, width="stretch")
    with table_tab:
        table_col, segment_col = st.columns(2)
        with table_col:
            st.dataframe(monthly, width="stretch", hide_index=True)
        with segment_col:
            st.dataframe(segments, width="stretch", hide_index=True)

def main() -> None:
    if not authenticate_user():
        return

    st.title("Enterprise Dashboard")
    st.caption(
        "Executive view of recruiting, call center, sales, marketing, and revenue performance."
    )

    dashboard_options = [
        "Main Growth Dashboard",
        "Recruiter Performance",
        "Call Center Performance",
        "Sales Performance",
        "Marketing Performance",
        "Gross Revenue",
        "Zoho Sales",
        "Zoho Leads",
    ]
    use_demo, selected_dashboard = render_sidebar(dashboard_options)

    try:
        if use_demo:
            deals = prepare_deals(demo_deals())
            leads = demo_leads()
        else:
            deals = prepare_deals(load_zoho_module("Deals", DEAL_FIELDS))
            leads = load_zoho_module("Leads", LEAD_FIELDS)
    except ZohoApiError as exc:
        st.error("Could not fetch data from Zoho.")
        st.exception(exc)
        st.stop()
    except Exception as exc:
        st.error("An unexpected error occurred while loading the dashboard.")
        st.exception(exc)
        st.stop()

    recruiter_data = demo_recruiter_performance()
    call_center_data = demo_call_center_performance()
    sales_data = demo_sales_performance()
    marketing_data = demo_marketing_performance()
    revenue_monthly = demo_gross_revenue_monthly()
    revenue_segments = demo_gross_revenue_segments()

    if selected_dashboard == "Main Growth Dashboard":
        render_growth_dashboard(deals, leads, call_center_data, revenue_monthly)
    elif selected_dashboard == "Recruiter Performance":
        render_recruiter_performance(recruiter_data)
    elif selected_dashboard == "Call Center Performance":
        render_call_center_performance(call_center_data)
    elif selected_dashboard == "Sales Performance":
        render_sales_performance(sales_data)
    elif selected_dashboard == "Marketing Performance":
        render_marketing_performance(marketing_data)
    elif selected_dashboard == "Gross Revenue":
        render_gross_revenue(revenue_monthly, revenue_segments)
    elif selected_dashboard == "Zoho Sales":
        render_deals(deals)
    elif selected_dashboard == "Zoho Leads":
        render_leads(leads)
    else:
        st.info("Select a dashboard from the sidebar.")


if __name__ == "__main__":
    main()
