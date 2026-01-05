-- DATABASE: sdn_controller

-- DEVICES
CREATE TABLE IF NOT EXISTS devices (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(64) UNIQUE NOT NULL,

    device_type VARCHAR(32) NOT NULL,
    southbound VARCHAR(32),
    status VARCHAR(32) DEFAULT 'active',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_seen  TIMESTAMP
);

-- SERVERS
CREATE TABLE IF NOT EXISTS servers (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(64) UNIQUE NOT NULL,

    hostname VARCHAR(128),
    main_username VARCHAR(64),

    os_version VARCHAR(64),
    architecture VARCHAR(64),
    architecture_bits INTEGER,
    processor_type VARCHAR(128),

    vendor VARCHAR(64),
    serial_number VARCHAR(128),

    main_ip_address VARCHAR(64),
    main_mac_address VARCHAR(64),
    main_interface VARCHAR(64),

    southbound VARCHAR(32),
    status VARCHAR(32),

    virtualization VARCHAR(32),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_seen  TIMESTAMP,

    CONSTRAINT fk_servers_device
        FOREIGN KEY (device_id)
        REFERENCES devices(device_id)
        ON DELETE CASCADE
);

-- ROUTERS
CREATE TABLE IF NOT EXISTS routers (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(64) UNIQUE NOT NULL,

    username VARCHAR(64),
    password TEXT,

    identity VARCHAR(128),
    os_version VARCHAR(64),

    model VARCHAR(64),
    serial_number VARCHAR(128),

    vendor VARCHAR(64),

    main_ip_address VARCHAR(64),
    main_mac_address VARCHAR(64),
    main_interface VARCHAR(64),

    southbound VARCHAR(32),
    status VARCHAR(32),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_seen  TIMESTAMP,

    CONSTRAINT fk_routers_device
        FOREIGN KEY (device_id)
        REFERENCES devices(device_id)
        ON DELETE CASCADE
);


-- SWITCHS
CREATE TABLE IF NOT EXISTS switchs (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(64) UNIQUE NOT NULL,

    username VARCHAR(64),
    password TEXT,

    identity VARCHAR(128),
    os_version VARCHAR(64),

    model VARCHAR(64),
    serial_number VARCHAR(128),

    vendor VARCHAR(64),

    main_ip_address VARCHAR(64),
    main_mac_address VARCHAR(64),
    main_interface VARCHAR(64),

    southbound VARCHAR(32),
    status VARCHAR(32),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_seen  TIMESTAMP,

    CONSTRAINT fk_switchs_device
        FOREIGN KEY (device_id)
        REFERENCES devices(device_id)
        ON DELETE CASCADE
);

-- ACCESS POINTS
CREATE TABLE IF NOT EXISTS access_points (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(64) UNIQUE NOT NULL,

    username VARCHAR(64),
    password TEXT,

    identity VARCHAR(128),

    os_version VARCHAR(64),
    model VARCHAR(64),
    serial_number VARCHAR(128),

    vendor VARCHAR(64),

    main_ip_address VARCHAR(64),
    main_mac_address VARCHAR(64),
    main_interface VARCHAR(64),

    southbound VARCHAR(32),
    status VARCHAR(32),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_seen  TIMESTAMP,

    CONSTRAINT fk_access_points_device
        FOREIGN KEY (device_id)
        REFERENCES devices(device_id)
        ON DELETE CASCADE
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);

CREATE INDEX IF NOT EXISTS idx_servers_device_id ON servers(device_id);
CREATE INDEX IF NOT EXISTS idx_routers_device_id ON routers(device_id);
CREATE INDEX IF NOT EXISTS idx_switchs_device_id ON switchs(device_id);
CREATE INDEX IF NOT EXISTS idx_access_points_device_id ON access_points(device_id);