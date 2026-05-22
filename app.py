from __future__ import annotations

import math
from html import escape
from typing import Any

import pandas as pd
import plotly.express as px
import requests
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
    page_title="BathWorks MI Dashboard",
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
DIMENSION_LABELS = {
    "City": "Service Area",
    "Tenant": "Market / Location",
    "Industry": "Customer Segment",
    "Product": "Remodel Product",
}
LOGIN_USER = "camilo.cast"
LOGIN_PASSWORD = "123456"
DEMO_AUTH_TOKEN = "camilo-cast-demo"
COMPANY_GROWTH_TARGET = 0.80
BATHWORKS_LOGO_URL = (
    "https://www.bathworksmi.com/_next/image?q=75&url=%2Fcdn--media%2F"
    "jacuzzi_bathworks_logo_black_3x__1__oiyy6yi7cg9h3kzs0umcf9-924x164.png&w=1920"
)
CHART_COLORWAY = [
    "#1D4ED8",
    "#EF4444",
    "#F59E0B",
    "#10B981",
    "#8B5CF6",
    "#EC4899",
    "#06B6D4",
    "#84CC16",
]
CITY_COLORS = {
    "Grand Rapids": "#1D4ED8",
    "Holland": "#14B8A6",
    "Muskegon": "#F97316",
    "Kalamazoo": "#8B5CF6",
    "Saginaw": "#EF4444",
    "Traverse City": "#22C55E",
}
KPI_COLORS = {
    "Current": "#1D4ED8",
    "Target": "#EF4444",
    "Gap": "#F59E0B",
    "Actual Revenue": "#1D4ED8",
    "Seasonal Target": "#EF4444",
    "Gross_Revenue": "#2563EB",
    "Net_Revenue": "#10B981",
    "Refunds": "#F97316",
    "Pipeline": "#7C3AED",
    "Closed_Won": "#10B981",
    "Forecast": "#F59E0B",
    "Candidates": "#2563EB",
    "Interviews": "#06B6D4",
    "Offers": "#F59E0B",
    "Hires": "#22C55E",
    "Answered": "#10B981",
    "Missed": "#EF4444",
    "Calls": "#2563EB",
    "Agents": "#8B5CF6",
    "Recommended_Agents": "#F59E0B",
    "SLA": "#14B8A6",
    "CSAT": "#EC4899",
    "Leads": "#2563EB",
    "MQL": "#F59E0B",
    "SQL": "#22C55E",
}
PRODUCT_COLORS = {
    "Jacuzzi Bathtub": "#1D4ED8",
    "Walk-In Shower": "#14B8A6",
    "Tub-to-Shower Conversion": "#F97316",
    "Shower-to-Tub Conversion": "#8B5CF6",
    "Senior Safety Remodel": "#EC4899",
}
RECRUITER_COLORS = {
    "Ana Torres": "#1D4ED8",
    "Miguel Rios": "#F97316",
    "Valeria Gomez": "#22C55E",
    "Santiago Mora": "#EF4444",
    "Nina Patel": "#8B5CF6",
    "Laura Pena": "#1D4ED8",
    "Daniel Ortiz": "#F97316",
    "Camilo Ruiz": "#22C55E",
    "Paula Mejia": "#EF4444",
    "Ava Chen": "#8B5CF6",
    "Noah Smith": "#06B6D4",
}
CHANNEL_COLORS = {
    "Paid Search": "#1D4ED8",
    "Social Ads": "#EC4899",
    "Email": "#F59E0B",
    "Home Shows": "#10B981",
    "Organic": "#22C55E",
    "Referrals": "#8B5CF6",
}
SEGMENT_COLORS = {
    "Wet Area Remodel": "#1D4ED8",
    "Aging-in-Place": "#8B5CF6",
    "Jacuzzi Dealer": "#14B8A6",
    "Homeowner Remodel": "#F97316",
    "Veteran Accessibility": "#EC4899",
}
SEASONAL_MONTH_WEIGHTS = {
    "Jan": 0.055,
    "Feb": 0.060,
    "Mar": 0.075,
    "Apr": 0.095,
    "May": 0.115,
    "Jun": 0.120,
    "Jul": 0.115,
    "Aug": 0.105,
    "Sep": 0.095,
    "Oct": 0.080,
    "Nov": 0.050,
    "Dec": 0.035,
}
MONTH_ORDER = list(SEASONAL_MONTH_WEIGHTS)
SERVICE_AREAS = {
    "Grand Rapids": {
        "latitude": 42.9634,
        "longitude": -85.6681,
        "census_name": "Grand Rapids city, Michigan",
        "datausa_place_id": "16000US2634000",
    },
    "Holland": {
        "latitude": 42.7875,
        "longitude": -86.1089,
        "census_name": "Holland city, Michigan",
        "datausa_place_id": "16000US2638640",
    },
    "Muskegon": {
        "latitude": 43.2342,
        "longitude": -86.2484,
        "census_name": "Muskegon city, Michigan",
        "datausa_place_id": "16000US2656320",
    },
    "Kalamazoo": {
        "latitude": 42.2917,
        "longitude": -85.5872,
        "census_name": "Kalamazoo city, Michigan",
        "datausa_place_id": "16000US2642160",
    },
    "Saginaw": {
        "latitude": 43.4195,
        "longitude": -83.9508,
        "census_name": "Saginaw city, Michigan",
        "datausa_place_id": "16000US2670520",
    },
    "Traverse City": {
        "latitude": 44.7631,
        "longitude": -85.6206,
        "census_name": "Traverse City city, Michigan",
        "datausa_place_id": "16000US2680340",
    },
}


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


@st.cache_data(ttl=900, show_spinner=False)
def load_open_meteo_weather() -> pd.DataFrame:
    rows = []
    for city, meta in SERVICE_AREAS.items():
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": meta["latitude"],
                "longitude": meta["longitude"],
                "current": "temperature_2m,precipitation,wind_speed_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "America/Detroit",
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        current = payload.get("current", {})
        rows.append(
            {
                "City": city,
                "API Source": "Open-Meteo",
                "Temperature": current.get("temperature_2m"),
                "Precipitation": current.get("precipitation"),
                "Wind Speed": current.get("wind_speed_10m"),
                "Fetched Time": current.get("time"),
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(ttl=900, show_spinner=False)
def load_nws_alerts() -> pd.DataFrame:
    rows = []
    headers = {"User-Agent": "BathWorksMI-Dashboard/1.0"}
    for city, meta in SERVICE_AREAS.items():
        response = requests.get(
            "https://api.weather.gov/alerts/active",
            params={"point": f"{meta['latitude']},{meta['longitude']}"},
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        features = response.json().get("features", [])
        events = sorted(
            {
                feature.get("properties", {}).get("event", "Unknown alert")
                for feature in features
            }
        )
        rows.append(
            {
                "City": city,
                "API Source": "National Weather Service",
                "Active Alerts": len(features),
                "Alert Types": ", ".join(events) if events else "None",
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(ttl=900, show_spinner=False)
def load_open_meteo_air_quality() -> pd.DataFrame:
    rows = []
    for city, meta in SERVICE_AREAS.items():
        response = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={
                "latitude": meta["latitude"],
                "longitude": meta["longitude"],
                "current": "us_aqi,pm2_5",
                "timezone": "America/Detroit",
            },
            timeout=20,
        )
        response.raise_for_status()
        current = response.json().get("current", {})
        rows.append(
            {
                "City": city,
                "API Source": "Open-Meteo Air Quality",
                "US AQI": current.get("us_aqi"),
                "PM2.5": current.get("pm2_5"),
            }
        )
    return pd.DataFrame(rows)


def datausa_query(
    cube: str,
    drilldowns: str,
    measures: str,
    include: str,
) -> pd.DataFrame:
    response = requests.get(
        "https://api.datausa.io/tesseract/data.jsonrecords",
        params={
            "cube": cube,
            "drilldowns": drilldowns,
            "measures": measures,
            "include": include,
            "limit": "100,0",
        },
        timeout=40,
    )
    response.raise_for_status()
    return pd.DataFrame(response.json().get("data", []))


@st.cache_data(ttl=86400, show_spinner=False)
def load_datausa_market_data() -> pd.DataFrame:
    place_ids = ",".join(meta["datausa_place_id"] for meta in SERVICE_AREAS.values())
    city_lookup = {meta["datausa_place_id"]: city for city, meta in SERVICE_AREAS.items()}

    population = datausa_query(
        cube="acs_yg_total_population_5",
        drilldowns="Place,Year",
        measures="Population",
        include=f"Year:2023;Place:{place_ids}",
    )
    income = datausa_query(
        cube="acs_ygr_median_household_income_race_5",
        drilldowns="Place,Year,Race",
        measures="Household Income by Race",
        include=f"Year:2023;Race:0;Place:{place_ids}",
    )
    home_value = datausa_query(
        cube="acs_yg_housing_median_value_5",
        drilldowns="Place,Year",
        measures="Property Value",
        include=f"Year:2023;Place:{place_ids}",
    )

    market = pd.DataFrame({"Place ID": list(city_lookup)})
    for frame in [population, income, home_value]:
        if not frame.empty and "Place ID" in frame:
            market = market.merge(frame, on="Place ID", how="left")

    market["City"] = market["Place ID"].map(city_lookup)
    market = market.rename(
        columns={
            "Household Income by Race": "Median Household Income",
            "Property Value": "Median Home Value",
        }
    )
    for column in ["Population", "Median Household Income", "Median Home Value"]:
        if column not in market:
            market[column] = pd.NA
        market[column] = pd.to_numeric(market[column], errors="coerce")
        market.loc[market[column] < 0, column] = pd.NA
    market["API Source"] = "Data USA ACS 5-Year"
    return market[
        [
            "City",
            "API Source",
            "Population",
            "Median Household Income",
            "Median Home Value",
        ]
    ].sort_values("City")


def fallback_weather_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "City": list(SERVICE_AREAS),
            "Temperature": [65] * len(SERVICE_AREAS),
            "Precipitation": [0] * len(SERVICE_AREAS),
            "Wind Speed": [5] * len(SERVICE_AREAS),
        }
    )


def load_external_api_context() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    list[str],
    int,
]:
    api_errors = []
    connected_sources = 0
    try:
        weather = load_open_meteo_weather()
        connected_sources += int(not weather.empty)
    except Exception as exc:
        api_errors.append(f"Open-Meteo failed: {exc}")
        weather = fallback_weather_frame()

    try:
        alerts = load_nws_alerts()
        connected_sources += int(not alerts.empty)
    except Exception as exc:
        api_errors.append(f"National Weather Service failed: {exc}")
        alerts = pd.DataFrame(columns=["City", "Active Alerts", "Alert Types"])

    try:
        air_quality = load_open_meteo_air_quality()
        connected_sources += int(not air_quality.empty)
    except Exception as exc:
        api_errors.append(f"Open-Meteo Air Quality failed: {exc}")
        air_quality = pd.DataFrame(columns=["City", "US AQI", "PM2.5"])

    try:
        market = load_datausa_market_data()
        connected_sources += int(not market.empty)
    except Exception as exc:
        api_errors.append(f"Data USA market API failed: {exc}")
        market = pd.DataFrame(
            columns=["City", "Population", "Median Household Income", "Median Home Value"]
        )

    return weather, alerts, air_quality, market, api_errors, connected_sources


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


def chart_theme(fig: Any, height: int = 360) -> None:
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=50, b=20),
        colorway=CHART_COLORWAY,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="",
    )


def color_map_for(column: str | None) -> dict[str, str] | None:
    if column == "City":
        return CITY_COLORS
    if column == "Product":
        return PRODUCT_COLORS
    if column == "Recruiter":
        return RECRUITER_COLORS
    if column == "Channel":
        return CHANNEL_COLORS
    if column == "Industry":
        return SEGMENT_COLORS
    return None


def render_logo(width: int = 420) -> None:
    st.markdown(
        f"""
        <div style="background:#ffffff;border-radius:10px;padding:14px 18px;
                    display:inline-block;margin-bottom:18px;">
            <img src="{BATHWORKS_LOGO_URL}" alt="BathWorks MI Logo"
                 style="width:{width}px;max-width:100%;height:auto;display:block;" />
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_logo() -> None:
    st.sidebar.markdown(
        f"""
        <div style="background:#ffffff;border-radius:8px;padding:10px 12px;margin-bottom:18px;">
            <img src="{BATHWORKS_LOGO_URL}" alt="BathWorks MI Logo"
                 style="width:100%;height:auto;display:block;" />
        </div>
        """,
        unsafe_allow_html=True,
    )


def query_param(name: str, default: str = "") -> str:
    value = st.query_params.get(name, default)
    if isinstance(value, list):
        return str(value[0]) if value else default
    return str(value)


def set_query_param(name: str, value: str) -> None:
    st.query_params[name] = value


def authenticate_user() -> bool:
    if st.session_state.get("authenticated"):
        return True
    if query_param("auth") == DEMO_AUTH_TOKEN:
        st.session_state["authenticated"] = True
        st.session_state["username"] = LOGIN_USER
        return True

    render_logo()
    st.title("BathWorks MI Performance Dashboard")
    st.caption("Sign in to review lead flow, appointments, sales, staffing, and revenue growth.")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")

    if submitted:
        if username == LOGIN_USER and password == LOGIN_PASSWORD:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            set_query_param("auth", DEMO_AUTH_TOKEN)
            st.rerun()
        st.error("Invalid username or password.")

    st.info("Demo credentials: camilo.cast / 123456")
    return False


def render_dimension_filters(df: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
    available = [column for column in DIMENSION_COLUMNS if column in df.columns]
    if not available or df.empty:
        return df

    with st.expander("Filters", expanded=False):
        columns = st.columns(len(available))
        filtered = df.copy()
        for index, column in enumerate(available):
            options = sorted(filtered[column].dropna().astype(str).unique())
            label = DIMENSION_LABELS.get(column, column)
            selected = columns[index].multiselect(
                label,
                options,
                default=[],
                key=f"{key_prefix}_{column}_dropdown",
                placeholder=f"All {label.lower()}",
                help=f"Leave empty to include all {label.lower()}.",
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
    chart_color = color
    if chart_color is None and x in {"City", "Product", "Industry", "Channel", "Recruiter"}:
        chart_color = x
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=chart_color,
        title=title,
        color_discrete_map=color_map_for(chart_color),
    )
    chart_theme(fig, height)
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
    dashboard_from_url = query_param("dashboard", dashboard_options[0])
    if dashboard_from_url in dashboard_options:
        st.session_state["selected_dashboard"] = dashboard_from_url
    elif st.session_state.get("selected_dashboard") not in dashboard_options:
        st.session_state["selected_dashboard"] = dashboard_options[0]

    render_sidebar_logo()
    st.sidebar.title("BathWorks Dashboards")
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
            color: rgba(250, 250, 250, 0.88);
            background: transparent;
            font-weight: 600;
            border: 1px solid rgba(250, 250, 250, 0.10);
            box-shadow: none;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
            background: rgba(250, 250, 250, 0.10);
            color: #ffffff;
            border-color: rgba(250, 250, 250, 0.18);
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
        @media (prefers-color-scheme: light) {
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
                color: #2f343d;
                border-color: rgba(47, 52, 61, 0.08);
            }
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
                background: #f3f5f8;
                color: #111827;
                border-color: rgba(47, 52, 61, 0.12);
            }
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
                color: #ffffff;
            }
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
            set_query_param("dashboard", option)
            st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Settings")
    st.sidebar.caption(f"Signed in as {st.session_state.get('username', LOGIN_USER)}")
    use_demo = st.sidebar.toggle(
        "Use demo data",
        value=not has_zoho_secrets(),
        help="Turn this off after .streamlit/secrets.toml is configured.",
    )
    st.sidebar.caption("Live data can be read from Zoho CRM API v8.")
    if st.sidebar.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()
    if st.sidebar.button("Sign out"):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()
    return use_demo, st.session_state["selected_dashboard"]


def render_deals(deals: pd.DataFrame) -> None:
    st.subheader("Zoho sales pipeline")
    if deals.empty:
        st.info("No deals are available for the current filters.")
        return

    filtered = render_dimension_filters(deals, "zoho_deals")
    stage_options = sorted(deals["Stage"].dropna().unique()) if "Stage" in deals else []
    selected_stages = st.multiselect(
        "Stages",
        stage_options,
        default=[],
        key="zoho_deals_stage_dropdown",
        placeholder="All stages",
        help="Leave empty to include all deal stages.",
    )
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
                color="Stage",
                title="Pipeline by stage",
                labels={"Stage": "Stage", "Amount": "Amount"},
            )
            chart_theme(fig, 360)
            st.plotly_chart(fig, width="stretch")
    with table_col:
        columns = [col for col in DEAL_FIELDS if col in filtered.columns]
        st.dataframe(filtered[columns], width="stretch", hide_index=True)


def render_leads(leads: pd.DataFrame) -> None:
    st.subheader("Zoho lead flow")
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
                color_discrete_sequence=CHART_COLORWAY,
            )
            chart_theme(fig, 320)
            st.plotly_chart(fig, width="stretch")

    columns = [col for col in LEAD_FIELDS if col in leads.columns]
    st.dataframe(leads[columns], width="stretch", hide_index=True)


def build_seasonal_growth_plan(revenue_monthly: pd.DataFrame) -> tuple[pd.DataFrame, float, float]:
    monthly_actuals = (
        revenue_monthly.groupby("Month", as_index=False)["Gross_Revenue"]
        .sum()
        .rename(columns={"Gross_Revenue": "Actual Revenue"})
    )
    monthly_actuals["Month"] = pd.Categorical(
        monthly_actuals["Month"], categories=MONTH_ORDER, ordered=True
    )
    monthly_actuals = monthly_actuals.sort_values("Month")

    actual_months = [month for month in MONTH_ORDER if month in set(monthly_actuals["Month"].astype(str))]
    generated_to_date = float(monthly_actuals["Actual Revenue"].sum())
    actual_weight = sum(SEASONAL_MONTH_WEIGHTS[month] for month in actual_months)
    baseline_full_year = generated_to_date / actual_weight if actual_weight else generated_to_date
    year_end_target = baseline_full_year * (1 + COMPANY_GROWTH_TARGET)

    plan = pd.DataFrame(
        {
            "Month": MONTH_ORDER,
            "Seasonal_Weight": [SEASONAL_MONTH_WEIGHTS[month] for month in MONTH_ORDER],
        }
    )
    plan = plan.merge(monthly_actuals, on="Month", how="left")
    plan["Actual Revenue"] = plan["Actual Revenue"].fillna(0)
    plan["Seasonal Target"] = plan["Seasonal_Weight"] * year_end_target
    plan["Cumulative Actual"] = plan["Actual Revenue"].cumsum()
    plan["Cumulative Target"] = plan["Seasonal Target"].cumsum()
    plan["Remaining Required"] = (plan["Cumulative Target"] - plan["Cumulative Actual"]).clip(lower=0)
    plan["Market Season"] = plan["Month"].map(
        {
            "Jan": "Slow planning",
            "Feb": "Slow planning",
            "Mar": "Ramp up",
            "Apr": "Peak remodel demand",
            "May": "Peak remodel demand",
            "Jun": "Peak remodel demand",
            "Jul": "Peak remodel demand",
            "Aug": "High demand",
            "Sep": "High demand",
            "Oct": "Moderate demand",
            "Nov": "Holiday slowdown",
            "Dec": "Holiday slowdown",
        }
    )
    return plan, generated_to_date, year_end_target


def render_revenue_target_cards(generated_to_date: float, year_end_target: float) -> None:
    remaining = year_end_target - generated_to_date
    progress = generated_to_date / year_end_target * 100 if year_end_target else 0
    st.markdown(
        f"""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:8px 0 22px 0;">
            <div style="border:1px solid rgba(29,78,216,.35);border-radius:14px;padding:26px;
                        background:linear-gradient(135deg, rgba(29,78,216,.20), rgba(20,184,166,.10));">
                <div style="font-size:0.85rem;text-transform:uppercase;letter-spacing:.08em;font-weight:800;">
                    Generated so far
                </div>
                <div style="font-size:3.2rem;line-height:1.1;font-weight:900;margin-top:8px;">
                    {money(generated_to_date)}
                </div>
                <div style="margin-top:10px;opacity:.78;">Current BathWorks MI gross revenue in the demo period.</div>
            </div>
            <div style="border:1px solid rgba(239,68,68,.38);border-radius:14px;padding:26px;
                        background:linear-gradient(135deg, rgba(239,68,68,.20), rgba(245,158,11,.14));">
                <div style="font-size:0.85rem;text-transform:uppercase;letter-spacing:.08em;font-weight:800;">
                    Year-end target for +80%
                </div>
                <div style="font-size:3.2rem;line-height:1.1;font-weight:900;margin-top:8px;">
                    {money(year_end_target)}
                </div>
                <div style="margin-top:10px;opacity:.78;">
                    Remaining gap: <strong>{money(remaining)}</strong> · Progress: <strong>{progress:.1f}%</strong>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_growth_dashboard(
    deals: pd.DataFrame,
    leads: pd.DataFrame,
    call_center: pd.DataFrame,
    revenue_monthly: pd.DataFrame,
) -> None:
    st.subheader("BathWorks MI growth dashboard")
    st.caption("Where BathWorks is today vs where it needs to be to reach 80% growth by year end.")

    staffing = build_call_center_staffing_model(call_center)
    seasonal_plan, gross_revenue, target_revenue = build_seasonal_growth_plan(revenue_monthly)
    revenue_gap = target_revenue - gross_revenue
    render_revenue_target_cards(gross_revenue, target_revenue)

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
            color_discrete_map=KPI_COLORS,
        )
        chart_theme(fig, 390)
        st.plotly_chart(fig, width="stretch")

    with route_col:
        staffing_by_city = staffing.sort_values("Agent_Gap", ascending=False)
        fig = px.bar(
            staffing_by_city,
            x="City",
            y="Agent_Gap",
            color="City",
            title="Hiring gap by market",
            labels={"Agent_Gap": "Agent gap"},
            color_discrete_map=CITY_COLORS,
        )
        chart_theme(fig, 390)
        st.plotly_chart(fig, width="stretch")

    seasonal_chart = seasonal_plan.melt(
        id_vars=["Month", "Market Season"],
        value_vars=["Actual Revenue", "Seasonal Target"],
        var_name="Scenario",
        value_name="Revenue",
    )
    season_col1, season_col2 = st.columns([1.2, 1])
    with season_col1:
        fig = px.bar(
            seasonal_chart,
            x="Month",
            y="Revenue",
            color="Scenario",
            barmode="group",
            title="Seasonal growth plan, not a flat monthly target",
            hover_data=["Market Season"],
            color_discrete_map=KPI_COLORS,
            category_orders={"Month": MONTH_ORDER},
        )
        chart_theme(fig, 390)
        st.plotly_chart(fig, width="stretch")
    with season_col2:
        fig = px.line(
            seasonal_plan,
            x="Month",
            y=["Cumulative Actual", "Cumulative Target"],
            markers=True,
            title="Cumulative progress to +80% target",
            color_discrete_map={
                "Cumulative Actual": "#1D4ED8",
                "Cumulative Target": "#EF4444",
            },
            category_orders={"Month": MONTH_ORDER},
        )
        chart_theme(fig, 390)
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
            title="Revenue base by market / location",
            color_discrete_map=KPI_COLORS,
        )
        chart_theme(fig, 360)
        st.plotly_chart(fig, width="stretch")
    with detail_col2:
        fig = px.scatter(
            city_revenue,
            x="Gross_Revenue",
            y="Revenue_Gap",
            size="Target_Revenue",
            color="City",
            title="Market revenue gap to +80%",
            color_discrete_map=CITY_COLORS,
        )
        chart_theme(fig, 360)
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
    st.subheader("Recruiting and installer staffing")
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
            color_discrete_map=KPI_COLORS,
        )
        chart_theme(fig, 380)
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
            color_discrete_map=RECRUITER_COLORS,
        )
        chart_theme(fig, 380)
        st.plotly_chart(fig, width="stretch")

    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        by_city = df.groupby("City", as_index=False)["Hires"].sum()
        plot_bar(by_city, "City", "Hires", "Hires by city")
    with sub_col2:
        by_industry = df.groupby("Industry", as_index=False)["Candidates"].sum()
        plot_bar(by_industry, "Industry", "Candidates", "Candidates by customer segment")
    with sub_col3:
        by_product = df.groupby("Product", as_index=False)["Open_Roles"].sum()
        plot_bar(by_product, "Product", "Open_Roles", "Open roles by product")

    st.dataframe(df, width="stretch", hide_index=True)


def render_call_center_performance(df: pd.DataFrame) -> None:
    st.subheader("Lead and appointment center performance")
    st.caption("BathWorks growth target: 80% expansion across service markets.")
    df = render_dimension_filters(df, "call_center")
    if df.empty:
        st.info("No appointment center records match the current filters.")
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
            color_discrete_map=KPI_COLORS,
        )
        chart_theme(fig, 360)
        st.plotly_chart(fig, width="stretch")
    with table_col:
        service_by_team = df.groupby("Team", as_index=False)[["SLA", "CSAT"]].mean()
        fig = px.line(
            service_by_team,
            x="Team",
            y=["SLA", "CSAT"],
            markers=True,
            title="SLA and satisfaction by team",
            color_discrete_map=KPI_COLORS,
        )
        chart_theme(fig, 360)
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
            color_discrete_map=KPI_COLORS,
        )
        chart_theme(fig, 340)
        st.plotly_chart(fig, width="stretch")
    with sub_col2:
        by_tenant = df.groupby("Tenant", as_index=False)["Conversions"].sum()
        plot_bar(by_tenant, "Tenant", "Conversions", "Appointments by market / location")
    with sub_col3:
        by_industry = df.groupby("Industry", as_index=False)["CSAT"].mean()
        plot_bar(by_industry, "Industry", "CSAT", "CSAT by customer segment")

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
            color_discrete_map=CITY_COLORS,
        )
        fig.add_scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            name="Regression line",
            line=dict(color="#F59E0B", width=3),
        )
        chart_theme(fig, 390)
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
            color_discrete_map=KPI_COLORS,
        )
        chart_theme(fig, 390)
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
            color_discrete_map=KPI_COLORS,
        )
        chart_theme(fig, 380)
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
            color_discrete_map=RECRUITER_COLORS,
        )
        chart_theme(fig, 380)
        st.plotly_chart(fig, width="stretch")

    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        by_city = df.groupby("City", as_index=False)["Pipeline"].sum()
        plot_bar(by_city, "City", "Pipeline", "Pipeline by city")
    with sub_col2:
        by_industry = df.groupby("Industry", as_index=False)["Closed_Won"].sum()
        plot_bar(by_industry, "Industry", "Closed_Won", "Closed won by customer segment")
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
            color_discrete_map=KPI_COLORS,
        )
        chart_theme(fig, 360)
        st.plotly_chart(fig, width="stretch")
    with table_col:
        fig = px.scatter(
            marketing_by_channel,
            x="Spend",
            y="Revenue",
            size="MQL",
            color="Channel",
            title="Spend vs revenue",
            color_discrete_map=CHANNEL_COLORS,
        )
        chart_theme(fig, 360)
        st.plotly_chart(fig, width="stretch")

    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        by_city = df.groupby("City", as_index=False)["Leads"].sum()
        plot_bar(by_city, "City", "Leads", "Leads by city")
    with sub_col2:
        by_tenant = df.groupby("Tenant", as_index=False)["Revenue"].sum()
        plot_bar(by_tenant, "Tenant", "Revenue", "Revenue by market / location")
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
            color_discrete_map=KPI_COLORS,
            title="Monthly revenue",
        )
        chart_theme(fig, 380)
        st.plotly_chart(fig, width="stretch")

        split_col1, split_col2 = st.columns(2)
        with split_col1:
            by_tenant = monthly.groupby("Tenant", as_index=False)["Gross_Revenue"].sum()
            plot_bar(by_tenant, "Tenant", "Gross_Revenue", "Gross revenue by market / location")
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
            color_discrete_map={
                "New": "#1D4ED8",
                "Expansion": "#F59E0B",
                "Recurring": "#10B981",
            },
        )
        chart_theme(fig, 380)
        st.plotly_chart(fig, width="stretch")
    with segment_tab:
        if segments.empty:
            st.info("No segment detail is available for the current filters.")
        else:
            fig = px.sunburst(
                segments,
                path=["Region", "Segment", "Industry"],
                values="Revenue",
                color="Segment",
                title="Revenue by region, service segment, and customer segment",
                color_discrete_sequence=CHART_COLORWAY,
            )
            chart_theme(fig, 420)
            st.plotly_chart(fig, width="stretch")
    with table_tab:
        table_col, segment_col = st.columns(2)
        with table_col:
            st.dataframe(monthly, width="stretch", hide_index=True)
        with segment_col:
            st.dataframe(segments, width="stretch", hide_index=True)


def safe_float(value: Any, fallback: float = 0.0) -> float:
    numeric = pd.to_numeric(value, errors="coerce")
    return fallback if pd.isna(numeric) else float(numeric)


def weather_install_risk(row: pd.Series) -> float:
    precipitation = safe_float(row.get("Precipitation"))
    wind_speed = safe_float(row.get("Wind Speed"))
    temperature = safe_float(row.get("Temperature"), 65)
    precip_risk = min(45, precipitation * 120)
    wind_risk = max(0, wind_speed - 15) * 2.5
    cold_risk = max(0, 35 - temperature) * 1.2
    heat_risk = max(0, temperature - 88) * 0.8
    return min(100, precip_risk + wind_risk + cold_risk + heat_risk)


def build_external_api_analysis(
    weather: pd.DataFrame,
    alerts: pd.DataFrame,
    air_quality: pd.DataFrame,
    market: pd.DataFrame,
) -> pd.DataFrame:
    analysis = (
        weather.drop(columns=["API Source"], errors="ignore")
        .merge(alerts.drop(columns=["API Source"], errors="ignore"), on="City", how="left")
        .merge(air_quality.drop(columns=["API Source"], errors="ignore"), on="City", how="left")
        .merge(market.drop(columns=["API Source"], errors="ignore"), on="City", how="left")
    )
    fallback_columns = {
        "Active Alerts": 0,
        "Alert Types": "None",
        "US AQI": 50,
        "PM2.5": 8,
        "Population": pd.NA,
        "Median Household Income": pd.NA,
        "Median Home Value": pd.NA,
    }
    for column, fallback in fallback_columns.items():
        if column not in analysis:
            analysis[column] = fallback

    analysis["Install Risk Score"] = analysis.apply(weather_install_risk, axis=1)
    analysis["Active Alerts"] = pd.to_numeric(analysis["Active Alerts"], errors="coerce").fillna(0)
    analysis["US AQI"] = pd.to_numeric(analysis["US AQI"], errors="coerce").fillna(50)
    analysis["PM2.5"] = pd.to_numeric(analysis["PM2.5"], errors="coerce").fillna(8)
    analysis["Alert Risk"] = analysis["Active Alerts"] * 12
    analysis["Air Quality Risk"] = (analysis["US AQI"] / 2).clip(upper=60)

    for column in ["Population", "Median Household Income", "Median Home Value"]:
        analysis[column] = pd.to_numeric(analysis[column], errors="coerce")

    neutral_score = pd.Series([50.0] * len(analysis), index=analysis.index)
    analysis["Population Score"] = (
        min_max_normalize(analysis["Population"]) * 100
        if analysis["Population"].notna().any()
        else neutral_score
    )
    analysis["Income Score"] = (
        min_max_normalize(analysis["Median Household Income"]) * 100
        if analysis["Median Household Income"].notna().any()
        else neutral_score
    )
    analysis["Home Value Score"] = (
        min_max_normalize(analysis["Median Home Value"]) * 100
        if analysis["Median Home Value"].notna().any()
        else neutral_score
    )
    analysis["Operations Readiness Score"] = (
        100
        - analysis["Install Risk Score"]
        - analysis["Alert Risk"]
        - analysis["Air Quality Risk"] * 0.35
    ).clip(lower=0, upper=100)
    analysis["Market Opportunity Score"] = (
        analysis["Population Score"] * 0.30
        + analysis["Income Score"] * 0.25
        + analysis["Home Value Score"] * 0.20
        + analysis["Operations Readiness Score"] * 0.25
    )
    analysis["Suggested Action"] = analysis["Market Opportunity Score"].map(
        lambda score: "Prioritize appointments"
        if score >= 70
        else "Watch and nurture"
        if score >= 45
        else "Maintain coverage"
    )
    return analysis.sort_values("Market Opportunity Score", ascending=False)


def add_notification(
    notifications: list[dict[str, str]],
    severity: str,
    title: str,
    message: str,
    source: str,
) -> None:
    notifications.append(
        {
            "Severity": severity,
            "Title": title,
            "Message": message,
            "Source": source,
        }
    )


def build_dashboard_notifications(
    deals: pd.DataFrame,
    leads: pd.DataFrame,
    call_center: pd.DataFrame,
    revenue_monthly: pd.DataFrame,
    external_analysis: pd.DataFrame,
    api_errors: list[str],
) -> list[dict[str, str]]:
    notifications: list[dict[str, str]] = []

    for _, row in external_analysis.iterrows():
        city = str(row.get("City", "Unknown market"))
        install_risk = safe_float(row.get("Install Risk Score"))
        active_alerts = safe_float(row.get("Active Alerts"))
        aqi = safe_float(row.get("US AQI"), 50)
        readiness = safe_float(row.get("Operations Readiness Score"), 100)
        alert_types = str(row.get("Alert Types") or "weather alerts")

        if active_alerts >= 1:
            add_notification(
                notifications,
                "High" if active_alerts >= 2 else "Medium",
                f"{city}: official weather alert active",
                f"{int(active_alerts)} active alert(s): {alert_types}. Review same-day routing and installer start times.",
                "National Weather Service",
            )

        if install_risk >= 20:
            add_notification(
                notifications,
                "High" if install_risk >= 40 else "Medium",
                f"{city}: installation weather risk",
                f"Install risk is {install_risk:.1f}/100 based on precipitation, wind, and temperature.",
                "Open-Meteo Forecast",
            )

        if aqi >= 70:
            add_notification(
                notifications,
                "High" if aqi >= 100 else "Medium",
                f"{city}: air quality watch",
                f"Current AQI is {aqi:.0f}. Consider crew exposure, outdoor prep, and customer communication.",
                "Open-Meteo Air Quality",
            )

        if readiness < 70:
            add_notification(
                notifications,
                "Medium",
                f"{city}: operations readiness below target",
                f"Readiness is {readiness:.1f}/100 after weather, alerts, and air quality signals.",
                "External API Score",
            )

    staffing = build_call_center_staffing_model(call_center)
    staffing_gap = staffing[staffing["Agent_Gap"] > 0].sort_values("Agent_Gap", ascending=False)
    if not staffing_gap.empty:
        total_gap = int(staffing_gap["Agent_Gap"].sum())
        top_markets = ", ".join(
            f"{row.City} (+{int(row.Agent_Gap)})" for row in staffing_gap.head(3).itertuples()
        )
        add_notification(
            notifications,
            "High" if total_gap >= 4 else "Medium",
            "Appointment center staffing gap",
            f"{total_gap} additional agent(s) are recommended for the +80% growth target. Biggest gaps: {top_markets}.",
            "Workforce Model",
        )

    _, generated_to_date, year_end_target = build_seasonal_growth_plan(revenue_monthly)
    revenue_gap = max(0, year_end_target - generated_to_date)
    progress = generated_to_date / year_end_target * 100 if year_end_target else 0
    if revenue_gap > 0:
        add_notification(
            notifications,
            "High" if progress < 50 else "Medium",
            "Revenue gap to year-end growth target",
            f"{money(revenue_gap)} remains to reach the +80% target. Current progress is {progress:.1f}%.",
            "Growth Plan",
        )

    pipeline = float(deals.get("Amount", pd.Series(dtype=float)).sum())
    target_pipeline = pipeline * (1 + COMPANY_GROWTH_TARGET)
    if pipeline > 0:
        add_notification(
            notifications,
            "Info",
            "Pipeline target check",
            f"Current pipeline is {money(pipeline)}. A +80% scenario points to {money(target_pipeline)}.",
            "Zoho Pipeline",
        )

    current_leads = len(leads)
    target_leads = math.ceil(current_leads * (1 + COMPANY_GROWTH_TARGET))
    if current_leads:
        add_notification(
            notifications,
            "Info",
            "Lead volume target check",
            f"{target_leads - current_leads:,} additional leads are needed to model an +80% lead-growth scenario.",
            "Zoho Leads",
        )

    if api_errors:
        add_notification(
            notifications,
            "Info",
            "External API availability",
            "Some public API signals are unavailable right now, so fallback values are being used where needed.",
            "API Monitor",
        )

    severity_rank = {"High": 0, "Medium": 1, "Info": 2}
    return sorted(notifications, key=lambda item: severity_rank.get(item["Severity"], 3))


def render_notification_card(notification: dict[str, str]) -> None:
    severity = notification["Severity"]
    colors = {
        "High": ("#DC2626", "rgba(220,38,38,.13)"),
        "Medium": ("#F59E0B", "rgba(245,158,11,.16)"),
        "Info": ("#2563EB", "rgba(37,99,235,.13)"),
    }
    accent, background = colors.get(severity, colors["Info"])
    st.markdown(
        f"""
        <div class="notification-card" style="border-left-color:{accent};background:{background};">
            <div class="notification-topline">
                <span class="notification-badge" style="background:{accent};">{escape(severity)}</span>
                <span class="notification-source">{escape(notification['Source'])}</span>
            </div>
            <div class="notification-title">{escape(notification['Title'])}</div>
            <div class="notification-message">{escape(notification['Message'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_notification_center(
    deals: pd.DataFrame,
    leads: pd.DataFrame,
    call_center: pd.DataFrame,
    revenue_monthly: pd.DataFrame,
) -> None:
    weather, alerts, air_quality, market, api_errors, connected_sources = load_external_api_context()
    external_analysis = build_external_api_analysis(weather, alerts, air_quality, market)
    notifications = build_dashboard_notifications(
        deals,
        leads,
        call_center,
        revenue_monthly,
        external_analysis,
        api_errors,
    )
    weather_notifications = [
        item
        for item in notifications
        if item["Source"] in {"Open-Meteo Forecast", "National Weather Service", "Open-Meteo Air Quality"}
    ]
    high_priority = [item for item in notifications if item["Severity"] == "High"]
    medium_priority = [item for item in notifications if item["Severity"] == "Medium"]
    status_label = "Action needed" if high_priority else "Monitoring"
    status_color = "#DC2626" if high_priority else "#2563EB"

    st.markdown(
        """
        <style>
        .notification-menu-banner {
            border: 1px solid rgba(239, 91, 91, .28);
            border-radius: 14px;
            padding: 14px 16px;
            margin: 14px 0 10px 0;
            background: linear-gradient(135deg, rgba(239, 91, 91, .14), rgba(37, 99, 235, .08));
            box-shadow: 0 10px 28px rgba(15, 23, 42, .08);
        }
        .notification-menu-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }
        .notification-heading {
            font-size: 1.05rem;
            font-weight: 800;
        }
        .notification-summary {
            opacity: .76;
            font-size: .88rem;
        }
        .notification-pill-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            justify-content: flex-end;
        }
        .notification-pill {
            border-radius: 999px;
            padding: 5px 10px;
            color: #fff;
            font-size: .76rem;
            font-weight: 800;
            white-space: nowrap;
        }
        div[data-testid="stPopover"] button {
            border-radius: 999px;
            border: 1px solid rgba(239, 91, 91, .40);
            background: linear-gradient(135deg, #ef5b5b, #2563eb);
            color: #ffffff;
            font-weight: 800;
            box-shadow: 0 10px 24px rgba(239, 91, 91, .18);
        }
        div[data-testid="stPopover"] button:hover {
            border-color: rgba(239, 91, 91, .70);
            color: #ffffff;
            filter: brightness(1.04);
        }
        .notification-card {
            border-left: 5px solid;
            border-radius: 9px;
            padding: 12px 14px;
            margin-bottom: 10px;
        }
        .notification-topline {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }
        .notification-badge {
            color: #fff;
            border-radius: 999px;
            padding: 2px 8px;
            font-size: .72rem;
            font-weight: 800;
            text-transform: uppercase;
        }
        .notification-source {
            font-size: .78rem;
            font-weight: 700;
            opacity: .72;
        }
        .notification-title {
            font-weight: 800;
            margin-bottom: 2px;
        }
        .notification-message {
            opacity: .84;
            line-height: 1.35;
            font-size: .92rem;
        }
        @media (prefers-color-scheme: light) {
            .notification-menu-banner {
                background: #ffffff;
                border-color: rgba(15, 23, 42, .12);
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="notification-menu-banner">
            <div class="notification-menu-header">
                <div>
                    <div class="notification-heading">Notifications</div>
                    <div class="notification-summary">
                        Quick operational alerts, hidden in a dropdown so dashboards stay clean.
                    </div>
                </div>
                <div class="notification-pill-row">
                    <span class="notification-pill" style="background:{status_color};">{status_label}</span>
                    <span class="notification-pill" style="background:#DC2626;">{len(high_priority)} High</span>
                    <span class="notification-pill" style="background:#F59E0B;">{len(medium_priority)} Medium</span>
                    <span class="notification-pill" style="background:#2563EB;">{connected_sources}/4 APIs</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.popover(f"Open notification menu ({len(notifications)})", use_container_width=True):
        st.markdown("#### Notification Menu")
        st.caption(
            f"{len(high_priority)} high priority · {len(medium_priority)} medium priority · "
            f"{len(weather_notifications)} weather/air signals · {connected_sources}/4 APIs connected"
        )
        if not notifications:
            st.success("No active operational notifications right now.")
            return

        for notification in notifications[:8]:
            render_notification_card(notification)


def render_external_api_insights() -> None:
    st.subheader("External API insights")
    st.caption(
        "Open APIs can enrich the dashboard with market, weather, air quality, and operational context from outside Zoho."
    )

    weather, alerts, air_quality, market, api_errors, connected_sources = load_external_api_context()

    for error in api_errors:
        st.warning(error)

    analysis = build_external_api_analysis(weather, alerts, air_quality, market)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Connected API sources", f"{connected_sources}/4")
    with col2:
        metric_card("Avg install risk", percent(float(analysis["Install Risk Score"].mean())))
    with col3:
        metric_card("Best market", str(analysis.iloc[0]["City"]))
    with col4:
        metric_card("Active weather alerts", f"{int(analysis['Active Alerts'].fillna(0).sum())}")

    weather_col, market_col = st.columns(2)
    with weather_col:
        fig = px.bar(
            analysis.sort_values("Install Risk Score", ascending=False),
            x="City",
            y="Install Risk Score",
            color="City",
            title="Operational install risk from weather APIs",
            hover_data=["Temperature", "Precipitation", "Wind Speed", "Alert Types"],
            color_discrete_map=CITY_COLORS,
        )
        chart_theme(fig, 380)
        st.plotly_chart(fig, width="stretch")
    with market_col:
        fig = px.bar(
            analysis,
            x="City",
            y="Market Opportunity Score",
            color="City",
            title="Market opportunity score from Data USA + external signals",
            hover_data=[
                "Population",
                "Median Household Income",
                "Median Home Value",
                "Operations Readiness Score",
                "Suggested Action",
            ],
            color_discrete_map=CITY_COLORS,
        )
        chart_theme(fig, 380)
        st.plotly_chart(fig, width="stretch")

    demo_col, alert_col = st.columns(2)
    with demo_col:
        fig = px.scatter(
            analysis,
            x="Median Household Income",
            y="Median Home Value",
            size="Population",
            color="City",
            title="Housing and income context by service area",
            color_discrete_map=CITY_COLORS,
        )
        chart_theme(fig, 360)
        st.plotly_chart(fig, width="stretch")
    with alert_col:
        air = analysis.melt(
            id_vars="City",
            value_vars=["US AQI", "PM2.5"],
            var_name="Air Metric",
            value_name="Value",
        )
        fig = px.bar(
            air,
            x="City",
            y="Value",
            color="Air Metric",
            barmode="group",
            title="Air quality from Open-Meteo",
            color_discrete_map={"US AQI": "#8B5CF6", "PM2.5": "#F59E0B"},
        )
        chart_theme(fig, 360)
        st.plotly_chart(fig, width="stretch")

    alert_col, action_col = st.columns(2)
    with alert_col:
        fig = px.bar(
            analysis,
            x="City",
            y="Active Alerts",
            color="City",
            title="Active National Weather Service alerts",
            color_discrete_map=CITY_COLORS,
        )
        chart_theme(fig, 360)
        st.plotly_chart(fig, width="stretch")
    with action_col:
        fig = px.bar(
            analysis.sort_values("Operations Readiness Score", ascending=False),
            x="City",
            y="Operations Readiness Score",
            color="City",
            title="Operations readiness score",
            hover_data=["Install Risk Score", "Alert Risk", "Air Quality Risk"],
            color_discrete_map=CITY_COLORS,
        )
        chart_theme(fig, 360)
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### How these external statistics can be used")
    st.write(
        "Weather signals can protect installation schedules, Data USA market data can prioritize "
        "higher-opportunity service areas, National Weather Service alerts can flag routing risk, "
        "and air quality can help operations decide when outdoor prep or crew exposure needs attention."
    )
    st.dataframe(
        analysis[
            [
                "City",
                "Temperature",
                "Precipitation",
                "Wind Speed",
                "Active Alerts",
                "US AQI",
                "PM2.5",
                "Population",
                "Median Household Income",
                "Median Home Value",
                "Install Risk Score",
                "Operations Readiness Score",
                "Market Opportunity Score",
                "Suggested Action",
            ]
        ].style.format(
            {
                "Temperature": "{:.1f}",
                "Precipitation": "{:.2f}",
                "Wind Speed": "{:.1f}",
                "US AQI": "{:.0f}",
                "PM2.5": "{:.1f}",
                "Population": "{:,.0f}",
                "Median Household Income": "${:,.0f}",
                "Median Home Value": "${:,.0f}",
                "Install Risk Score": "{:.1f}",
                "Operations Readiness Score": "{:.1f}",
                "Market Opportunity Score": "{:.1f}",
            },
            na_rep="N/A",
        ),
        width="stretch",
        hide_index=True,
    )


def main() -> None:
    if not authenticate_user():
        return

    st.title("BathWorks MI Performance Dashboard")
    st.caption(
        "Executive view of lead flow, appointments, sales, installer staffing, and revenue growth."
    )

    dashboard_options = [
        "Main Growth Dashboard",
        "Recruiter Performance",
        "Appointment Center Performance",
        "Sales Performance",
        "Marketing Performance",
        "Gross Revenue",
        "External API Insights",
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

    render_notification_center(deals, leads, call_center_data, revenue_monthly)

    if selected_dashboard == "Main Growth Dashboard":
        render_growth_dashboard(deals, leads, call_center_data, revenue_monthly)
    elif selected_dashboard == "Recruiter Performance":
        render_recruiter_performance(recruiter_data)
    elif selected_dashboard == "Appointment Center Performance":
        render_call_center_performance(call_center_data)
    elif selected_dashboard == "Sales Performance":
        render_sales_performance(sales_data)
    elif selected_dashboard == "Marketing Performance":
        render_marketing_performance(marketing_data)
    elif selected_dashboard == "Gross Revenue":
        render_gross_revenue(revenue_monthly, revenue_segments)
    elif selected_dashboard == "External API Insights":
        render_external_api_insights()
    elif selected_dashboard == "Zoho Sales":
        render_deals(deals)
    elif selected_dashboard == "Zoho Leads":
        render_leads(leads)
    else:
        st.info("Select a dashboard from the sidebar.")


if __name__ == "__main__":
    main()
