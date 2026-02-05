#$ $ Build and push to ECR
# docker build -t pdf-generator .
# docker tag pdf-generator:latest <repo_url>:latest
# docker push <repo_url>:latest

# $ Buid and run locally
# docker build -t pdf-lambda .
# docker run -p 9000:8080 pdf-lambda
# curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
#  -d '{}'

FROM public.ecr.aws/lambda/python:3.10

COPY app/ ${LAMBDA_TASK_ROOT}

RUN pip install reportlab

CMD ["lambda_handler.handler"]