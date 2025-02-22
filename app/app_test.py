#!/usr/bin/env python3
"""
app/app.py

A Streamlit dashboard that both simulates IoT sensor data and visualizes it in real time.
Simulation functions run as background threads and update shared data in st.session_state.
"""

import streamlit as st
import threading
import time
import random
import datetime
import pandas as pd
import altair as alt
from dotenv import load_dotenv
import os

# Load environment variables from .env file (if needed)
load_dotenv()

# Initialize shared simulated data in session_state if not present
if "simulated_data" not in st.session_state:
    st.session_state.simulated_data = {
        "building": [],
        "hvac": [],
        "dhw": [],
        "lighting": [],
        "occupancy": [],
        "environment": []
    }

# -------------- Simulation Functions --------------

def simulate_building_data():
    """Simulate building main panel data at 1-minute intervals."""
    while True:
        data = {
            "timestamp": datetime.datetime.now(),
            "building_total_energy_kwh": round(random.uniform(1000, 2000), 2),
            "building_demand_kw": round(random.uniform(50, 150), 2)
        }
        st.session_state.simulated_data["building"].append(data)
        # Keep only the latest 100 records
        st.session_state.simulated_data["building"] = st.session_state.simulated_data["building"][-100:]
        time.sleep(60)

def simulate_hvac_data():
    """Simulate HVAC data at 1-minute intervals."""
    while True:
        data = {
            "timestamp": datetime.datetime.now(),
            "hvac_runtime_minutes": random.randint(0, 60),
            "hvac_power_kw": round(random.uniform(0.5, 3.0), 2)
        }
        st.session_state.simulated_data["hvac"].append(data)
        st.session_state.simulated_data["hvac"] = st.session_state.simulated_data["hvac"][-100:]
        time.sleep(60)

def simulate_dhw_data():
    """Simulate Domestic Hot Water (DHW) heater data at 5-minute intervals."""
    while True:
        data = {
            "timestamp": datetime.datetime.now(),
            "energy_consumption_kwh": round(random.uniform(10, 50), 2),
            "cycle_duration_minutes": random.randint(5, 30)
        }
        st.session_state.simulated_data["dhw"].append(data)
        st.session_state.simulated_data["dhw"] = st.session_state.simulated_data["dhw"][-100:]
        time.sleep(300)

def simulate_lighting_data():
    """Simulate common lighting data at 1-minute intervals."""
    while True:
        data = {
            "timestamp": datetime.datetime.now(),
            "lighting_energy_kwh": round(random.uniform(1, 5), 2)
        }
        st.session_state.simulated_data["lighting"].append(data)
        st.session_state.simulated_data["lighting"] = st.session_state.simulated_data["lighting"][-100:]
        time.sleep(60)

def simulate_occupancy_data():
    """Simulate occupancy sensor events at 1-minute intervals."""
    while True:
        data = {
            "timestamp": datetime.datetime.now(),
            "activation_events": random.randint(0, 10),
            "battery_level": random.randint(20, 100)
        }
        st.session_state.simulated_data["occupancy"].append(data)
        st.session_state.simulated_data["occupancy"] = st.session_state.simulated_data["occupancy"][-100:]
        time.sleep(60)

def simulate_environment_data():
    """Simulate environmental sensor data at 5-minute intervals."""
    while True:
        data = {
            "timestamp": datetime.datetime.now(),
            "ambient_temp": round(random.uniform(65, 80), 1),
            "humidity": round(random.uniform(30, 60), 1)
        }
        st.session_state.simulated_data["environment"].append(data)
        st.session_state.simulated_data["environment"] = st.session_state.simulated_data["environment"][-100:]
        time.sleep(300)

# -------------- Start Simulation Threads (Once) --------------

if "simulation_started" not in st.session_state:
    st.session_state.simulation_started = True
    threading.Thread(target=simulate_building_data, daemon=True).start()
    threading.Thread(target=simulate_hvac_data, daemon=True).start()
    threading.Thread(target=simulate_dhw_data, daemon=True).start()
    threading.Thread(target=simulate_lighting_data, daemon=True).start()
    threading.Thread(target=simulate_occupancy_data, daemon=True).start()
    threading.Thread(target=simulate_environment_data, daemon=True).start()

# -------------- Dashboard UI --------------

st.title("Interactive EMS Dashboard")
st.markdown("This dashboard displays real-time simulated sensor data.")

# Refresh button to manually force a re-run of the script
if st.button("Refresh Data"):
    st.experimental_rerun()

# Display Building Data
st.header("Building Data")
if st.session_state.simulated_data["building"]:
    df_building = pd.DataFrame(st.session_state.simulated_data["building"])
    chart_building = alt.Chart(df_building).mark_line().encode(
        x=alt.X("timestamp:T", title="Time"),
        y=alt.Y("building_total_energy_kwh:Q", title="Total Energy (kWh)"),
        tooltip=["timestamp:T", "building_total_energy_kwh:Q"]
    ).properties(width=700, height=300, title="Total Energy Consumption Over Time")
    st.altair_chart(chart_building, use_container_width=True)
else:
    st.write("No building data available yet.")

# Display HVAC Data
st.header("HVAC Data")
if st.session_state.simulated_data["hvac"]:
    df_hvac = pd.DataFrame(st.session_state.simulated_data["hvac"])
    chart_hvac = alt.Chart(df_hvac).mark_line(color="green").encode(
        x=alt.X("timestamp:T", title="Time"),
        y=alt.Y("hvac_power_kw:Q", title="HVAC Power (kW)"),
        tooltip=["timestamp:T", "hvac_power_kw:Q"]
    ).properties(width=700, height=300, title="HVAC Power Consumption Over Time")
    st.altair_chart(chart_hvac, use_container_width=True)
else:
    st.write("No HVAC data available yet.")

# Display DHW Data
st.header("DHW Data")
if st.session_state.simulated_data["dhw"]:
    df_dhw = pd.DataFrame(st.session_state.simulated_data["dhw"])
    chart_dhw = alt.Chart(df_dhw).mark_line(color="orange").encode(
        x=alt.X("timestamp:T", title="Time"),
        y=alt.Y("energy_consumption_kwh:Q", title="Energy Consumption (kWh)"),
        tooltip=["timestamp:T", "energy_consumption_kwh:Q"]
    ).properties(width=700, height=300, title="DHW Energy Consumption Over Time")
    st.altair_chart(chart_dhw, use_container_width=True)
else:
    st.write("No DHW data available yet.")

# Display Lighting Data
st.header("Lighting Data")
if st.session_state.simulated_data["lighting"]:
    df_lighting = pd.DataFrame(st.session_state.simulated_data["lighting"])
    chart_lighting = alt.Chart(df_lighting).mark_line(color="purple").encode(
        x=alt.X("timestamp:T", title="Time"),
        y=alt.Y("lighting_energy_kwh:Q", title="Lighting Energy (kWh)"),
        tooltip=["timestamp:T", "lighting_energy_kwh:Q"]
    ).properties(width=700, height=300, title="Lighting Energy Consumption Over Time")
    st.altair_chart(chart_lighting, use_container_width=True)
else:
    st.write("No lighting data available yet.")

# Display Occupancy Data
st.header("Occupancy Data")
if st.session_state.simulated_data["occupancy"]:
    df_occupancy = pd.DataFrame(st.session_state.simulated_data["occupancy"])
    chart_occupancy = alt.Chart(df_occupancy).mark_line(color="red").encode(
        x=alt.X("timestamp:T", title="Time"),
        y=alt.Y("activation_events:Q", title="Activation Events"),
        tooltip=["timestamp:T", "activation_events:Q", "battery_level:Q"]
    ).properties(width=700, height=300, title="Occupancy Activation Events Over Time")
    st.altair_chart(chart_occupancy, use_container_width=True)
else:
    st.write("No occupancy data available yet.")

# Display Environmental Data
st.header("Environmental Data")
if st.session_state.simulated_data["environment"]:
    df_environment = pd.DataFrame(st.session_state.simulated_data["environment"])
    chart_environment = alt.Chart(df_environment).mark_line(color="blue").encode(
        x=alt.X("timestamp:T", title="Time"),
        y=alt.Y("ambient_temp:Q", title="Ambient Temperature (°F)"),
        tooltip=["timestamp:T", "ambient_temp:Q", "humidity:Q"]
    ).properties(width=700, height=300, title="Ambient Temperature Over Time")
    st.altair_chart(chart_environment, use_container_width=True)
else:
    st.write("No environmental data available yet.")

st.write("Last updated:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))