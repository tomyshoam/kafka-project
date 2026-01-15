data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-*-amd64-server-*"]
  }
}

locals {
  tags = {
    Project = var.project_name
    Owner   = "tosh"
  }
}

# -----------------------
# VPC + networking
# -----------------------
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = merge(local.tags, { Name = "${var.project_name}-vpc" })
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.tags, { Name = "${var.project_name}-igw" })
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.azs[0]
  map_public_ip_on_launch = true
  tags                    = merge(local.tags, { Name = "${var.project_name}-public" })
}

resource "aws_subnet" "private" {
  for_each                = toset(var.private_subnet_cidrs)
  vpc_id                  = aws_vpc.this.id
  cidr_block              = each.value
  availability_zone       = var.azs[index(var.private_subnet_cidrs, each.value)]
  map_public_ip_on_launch = false
  tags                    = merge(local.tags, { Name = "${var.project_name}-private-${each.value}" })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.tags, { Name = "${var.project_name}-rt-public" })
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# NAT for private subnets outbound internet (GitHub clone, apt, Docker pulls, SSM traffic)
resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = merge(local.tags, { Name = "${var.project_name}-nat-eip" })
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id
  depends_on    = [aws_internet_gateway.igw]
  tags          = merge(local.tags, { Name = "${var.project_name}-nat" })
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.tags, { Name = "${var.project_name}-rt-private" })
}

resource "aws_route" "private_to_nat" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat.id
}

resource "aws_route_table_association" "private_assoc" {
  for_each       = aws_subnet.private
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private.id
}

# -----------------------
# Security Groups
# -----------------------
resource "aws_security_group" "app_sg" {
  name        = "${var.project_name}-app-sg"
  description = "App server SG"
  vpc_id      = aws_vpc.this.id

  # UI access
  ingress {
    description = "Web UI"
    from_port   = 9000
    to_port     = 9000
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  # Optional SSH fallback (SSM is preferred)
  ingress {
    description = "SSH to app (optional)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${var.project_name}-app-sg" })
}

resource "aws_security_group" "kafka_sg" {
  name        = "${var.project_name}-kafka-sg"
  description = "Kafka SG - only from app"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "Kafka from app"
    from_port       = 9092
    to_port         = 9092
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${var.project_name}-kafka-sg" })
}

resource "aws_security_group" "mongo_sg" {
  name        = "${var.project_name}-mongo-sg"
  description = "Mongo SG - only from app"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "MongoDB from app"
    from_port       = 27017
    to_port         = 27017
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${var.project_name}-mongo-sg" })
}

# -----------------------
# IAM for SSM
# -----------------------
resource "aws_iam_role" "ssm_role" {
  name               = "${var.project_name}-ssm-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ssm_profile" {
  name = "${var.project_name}-ssm-profile"
  role = aws_iam_role.ssm_role.name
}

# -----------------------
# User data templates
# -----------------------
locals {
  app_user_data = templatefile("${path.module}/user_data/app.sh", {
    repo_url         = var.repo_url
    kafka_private_ip = aws_instance.kafka.private_ip
    mongo_private_ip = aws_instance.mongo.private_ip
  })

  kafka_user_data = templatefile("${path.module}/user_data/kafka.sh", {
    repo_url = var.repo_url
  })

  mongo_user_data = templatefile("${path.module}/user_data/mongo.sh", {
    repo_url = var.repo_url
  })
}

# -----------------------
# EC2 instances
# -----------------------
resource "aws_instance" "app" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_app
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.app_sg.id]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.ssm_profile.name
  user_data                   = local.app_user_data

  key_name = var.ssh_key_name != "" ? var.ssh_key_name : null

  tags = merge(local.tags, { Name = "${var.project_name}-app" })
}

resource "aws_instance" "kafka" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type_kafka
  subnet_id              = values(aws_subnet.private)[0].id
  vpc_security_group_ids = [aws_security_group.kafka_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ssm_profile.name
  user_data              = local.kafka_user_data

  tags = merge(local.tags, { Name = "${var.project_name}-kafka" })
}

resource "aws_instance" "mongo" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type_mongo
  subnet_id              = values(aws_subnet.private)[1].id
  vpc_security_group_ids = [aws_security_group.mongo_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ssm_profile.name
  user_data              = local.mongo_user_data

  tags = merge(local.tags, { Name = "${var.project_name}-mongo" })
}
