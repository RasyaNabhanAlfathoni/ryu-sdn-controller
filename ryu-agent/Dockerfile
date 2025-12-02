FROM python:3.9-slim

WORKDIR /ryu-agent

# Install system dependencies untuk agent operations
RUN apt-get update && apt-get install -y \
    net-tools \
    sudo \
    iproute2 \
    iputils-ping \
    curl \
    ufw \
    firewalld \
    nmap \
    traceroute \
    dnsutils \
    lldpd \
    util-linux \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua file agent
COPY . .

# Create directory untuk lldpd socket
RUN mkdir -p /var/run/lldpd

# Expose port untuk agent API (informational saja)
EXPOSE 8080

# Default command
CMD ["python3", "agent_register.py", "--verbose"]