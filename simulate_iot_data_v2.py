#!/usr/bin/env python3
"""
simulate_iot_data.py

Simulates IoT sensor data and publishes it to AWS IoT Core.
This script uses the AWS IoT Device SDK for Python and retrieves
the device's certificate and private key from AWS Secrets Manager.
It simulates multiple monitoring points at intervals based on the RTEM system design criteria,
including unit-specific space temperature readings (bedroom, living room, kitchen) at 5‑minute intervals.
"""

import json
import random
import time
import datetime
import threading
import boto3
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# ----- Helper to retrieve secrets from AWS Secrets Manager -----
def get_secret(secret_name, region_name="us-east-1"):
    client = boto3.client("secretsmanager", region_name=region_name)
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    secret = get_secret_value_response["SecretString"]
    return json.loads(secret)

# ----- Retrieve IoT device credentials from Secrets Manager -----
secret_name = "ems/iot_device_credentials"
credentials = get_secret(secret_name)
with open("/tmp/certificate.pem.crt", "w") as cert_file:
    cert_file.write(credentials.get("certificate_pem"))
with open("/tmp/private.pem.key", "w") as key_file:
    key_file.write(credentials.get("private_key"))

# ----- Configuration Variables -----
IOT_ENDPOINT = "<YOUR_IOT_ENDPOINT_FROM_TERRAFORM>"  # Replace with the output value from Terraform
CERTIFICATE_PATH = "/tmp/certificate.pem.crt"
PRIVATE_KEY_PATH = "/tmp/private.pem.key"
ROOT_CA_PATH = "/path/to/AmazonRootCA1.pem"  # Download AmazonRootCA1.pem from AWS IoT documentation

# ----- Initialize the MQTT Client -----
client = AWSIoTMQTTClient("ems-simulated-device")
client.configureEndpoint(IOT_ENDPOINT, 8883)
client.configureCredentials(ROOT_CA_PATH, PRIVATE_KEY_PATH, CERTIFICATE_PATH)
client.configureOfflinePublishQueueing(-1)
client.configureDrainingFrequency(2)
client.configureConnectDisconnectTimeout(10)
client.configureMQTTOperationTimeout(5)

client.connect()

# ------------------ Simulation Functions ------------------

# Building-Level Monitoring

def simulate_building_main_panel():
    """Main Service Panel Energy Meter (1-minute interval)"""
    while True:
        data = {
            "device_id": "building_main_panel",
            "edge_time_stamp": str(datetime.datetime.now()),
            "building_total_energy_kwh": round(random.uniform(1000, 2000), 2),
            "building_demand_kw": round(random.uniform(50, 150), 2)
        }
        client.publish("ems/building/main_panel", json.dumps(data), 1)
        print("Published building main panel data:", data)
        time.sleep(60)

def simulate_gateway_health():
    """Local Gateway/Controller Health (30-second interval)"""
    while True:
        data = {
            "device_id": "local_gateway",
            "edge_time_stamp": str(datetime.datetime.now()),
            "status": random.choice(["OK", "WARN", "ERROR"]),
            "message": "Gateway health check"
        }
        client.publish("ems/building/gateway_health", json.dumps(data), 1)
        print("Published gateway health data:", data)
        time.sleep(30)

def simulate_network_monitoring():
    """Communication Network Monitoring (1-minute interval)"""
    while True:
        data = {
            "device_id": "network_monitor",
            "edge_time_stamp": str(datetime.datetime.now()),
            "latency_ms": random.randint(10, 100),
            "packet_loss_percent": round(random.uniform(0, 5), 2)
        }
        client.publish("ems/building/network", json.dumps(data), 1)
        print("Published network monitoring data:", data)
        time.sleep(60)

# Unit-Level Monitoring (for 4 Units)

def simulate_unit_panel(unit_id):
    """Unit Main Distribution Panel Sub-Meter (1-minute interval)"""
    while True:
        data = {
            "device_id": f"unit_{unit_id}_panel",
            "unit_id": unit_id,
            "edge_time_stamp": str(datetime.datetime.now()),
            "sub_meter_energy_kwh": round(random.uniform(100, 200), 2),
            "demand_kw": round(random.uniform(10, 50), 2)
        }
        topic = f"ems/unit/{unit_id}/panel"
        client.publish(topic, json.dumps(data), 1)
        print(f"Published unit {unit_id} panel data:", data)
        time.sleep(60)

def simulate_unit_hvac(unit_id):
    """Mini-Split HVAC Systems (1-minute interval)"""
    while True:
        data = {
            "device_id": f"unit_{unit_id}_hvac",
            "unit_id": unit_id,
            "edge_time_stamp": str(datetime.datetime.now()),
            "hvac_runtime_minutes": random.randint(0, 60),
            "hvac_power_kw": round(random.uniform(0.5, 3.0), 2)
        }
        topic = f"ems/unit/{unit_id}/hvac"
        client.publish(topic, json.dumps(data), 1)
        print(f"Published unit {unit_id} HVAC data:", data)
        time.sleep(60)

def simulate_unit_dhw(unit_id):
    """Electric Domestic Hot Water (DHW) Heater (5-minute interval)"""
    while True:
        data = {
            "device_id": f"unit_{unit_id}_dhw",
            "unit_id": unit_id,
            "edge_time_stamp": str(datetime.datetime.now()),
            "energy_consumption_kwh": round(random.uniform(10, 50), 2),
            "cycle_duration_minutes": random.randint(5, 30)
        }
        topic = f"ems/unit/{unit_id}/dhw"
        client.publish(topic, json.dumps(data), 1)
        print(f"Published unit {unit_id} DHW data:", data)
        time.sleep(300)

def simulate_unit_appliance(unit_id):
    """Electric Appliance Circuits (1-minute interval)"""
    while True:
        data = {
            "device_id": f"unit_{unit_id}_appliance",
            "unit_id": unit_id,
            "edge_time_stamp": str(datetime.datetime.now()),
            "appliance_energy_kwh": round(random.uniform(1, 5), 2)
        }
        topic = f"ems/unit/{unit_id}/appliance"
        client.publish(topic, json.dumps(data), 1)
        print(f"Published unit {unit_id} appliance data:", data)
        time.sleep(60)

def simulate_unit_space_temperature(unit_id, room):
    """Space Temperature Monitoring for a specific room in a unit (5-minute interval)"""
    while True:
        data = {
            "device_id": f"unit_{unit_id}_space_temp_{room}",
            "unit_id": unit_id,
            "edge_time_stamp": str(datetime.datetime.now()),
            "room": room,
            "temperature_f": round(random.uniform(65, 75), 2)
        }
        topic = f"ems/unit/{unit_id}/space_temperature/{room}"
        client.publish(topic, json.dumps(data), 1)
        print(f"Published space temperature data for unit {unit_id} {room}:", data)
        time.sleep(300)

# Common Areas Monitoring

def simulate_common_lighting():
    """Common Hallways LED Lighting Circuit (1-minute interval)"""
    while True:
        data = {
            "device_id": "common_lighting",
            "edge_time_stamp": str(datetime.datetime.now()),
            "lighting_energy_kwh": round(random.uniform(1, 5), 2)
        }
        client.publish("ems/common/lighting", json.dumps(data), 1)
        print("Published common area lighting data:", data)
        time.sleep(60)

def simulate_occupancy_events():
    """Occupancy sensor event-driven logging (immediate reporting)"""
    while True:
        data = {
            "device_id": "occupancy_sensor",
            "edge_time_stamp": str(datetime.datetime.now()),
            "event": "motion_detected"
        }
        client.publish("ems/common/occupancy/event", json.dumps(data), 1)
        print("Published occupancy event:", data)
        time.sleep(random.randint(10, 30))

def simulate_occupancy_health():
    """Occupancy sensor periodic health check (1-minute interval)"""
    while True:
        data = {
            "device_id": "occupancy_sensor",
            "edge_time_stamp": str(datetime.datetime.now()),
            "battery_level": random.randint(20, 100),
            "status": random.choice(["OK", "LOW_BATTERY"])
        }
        client.publish("ems/common/occupancy/health", json.dumps(data), 1)
        print("Published occupancy health check:", data)
        time.sleep(60)

def simulate_environmental():
    """Environmental Sensors (5-minute interval)"""
    while True:
        data = {
            "device_id": "environment_sensor",
            "edge_time_stamp": str(datetime.datetime.now()),
            "ambient_temp": round(random.uniform(65, 80), 1),
            "humidity": round(random.uniform(30, 60), 1)
        }
        client.publish("ems/common/environment", json.dumps(data), 1)
        print("Published environmental data:", data)
        time.sleep(300)

# ------------------ Main Thread: Start Simulation Threads ------------------

if __name__ == "__main__":
    threads = []

    # Building-Level Threads
    threads.append(threading.Thread(target=simulate_building_main_panel))
    threads.append(threading.Thread(target=simulate_gateway_health))
    threads.append(threading.Thread(target=simulate_network_monitoring))

    # Unit-Level Threads (for 4 units)
    for unit_id in range(1, 5):
        threads.append(threading.Thread(target=simulate_unit_panel, args=(unit_id,)))
        threads.append(threading.Thread(target=simulate_unit_hvac, args=(unit_id,)))
        threads.append(threading.Thread(target=simulate_unit_dhw, args=(unit_id,)))
        threads.append(threading.Thread(target=simulate_unit_appliance, args=(unit_id,)))
        # Space Temperature Threads for each room within the unit
        for room in ["bedroom", "living_room", "kitchen"]:
            threads.append(threading.Thread(target=simulate_unit_space_temperature, args=(unit_id, room)))

    # Common Areas Threads
    threads.append(threading.Thread(target=simulate_common_lighting))
    threads.append(threading.Thread(target=simulate_occupancy_events))
    threads.append(threading.Thread(target=simulate_occupancy_health))
    threads.append(threading.Thread(target=simulate_environmental))

    # Start all threads as daemon threads
    for t in threads:
        t.daemon = True
        t.start()

    # Keep the main thread alive.
    while True:
        time.sleep(1)