variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "iot_thing_name" {
  description = "Name of the AWS IoT Thing"
  type        = string
  default     = "ems-monitoring-device"
}

variable "iot_policy_name" {
  description = "Name of the AWS IoT Policy"
  type        = string
  default     = "ems_iot_policy"
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table to store sensor data"
  type        = string
  default     = "SensorData"
}