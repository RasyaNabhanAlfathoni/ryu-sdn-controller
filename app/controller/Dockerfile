FROM python:3.9-slim

WORKDIR /opt/sdn-controller

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install setuptools==20.3.4

# install ryu controller
RUN git clone https://github.com/faucetsdn/ryu.git . \
    && pip install .

# install dependency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# logs wsgi ke docker logs
ENV PYTHONUNBUFFERED=1

# copy isi file app controller
COPY . .
COPY entrypoint.sh .

#RUN mkdir -p /opt/prometheus \
#    && cp /opt/sdn-controller/snmp_targets.json /opt/prometheus/ \
#    && cp /opt/sdn-controller/server_targets.json /opt/prometheus/ \
#    && cp /opt/sdn-controller/snmp.yml /opt/prometheus/

RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
