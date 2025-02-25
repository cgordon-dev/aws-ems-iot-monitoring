#!/usr/bin/env python3
"""
simulate_iot_data.py

Simulates IoT sensor data and publishes it to AWS IoT Core.
This script uses the AWS IoT Device SDK for Python and retrieves
the device's certificate and private key from AWS Secrets Manager
or environment variables.
"""

import json
import random
import time
import datetime
import os
import boto3
import logging
from pathlib import Path
from dotenv import load_dotenv
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IoTSimulator")

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
credentials = get_iot_credentials()

# Create temp directory if it doesn't exist
os.makedirs('/tmp', exist_ok=True)

with open("/tmp/certificate.pem.crt", "w") as cert_file:
    cert_file.write(credentials.get("certificate_pem"))
with open("/tmp/private.pem.key", "w") as key_file:
    key_file.write(credentials.get("private_key"))

# ----- Configuration Variables -----
IOT_ENDPOINT = os.getenv("IOT_ENDPOINT")
if not IOT_ENDPOINT:
    logger.error("IOT_ENDPOINT not set. Please set it in your environment or .env file.")
    raise ValueError("IOT_ENDPOINT environment variable is required")

CERTIFICATE_PATH = "/tmp/certificate.pem.crt"
PRIVATE_KEY_PATH = "/tmp/private.pem.key"

# Try to locate AmazonRootCA1.pem in a few different places
root_ca_locations = [
    os.getenv("ROOT_CA_PATH"),
    "./AmazonRootCA1.pem",
    "./certs/AmazonRootCA1.pem",
    os.path.expanduser("~/AmazonRootCA1.pem"),
    os.path.expanduser("~/certs/AmazonRootCA1.pem"),
]

ROOT_CA_PATH = None
for location in root_ca_locations:
    if location and Path(location).exists():
        ROOT_CA_PATH = location
        break

if not ROOT_CA_PATH:
    logger.warning("AmazonRootCA1.pem not found. Downloading it now...")
    try:
        import requests
        root_ca_content = requests.get("https://www.amazontrust.com/repository/AmazonRootCA1.pem").text
        os.makedirs("./certs", exist_ok=True)
        with open("./certs/AmazonRootCA1.pem", "w") as f:
            f.write(root_ca_content)
        ROOT_CA_PATH = "./certs/AmazonRootCA1.pem"
        logger.info(f"Downloaded AmazonRootCA1.pem to {ROOT_CA_PATH}")
    except Exception as e:
        logger.error(f"Failed to download AmazonRootCA1.pem: {str(e)}")
        raise ValueError("ROOT_CA_PATH not found and could not be downloaded")

# ----- Initialize the MQTT Client -----
logger.info(f"Connecting to IoT endpoint: {IOT_ENDPOINT}")
client = AWSIoTMQTTClient("ems-simulated-device")
client.configureEndpoint(IOT_ENDPOINT, 8883)
client.configureCredentials(ROOT_CA_PATH, PRIVATE_KEY_PATH, CERTIFICATE_PATH)
client.configureOfflinePublishQueueing(-1)
client.configureDrainingFrequency(2)
client.configureConnectDisconnectTimeout(10)
client.configureMQTTOperationTimeout(5)

# Connect with retry logic
max_retries = 5
for attempt in range(max_retries):
    try:
        logger.info(f"Connecting to AWS IoT Core, attempt {attempt+1}/{max_retries}")
        connect_result = client.connect()
        logger.info(f"Connection successful: {connect_result}")
        break
    except Exception as e:
        logger.error(f"Connection attempt {attempt+1} failed: {str(e)}")
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        else:
            logger.error("Failed to connect to AWS IoT Core after maximum retries")
            raise

def generate_sensor_data(sensor_type):
    """Generate simulated sensor data based on the sensor type"""
    # Get device ID from environment variable or use default
    device_id = os.getenv("DEVICE_ID", "ems-monitoring-device")
    
    # Add TTL value for DynamoDB (current timestamp + 30 days in seconds)
    ttl_value = int((datetime.datetime.now() + 
                    datetime.timedelta(days=30)).timestamp())
    
    data = {
        "device_id": device_id,
        "sensor_type": sensor_type,
        "edge_time_stamp": str(datetime.datetime.now()),
        "ttl": ttl_value
    }
    if sensor_type == "building":
        data["building_total_energy_kwh"] = round(random.uniform(1000, 2000), 2)
        data["building_demand_kw"] = round(random.uniform(50, 150), 2)
    elif sensor_type == "hvac":
        data["hvac_runtime_minutes"] = random.randint(0, 60)
        data["hvac_power_kw"] = round(random.uniform(0.5, 3.0), 2)
    elif sensor_type == "dhw":
        data["energy_consumption_kwh"] = round(random.uniform(10, 50), 2)
        data["cycle_duration_minutes"] = random.randint(5, 30)
    elif sensor_type == "lighting":
        data["lighting_energy_kwh"] = round(random.uniform(1, 5), 2)
    elif sensor_type == "occupancy":
        data["activation_events"] = random.randint(0, 10)
        data["battery_level"] = random.randint(20, 100)
    elif sensor_type == "environment":
        data["ambient_temp"] = round(random.uniform(65, 80), 1)
        data["humidity"] = round(random.uniform(30, 60), 1)
    return data

def publish_with_retry(topic, message, qos=1, max_retries=3):
    """Publish a message with retry logic"""
    for attempt in range(max_retries):
        try:
            result = client.publish(topic, message, qos)
            return result
        except Exception as e:
            logger.error(f"Publish attempt {attempt+1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                logger.error(f"Failed to publish to topic {topic} after maximum retries")
                return False

# Main loop
logger.info("Starting IoT data simulation")
interval = int(os.getenv("PUBLISH_INTERVAL_SECONDS", "5"))

try:
    while True:
        # Publish sensor data under different topics
        building_data = generate_sensor_data("building")
        publish_with_retry("ems/building", json.dumps(building_data))
        logger.info(f"Published building data: {building_data}")

        hvac_data = generate_sensor_data("hvac")
        publish_with_retry("ems/hvac", json.dumps(hvac_data))
        logger.info(f"Published HVAC data: {hvac_data}")

        dhw_data = generate_sensor_data("dhw")
        publish_with_retry("ems/dhw", json.dumps(dhw_data))
        logger.info(f"Published DHW data: {dhw_data}")

        lighting_data = generate_sensor_data("lighting")
        publish_with_retry("ems/lighting", json.dumps(lighting_data))
        logger.info(f"Published Lighting data: {lighting_data}")

        occupancy_data = generate_sensor_data("occupancy")
        publish_with_retry("ems/occupancy", json.dumps(occupancy_data))
        logger.info(f"Published Occupancy data: {occupancy_data}")

        environment_data = generate_sensor_data("environment")
        publish_with_retry("ems/environment", json.dumps(environment_data))
        logger.info(f"Published Environment data: {environment_data}")

        time.sleep(interval)
except KeyboardInterrupt:
    logger.info("Simulation stopped by user")
except Exception as e:
    logger.error(f"Simulation error: {str(e)}")
finally:
    client.disconnect()
    logger.info("Disconnected from AWS IoT Core")