resource "aws_vpc" "main" {
  cidr_block       = "10.0.0.0/16"
  instance_tenancy = "default"

  tags = {
    Name = "main"
  }
}

# $ Subnets in Availability Zone A
resource "aws_subnet" "public_subnet_az_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.0.0/24"
  availability_zone       = var.availability_zone_a
  map_public_ip_on_launch = true

  tags = {
    Name = "public_subnet_az_a"
  }
}

resource "aws_subnet" "private_subnet_az_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = var.availability_zone_a

  tags = {
    Name = "private_subnet_az_a"
  }
}

# $ Subnets in Availability Zone B
resource "aws_subnet" "public_subnet_az_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = var.availability_zone_b
  map_public_ip_on_launch = true

  tags = {
    Name = "public_subnet_az_b"
  }
}

resource "aws_subnet" "private_subnet_az_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = var.availability_zone_b

  tags = {
    Name = "private_subnet_az_b"
  }
}

# $ Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name = "main_vpc_igw"
  }
}

# $ Route Table for Public Subnets
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "public_route_table"
  }
}

resource "aws_route" "public_route" {
  route_table_id         = aws_route_table.public_rt.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# $ Associate Public Subnets with Route Table
resource "aws_route_table_association" "public_subnet_az_a" {
  subnet_id      = aws_subnet.public_subnet_az_a.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "public_subnet_az_b" {
  subnet_id      = aws_subnet.public_subnet_az_b.id
  route_table_id = aws_route_table.public_rt.id
}

# $ Security Group for Public Subnets
resource "aws_security_group" "public_sg" {
  vpc_id      = aws_vpc.main.id
  name        = "public_sg"
  description = "Security group for public subnets"
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    # add your own IP address here to restrict access
    # cidr_blocks = ["YOUR_IP_ADDRESS/32"]
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "public_sg"
  }
}   