# Troubleshooting Guide

This document provides solutions for common issues encountered when deploying and running the AWS EMS IoT Monitoring System.

## AWS Infrastructure Issues

### Terraform Initialization Fails

**Problem**: Error when running `terraform init`.

**Solutions**:
1. Check that you have sufficient AWS permissions to create resources
2. Verify the S3 bucket for remote state exists
3. Ensure your AWS credentials are correctly configured

```bash
aws configure list
```

### IoT Device Connection Failures

**Problem**: The IoT data simulator fails to connect to AWS IoT Core.

**Solutions**:
1. Verify your IoT endpoint in the `.env` file matches your AWS IoT Core endpoint
2. Check that the certificate and private key are correctly stored
3. Ensure the IoT policy has sufficient permissions

```bash
# Verify your IoT endpoint
aws iot describe-endpoint --endpoint-type iot:Data-ATS
```

### DynamoDB Table Not Found

**Problem**: The dashboard or IoT rule can't find the DynamoDB table.

**Solutions**:
1. Check if the table was created by Terraform
2. Ensure the table name in `.env` matches the Terraform output
3. Verify IAM permissions allow access to the table

```bash
# List DynamoDB tables
aws dynamodb list-tables
```

## IoT Simulator Issues

### Missing Dependencies

**Problem**: The simulator fails due to missing Python packages.

**Solution**: Install the required packages:

```bash
pip install -r requirements.txt
```

### Certificate Permissions

**Problem**: Error regarding certificate permissions when running the simulator.

**Solution**: Check that the credentials are accessible and properly formatted:

```bash
# If using Secrets Manager
aws secretsmanager get-secret-value --secret-id ems/iot_device_credentials
```

## Dashboard Issues

### Authentication Failed

**Problem**: Unable to log in to the dashboard.

**Solutions**:
1. Check that you are using the correct username/password (default: admin/admin)
2. Verify the `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD_HASH` in `.env`
3. Reset the password by updating the SHA256 hash in the `.env` file

```bash
# Generate a new password hash (replace 'newpassword' with your desired password)
echo -n "newpassword" | shasum -a 256 | awk '{print $1}'
```

### No Data Displayed

**Problem**: Dashboard shows no data.

**Solutions**:
1. Check that the simulator is running and publishing data
2. Verify the DynamoDB table contains records
3. Ensure the dashboard and DynamoDB are in the same AWS region

```bash
# Scan the DynamoDB table for records
aws dynamodb scan --table-name sensor_data --max-items 5
```

### Docker Container Fails

**Problem**: Docker container for the dashboard fails to start.

**Solutions**:
1. Check Docker logs for errors
2. Ensure all environment variables are correctly passed to the container
3. Verify port 8501 is not in use by another process

```bash
# Check container logs
docker logs <container_id>
```

## General Troubleshooting Steps

1. **Check AWS CloudWatch Logs**:
   ```bash
   aws logs get-log-events --log-group-name /aws/iot/iot-rule-errors --log-stream-name <stream-name>
   ```

2. **Verify AWS IAM Permissions**:
   ```bash
   aws iam get-role --role-name iot_dynamodb_role
   ```

3. **Test IoT Core Connectivity**:
   ```bash
   aws iot publish --topic "test/message" --payload "{\"test\":\"Hello World\"}"
   ```

4. **Restart the Services**:
   - Restart the IoT simulator
   - Rebuild and restart the Docker container
   - Refresh the browser cache

For additional support, please file an issue in the GitHub repository with detailed error messages and the steps you've already taken to resolve the issue.