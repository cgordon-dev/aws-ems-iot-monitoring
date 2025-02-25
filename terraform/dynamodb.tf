resource "aws_dynamodb_table" "sensor_data" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sensor_type"      # Partition key: sensor type (e.g., building, hvac, etc.)
  range_key    = "edge_time_stamp"  # Sort key: timestamp

  attribute {
    name = "sensor_type"
    type = "S"
  }

  attribute {
    name = "edge_time_stamp"
    type = "S"
  }

  attribute {
    name = "device_id"
    type = "S"
  }

  # Enable point-in-time recovery for production workloads
  point_in_time_recovery {
    enabled = true
  }

  # Add GSI for querying by device_id
  global_secondary_index {
    name               = "DeviceIdIndex"
    hash_key           = "device_id"
    range_key          = "edge_time_stamp"
    write_capacity     = 0
    read_capacity      = 0
    projection_type    = "ALL"
  }

  # Enable TTL for data retention policy
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Enable server-side encryption
  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "EMS-Sensor-Data"
    Environment = var.environment
    Project     = var.project_name
  }
}