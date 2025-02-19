output "iot_endpoint" {
  description = "The AWS IoT Data (ATS) endpoint for devices"
  value       = data.aws_iot_endpoint.iot_endpoint.endpoint_address
}

output "certificate_pem" {
  description = "The IoT Certificate PEM"
  value       = aws_iot_certificate.ems_certificate.certificate_pem
  sensitive   = true
}

output "private_key" {
  description = "The IoT Certificate Private Key"
  value       = aws_iot_certificate.ems_certificate.private_key
  sensitive   = true
}

output "certificate_arn" {
  description = "The IoT Certificate ARN"
  value       = aws_iot_certificate.ems_certificate.arn
  sensitive   = true
}