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
}