terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Grupo de seguridad : permite Streamlit
resource "aws_security_group" "bot_sg" {
  name        = "bot-horarios-sg"
  description = "Security Group that allows ssh and streamlit"

  # ssh 
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  #streamlit abierto para pruebas
  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Salida a internet
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "bot_horarios" {
  ami                    = "ami-0fa3fe0fa7920f68e"
  instance_type          = "t3.micro"
  key_name               = "EduSched" 
  vpc_security_group_ids = [aws_security_group.bot_sg.id]

  root_block_device {
    volume_size = 20
  }

  tags = {
    Name = "bot-horarios"
  }
}

output "instance_ip" {
  value = aws_instance.bot_horarios.public_ip
}
