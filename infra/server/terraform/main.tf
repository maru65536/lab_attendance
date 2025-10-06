terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

locals {
  backup_bucket_arn     = "arn:aws:s3:::${var.backup_bucket_name}"
  backup_bucket_objects = "${local.backup_bucket_arn}/*"
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lab_app_role" {
  name               = "lab-attendance-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

data "aws_iam_policy_document" "lab_app_s3" {
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      local.backup_bucket_arn,
      local.backup_bucket_objects
    ]
  }
}

resource "aws_iam_role_policy" "lab_app_s3" {
  name   = "lab-attendance-s3-backup"
  role   = aws_iam_role.lab_app_role.id
  policy = data.aws_iam_policy_document.lab_app_s3.json
}

resource "aws_iam_instance_profile" "lab_app_profile" {
  name = "lab-attendance-instance-profile"
  role = aws_iam_role.lab_app_role.name
}

# VPC (デフォルトVPCを使用)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# 最新のUbuntu 24.04 LTS AMIを取得
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# キーペア（既存のものを使用、または新規作成）
resource "aws_key_pair" "lab_app_key" {
  key_name   = var.ssh_key_name
  public_key = file(pathexpand(var.ssh_public_key_path))
}

# セキュリティグループ
resource "aws_security_group" "lab_app_sg" {
  name        = "lab-attendance-app-sg"
  description = "Security group for lab attendance app"
  vpc_id      = data.aws_vpc.default.id

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Next.js dev port（開発時のみ）
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  # FastAPI port（開発時のみ）
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  # Outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lab-attendance-app-sg"
  }
}

# EC2インスタンス
resource "aws_instance" "lab_app_server" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.lab_app_key.key_name
  vpc_security_group_ids      = [aws_security_group.lab_app_sg.id]
  subnet_id                   = data.aws_subnets.default.ids[0]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.lab_app_profile.name

  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -euo pipefail

    export DEBIAN_FRONTEND=noninteractive

    apt-get update -y
    apt-get upgrade -y

    # Install base packages
    apt-get install -y build-essential curl git unzip sqlite3 python3 python3-venv python3-pip

    # Install Node.js 20 LTS
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs

    # Install nginx
    apt-get install -y nginx
    systemctl enable nginx
    systemctl start nginx

    # Install AWS CLI for backups
    apt-get install -y awscli

    # Prepare application directories
    mkdir -p /home/ubuntu/lab_attendance/backend
    mkdir -p /home/ubuntu/lab_attendance/frontend
    chown -R ubuntu:ubuntu /home/ubuntu/lab_attendance

    mkdir -p /var/log/lab-app
    chown ubuntu:ubuntu /var/log/lab-app

    # Install AWS CLI for backups
    apt-get install -y awscli

    # Enable UFW if desired (disabled by default)
  EOF
  )

  tags = {
    Name = "lab-attendance-app-server"
  }

  # ボリューム設定（t2.nanoのデフォルトは8GB、コスト削減のため最小サイズ）
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 8
    encrypted             = true
    delete_on_termination = true # インスタンス削除時にボリュームも削除してコスト削減
  }
}

# Elastic IP（固定IPアドレス）
resource "aws_eip" "lab_app_eip" {
  instance = aws_instance.lab_app_server.id
  domain   = "vpc"

  tags = {
    Name = "lab-attendance-app-eip"
  }
}
