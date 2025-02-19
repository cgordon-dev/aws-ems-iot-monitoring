#!/bin/bash
# setup_tools.sh
# This script installs AWS CLI v2, Terraform, Docker, Git, and Python 3.9+ on an Ubuntu system.

set -e

echo "Starting local tools installation..."

##############################
# Update Package List
##############################
echo "Updating apt-get package list..."
sudo apt-get update -y

##############################
# Install Git
##############################
if ! command -v git &>/dev/null; then
  echo "Git not found. Installing Git..."
  sudo apt-get install -y git
else
  echo "Git is already installed."
fi

##############################
# Install Python 3.9
##############################
if ! command -v python3.9 &>/dev/null; then
  echo "Python 3.9 not found. Installing Python 3.9..."
  sudo apt-get install -y python3.9 python3.9-venv python3.9-dev
else
  echo "Python 3.9 is already installed."
fi

##############################
# Install AWS CLI v2
##############################
if ! command -v aws &>/dev/null; then
  echo "AWS CLI not found. Installing AWS CLI v2..."
  curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
  unzip awscliv2.zip
  sudo ./aws/install
  rm -rf aws awscliv2.zip
else
  echo "AWS CLI is already installed."
fi

##############################
# Install Terraform
##############################
if ! command -v terraform &>/dev/null; then
  echo "Terraform not found. Installing Terraform..."
  TERRAFORM_VERSION="1.3.7"
  wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip
  unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip
  sudo mv terraform /usr/local/bin/
  rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip
else
  echo "Terraform is already installed."
fi

##############################
# Install Docker
##############################
if ! command -v docker &>/dev/null; then
  echo "Docker not found. Installing Docker..."
  sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io
  echo "Adding current user to docker group..."
  sudo usermod -aG docker $USER
else
  echo "Docker is already installed."
fi

echo "Installation complete."
echo "NOTE: Please restart your terminal session to ensure that group membership changes (e.g., Docker) take effect."