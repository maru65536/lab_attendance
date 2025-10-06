# 変数定義
variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "ssh_key_name" {
  description = "Name to assign to the AWS key pair"
  type        = string
  default     = "lab-attendance-app-key"
}

variable "ssh_public_key_path" {
  description = "Path to the SSH public key that will be uploaded to AWS"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "ssh_private_key_path" {
  description = "Path to the SSH private key used for provisioning and manual access"
  type        = string
  default     = "~/.ssh/id_ed25519"
}

variable "admin_cidr_blocks" {
  description = "CIDR blocks that can access admin-only ports (SSH, 3000, 8000)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "maru65536.com"
}

variable "backup_bucket_name" {
  description = "S3 bucket used for SQLite backups"
  type        = string
  default     = "lab-attendance-backups"
}
