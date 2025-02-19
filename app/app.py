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

st.title("Interactive EMS Dashboard")
st.markdown("### Energy Monitoring and Visualization")
st.markdown("This dashboard displays sensor data stored in DynamoDB.")

# ----- Function to query DynamoDB for sensor data -----
@st.cache_data(ttl=60)
def fetch_sensor_data():
    # Initialize DynamoDB client (ensure the instance has proper IAM role or credentials)
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

# ----- Sidebar Filters -----
st.sidebar.header("Filters & Options")
start_date = st.sidebar.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=1))
end_date = st.sidebar.date_input("End Date", datetime.date.today())
if start_date > end_date:
    st.sidebar.error("Error: Start date must be before end date.")

if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()

# ----- Retrieve Data -----
df = fetch_sensor_data()
if not df.empty and "timestamp" in df.columns:
    df = df[(df['timestamp'].dt.date >= start_date) & (df['timestamp'].dt.date <= end_date)]
else:
    st.info("No data available. Please check your DynamoDB table and IoT pipeline.")

if st.sidebar.checkbox("Show Raw Data", False):
    st.subheader("Raw Sensor Data")
    st.write(df.head(20))

# ----- Visualization: Building Total Energy Consumption -----
if "building_total_energy_kwh" in df.columns:
    st.subheader("Building Total Energy Consumption")
    chart = alt.Chart(df).mark_line().encode(
        x=alt.X('timestamp:T', title="Time"),
        y=alt.Y('building_total_energy_kwh:Q', title="Total Energy (kWh)"),
        tooltip=['timestamp:T', 'building_total_energy_kwh:Q']
    ).properties(width=700, height=300, title="Total Energy Consumption")
    st.altair_chart(chart, use_container_width=True)
else:
    st.warning("Field 'building_total_energy_kwh' not found.")

# Additional visualizations for HVAC, DHW, Lighting, etc. can be added similarly.
st.markdown("### Real-Time Updates")
st.write("Last updated:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))