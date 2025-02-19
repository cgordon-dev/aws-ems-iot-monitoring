###############################
# AWS IoT Core Resources
###############################

resource "aws_iot_thing" "ems_device" {
  name = var.iot_thing_name
}

resource "aws_iot_certificate" "ems_certificate" {
  active = true
}

resource "aws_iot_policy" "ems_policy" {
  name   = var.iot_policy_name
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iot:Publish",
        "iot:Receive",
        "iot:Connect",
        "iot:Subscribe"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iot_policy_attachment" "ems_policy_attachment" {
  policy = aws_iot_policy.ems_policy.name
  target = aws_iot_certificate.ems_certificate.arn
}

resource "aws_iot_thing_principal_attachment" "ems_thing_attachment" {
  thing_name = aws_iot_thing.ems_device.name
  principal  = aws_iot_certificate.ems_certificate.arn
}

data "aws_iot_endpoint" "iot_endpoint" {
  endpoint_type = "iot:Data-ATS"
}