FROM qorzj/python:3.11-torch

WORKDIR /project

ADD requirements.txt .

# Install project dependencies with cache mount
# This keeps pip cache even if requirements.txt changes
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Create necessary directories
RUN mkdir -p logs

# Copy application files
ADD .env.staging .
ADD .env.production .
ADD .pyway.conf .
ADD config ./config
ADD shared ./shared
ADD src ./src
ADD migration ./migration
ADD openapi ./openapi
ADD main.py .
ADD Makefile .

CMD python main.py
EXPOSE 8080
