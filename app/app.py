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
import os
import logging
import time
import hashlib
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EMSDashboard")

# Load environment variables
load_dotenv()

# Basic authentication function
def check_password():
    """Returns `True` if the user had the correct password."""
    # Get username/password from environment variables with defaults
    correct_username = os.getenv("DASHBOARD_USERNAME", "admin")
    # Use a hashed version of the password
    correct_password_hash = os.getenv("DASHBOARD_PASSWORD_HASH", 
                                     hashlib.sha256("admin".encode()).hexdigest())
    
    def validate_credentials(username, password):
        return (username == correct_username and 
                hashlib.sha256(password.encode()).hexdigest() == correct_password_hash)
    
    # If already authenticated, don't show login again
    if st.session_state.get("authenticated", False):
        return True

    # Show login form
    st.markdown("### Dashboard Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if validate_credentials(username, password):
            st.session_state["authenticated"] = True
            return True
        else:
            st.error("Invalid username or password")
            # Add delay to prevent brute force attacks
            time.sleep(1)
            return False
    return False

# Set page configuration for improved layout
st.set_page_config(
    page_title="EMS Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check authentication before showing dashboard
if check_password():
    st.title("Interactive EMS Dashboard")
    st.markdown("### Energy Monitoring and Visualization")
    st.markdown("This dashboard displays sensor data stored in DynamoDB.")

# Only setup auto-refresh if authenticated
if st.session_state.get("authenticated", False):
    # Auto-refresh the page every 60 seconds (configurable)
    refresh_interval = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", "60")) * 1000
    st_autorefresh(interval=refresh_interval, key="datarefresh")

# ----- AWS Configuration -----
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "sensor_data")

# ----- Function to query DynamoDB for sensor data -----
@st.cache_data(ttl=60)
def fetch_sensor_data(table_name, region_name, start_date=None, end_date=None, device_id=None, sensor_type=None):
    """
    Query sensor data from DynamoDB with optional filters.
    Uses efficient Query operations with GSIs for better performance.
    """
    try:
        # Initialize DynamoDB resource (ensure proper IAM role or credentials are set)
        dynamodb = boto3.resource('dynamodb', region_name=region_name)
        table = dynamodb.Table(table_name)
        
        logger.info(f"Fetching data from DynamoDB table: {table_name}")
        
        items = []
        
        # If we have a device_id filter, use the GSI
        if device_id and not sensor_type:
            logger.info(f"Querying GSI by device_id: {device_id}")
            
            query_params = {
                'IndexName': 'DeviceIdIndex',
                'KeyConditionExpression': boto3.dynamodb.conditions.Key('device_id').eq(device_id)
            }
            
            if start_date and end_date:
                # Convert dates to ISO format string to match DynamoDB format
                start_ts = datetime.datetime.combine(start_date, datetime.time.min).isoformat()
                end_ts = datetime.datetime.combine(end_date, datetime.time.max).isoformat()
                
                query_params['KeyConditionExpression'] = (
                    query_params['KeyConditionExpression'] & 
                    boto3.dynamodb.conditions.Key('edge_time_stamp').between(start_ts, end_ts)
                )
            
            response = table.query(**query_params)
            items.extend(response.get('Items', []))
            
            while 'LastEvaluatedKey' in response:
                logger.info("Fetching additional page of query results")
                query_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = table.query(**query_params)
                items.extend(response.get('Items', []))
        
        # If we have a sensor_type filter, use the primary key
        elif sensor_type and not device_id:
            logger.info(f"Querying by sensor_type: {sensor_type}")
            
            query_params = {
                'KeyConditionExpression': boto3.dynamodb.conditions.Key('sensor_type').eq(sensor_type)
            }
            
            if start_date and end_date:
                # Convert dates to ISO format string to match DynamoDB format
                start_ts = datetime.datetime.combine(start_date, datetime.time.min).isoformat()
                end_ts = datetime.datetime.combine(end_date, datetime.time.max).isoformat()
                
                query_params['KeyConditionExpression'] = (
                    query_params['KeyConditionExpression'] & 
                    boto3.dynamodb.conditions.Key('edge_time_stamp').between(start_ts, end_ts)
                )
            
            response = table.query(**query_params)
            items.extend(response.get('Items', []))
            
            while 'LastEvaluatedKey' in response:
                logger.info("Fetching additional page of query results")
                query_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = table.query(**query_params)
                items.extend(response.get('Items', []))
        
        # If we have both or neither, fall back to scan with FilterExpression
        else:
            logger.info("Using scan with filter expressions")
            scan_params = {}
            filter_expressions = []
            
            if device_id:
                filter_expressions.append(boto3.dynamodb.conditions.Attr('device_id').eq(device_id))
            
            if sensor_type:
                filter_expressions.append(boto3.dynamodb.conditions.Attr('sensor_type').eq(sensor_type))
            
            if start_date and end_date:
                # Convert dates to ISO format string
                start_ts = datetime.datetime.combine(start_date, datetime.time.min).isoformat()
                end_ts = datetime.datetime.combine(end_date, datetime.time.max).isoformat()
                filter_expressions.append(
                    boto3.dynamodb.conditions.Attr('edge_time_stamp').between(start_ts, end_ts)
                )
            
            # Combine filter expressions if we have any
            if filter_expressions:
                combined_filter = filter_expressions[0]
                for expr in filter_expressions[1:]:
                    combined_filter = combined_filter & expr
                scan_params['FilterExpression'] = combined_filter
            
            response = table.scan(**scan_params)
            items.extend(response.get("Items", []))
            
            # Paginate through results if necessary
            while 'LastEvaluatedKey' in response:
                logger.info("Fetching additional page of scan results")
                scan_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = table.scan(**scan_params)
                items.extend(response.get("Items", []))
        
        if not items:
            logger.warning("No items found in DynamoDB table")
            return pd.DataFrame()
            
        df = pd.DataFrame(items)
        
        # Convert timestamp string to datetime if available
        if "edge_time_stamp" in df.columns:
            df['timestamp'] = pd.to_datetime(df['edge_time_stamp'])
            
        logger.info(f"Retrieved {len(df)} records from DynamoDB")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data from DynamoDB: {str(e)}")
        st.error(f"Error fetching data from DynamoDB: {str(e)}")
        return pd.DataFrame()

# Only show main dashboard content if authenticated
if st.session_state.get("authenticated", False):
    # ----- Sidebar Filters -----
    st.sidebar.header("Filters & Options")

    # Date range selection
    default_days_back = int(os.getenv("DEFAULT_DAYS_BACK", "1"))
    start_date = st.sidebar.date_input(
        "Start Date", 
        datetime.date.today() - datetime.timedelta(days=default_days_back)
    )
    end_date = st.sidebar.date_input("End Date", datetime.date.today())

    if start_date > end_date:
        st.sidebar.error("Error: Start date must be before end date.")

    # AWS Region selection (for advanced users)
    regions = ["us-east-1", "us-east-2", "us-west-1", "us-west-2", "eu-west-1", "eu-central-1", "ap-northeast-1", "ap-southeast-1"]
    selected_region = st.sidebar.selectbox("AWS Region", regions, index=regions.index(AWS_REGION) if AWS_REGION in regions else 0)

    # DynamoDB table selection (for advanced users)
    selected_table = st.sidebar.text_input("DynamoDB Table", DYNAMODB_TABLE)

    # Manual refresh button
    if st.sidebar.button("Refresh Data"):
        st.cache_data.clear()
        
    # System metrics/monitoring
    with st.sidebar.expander("System Metrics"):
        st.write("Dashboard version: 1.0.0")
        st.write(f"Environment: {os.getenv('ENVIRONMENT', 'production')}")
        st.write(f"Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if st.button("Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared successfully")

    # ----- Retrieve Data -----
    with st.spinner("Fetching sensor data..."):
        df = fetch_sensor_data(selected_table, selected_region, start_date, end_date)

# Only process data if authenticated
if not st.session_state.get("authenticated", False):
    # Stop rendering here if not authenticated
    pass
elif 'df' in locals() and df.empty:
    st.info("No data available for the selected filters. Please check your DynamoDB table and IoT pipeline.")
    
    # Show connection guide if no data
    with st.expander("Troubleshooting Guide"):
        st.write("""
        ### Troubleshooting Steps:
        1. Verify your AWS credentials are set up correctly
        2. Check that the DynamoDB table exists in the selected region
        3. Ensure the IoT device is publishing data to AWS IoT Core
        4. Verify the IoT rule is correctly forwarding data to DynamoDB
        5. Check for permissions issues with IAM roles
        """)
elif 'df' in locals():
    # Additional filtering by Device ID if available
    if "device_id" in df.columns:
        device_ids = sorted(df["device_id"].unique())
        selected_devices = st.sidebar.multiselect("Select Device(s)", device_ids, default=device_ids)
        if selected_devices:  # Only filter if devices are selected
            df = df[df["device_id"].isin(selected_devices)]
    
    # Filter by sensor type if available
    if "sensor_type" in df.columns:
        sensor_types = sorted(df["sensor_type"].unique())
        selected_sensors = st.sidebar.multiselect("Select Sensor Types", sensor_types, default=sensor_types)
        if selected_sensors:  # Only filter if sensor types are selected
            df = df[df["sensor_type"].isin(selected_sensors)]
    
    # ----- Dashboard Tabs -----
    tabs = st.tabs(["Overview", "Energy Analysis", "Device Details", "Raw Data"])
    
    with tabs[0]:  # Overview Tab
        st.header("System Overview")
        
        # KPI Metrics Cards
        metrics = {}
        if "building_total_energy_kwh" in df.columns:
            metrics["Avg Total Energy (kWh)"] = round(df["building_total_energy_kwh"].mean(), 2)
        if "building_demand_kw" in df.columns:
            metrics["Avg Demand (kW)"] = round(df["building_demand_kw"].mean(), 2)
        
        # Always show record count
        metrics["Total Records"] = len(df)
        
        # Create metric columns dynamically based on available metrics
        num_metrics = len(metrics)
        if num_metrics > 0:
            metric_cols = st.columns(num_metrics)
            for i, (label, value) in enumerate(metrics.items()):
                with metric_cols[i]:
                    st.metric(label, value)
        
        # Summary visualization
        if not df.empty and "timestamp" in df.columns:
            st.subheader("Recent Activity")
            
            # Group by hour and sensor_type if available
            if "sensor_type" in df.columns:
                # Create a timeseries of record counts by sensor type
                df['hour'] = df['timestamp'].dt.floor('H')
                activity_df = df.groupby(['hour', 'sensor_type']).size().reset_index(name='count')
                
                chart = alt.Chart(activity_df).mark_line().encode(
                    x=alt.X('hour:T', title="Time"),
                    y=alt.Y('count:Q', title="Number of Records"),
                    color=alt.Color('sensor_type:N', title="Sensor Type"),
                    tooltip=['hour:T', 'sensor_type:N', 'count:Q']
                ).properties(
                    width=700, 
                    height=300,
                    title="Sensor Activity by Hour"
                ).interactive()
                
                st.altair_chart(chart, use_container_width=True)
            
    with tabs[1]:  # Energy Analysis Tab
        st.header("Energy Analysis")
        
        # ----- Visualization: Building Total Energy Consumption -----
        if "building_total_energy_kwh" in df.columns:
            st.subheader("Building Total Energy Consumption")
            
            # Aggregate data by hour for smoother visualization
            df_hourly = df.copy()
            df_hourly['hour'] = df_hourly['timestamp'].dt.floor('H')
            energy_hourly = df_hourly.groupby('hour')['building_total_energy_kwh'].mean().reset_index()
            
            chart_energy = alt.Chart(energy_hourly).mark_line().encode(
                x=alt.X('hour:T', title="Time"),
                y=alt.Y('building_total_energy_kwh:Q', title="Total Energy (kWh)"),
                tooltip=['hour:T', 'building_total_energy_kwh:Q']
            ).properties(
                width=700, 
                height=300, 
                title="Total Energy Consumption (Hourly Average)"
            ).interactive()
            
            st.altair_chart(chart_energy, use_container_width=True)
            
            # Show daily energy usage pattern if enough data
            if len(df) > 24:
                st.subheader("Daily Energy Usage Pattern")
                df_hourly['hour_of_day'] = df_hourly['timestamp'].dt.hour
                hourly_pattern = df_hourly.groupby('hour_of_day')['building_total_energy_kwh'].mean().reset_index()
                
                chart_pattern = alt.Chart(hourly_pattern).mark_bar().encode(
                    x=alt.X('hour_of_day:O', title="Hour of Day"),
                    y=alt.Y('building_total_energy_kwh:Q', title="Avg Energy (kWh)"),
                    tooltip=['hour_of_day:O', 'building_total_energy_kwh:Q']
                ).properties(
                    width=700, 
                    height=300, 
                    title="Average Energy Usage by Hour of Day"
                )
                
                st.altair_chart(chart_pattern, use_container_width=True)
        else:
            st.warning("Field 'building_total_energy_kwh' not found in the data.")
        
        # ----- Visualization: Building Demand -----
        if "building_demand_kw" in df.columns:
            st.subheader("Building Demand")
            
            # Aggregate by hour
            if 'hour' not in df_hourly.columns:
                df_hourly['hour'] = df_hourly['timestamp'].dt.floor('H')
            demand_hourly = df_hourly.groupby('hour')['building_demand_kw'].mean().reset_index()
            
            chart_demand = alt.Chart(demand_hourly).mark_line(color="red").encode(
                x=alt.X('hour:T', title="Time"),
                y=alt.Y('building_demand_kw:Q', title="Demand (kW)"),
                tooltip=['hour:T', 'building_demand_kw:Q']
            ).properties(
                width=700, 
                height=300, 
                title="Building Demand (Hourly Average)"
            ).interactive()
            
            st.altair_chart(chart_demand, use_container_width=True)
        else:
            st.warning("Field 'building_demand_kw' not found in the data.")
    
    with tabs[2]:  # Device Details Tab
        st.header("Device Details")
        
        if "device_id" in df.columns:
            # Device selector
            device_list = sorted(df["device_id"].unique())
            if device_list:
                selected_device = st.selectbox("Select a Device", device_list)
                device_df = df[df["device_id"] == selected_device]
                
                # Device metadata and stats
                st.subheader(f"Device: {selected_device}")
                
                # Show all sensor types for this device
                if "sensor_type" in device_df.columns:
                    st.write("Sensor Types:", ", ".join(sorted(device_df["sensor_type"].unique())))
                
                # Display last received data
                if not device_df.empty:
                    st.write("Last data received:", device_df["timestamp"].max())
                    
                    # Display latest record details
                    latest_record = device_df.sort_values("timestamp", ascending=False).iloc[0].to_dict()
                    st.subheader("Latest Reading")
                    
                    # Format the data nicely
                    col1, col2 = st.columns(2)
                    with col1:
                        for key, value in list(latest_record.items())[:len(latest_record)//2]:
                            if key not in ["timestamp", "hour", "hour_of_day"]:
                                st.write(f"**{key}:** {value}")
                    with col2:
                        for key, value in list(latest_record.items())[len(latest_record)//2:]:
                            if key not in ["timestamp", "hour", "hour_of_day"]:
                                st.write(f"**{key}:** {value}")
                                
                    # Device activity timeline
                    st.subheader("Device Activity Timeline")
                    timeline_df = device_df.copy()
                    timeline_df['hour'] = timeline_df['timestamp'].dt.floor('H')
                    timeline_df = timeline_df.groupby('hour').size().reset_index(name='messages')
                    
                    activity_chart = alt.Chart(timeline_df).mark_bar().encode(
                        x=alt.X('hour:T', title="Time"),
                        y=alt.Y('messages:Q', title="Messages"),
                        tooltip=['hour:T', 'messages:Q']
                    ).properties(
                        width=700, 
                        height=200, 
                        title="Message Activity Over Time"
                    )
                    
                    st.altair_chart(activity_chart, use_container_width=True)
                else:
                    st.warning(f"No data available for device {selected_device}")
            else:
                st.warning("No device data available")
        else:
            st.warning("Device ID field not found in the data")
    
    with tabs[3]:  # Raw Data Tab
        st.header("Raw Data")
        
        # Data format options
        data_format = st.radio("Data Format", ["Table", "JSON"], horizontal=True)
        
        # Row limit
        row_limit = st.slider("Number of Rows", min_value=10, max_value=1000, value=100, step=10)
        
        # Sort options
        sort_by = st.selectbox("Sort By", ["timestamp", "device_id", "sensor_type"] if all(x in df.columns for x in ["timestamp", "device_id", "sensor_type"]) else df.columns.tolist())
        sort_order = st.radio("Sort Order", ["Descending", "Ascending"], horizontal=True)
        
        # Sort and limit the dataframe
        sorted_df = df.sort_values(
            by=sort_by, 
            ascending=(sort_order == "Ascending")
        ).head(row_limit)
        
        # Display according to selected format
        if data_format == "Table":
            st.dataframe(sorted_df, use_container_width=True)
        else:  # JSON format
            for i, record in enumerate(sorted_df.to_dict('records')):
                with st.expander(f"Record {i+1}"):
                    st.json(record)

# Footer with metadata - only show if authenticated
if st.session_state.get("authenticated", False):
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"Dashboard last refreshed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with col2:
        st.write(f"DynamoDB Table: {selected_table} | Region: {selected_region}")
    with col3:
        # Add monitoring metrics
        try:
            memory_usage = round(os.popen('ps -o rss= -p %d' % os.getpid()).read().strip())
            st.write(f"Memory usage: {memory_usage} KB")
        except Exception:
            st.write("Monitoring metrics unavailable")