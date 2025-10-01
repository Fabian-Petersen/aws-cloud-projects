# % create a key using the cli
# % ssh-keygen -t ed25519 -f <PROJECT_NAME>_sshkey.pem
# % dont need to add a passphrase
# % run command ssh -i uwc-booking-app_sshkey.pem ubuntu@<EC2_PUBLIC_IP> to ssh into ec2 instance.

resource "aws_key_pair" "SSH_key" {
  key_name   = var.key_name
  public_key = file("./${var.project_name}_sshkey.pem.pub")

  tags = {
    Name = "ec2_instance_key_pair"
  }
}

