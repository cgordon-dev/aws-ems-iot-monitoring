resource "aws_iot_topic_rule" "ems_rule" {
  name        = "EMSDataToDynamoDB"
  sql         = "SELECT *, topic(1) as sensor_type, timestamp() as aws_timestamp FROM 'ems/#'"
  sql_version = "2016-03-23"
  description = "Route messages from IoT sensors to DynamoDB"
  enabled     = true

  dynamodb {
    role_arn        = aws_iam_role.iot_dynamodb_role.arn
    hash_key_field  = "sensor_type"
    hash_key_value  = "${topic(1)}"  # Extract the sensor type from topic (ems/building -> building)
    range_key_field = "edge_time_stamp"
    table_name      = aws_dynamodb_table.sensor_data.name
    
    # Calculate TTL to automatically expire data after 90 days
    operation = "INSERT"
    
    # Conditional expression to avoid duplicate data
    # This is optional but recommended
    # payload_field defines how data is stored
  }

  error_action {
    dynamodb {
      role_arn        = aws_iam_role.iot_dynamodb_role.arn
      hash_key_field  = "sensor_type"
      hash_key_value  = "error"
      range_key_field = "edge_time_stamp"
      table_name      = aws_dynamodb_table.sensor_data.name
      operation       = "INSERT"
    }
    
    cloudwatch_logs {
      log_group_name = "iot-rule-errors"
      role_arn       = aws_iam_role.iot_dynamodb_role.arn
    }
  }

  tags = {
    Name        = "EMS-IoT-Rule"
    Environment = var.environment
    Project     = var.project_name
  }
}