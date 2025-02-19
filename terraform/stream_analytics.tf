resource "aws_iot_topic_rule" "ems_rule" {
  name        = "EMSDataToDynamoDB"
  sql         = "SELECT * FROM 'ems/#'"
  sql_version = "2016-03-23"

  dynamodb {
    role_arn        = aws_iam_role.iot_dynamodb_role.arn
    hash_key_field  = "sensor_type"
    hash_key_value  = "${topic()}"   # The topic (e.g., ems/building) defines the sensor type
    range_key_field = "edge_time_stamp"
    table_name      = aws_dynamodb_table.sensor_data.name
    payload_field   = "data"
  }

  error_action {
    dynamodb {
      role_arn   = aws_iam_role.iot_dynamodb_role.arn
      table_name = aws_dynamodb_table.sensor_data.name
    }
  }
}