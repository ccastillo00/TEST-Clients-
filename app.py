from __future__ import annotations

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


def render_sidebar() -> bool:
    st.sidebar.title("Settings")
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
    return use_demo


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
        fig = px.bar(
            df,
            x="Recruiter",
            y=["Candidates", "Interviews", "Offers", "Hires"],
            barmode="group",
            title="Recruiter funnel",
        )
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with table_col:
        fig = px.scatter(
            df,
            x="Avg_Days_To_Hire",
            y="Quality_Score",
            size="Hires",
            color="City",
            hover_data=["Recruiter", "Tenant", "Industry", "Product"],
            title="Quality vs speed by city",
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
    df = render_dimension_filters(df, "call_center")
    if df.empty:
        st.info("No call center records match the current filters.")
        return
    answer_rate = df["Answered"].sum() / df["Calls"].sum() * 100
    avg_sla = float(df["SLA"].mean())
    avg_csat = float(df["CSAT"].mean())
    total_conversions = int(df["Conversions"].sum())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Answer rate", percent(answer_rate))
    with col2:
        metric_card("Average SLA", percent(avg_sla))
    with col3:
        metric_card("Average CSAT", f"{avg_csat:.1f}/5")
    with col4:
        metric_card("Conversions", f"{total_conversions:,}")

    chart_col, table_col = st.columns([1, 1])
    with chart_col:
        fig = px.bar(
            df,
            x="Team",
            y=["Answered", "Missed"],
            barmode="stack",
            title="Answered vs missed calls",
        )
        fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with table_col:
        fig = px.line(
            df,
            x="Team",
            y=["SLA", "CSAT"],
            markers=True,
            title="SLA and satisfaction by team",
        )
        fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        by_city = df.groupby("City", as_index=False)["Calls"].sum()
        plot_bar(by_city, "City", "Calls", "Call volume by city")
    with sub_col2:
        by_tenant = df.groupby("Tenant", as_index=False)["Conversions"].sum()
        plot_bar(by_tenant, "Tenant", "Conversions", "Conversions by tenant")
    with sub_col3:
        by_industry = df.groupby("Industry", as_index=False)["CSAT"].mean()
        plot_bar(by_industry, "Industry", "CSAT", "CSAT by industry")

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
        fig = px.bar(
            df,
            x="Rep",
            y=["Pipeline", "Closed_Won", "Forecast"],
            barmode="group",
            title="Pipeline, closed won, and forecast",
        )
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with table_col:
        fig = px.scatter(
            df,
            x="Win_Rate",
            y="Avg_Deal_Size",
            size="Deals_Won",
            color="Rep",
            title="Win rate vs average ticket",
            hover_data=["City", "Tenant", "Industry", "Product"],
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
        funnel = df.melt(
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
            df,
            x="Spend",
            y="Revenue",
            size="MQL",
            color="Channel",
            hover_data=["City", "Tenant", "Industry", "Product"],
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

    use_demo = render_sidebar()

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

    if use_demo:
        (
            recruiter_tab,
            call_center_tab,
            sales_tab,
            marketing_tab,
            revenue_tab,
            zoho_sales_tab,
            zoho_leads_tab,
        ) = st.tabs(
            [
                "Recruiter Performance",
                "Call Center Performance",
                "Sales Performance",
                "Marketing Performance",
                "Gross Revenue",
                "Zoho Sales",
                "Zoho Leads",
            ]
        )
        with recruiter_tab:
            render_recruiter_performance(demo_recruiter_performance())
        with call_center_tab:
            render_call_center_performance(demo_call_center_performance())
        with sales_tab:
            render_sales_performance(demo_sales_performance())
        with marketing_tab:
            render_marketing_performance(demo_marketing_performance())
        with revenue_tab:
            render_gross_revenue(demo_gross_revenue_monthly(), demo_gross_revenue_segments())
        with zoho_sales_tab:
            render_deals(deals)
        with zoho_leads_tab:
            render_leads(leads)
    else:
        tab_sales, tab_leads = st.tabs(["Sales", "Leads"])
        with tab_sales:
            render_deals(deals)
        with tab_leads:
            render_leads(leads)


if __name__ == "__main__":
    main()
