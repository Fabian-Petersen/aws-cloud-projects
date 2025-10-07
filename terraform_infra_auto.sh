#!/bin/bash

set -e

# Variables
region=af-south-1
# ENV={dev,staging,prod}

# --- Create Directories for the project ---

#$ [Step 1] - Prompt user for project name -
read -p "Enter the project name: " PROJECT_NAME

if [ -z "$PROJECT_NAME" ]; then # -z is false or (empty)
  echo "❌ Project name cannot be empty."
  exit 1
fi

#$ Check if project directory already exists
if [ -d "./projects/$PROJECT_NAME" ]; then
  echo "❌ Project $PROJECT_NAME already exists."
  exit 1
fi

mkdir -p ./projects/$PROJECT_NAME
# cd ./projects/$PROJECT_NAME || exit 1
echo "Project directory: /projects/$PROJECT_NAME created."

#$ [Step 2] - Prompt the user for cloud providers -
# use the dialog command to create a checklist for cloud providers
cmd=(dialog --separate-output --checklist "Select Cloud Providers for the project:" 22 76 16)
  options=(
    1 "aws" off
    2 "azure" off
    3 "google cloud" off
  )
# create a variable to hold the choices for the providers selected
  provider_options=$("${cmd[@]}" "${options[@]}" 2>&1 >/dev/tty)
  clear       
  
  # dialog return numbers for each choice, convert to comma-separated string
  CLOUD_PROVIDER=""
  for choice in $provider_options; do
    case $choice in
      1) PROVIDERS+="aws," ;;
      2) PROVIDERS+="azure," ;;
      3) PROVIDERS+="google," ;;
    esac
  done
# Remove trailing commas and create an array
IFS=',' read -r -a PROVIDERS_ARRAY <<< "$PROVIDERS"
echo "Selected providers: ${PROVIDERS_ARRAY[@]}"

#$ [Step 3] - Prompt user for environments they would like for the project -
cmd=(dialog --separate-output --checklist "Select Project Development Evironment:" 22 76 16)
  options=(
    1 "dev" off
    2 "staging" off
    3 "prod" off
    4 "none" off
  )

  choices=$("${cmd[@]}" "${options[@]}" 2>&1 >/dev/tty)
  clear
  echo "choices: $choices"         # debugging line       

# Convert choices to comma-separated string
  ENV_STAGES=""
  for choice in $choices; do
    case $choice in
      1) ENV_STAGES+="dev," ;;
      2) ENV_STAGES+="staging," ;;
      3) ENV_STAGES+="prod," ;;
      3) ENV_STAGES+="none," ;;
    esac
  done

# echo "stages: $ENV_STAGES"

# # Remove trailing comma and handle 'none' case
if [[ $ENV_STAGES == *"none"* ]]; then
  ENV_STAGES=""
exit 1
else
  ENV_STAGES=${ENV_STAGES%,}
    echo "[INFO] Selected stages: $ENV_STAGES"
  IFS=',' read -r -a STAGES_ARRAY <<< "$ENV_STAGES" # convert to array and remove trailing comma
  mkdir -p ./projects/${PROJECT_NAME}/env
  for stage in "${STAGES_ARRAY[@]}"; do
    echo "➡ Creating $stage directory..."
    mkdir -p ./projects/${PROJECT_NAME}/env/$stage
    touch ./projects/${PROJECT_NAME}/env/$stage/variables.tfvars main.tf variables.tf
  done
   echo "[INFO] Environment files created in /env/"
fi

#$ [Step 4] - Create project directory with env subdirectory and stage subdirectories -

#$ [Step 5] - Create variables.tf & providers.tf files in the root directory -
#$ [Step 6] - Create backend.tf and terraform.tfvars files in each stage subdirectory -
#$ [Step 7] - Create .gitignore file in the root directory -

# $ [Step 3] --- Create project directory ---

# #$ Create the providers.tf file in the root env directory & add basic content
cd ./projects/$PROJECT_NAME
touch main.tf variables.tf providers.tf
cat <<EOF > ./projects/${PROJECT_NAME}/providers.tf
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
EOF

# Append providers dynamically
for PROV in "${PROVIDERS_ARRAY[@]}"; do 
  cat <<EOP >> ./projects/${PROJECT_NAME}/providers.tf
provider "${PROV}" {
  alias  = "$ENV"
  region = "$region"
}

EOP
done

# #$ Create the backend files for each environment & add basic content
for ENV in "${STAGES[@]}"; do
  cat <<EOF > ./projects/$PROJECT_NAME/env/$ENV/backend.tf
terraform {
  backend "s3" {
    bucket         = "terraform-state-fabian-v3"
    key            = "${PROJECT_NAME}/${ENV}-terraform.tfstate"
    region         = "${region}"
    use_lockfile   = true
    encrypt        = true
    profile        = "fabian-user2"
    dynamodb_table = "terraform-locks-fabian-v3"
  }
}
EOF
done

# --- .gitignore ---
cat <<EOF > ./projects/$PROJECT_NAME/.gitignore
# Terraform
.terraform/
*.tfstate
*.tfstate.*
.crash
*.backup
*.log
.terraform.lock.hcl
EOF

echo "[INFO] ✅ .gitignore created."

# # --- Init Git ---
# # cd $PROJECT_NAME
# # git init
# # git add .
# # git commit -m "Initial commit - Terraform project structure for $PROJECT_NAME"
# # echo "[INFO] ✅ Git repository initialized."

echo "🚀 Terraform project structure for $PROJECT_NAME successfully created."