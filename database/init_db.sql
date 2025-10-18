CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    ip_address VARCHAR(50),
    mac_address VARCHAR(50),
    type VARCHAR(50), -- ini isinya mikrotik / server / cisco / tplink
    status VARCHAR(20),
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE server_metrics (
    id SERIAL PRIMARY KEY,
    device_id INT REFERENCES devices(id),
    cpu_usage FLOAT,
    memory_usage FLOAT,
    storage_usage FLOAT,
    io_read BIGINT,
    io_write BIGINT,
    net_rx BIGINT,
    net_tx BIGINT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    device_id INT REFERENCES devices(id),
    log_text TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
