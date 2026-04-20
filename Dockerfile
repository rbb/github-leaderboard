# Dockerfile (Inside the repo)
FROM python:3.12-slim

# Install system dependencies
# openssh-client is required for the `scp` command at the end of your pipeline
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the entire project
COPY . .

# Install the project using pyproject.toml 
# (This installs the package and its dependencies)
RUN pip install --no-cache-dir .

# Optional: Ensure SSH directory exists with correct permissions
RUN mkdir -p -m 0700 /root/.ssh
