#!/usr/bin/env python3
"""
app/app.py

A Streamlit dashboard that queries sensor data from DynamoDB and displays interactive visualizations.
"""

import streamlit as st
import pandas as pd
import altair as alt
import boto3
import datetime
from streamlit_autorefresh import st_autorefresh

# Set page configuration for improved layout
st.set_page_config(page_title="EMS Dashboard", layout="wide")
st.title("Interactive EMS Dashboard")
st.markdown("### Energy Monitoring and Visualization")
st.markdown("This dashboard displays sensor data stored in DynamoDB.")

# Auto-refresh the page every 60 seconds
st_autorefresh(interval=60000, key="datarefresh")

# ----- Function to query DynamoDB for sensor data -----
@st.cache_data(ttl=60)
def fetch_sensor_data():
    try:
        # Initialize DynamoDB resource (ensure proper IAM role or credentials are set)
        dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
        table = dynamodb.Table("SensorData")
        # For simplicity, performing a full table scan; in production, use queries with proper filters.
        response = table.scan()
        items = response.get("Items", [])
        df = pd.DataFrame(items)
        # Convert timestamp string to datetime if available
        if "edge_time_stamp" in df.columns:
            df['timestamp'] = pd.to_datetime(df['edge_time_stamp'])
        return df
    except Exception as e:
        st.error("Error fetching data from DynamoDB: " + str(e))
        return pd.DataFrame()

# ----- Sidebar Filters -----
st.sidebar.header("Filters & Options")
start_date = st.sidebar.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=1))
end_date = st.sidebar.date_input("End Date", datetime.date.today())
if start_date > end_date:
    st.sidebar.error("Error: Start date must be before end date.")

if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()

# ----- Retrieve Data -----
with st.spinner("Fetching sensor data..."):
    df = fetch_sensor_data()

if not df.empty and "timestamp" in df.columns:
    # Filter data based on the selected date range
    df = df[(df['timestamp'].dt.date >= start_date) & (df['timestamp'].dt.date <= end_date)]
else:
    st.info("No data available. Please check your DynamoDB table and IoT pipeline.")

# Additional filtering by Device ID if available
if not df.empty and "device_id" in df.columns:
    device_ids = sorted(df["device_id"].unique())
    selected_devices = st.sidebar.multiselect("Select Device(s)", device_ids, default=device_ids)
    df = df[df["device_id"].isin(selected_devices)]

# ----- KPI Metrics -----
if not df.empty and "building_total_energy_kwh" in df.columns and "building_demand_kw" in df.columns:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Avg Total Energy (kWh)", round(df["building_total_energy_kwh"].mean(), 2))
    with col2:
        st.metric("Avg Demand (kW)", round(df["building_demand_kw"].mean(), 2))
    with col3:
        st.metric("Total Records", len(df))

# Optional: Show Raw Data
if st.sidebar.checkbox("Show Raw Data", False):
    st.subheader("Raw Sensor Data")
    st.write(df.head(20))

# ----- Visualization: Building Total Energy Consumption -----
if "building_total_energy_kwh" in df.columns:
    st.subheader("Building Total Energy Consumption")
    chart_energy = alt.Chart(df).mark_line().encode(
        x=alt.X('timestamp:T', title="Time"),
        y=alt.Y('building_total_energy_kwh:Q', title="Total Energy (kWh)"),
        tooltip=['timestamp:T', 'building_total_energy_kwh:Q']
    ).properties(width=700, height=300, title="Total Energy Consumption")
    st.altair_chart(chart_energy, use_container_width=True)
else:
    st.warning("Field 'building_total_energy_kwh' not found.")

# ----- Visualization: Building Demand -----
if "building_demand_kw" in df.columns:
    st.subheader("Building Demand")
    chart_demand = alt.Chart(df).mark_line(color="red").encode(
        x=alt.X('timestamp:T', title="Time"),
        y=alt.Y('building_demand_kw:Q', title="Demand (kW)"),
        tooltip=['timestamp:T', 'building_demand_kw:Q']
    ).properties(width=700, height=300, title="Building Demand (kW)")
    st.altair_chart(chart_demand, use_container_width=True)
else:
    st.warning("Field 'building_demand_kw' not found.")

st.markdown("### Real-Time Updates")
st.write("Last updated:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))