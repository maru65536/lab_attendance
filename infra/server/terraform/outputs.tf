# アウトプット設定
output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.lab_app_server.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_eip.lab_app_eip.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.lab_app_server.public_dns
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ${var.ssh_private_key_path} ubuntu@${aws_eip.lab_app_eip.public_ip}"
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.lab_app_sg.id
}

output "elastic_ip" {
  description = "Elastic IP address"
  value       = aws_eip.lab_app_eip.public_ip
}

output "domain_name" {
  description = "Configured domain name"
  value       = var.domain_name
}
