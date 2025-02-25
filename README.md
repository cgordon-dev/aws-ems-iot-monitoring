# AWS EMS IoT Monitoring System

This repository provides a complete production-ready solution for an Energy Management System (EMS) using AWS services. The solution includes:

- **AWS IoT Core & Data Pipeline:**  
  Provisioned with Terraform, it creates:
  - A unified IoT Thing with certificate and policy.
  - A DynamoDB table for sensor data with encryption and point-in-time recovery.
  - An IoT Rule that routes messages (published on topics such as `ems/building`, `ems/hvac`, etc.) to DynamoDB.

- **Simulated IoT Data Producer:**  
  A Python script (`simulate_iot_data.py`) that simulates sensor data and publishes messages to AWS IoT Core using the AWS IoT Device SDK. It retrieves certificate credentials securely from AWS Secrets Manager.

- **Streamlit Dashboard:**  
  A dockerized dashboard (in the `app` folder) that queries DynamoDB using Boto3 and displays interactive visualizations of the sensor data. Includes secure authentication.

- **CI/CD Pipeline:**  
  A GitHub Actions workflow (`.github/workflows/ci-cd.yml`) that runs Terraform to provision infrastructure, builds the Docker image for the dashboard, and pushes it to Amazon ECR.

- **Local Setup Script:**  
  `setup_tools.sh` installs required tools (AWS CLI, Terraform, Docker, Git, Python 3.9+).

## Prerequisites

- An AWS account
- Basic familiarity with AWS services (IAM, IoT Core, DynamoDB)
- Local machine with Linux/macOS (for Windows, use WSL)
- Git to clone this repository

## Detailed Deployment Guide

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/aws-ems-iot-monitoring.git
cd aws-ems-iot-monitoring
```

### 2. Install Required Tools

The project includes a setup script to install all necessary dependencies:

```bash
# Make the script executable
chmod +x setup_tools.sh

# For interactive installation (recommended for first-time setup)
./setup_tools.sh

# For non-interactive installation (CI/CD environments)
./setup_tools.sh --non-interactive
```

This script will install:
- AWS CLI v2
- Terraform
- Docker
- Git (if not already installed)
- Python 3.9+ with required packages

### 3. Configure AWS Credentials

Set up your AWS credentials if not already configured:

```bash
aws configure
```

Enter your AWS Access Key ID, Secret Access Key, default region (e.g., us-east-1), and output format (json).

### 4. Set Up Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit the file with your specific settings
nano .env  # or use your preferred editor
```

Update the following key settings in your `.env` file:
- `AWS_REGION`: Your AWS region
- `IOT_ENDPOINT`: Your AWS IoT endpoint (found in AWS IoT Core console)
- `DEVICE_ID`: A unique identifier for your IoT device

### 5. Deploy AWS Infrastructure with Terraform

```bash
cd terraform

# Initialize Terraform with remote state (uncomment backend config in main.tf first)
terraform init

# Plan the infrastructure changes
terraform plan -var-file=production.tfvars -out=tfplan

# Deploy the infrastructure
terraform apply -auto-approve tfplan
```

After deployment, Terraform will output important values:
- `iot_thing_name`: The name of the created IoT thing
- `iot_endpoint`: The IoT Core endpoint for publishing messages
- `dynamodb_table_name`: The name of the DynamoDB table storing sensor data

### 6. Store IoT Device Credentials

For production use, store the IoT credentials in AWS Secrets Manager:

```bash
# Get the certificate and private key paths from Terraform output
CERT_PATH=$(terraform output -raw certificate_pem_path)
KEY_PATH=$(terraform output -raw private_key_path)

# Create a secret in AWS Secrets Manager
aws secretsmanager create-secret \
  --name ems/iot_device_credentials \
  --secret-string "{\"certificate_pem\":\"$(cat $CERT_PATH)\",\"private_key\":\"$(cat $KEY_PATH)\"}"
```

### 7. Run the IoT Data Simulator

```bash
# Navigate back to project root
cd ..

# Start the simulator (ensure your .env file is properly configured)
python simulate_iot_data.py
```

The simulator will connect to AWS IoT Core using the credentials and start publishing simulated sensor data to various topics (`ems/building`, `ems/hvac`, etc.).

### 8. Launch the Dashboard

#### Option A: Running locally with Streamlit
```bash
cd app
streamlit run app.py
```

#### Option B: Running as a Docker container
```bash
cd app
docker build -t ems-dashboard .
docker run -p 8501:8501 --env-file ../.env ems-dashboard
```

Access the dashboard at http://localhost:8501 with these default credentials:
- Username: admin
- Password: admin

### 9. Monitoring and Maintenance

- View your data in the Streamlit dashboard
- Check AWS CloudWatch for IoT rule errors
- Inspect the DynamoDB table for stored data
- Monitor AWS IoT Core for device connectivity

### 10. Clean Up Resources (Optional)

When you're done, you can clean up all created AWS resources:

```bash
cd terraform
terraform destroy -var-file=production.tfvars
```

## Architecture Diagram

```
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│               │      │  AWS IoT Core │      │               │
│  IoT Devices  │─────▶│  (Message     │─────▶│  IoT Rule     │
│ (Simulator)   │      │   Broker)     │      │               │
└───────────────┘      └───────────────┘      └────────┬──────┘
                                                       │
                                                       ▼
┌───────────────┐                          ┌───────────────────┐
│               │                          │                   │
│  Streamlit    │◀─────────────────────────│  DynamoDB Table   │
│  Dashboard    │                          │                   │
└───────────────┘                          └───────────────────┘
```

## Security Considerations

- All database data is encrypted at rest with AWS-managed keys
- The Streamlit dashboard uses password authentication
- Docker container runs as non-root user
- Terraform state is encrypted in S3 with remote state locking
- IoT device credentials are securely stored in AWS Secrets Manager
- Downloads are verified with SHA256 checksums

## Troubleshooting

See the [Troubleshooting Guide](docs/troubleshooting.md) for common issues and solutions.