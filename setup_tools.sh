#!/bin/bash
# setup_tools.sh
# This script installs AWS CLI v2, Terraform, Docker, Git, and Python 3.9+ on macOS or Ubuntu systems.

set -e

# Parse command line arguments
INTERACTIVE=true

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --non-interactive) INTERACTIVE=false ;;
        -h|--help) 
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --non-interactive    Run in non-interactive mode (no prompts)"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Setup logging
LOG_DIR="./logs"
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
fi
LOG_FILE="$LOG_DIR/setup_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "Setup started at $(date)"
echo "Logging to $LOG_FILE"

# Function to check SHA256 checksum of a downloaded file
check_sha256() {
    local file=$1
    local expected_checksum=$2
    
    if [ -z "$expected_checksum" ]; then
        echo "Warning: No checksum provided for $file, skipping verification"
        return 0
    fi
    
    if command -v sha256sum &> /dev/null; then
        calculated_checksum=$(sha256sum "$file" | awk '{ print $1 }')
    elif command -v shasum &> /dev/null; then
        calculated_checksum=$(shasum -a 256 "$file" | awk '{ print $1 }')
    else
        echo "Warning: No checksum tool available, skipping verification"
        return 0
    fi
    
    if [ "$calculated_checksum" != "$expected_checksum" ]; then
        echo "Error: Checksum verification failed for $file"
        echo "Expected: $expected_checksum"
        echo "Got:      $calculated_checksum"
        return 1
    fi
    
    echo "Checksum verification passed for $file"
    return 0
}

echo "Starting local tools installation..."

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
  PLATFORM="macos"
  echo "Detected macOS system"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  PLATFORM="linux"
  echo "Detected Linux system"
  if [ -f /etc/lsb-release ]; then
    . /etc/lsb-release
    if [ "$DISTRIB_ID" == "Ubuntu" ]; then
      echo "Confirmed Ubuntu system"
      PLATFORM="ubuntu"
    fi
  fi
else
  echo "Unsupported operating system: $OSTYPE"
  exit 1
fi

##############################
# Install Git
##############################
if ! command -v git &>/dev/null; then
  echo "Git not found. Installing Git..."
  if [ "$PLATFORM" == "macos" ]; then
    # Check if Homebrew is installed
    if ! command -v brew &>/dev/null; then
      echo "Homebrew not found. Installing Homebrew..."
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    brew install git
  elif [ "$PLATFORM" == "ubuntu" ]; then
    sudo apt-get update -y
    sudo apt-get install -y git
  fi
else
  echo "Git is already installed."
fi

##############################
# Install Python 3.9+
##############################
if ! command -v python3 &>/dev/null; then
  echo "Python 3 not found. Installing Python..."
  if [ "$PLATFORM" == "macos" ]; then
    brew install python@3.9
  elif [ "$PLATFORM" == "ubuntu" ]; then
    sudo apt-get install -y python3.9 python3.9-venv python3.9-dev
  fi
else
  echo "Python 3 is already installed."
  python3 --version
fi

##############################
# Install AWS CLI v2
##############################
if ! command -v aws &>/dev/null; then
  echo "AWS CLI not found. Installing AWS CLI v2..."
  if [ "$PLATFORM" == "macos" ]; then
    # AWS CLI v2 for macOS with SHA256 verification
    # Note: Checksum should be periodically updated
    AWS_PKG="AWSCLIV2.pkg"
    # This is an example checksum - you should verify the actual current one
    AWS_CHECKSUM="2bf0f6e33f24f9c8d7ec3bc64587446facc5d43b156387803d357be63a4da3d8"
    
    curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "$AWS_PKG"
    check_sha256 "$AWS_PKG" "$AWS_CHECKSUM" || { echo "AWS CLI download failed verification"; exit 1; }
    sudo installer -pkg "$AWS_PKG" -target /
    rm "$AWS_PKG"
  elif [ "$PLATFORM" == "ubuntu" ]; then
    # AWS CLI v2 for Linux with SHA256 verification
    AWS_ZIP="awscliv2.zip"
    # This is an example checksum - you should verify the actual current one
    AWS_CHECKSUM="bef2d70cb743c63868ce9bdfeb4c0455fbd1199fe0f32f1d991f882b23f41761"
    
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "$AWS_ZIP"
    check_sha256 "$AWS_ZIP" "$AWS_CHECKSUM" || { echo "AWS CLI download failed verification"; exit 1; }
    unzip "$AWS_ZIP"
    sudo ./aws/install
    rm -rf aws "$AWS_ZIP"
  fi
else
  echo "AWS CLI is already installed."
  aws --version
fi

##############################
# Install Terraform
##############################
if ! command -v terraform &>/dev/null; then
  echo "Terraform not found. Installing Terraform..."
  TERRAFORM_VERSION="1.3.7"
  if [ "$PLATFORM" == "macos" ]; then
    brew tap hashicorp/tap
    brew install hashicorp/tap/terraform
  elif [ "$PLATFORM" == "ubuntu" ]; then
    TF_ZIP="terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
    # Terraform checksum - should be verified for each version
    TF_CHECKSUM="fe495aa929c8c1a8d5d0b1b5380ac5e10c5fd3aba8ced37ce399162e9b5790f5"
    
    wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/${TF_ZIP}
    check_sha256 "$TF_ZIP" "$TF_CHECKSUM" || { echo "Terraform download failed verification"; exit 1; }
    unzip ${TF_ZIP}
    sudo mv terraform /usr/local/bin/
    rm ${TF_ZIP}
  fi
else
  echo "Terraform is already installed."
  terraform --version
fi

##############################
# Install Docker
##############################
if ! command -v docker &>/dev/null; then
  echo "Docker not found. Installing Docker..."
  if [ "$PLATFORM" == "macos" ]; then
    echo "Please install Docker Desktop for Mac from https://www.docker.com/products/docker-desktop"
    echo "Or install via brew: brew install --cask docker"
  elif [ "$PLATFORM" == "ubuntu" ]; then
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    echo "Adding current user to docker group..."
    sudo usermod -aG docker $USER
  fi
else
  echo "Docker is already installed."
  docker --version
fi

##############################
# Install Python dependencies
##############################
echo "Installing Python dependencies..."
pip3 install -U boto3 awsiotsdk streamlit pandas altair streamlit_autorefresh python-dotenv requests prometheus-client

# Set up Python virtual environment if on Linux
if [ "$PLATFORM" == "ubuntu" ] || [ "$PLATFORM" == "linux" ]; then
  if [ ! -d "venv" ]; then
    echo "Setting up Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    python3 -m pip install --upgrade pip
    if [ -f "app/requirements.txt" ]; then
      python3 -m pip install -r app/requirements.txt
    fi
    echo "Python virtual environment created at './venv'"
    echo "Activate with 'source venv/bin/activate'"
  fi
fi

# Check AWS credentials
echo "Checking AWS credentials..."
if command -v aws &>/dev/null; then
  if $INTERACTIVE; then
    aws sts get-caller-identity || {
      echo "AWS credentials not configured."
      read -p "Would you like to configure AWS credentials now? [y/N] " -n 1 -r
      echo
      if [[ $REPLY =~ ^[Yy]$ ]]; then
        aws configure
      else
        echo "Please run 'aws configure' later to set up your credentials."
      fi
    }
  else
    aws sts get-caller-identity || echo "AWS credentials not configured. Please run 'aws configure' to set up your credentials."
  fi
fi

echo "Installation complete at $(date)."
echo "-------------------------------------"
echo "Next steps:"
echo "1. Configure AWS credentials (if not done): aws configure"
echo "2. Deploy infrastructure: cd terraform && terraform init && terraform apply"
echo "3. Run IoT simulator: python3 simulate_iot_data.py"
echo "4. Launch dashboard: cd app && streamlit run app.py"
echo "-------------------------------------"

if [ "$PLATFORM" == "ubuntu" ]; then
  echo "NOTE: Please restart your terminal session to ensure that group membership changes (e.g., Docker) take effect."
fi