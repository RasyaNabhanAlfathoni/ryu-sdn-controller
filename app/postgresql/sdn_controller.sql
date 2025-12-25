-- DATABASE: sdn_controller

-- DEVICES
CREATE TABLE IF NOT EXISTS devices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(100) NOT NULL UNIQUE,

    device_type ENUM('router', 'server', 'switch', 'AP') NOT NULL,
    southbound VARCHAR(50) NOT NULL,

    status VARCHAR(20) DEFAULT 'active',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NULL,

    INDEX idx_device_id (device_id),
    INDEX idx_device_type (device_type)
);

-- SERVERS
CREATE TABLE IF NOT EXISTS servers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(100) NOT NULL UNIQUE,

    hostname VARCHAR(255) DEFAULT 'unknown',
    main_username VARCHAR(100) DEFAULT 'unknown',

    os_version VARCHAR(100) DEFAULT 'unknown',
    architecture VARCHAR(50),
    architecture_bits INT,
    processor_type VARCHAR(100),

    vendor VARCHAR(100) DEFAULT 'unknown',

    main_ip_address VARCHAR(45),
    main_mac_address VARCHAR(20) DEFAULT 'unknown',
    main_interface VARCHAR(50) DEFAULT 'unknown',

    southbound VARCHAR(50) DEFAULT 'server_api',
    status VARCHAR(20) DEFAULT 'active',
    virtualization VARCHAR(50) DEFAULT 'physical',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NULL,

    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    INDEX idx_server_device_id (device_id),
    INDEX idx_main_ip (main_ip_address)
);

-- ROUTERS
CREATE TABLE IF NOT EXISTS routers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(100) NOT NULL UNIQUE,

    username VARCHAR(100) DEFAULT 'admin',
    password VARCHAR(255),

    identity VARCHAR(255) DEFAULT 'unknown',
    os_version VARCHAR(100) DEFAULT 'unknown',

    model VARCHAR(100),
    serial_number VARCHAR(100),

    vendor VARCHAR(100) DEFAULT 'unknown',

    main_ip_address VARCHAR(45),
    main_mac_address VARCHAR(20),
    main_interface VARCHAR(50) DEFAULT 'ether1',

    southbound VARCHAR(50) DEFAULT 'routeros_api',
    status VARCHAR(20) DEFAULT 'active',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NULL,

    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    INDEX idx_router_device_id (device_id),
    INDEX idx_router_serial (serial_number)
);


-- SWITCHS
CREATE TABLE IF NOT EXISTS switchs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(100) UNIQUE NOT NULL,

    username VARCHAR(100),
    password VARCHAR(255),

    identity VARCHAR(100),
    os_version VARCHAR(100),

    model VARCHAR(100),
    serial_number VARCHAR(100),

    vendor VARCHAR(50) DEFAULT 'Cisco',

    main_ip_address VARCHAR(45),
    main_mac_address VARCHAR(20),
    main_interface VARCHAR(50),

    southbound VARCHAR(50) DEFAULT 'snmp',
    status VARCHAR(20) DEFAULT 'active',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NULL,

    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);

-- ACCESS POINTS
CREATE TABLE IF NOT EXISTS access_points (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(100) NOT NULL UNIQUE,

    username VARCHAR(100) DEFAULT 'admin',
    password VARCHAR(255),

    identity VARCHAR(255) DEFAULT 'unknown',
    os_version VARCHAR(100) DEFAULT 'unknown',

    model VARCHAR(100),
    serial_number VARCHAR(100),

    vendor VARCHAR(100) DEFAULT 'unknown',

    main_ip_address VARCHAR(45),
    main_mac_address VARCHAR(20),
    main_interface VARCHAR(50) DEFAULT 'ether1',

    southbound VARCHAR(50) DEFAULT '',
    status VARCHAR(20) DEFAULT 'active',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NULL,

    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);