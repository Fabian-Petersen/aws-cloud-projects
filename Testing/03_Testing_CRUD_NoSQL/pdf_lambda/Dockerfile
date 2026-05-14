#$ $ Build and push to ECR
    # Retrieve an authentication token and authenticate your Docker client to your registry. Use the AWS CLI:
    #% aws ecr get-login-password --region af-south-1 | docker login --username AWS --password-stdin 157489943321.dkr.ecr.af-south-1.amazonaws.com
    # Note: If you receive an error using the AWS CLI, make sure that you have the latest version of the AWS CLI and Docker installed.
    # Build your Docker image using the following command. For information on building a Docker file from scratch see the instructions here 
    # . You can skip this step if your image is already built:
    # % docker build -t crud-nosql-pdf-generator .
    # After the build completes, tag your image so you can push the image to this repository:
    # % docker tag crud-nosql-pdf-generator:latest 157489943321.dkr.ecr.af-south-1.amazonaws.com/crud-nosql-pdf-generator:latest
    # Run the following command to push this image to your newly created AWS repository:
    # % docker push 157489943321.dkr.ecr.af-south-1.amazonaws.com/crud-nosql-pdf-generator:latest

# % Login to ECR 
# aws ecr get-login-password --region af-south-1 | docker login --username AWS --password-stdin 157489943321.dkr.ecr.af-south-1.amazonaws.com/crud-nosql-pdf-generator

# $ Buid and run locally
# docker build -t pdf-lambda .
# docker run -p 9000:8080 pdf-lambda:v1 or docker run -p 9000:8080 -e AWS_REGION=af-south-1 pdf-lambda:v3 (if a error is received for error)
# curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations"
#  -d '{}'
# curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d @test-event.json # with a test-event file

# * Errors Received
# - The Runtime.InvalidEntrypoint error in AWS Lambda container images is most commonly caused by an architecture mismatch between your build machine and the Lambda function configuration
# Fix:
# - change the build architecture in the console or force as per below command
# - docker build --platform linux/amd64 -t my-lambda-image .
# should see response

# % Error 2: image pushed to ecr created a multiple layer image `	
# % v1
# % Image Index
# % 16 March 2026, 09:40:18 (UTC+02)
# % 211.77
# % sha256:848f8d23260bd6e3089d6ca7c8a6951a1e01eedd06e77970b7d130d8534856b9
# % Image
# % 16 March 2026, 09:40:18 (UTC+02)
# % 211.77
# % sha256:3eeb08c84ff9ed0ba4f9173de76f9f661019b61d5bb2041ed90f749f9e5269e1
# % Image
# % 16 March 2026, 09:40:18 (UTC+02)
# % 0.00
# % sha256:f2fdc155ca2be7682c484b7484c54fa8faefd733d514326176b4d62e9e4c7c1c
# % -`.
# % Received an error trying to use the image `The image manifest, config or layer media type for the # source image 157489943321.dkr.ecr.af-south-1.amazonaws.com/crud-nosql-pdf-generator@sha256:848f8d23260bd6e3089d6ca7c8a6951a1e01eedd06e77970b7d130d8534856b9 is not supported.`
# Tried the following: 
# step 1: docker buildx build --platform linux/amd64 --provenance=false -t pdf-lambda:latest .
# step 2: docker tag pdf-lambda:latest 157489943321.dkr.ecr.af-south-1.amazonaws.com/crud-nosql-pdf-generator:v3
# step 3: docker push 157489943321.dkr.ecr.af-south-1.amazonaws.com/crud-nosql-pdf-generator:v3

FROM public.ecr.aws/lambda/python:3.10

COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY pdf_service/ ${LAMBDA_TASK_ROOT}/pdf_service/

# Install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install -r requirements.txt

# module name = filename without .py, function = lambda_handler
CMD ["lambda_handler.lambda_handler"]