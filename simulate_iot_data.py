#!/usr/bin/env python3
"""
simulate_iot_data.py

Simulates IoT sensor data and publishes it to AWS IoT Core.
This script uses the AWS IoT Device SDK for Python and retrieves
the device's certificate and private key from AWS Secrets Manager.
"""

import json
import random
import time
import datetime
import boto3
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# ----- Helper to retrieve secrets from AWS Secrets Manager -----
def get_secret(secret_name, region_name="us-east-1"):
    client = boto3.client("secretsmanager", region_name=region_name)
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    secret = get_secret_value_response["SecretString"]
    return json.loads(secret)

# ----- Retrieve IoT device credentials from Secrets Manager -----
# Ensure that a secret (e.g., ems/iot_device_credentials) exists with keys: "certificate_pem" and "private_key"
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

def generate_sensor_data(sensor_type):
    data = {
        "device_id": "ems-monitoring-device",
        "edge_time_stamp": str(datetime.datetime.now())
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

while True:
    # Publish sensor data under different topics
    building_data = generate_sensor_data("building")
    client.publish("ems/building", json.dumps(building_data), 1)
    print("Published building data:", building_data)

    hvac_data = generate_sensor_data("hvac")
    client.publish("ems/hvac", json.dumps(hvac_data), 1)
    print("Published HVAC data:", hvac_data)

    dhw_data = generate_sensor_data("dhw")
    client.publish("ems/dhw", json.dumps(dhw_data), 1)
    print("Published DHW data:", dhw_data)

    lighting_data = generate_sensor_data("lighting")
    client.publish("ems/lighting", json.dumps(lighting_data), 1)
    print("Published Lighting data:", lighting_data)

    occupancy_data = generate_sensor_data("occupancy")
    client.publish("ems/occupancy", json.dumps(occupancy_data), 1)
    print("Published Occupancy data:", occupancy_data)

    environment_data = generate_sensor_data("environment")
    client.publish("ems/environment", json.dumps(environment_data), 1)
    print("Published Environment data:", environment_data)

    time.sleep(5)