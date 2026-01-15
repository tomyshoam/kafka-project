variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "project_name" {
  type    = string
  default = "kafka-project"
}

variable "vpc_cidr" {
  type    = string
  default = "10.50.0.0/16"
}

variable "public_subnet_cidr" {
  type    = string
  default = "10.50.0.0/24"
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.50.10.0/24", "10.50.11.0/24"]
}

variable "azs" {
  type = list(string)
  # update to match your region’s AZ names if needed
  default = ["eu-central-1a", "eu-central-1b"]
}

variable "my_ip_cidr" {
  description = "Your public IP in CIDR form for SSH to app (optional). Example: 1.2.3.4/32"
  type        = string
}

variable "ssh_key_name" {
  description = "Optional: EC2 key pair name (only for app SSH fallback). Can be blank if you rely on SSM only."
  type        = string
  default     = ""
}

variable "repo_url" {
  description = "Git repo URL to clone"
  type        = string
  default     = "https://github.com/tomyshoam/pmk-project.git"
}

variable "instance_type_app" {
  type    = string
  default = "t3.small"
}

variable "instance_type_kafka" {
  type    = string
  default = "t3.small"
}

variable "instance_type_mongo" {
  type    = string
  default = "t3.small"
}
