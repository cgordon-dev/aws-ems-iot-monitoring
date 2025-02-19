# AWS EMS IoT Monitoring System

This repository provides a complete production-ready solution for an Energy Management System (EMS) using AWS services. The solution includes:

- **AWS IoT Core & Data Pipeline:**  
  Provisioned with Terraform, it creates:
  - A unified IoT Thing with certificate and policy.
  - A DynamoDB table for sensor data.
  - An IoT Rule that routes messages (published on topics such as `ems/building`, `ems/hvac`, etc.) to DynamoDB.

- **Simulated IoT Data Producer:**  
  A Python script (`simulate_iot_data.py`) that simulates sensor data and publishes messages to AWS IoT Core using the AWS IoT Device SDK. It retrieves certificate credentials securely from AWS Secrets Manager.

- **Streamlit Dashboard:**  
  A dockerized dashboard (in the `app` folder) that queries DynamoDB using Boto3 and displays interactive visualizations of the sensor data.

- **CI/CD Pipeline:**  
  A GitHub Actions workflow (`.github/workflows/ci-cd.yml`) that runs Terraform to provision infrastructure, builds the Docker image for the dashboard, and pushes it to Amazon ECR.

- **Local Setup Script:**  
  `setup_tools.sh` installs required tools (AWS CLI, Terraform, Docker, Git, Python 3.9+).

## Prerequisites

- An AWS account.
- AWS CLI configured with appropriate credentials.
- Terraform, Docker, Git, and Python 3.9+ installed locally.
- GitHub repository secrets:
  - `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (or use an IAM Role).
  - `ECR_REPO_URI` – Amazon ECR repository URI.
  - (Optional) `AWS_REGION` if different from the default.

## Deployment Steps

1. **Local Setup:**  
   Run the provided `setup_tools.sh` to install required local tools.

2. **Provision Infrastructure:**  
   In the `terraform` directory, run:
   ```bash
   terraform init
   terraform plan -out=tfplan
   terraform apply -auto-approve tfplan