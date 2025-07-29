terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-1"  # Tokyo region
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

# 最新のAmazon Linux 2 AMIを取得
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# キーペア（既存のものを使用、または新規作成）
resource "aws_key_pair" "lab_app_key" {
  key_name   = "lab-attendance-app-key"
  public_key = file("~/.ssh/id_ed25519.pub")  # 既存のSSH公開鍵を使用
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
    cidr_blocks = ["0.0.0.0/0"]
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
    cidr_blocks = ["0.0.0.0/0"]
  }

  # FastAPI port（開発時のみ）
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
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
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t2.micro"
  key_name              = aws_key_pair.lab_app_key.key_name
  vpc_security_group_ids = [aws_security_group.lab_app_sg.id]
  subnet_id             = data.aws_subnets.default.ids[0]

  # ユーザーデータスクリプト（初期セットアップ）
  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y
    
    # Node.js 18のインストール
    curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
    yum install -y nodejs
    
    # Python 3.9とpipのインストール
    yum install -y python3 python3-pip
    
    # nginxのインストール
    amazon-linux-extras install nginx1 -y
    
    # gitのインストール
    yum install -y git
    
    # sqlite3のインストール
    yum install -y sqlite
    
    # 作業ディレクトリの作成
    mkdir -p /var/www/lab-app
    chown ec2-user:ec2-user /var/www/lab-app
    
    # 基本的なファイアウォール設定
    systemctl enable nginx
    systemctl start nginx
    
    # ログファイルのセットアップ
    mkdir -p /var/log/lab-app
    chown ec2-user:ec2-user /var/log/lab-app
  EOF
  )

  tags = {
    Name = "lab-attendance-app-server"
  }

  # ボリューム設定（t2.nanoのデフォルトは8GB）
  root_block_device {
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
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