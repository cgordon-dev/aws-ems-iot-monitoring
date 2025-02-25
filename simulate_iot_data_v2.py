#!/usr/bin/env python3
"""
simulate_iot_data_v2.py

Simulates IoT sensor data and publishes it to AWS IoT Core.
This script uses the AWS IoT Device SDK for Python and can retrieve
the device's certificate and private key from various sources (environment variables, 
AWS Secrets Manager, or local files).

It simulates multiple monitoring points at intervals based on the RTEM system design criteria,
including unit-specific space temperature readings (bedroom, living room, kitchen) at 5‑minute intervals.

This script is designed to run as a service when the application is deployed.
"""

import os
import json
import random
import time
import datetime
import threading
import logging
import signal
import sys
import boto3
import requests
from pathlib import Path
from dotenv import load_dotenv
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/tmp/iot_simulator_v2.log")
    ]
)
logger = logging.getLogger("IoTSimulatorV2")

# Load environment variables from .env file if it exists
load_dotenv()

# ----- Helper to retrieve secrets from AWS Secrets Manager -----
def get_secret(secret_name, region_name=None):
    """Retrieve a secret from AWS Secrets Manager"""
    if not region_name:
        region_name = os.getenv("AWS_REGION", "us-east-1")
    
    try:
        client = boto3.client("secretsmanager", region_name=region_name)
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response["SecretString"]
        return json.loads(secret)
    except Exception as e:
        logger.error(f"Error retrieving secret {secret_name}: {str(e)}")
        return None

# ----- Get IoT device credentials -----
def get_iot_credentials():
    """Get IoT device credentials from Secrets Manager or environment variables"""
    # Method 1: Try to get credentials from environment variables first
    cert_env = os.getenv("IOT_CERTIFICATE")
    key_env = os.getenv("IOT_PRIVATE_KEY")
    
    if cert_env and key_env:
        logger.info("Using IoT credentials from environment variables")
        return {
            "certificate_pem": cert_env,
            "private_key": key_env
        }
    
    # Method 2: Try to get credentials from AWS Secrets Manager
    secret_name = os.getenv("IOT_SECRET_NAME", "ems/iot_device_credentials")
    logger.info(f"Attempting to retrieve IoT credentials from Secrets Manager: {secret_name}")
    credentials = get_secret(secret_name)
    
    if credentials:
        return credentials
    
    # Method 3: Look for local files
    logger.info("Checking for local credential files")
    base_dir = Path(__file__).parent
    cert_file = base_dir / "certs" / "certificate.pem.crt"
    key_file = base_dir / "certs" / "private.pem.key"
    
    if cert_file.exists() and key_file.exists():
        return {
            "certificate_pem": cert_file.read_text(),
            "private_key": key_file.read_text()
        }
    
    logger.error("Could not find IoT credentials")
    raise ValueError("IoT credentials not found in environment, Secrets Manager, or local files")

# ----- Retrieve IoT device credentials -----
try:
    credentials = get_iot_credentials()
    logger.info("Successfully retrieved IoT credentials")

    # Create temp directory if it doesn't exist
    os.makedirs('/tmp', exist_ok=True)

    with open("/tmp/certificate.pem.crt", "w") as cert_file:
        cert_file.write(credentials.get("certificate_pem"))
    with open("/tmp/private.pem.key", "w") as key_file:
        key_file.write(credentials.get("private_key"))
    
    CERTIFICATE_PATH = "/tmp/certificate.pem.crt"
    PRIVATE_KEY_PATH = "/tmp/private.pem.key"
except Exception as e:
    logger.error(f"Failed to get IoT credentials: {str(e)}")
    sys.exit(1)

# ----- Configuration Variables -----
IOT_ENDPOINT = os.getenv("IOT_ENDPOINT")
if not IOT_ENDPOINT:
    logger.error("IOT_ENDPOINT not set. Please set it in your environment or .env file.")
    sys.exit(1)

# Try to locate AmazonRootCA1.pem or download it
root_ca_locations = [
    os.getenv("ROOT_CA_PATH"),
    "./AmazonRootCA1.pem",
    "./certs/AmazonRootCA1.pem",
    os.path.expanduser("~/AmazonRootCA1.pem"),
    os.path.expanduser("~/certs/AmazonRootCA1.pem"),
    "/tmp/AmazonRootCA1.pem"
]

ROOT_CA_PATH = None
for location in root_ca_locations:
    if location and Path(location).exists():
        ROOT_CA_PATH = location
        break

if not ROOT_CA_PATH:
    logger.warning("AmazonRootCA1.pem not found. Downloading it now...")
    try:
        root_ca_content = requests.get("https://www.amazontrust.com/repository/AmazonRootCA1.pem").text
        os.makedirs("./certs", exist_ok=True)
        with open("./certs/AmazonRootCA1.pem", "w") as f:
            f.write(root_ca_content)
        ROOT_CA_PATH = "./certs/AmazonRootCA1.pem"
        logger.info(f"Downloaded AmazonRootCA1.pem to {ROOT_CA_PATH}")
    except Exception as e:
        logger.error(f"Failed to download AmazonRootCA1.pem: {str(e)}")
        sys.exit(1)

# Get device ID from environment variable or use default
DEVICE_ID_PREFIX = os.getenv("DEVICE_ID", "ems-monitoring-device")

# ----- Initialize the MQTT Client -----
logger.info(f"Connecting to IoT endpoint: {IOT_ENDPOINT}")
client = AWSIoTMQTTClient(f"{DEVICE_ID_PREFIX}-v2")
client.configureEndpoint(IOT_ENDPOINT, 8883)
client.configureCredentials(ROOT_CA_PATH, PRIVATE_KEY_PATH, CERTIFICATE_PATH)
client.configureOfflinePublishQueueing(-1)
client.configureDrainingFrequency(2)
client.configureConnectDisconnectTimeout(10)
client.configureMQTTOperationTimeout(5)

# Connect with retry logic
connected = False
max_retries = 5
for attempt in range(max_retries):
    try:
        logger.info(f"Connecting to AWS IoT Core, attempt {attempt+1}/{max_retries}")
        connect_result = client.connect()
        logger.info(f"Connection successful: {connect_result}")
        connected = True
        break
    except Exception as e:
        logger.error(f"Connection attempt {attempt+1} failed: {str(e)}")
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

if not connected:
    logger.error("Failed to connect to AWS IoT Core after maximum retries")
    sys.exit(1)

# ------------------ Simulation Functions ------------------

def simulate_building_main_panel():
    """Main Service Panel Energy Meter (1-minute interval)"""
    while True:
        try:
            # Get device ID from environment variable or use default
            device_id = f"{DEVICE_ID_PREFIX}_building_main_panel"
            
            # Add TTL value for DynamoDB (current timestamp + 30 days in seconds)
            ttl_value = calculate_ttl()
            
            data = {
                "device_id": device_id,
                "sensor_type": "building",
                "edge_time_stamp": str(datetime.datetime.now()),
                "building_total_energy_kwh": round(random.uniform(1000, 2000), 2),
                "building_demand_kw": round(random.uniform(50, 150), 2),
                "ttl": ttl_value
            }
            publish_with_retry("ems/building/main_panel", json.dumps(data), 1)
            logger.info(f"Published building main panel data: {data['building_total_energy_kwh']} kWh, {data['building_demand_kw']} kW")
            time.sleep(60)
        except Exception as e:
            logger.error(f"Error in building_main_panel simulation: {str(e)}")
            time.sleep(60)  # Continue with next interval

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

# ----- Helper for thread-safe publishing -----
def publish_with_retry(topic, message, qos=1, max_retries=3):
    """Publish a message with retry logic"""
    for attempt in range(max_retries):
        try:
            result = client.publish(topic, message, qos)
            return result
        except Exception as e:
            logger.error(f"Publish attempt {attempt+1} failed for topic {topic}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                logger.error(f"Failed to publish to topic {topic} after maximum retries")
                return False

# ----- TTL helper function -----
def calculate_ttl(days=30):
    """Calculate TTL value for DynamoDB (current timestamp + specified days in seconds)"""
    return int((datetime.datetime.now() + datetime.timedelta(days=days)).timestamp())

# ----- Signal handler for graceful shutdown -----
def signal_handler(sig, frame):
    """Handle graceful shutdown"""
    logger.info("Stopping IoT simulator (received signal to shutdown)")
    client.disconnect()
    logger.info("Disconnected from AWS IoT Core")
    sys.exit(0)

# Set up signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ------------------ Main Thread: Start Simulation Threads ------------------

def main():
    """Main function to start the simulation"""
    threads = []
    
    # Building-Level Threads
    threads.append(threading.Thread(target=simulate_building_main_panel))
    threads.append(threading.Thread(target=simulate_gateway_health))
    threads.append(threading.Thread(target=simulate_network_monitoring))

    # Get number of units from environment or use default
    num_units = int(os.getenv("NUM_UNITS", "4"))
    logger.info(f"Simulating {num_units} units")
    
    # Unit-Level Threads
    for unit_id in range(1, num_units + 1):
        threads.append(threading.Thread(target=simulate_unit_panel, args=(unit_id,)))
        threads.append(threading.Thread(target=simulate_unit_hvac, args=(unit_id,)))
        threads.append(threading.Thread(target=simulate_unit_dhw, args=(unit_id,)))
        threads.append(threading.Thread(target=simulate_unit_appliance, args=(unit_id,)))
        for room in ["bedroom", "living_room", "kitchen"]:
            threads.append(threading.Thread(target=simulate_unit_space_temperature, args=(unit_id, room)))

    # Common Areas Threads
    threads.append(threading.Thread(target=simulate_common_lighting))
    threads.append(threading.Thread(target=simulate_occupancy_events))
    threads.append(threading.Thread(target=simulate_occupancy_health))
    threads.append(threading.Thread(target=simulate_environmental))

    logger.info(f"Starting {len(threads)} simulation threads")
    
    # Start all threads as daemon threads
    for t in threads:
        t.daemon = True
        t.start()
        time.sleep(0.1)  # Small delay to avoid overwhelming the connection

    # Log thread status
    logger.info(f"All {len(threads)} threads started successfully")
    
    # Keep the main thread alive while handling signals for graceful shutdown
    try:
        while True:
            time.sleep(10)
            logger.info("Simulator running - publishing data to AWS IoT Core")
    except KeyboardInterrupt:
        logger.info("Stopping IoT simulator (keyboard interrupt)")
        client.disconnect()
        logger.info("Disconnected from AWS IoT Core")
    except Exception as e:
        logger.error(f"Error in main thread: {str(e)}")
        client.disconnect()
        logger.error("Disconnected from AWS IoT Core due to error")
        sys.exit(1)

if __name__ == "__main__":
    main()