from database.db_connection import DBConnection
import json
import datetime

class DeviceRepository:

    # ============================
    # INSERT NETWORK DEVICE
    # ============================
    @staticmethod
    def insert_network_device(dev):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    INSERT INTO devices
                    (device_id, device_type, southbound, status,
                     created_at, updated_at, last_seen)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), NOW())
                """

                cursor.execute(sql, (
                    dev["device_id"],
                    dev.get("device_type"),
                    dev.get("southbound"),
                    dev.get("status", "active")
                ))

                conn.commit()
                return cursor.lastrowid

            finally:
                cursor.close()

    # ============================
    # UPDATE NETWORK DEVICE
    # ============================
    @staticmethod
    def update_network_device(device_id, data):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    UPDATE devices
                    SET device_type=%s,
                        southbound=%s,
                        status=%s,
                        last_seen=%s,
                        updated_at=NOW()
                    WHERE device_id=%s
                """

                cursor.execute(sql, (
                    data.get("device_type"),
                    data.get("southbound"),
                    data.get("status", "active"),
                    data.get("last_seen"),
                    device_id
                ))

                conn.commit()

            finally:
                cursor.close()

    # ============================
    # FIND BY SERIAL (ROUTER)
    # ============================
    @staticmethod
    def find_by_serial(serial):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                sql = """
                    SELECT 'router' AS type, r.device_id
                    FROM routers r
                    WHERE r.serial_number=%s
                """

                cursor.execute(sql, (serial,))
                return cursor.fetchone()

            finally:
                cursor.close()    
    
    # ============================
    # FIND DEVICE BY device_id
    # ============================
    @staticmethod
    def find_by_device_id(device_id):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(dictionary=True, buffered=True)
            try:
                # 1. CHECK SERVERS
                cursor.execute("""
                    SELECT 
                        s.*,
                        'server' AS device_type,
                        s.southbound,
                        s.status,
                        s.created_at AS global_created_at,
                        s.updated_at AS global_updated_at,
                        s.last_seen
                    FROM servers s
                    WHERE s.device_id = %s
                """, (device_id,))

                row = cursor.fetchone()
                cursor.fetchall()
                if row:
                    return row

                # 2. CHECK ROUTERS
                cursor.execute("""
                    SELECT 
                        r.*,
                        'router' AS device_type,
                        r.southbound,
                        r.status,
                        r.created_at AS global_created_at,
                        r.updated_at AS global_updated_at,
                        r.last_seen
                    FROM routers r
                    WHERE r.device_id = %s
                """, (device_id,))

                row = cursor.fetchone()
                cursor.fetchall()
                if row:
                    return row

                # 3. CHECK ACCESS POINTS
                cursor.execute("""
                    SELECT
                        ap.*,
                        'access_point' AS device_type,
                        ap.southbound,
                        ap.status,
                        ap.created_at AS global_created_at,
                        ap.updated_at AS global_updated_at,
                        ap.last_seen
                    FROM access_points ap
                    WHERE ap.device_id = %s
                """, (device_id,))

                row = cursor.fetchone()
                cursor.fetchall()
                return row

            finally:
                cursor.close()

    # ============================
    # INSERT SERVER
    # ============================
    @staticmethod
    def insert_server(dev):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    INSERT INTO servers
                    (device_id, hostname, main_username, os_version, architecture,
                     architecture_bits, processor_type, vendor, main_ip_address,
                     main_mac_address, main_interface, southbound, status,
                     virtualization, created_at, updated_at, last_seen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            NOW(), NOW(), NOW())
                """

                cursor.execute(sql, (
                    dev["device_id"],
                    dev.get("hostname", "unknown"),
                    dev.get("main_username", "unknown"),
                    dev.get("os_version", "unknown"),
                    dev.get("architecture"),
                    dev.get("architecture_bits"),
                    dev.get("processor_type"),
                    dev.get("vendor", "unknown"),
                    dev.get("main_ip_address"),
                    dev.get("main_mac_address", "unknown"),
                    dev.get("main_interface", "unknown"),
                    dev.get("southbound", "server_api"),
                    dev.get("status", "active"),
                    dev.get("virtualization", "physical")
                ))

                conn.commit()
                return cursor.lastrowid

            finally:
                cursor.close()

    # ============================
    # UPDATE SERVER
    # ============================
    @staticmethod
    def update_server(device_id, dev):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    UPDATE servers
                    SET hostname=%s,
                        main_username=%s,
                        os_version=%s,
                        architecture=%s,
                        architecture_bits=%s,
                        processor_type=%s,
                        vendor=%s,
                        main_ip_address=%s,
                        main_mac_address=%s,
                        main_interface=%s,
                        southbound=%s,
                        status=%s,
                        virtualization=%s,
                        updated_at=NOW(),
                        last_seen=NOW()
                    WHERE device_id=%s
                """

                cursor.execute(sql, (
                    dev.get("hostname", "unknown"),
                    dev.get("main_username", "unknown"),
                    dev.get("os_version", "unknown"),
                    dev.get("architecture"),
                    dev.get("architecture_bits"),
                    dev.get("processor_type"),
                    dev.get("vendor", "unknown"),
                    dev.get("main_ip_address"),
                    dev.get("main_mac_address", "unknown"),
                    dev.get("main_interface", "unknown"),
                    dev.get("southbound", "server_api"),
                    dev.get("status", "active"),
                    dev.get("virtualization", "physical"),
                    device_id
                ))

                conn.commit()

            finally:
                cursor.close()

    # ============================
    # INSERT ROUTER
    # ============================
    @staticmethod
    def insert_router(dev):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    INSERT INTO routers
                    (device_id, username, password, identity, os_version,
                     model, serial_number, vendor, main_ip_address,
                     main_mac_address, main_interface, southbound, status,
                     created_at, updated_at, last_seen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            NOW(), NOW(), NOW())
                """

                cursor.execute(sql, (
                    dev["device_id"],
                    dev.get("username", "admin"),
                    dev.get("password", ""),
                    dev.get("identity", "unknown"),
                    dev.get("os_version", "unknown"),
                    dev.get("model", ""),
                    dev.get("serial_number", ""),
                    dev.get("vendor", "unknown"),
                    dev.get("main_ip_address", ""),
                    dev.get("main_mac_address", ""),
                    dev.get("main_interface", "ether1"),
                    dev.get("southbound", "routeros_api"),
                    dev.get("status", "active")
                ))

                conn.commit()
                return cursor.lastrowid

            finally:
                cursor.close()

    # ============================
    # UPDATE ROUTER
    # ============================
    @staticmethod
    def update_router(device_id, dev):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    UPDATE routers
                    SET username=%s,
                        password=%s,
                        identity=%s,
                        os_version=%s,
                        model=%s,
                        serial_number=%s,
                        vendor=%s,
                        main_ip_address=%s,
                        main_mac_address=%s,
                        main_interface=%s,
                        southbound=%s,
                        status=%s,
                        updated_at=NOW(),
                        last_seen=NOW()
                    WHERE device_id=%s
                """

                cursor.execute(sql, (
                    dev.get("username", "admin"),
                    dev.get("password", ""),
                    dev.get("identity", "unknown"),
                    dev.get("os_version", "unknown"),
                    dev.get("model", ""),
                    dev.get("serial_number", ""),
                    dev.get("vendor", "unknown"),
                    dev.get("main_ip_address", ""),
                    dev.get("main_mac_address", ""),
                    dev.get("main_interface", "ether1"),
                    dev.get("southbound", "routeros_api"),
                    dev.get("status", "active"),
                    device_id
                ))

                conn.commit()

            finally:
                cursor.close()

    # ============================
    # INSERT ACCESS POINT
    # ============================
    @staticmethod
    def insert_access_point(dev):
        from database.db_connection import DBConnection

        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    INSERT INTO access_points
                    (device_id, username, password, identity, os_version,
                    board, serial_number, vendor, main_ip_address,
                    main_mac_address, main_interface, southbound, status,
                    created_at, updated_at, last_seen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            NOW(), NOW(), NOW())
                """

                cursor.execute(sql, (
                    dev["device_id"],
                    dev.get("username", "ubnt"),
                    dev.get("password", ""),
                    dev.get("identity", dev.get("hostname", "unknown")),
                    dev.get("os_version", "unknown"),
                    dev.get("board", dev.get("model", "")),
                    dev.get("serial_number", ""),
                    dev.get("vendor", "unifi"),
                    dev.get("main_ip_address"),
                    dev.get("main_mac_address", "unknown"),
                    dev.get("main_interface", "eth0"),
                    dev.get("southbound", "paramiko"),
                    dev.get("status", "active")
                ))

                conn.commit()
                return cursor.lastrowid

            finally:
                cursor.close()

    # ============================
    # UPDATE ACCESS POINT
    # ============================
    @staticmethod
    def update_access_point(device_id, dev):
        from database.db_connection import DBConnection

        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    UPDATE access_points
                    SET identity=%s,
                        os_version=%s,
                        board=%s,
                        vendor=%s,
                        main_ip_address=%s,
                        main_mac_address=%s,
                        main_interface=%s,
                        southbound=%s,
                        status=%s,
                        updated_at=NOW(),
                        last_seen=NOW()
                    WHERE device_id=%s
                """

                cursor.execute(sql, (
                    dev.get("identity", dev.get("hostname", "unknown")),
                    dev.get("os_version", "unknown"),
                    dev.get("board", dev.get("model", "")),
                    dev.get("vendor", "unifi"),
                    dev.get("main_ip_address"),
                    dev.get("main_mac_address", "unknown"),
                    dev.get("main_interface", "eth0"),
                    dev.get("southbound", "paramiko"),
                    dev.get("status", "active"),
                    device_id
                ))

                conn.commit()

            finally:
                cursor.close()

    # ============================
    # GET ALL SERVERS
    # ============================
    @staticmethod
    def get_all_servers():
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                sql = """
                    SELECT 
                        s.device_id,
                        'server' AS device_type,
                        s.hostname,
                        s.main_username,
                        s.os_version,
                        s.architecture,
                        s.architecture_bits,
                        s.processor_type,
                        s.vendor,
                        s.main_ip_address,
                        s.main_mac_address,
                        s.main_interface,
                        s.southbound,
                        s.status,
                        s.virtualization,
                        s.last_seen,
                        s.created_at,
                        s.updated_at
                    FROM servers s
                    ORDER BY s.last_seen DESC
                """
                cursor.execute(sql)
                return cursor.fetchall()
            finally:
                cursor.close()

    # ============================
    # GET ALL ROUTERS
    # ============================
    @staticmethod
    def get_all_routers():
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                sql = """
                    SELECT 
                        r.device_id,
                        'router' AS device_type,
                        r.identity AS hostname,
                        r.username AS main_username,
                        r.os_version,
                        NULL AS architecture,
                        NULL AS architecture_bits,
                        NULL AS processor_type,
                        r.vendor,
                        r.main_ip_address,
                        r.main_mac_address,
                        r.main_interface,
                        r.southbound,
                        r.status,
                        NULL AS virtualization,
                        r.last_seen,
                        r.created_at,
                        r.updated_at
                    FROM routers r
                    ORDER BY r.last_seen DESC
                """
                cursor.execute(sql)
                return cursor.fetchall()
            finally:
                cursor.close()

    # ============================
    # GET ALL ACCESS POINTS
    # ============================
    @staticmethod
    def get_all_access_points():
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                sql = """
                    SELECT 
                        ap.device_id,
                        'access_point' AS device_type,
                        ap.identity AS hostname,
                        ap.username AS main_username,
                        ap.os_version,
                        NULL AS architecture,
                        NULL AS architecture_bits,
                        NULL AS processor_type,
                        ap.vendor,
                        ap.main_ip_address,
                        ap.main_mac_address,
                        ap.main_interface,
                        ap.southbound,
                        ap.status,
                        NULL AS virtualization,
                        ap.last_seen,
                        ap.created_at,
                        ap.updated_at
                    FROM access_points ap
                    ORDER BY ap.last_seen DESC
                """
                cursor.execute(sql)
                return cursor.fetchall()
            finally:
                cursor.close()

    # ============================
    # LIST ALL DEVICES
    # ============================
    @staticmethod
    def list_all():
        servers = DeviceRepository.get_all_servers()
        routers = DeviceRepository.get_all_routers()
        access_points = DeviceRepository.get_all_access_points()

        devices = servers + routers + access_points
        devices.sort(key=lambda x: x.get("last_seen") or "", reverse=True)
        return devices

    # ============================
    # DELETE DEVICE
    # ============================
    @staticmethod
    def delete_device(device_id):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    DELETE sf FROM server_firewalls sf
                    INNER JOIN servers s ON sf.server_id = s.id
                    WHERE s.device_id = %s
                """, (device_id,))

                cursor.execute("""
                    DELETE si FROM server_interfaces si
                    INNER JOIN servers s ON si.server_id = s.id
                    WHERE s.device_id = %s
                """, (device_id,))

                cursor.execute("DELETE FROM servers WHERE device_id=%s", (device_id,))
                cursor.execute("DELETE FROM routers WHERE device_id=%s", (device_id,))
                cursor.execute("DELETE FROM devices WHERE device_id=%s", (device_id,))

                conn.commit()
                return True

            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    # ============================
    # GET SERVER INTERFACES
    # ============================
    @staticmethod
    def get_server_interfaces(device_id):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT 
                        si.id,
                        si.interface_name,
                        si.interface_status,
                        si.mac_address,
                        si.ip_address,
                        si.ip_netmask,
                        si.ip_broadcast,
                        si.ip_version,
                        si.created_at,
                        si.updated_at,
                        si.all_ips
                    FROM server_interfaces si
                    INNER JOIN servers s ON si.server_id = s.id
                    WHERE s.device_id = %s
                    ORDER BY si.interface_name
                """, (device_id,))

                interfaces = cursor.fetchall()

                for iface in interfaces:
                    iface["ip_addresses"] = []

                    if iface.get("all_ips"):
                        try:
                            iface["ip_addresses"] = json.loads(iface["all_ips"])
                        except Exception:
                            iface["ip_addresses"] = []

                    elif iface.get("ip_address"):
                        ip_str = iface["ip_address"]
                        if iface.get("ip_netmask"):
                            ip_str += f"/{iface['ip_netmask']}"
                        iface["ip_addresses"] = [ip_str]

                return interfaces

            finally:
                cursor.close()

    # ============================
    # GET SERVER FIREWALL
    # ============================
    @staticmethod
    def get_server_firewall(device_id):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT 
                        sf.firewall_type,
                        sf.status,
                        sf.default_zone,
                        sf.active_zones,
                        sf.rules_count,
                        sf.last_checked,
                        sf.created_at,
                        sf.updated_at
                    FROM server_firewalls sf
                    INNER JOIN servers s ON sf.server_id = s.id
                    WHERE s.device_id = %s
                """, (device_id,))

                return cursor.fetchone()

            finally:
                cursor.close()

    # ============================
    # INSERT SERVER INTERFACE
    # ============================
    @staticmethod
    def insert_server_interface(data):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO server_interfaces
                    (server_id, interface_name, interface_status, mac_address,
                     ip_address, ip_netmask, ip_broadcast, ip_version,
                     created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    data.get("server_id"),
                    data.get("interface_name"),
                    data.get("interface_status", "unknown"),
                    data.get("mac_address", "unknown"),
                    data.get("ip_address", ""),
                    data.get("ip_netmask", ""),
                    data.get("ip_broadcast", ""),
                    data.get("ip_version", "ipv4")
                ))

                conn.commit()
                return cursor.lastrowid

            finally:
                cursor.close()

    # ============================
    # UPSERT SERVER FIREWALL
    # ============================
    @staticmethod
    def upsert_server_firewall(data):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO server_firewalls
                    (server_id, firewall_type, status, default_zone, active_zones,
                     rules_count, last_checked, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        firewall_type = VALUES(firewall_type),
                        status = VALUES(status),
                        default_zone = VALUES(default_zone),
                        active_zones = VALUES(active_zones),
                        rules_count = VALUES(rules_count),
                        last_checked = VALUES(last_checked),
                        updated_at = NOW()
                """, (
                    data.get("server_id"),
                    data.get("firewall_type"),
                    data.get("status"),
                    data.get("default_zone"),
                    data.get("active_zones"),
                    data.get("rules_count", 0),
                    data.get("last_checked")
                ))

                conn.commit()

            finally:
                cursor.close()

     # ============================
    # DELETE SERVER INTERFACES
    # ============================
    @staticmethod
    def delete_server_interfaces(device_id):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                server_id = DeviceRepository.get_server_id(device_id)
                if not server_id:
                    return False

                cursor.execute(
                    "DELETE FROM server_interfaces WHERE server_id=%s",
                    (server_id,)
                )
                conn.commit()
                return True

            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    # ============================
    # HEALTHCHECK DEVICES
    # ============================
    @staticmethod
    def update_device_status(device_id, status, last_seen=None):
        """Update device status and last_seen timestamp"""
        last_seen_val = last_seen or datetime.datetime.now()

        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    UPDATE devices
                    SET status=%s,
                        last_seen=%s,
                        updated_at=NOW()
                    WHERE device_id=%s
                """, (status, last_seen_val, device_id))

                cursor.execute(
                    "SELECT device_type FROM devices WHERE device_id=%s",
                    (device_id,)
                )
                device = cursor.fetchone()

                if device and device.get("device_type") == "server":
                    cursor.execute("""
                        UPDATE servers
                        SET status=%s,
                            last_seen=%s,
                            updated_at=NOW()
                        WHERE device_id=%s
                    """, (status, last_seen_val, device_id))

                conn.commit()
                return True

            except Exception as e:
                conn.rollback()
                print(f"[DB-ERROR] update_device_status: {e}")
                return False
            finally:
                cursor.close()

    # ============================
    # UPDATE SERVER FIREWALL STATE
    # ============================
    @staticmethod
    def update_server_firewall_state(device_id, firewall_state):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                # Get server_id
                cursor.execute(
                    "SELECT id FROM servers WHERE device_id=%s",
                    (device_id,)
                )
                row = cursor.fetchone()
                if not row:
                    print(f"[DB-AUTO-ERROR] Device {device_id} not found")
                    return False

                server_id = row[0]

                firewall_type = firewall_state.get("detected_firewall") \
                                or firewall_state.get("firewall_type", "unknown")

                status = "unknown"
                rules_count = 0

                # === Parse firewall state ===
                if firewall_type == "ufw":
                    ufw_status = str(firewall_state.get("ufw_status", "")).lower()
                    if "active" in ufw_status:
                        status = "active"
                    elif "inactive" in ufw_status:
                        status = "inactive"

                    iptables_filter = firewall_state.get("iptables_filter", "")
                    if iptables_filter:
                        for line in iptables_filter.splitlines():
                            if any(x in line for x in ("ACCEPT", "DROP", "REJECT")):
                                rules_count += 1

                elif firewall_type == "iptables":
                    iptables_filter = firewall_state.get("iptables_filter", "")
                    if iptables_filter:
                        for line in iptables_filter.splitlines():
                            if any(x in line for x in ("ACCEPT", "DROP", "REJECT")):
                                rules_count += 1
                        status = "active" if rules_count > 0 else "inactive"

                elif firewall_type == "firewalld":
                    status = firewall_state.get("status", "unknown")

                cursor.execute("""
                    INSERT INTO server_firewalls
                    (server_id, firewall_type, status,
                     default_zone, active_zones,
                     rules_count, last_checked,
                     created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        firewall_type=VALUES(firewall_type),
                        status=VALUES(status),
                        default_zone=VALUES(default_zone),
                        active_zones=VALUES(active_zones),
                        rules_count=VALUES(rules_count),
                        last_checked=VALUES(last_checked),
                        updated_at=NOW()
                """, (
                    server_id,
                    firewall_type,
                    status,
                    "N/A",
                    "[]",
                    rules_count
                ))

                conn.commit()
                print(f"[DB-AUTO] Firewall updated for {device_id}")
                return True

            except Exception as e:
                conn.rollback()
                print(f"[DB-AUTO-ERROR] update_server_firewall_state: {e}")
                return False
            finally:
                cursor.close()
        """Update interface state ke database setelah action - SIMPAN SEMUA IPs"""
        try:
            conn = DBConnection.get_conn()
            cursor = conn.cursor()
            
            # Get server_id
            cursor.execute("SELECT id FROM servers WHERE device_id = %s", (device_id,))
            result = cursor.fetchone()
            if not result:
                print(f"[DB-AUTO-ERROR] Device {device_id} not found")
                return False
            
            server_id = result[0]
            
            print(f"[DB-AUTO-DEBUG] Updating interface {interface_name} for device {device_id}")
            print(f"[DB-AUTO-DEBUG] Raw interface data: {interface_data}")
            
            # 1. Ambil status dari interface_data (prioritas utama)
            interface_status = interface_data.get("status", "unknown")
            print(f"[DB-AUTO-DEBUG] Status from interface_data: {interface_status}")

            # Ambil IP pertama untuk backward compatibility
            ip_address = interface_data.get("ip_address") or interface_data.get("address", "")
            ip_netmask = interface_data.get("ip_netmask") or interface_data.get("netmask", "")        
            
            # 2. Jika masih unknown, coba deteksi dari IP
            if interface_status == "unknown":
                print(f"[DB-AUTO-DEBUG] IP: {ip_address}, Netmask: {ip_netmask}")
                
                # Check jika ada flag 'up' atau 'down' di data lain
                operational_state = interface_data.get("operstate", "").lower()
                admin_state = interface_data.get("admin_state", "").lower()
                
                if "up" in operational_state or "up" in admin_state:
                    interface_status = "up"
                elif "down" in operational_state or "down" in admin_state:
                    interface_status = "down"
                elif ip_address and ip_address != "" and not ip_address.startswith("127."):
                    interface_status = "up"
                else:
                    interface_status = "down"
            
            print(f"[DB-AUTO-DEBUG] Final interface_status: {interface_status}")
            
            # 2. Ambil SEMUA IPs dari agent response
            all_ips_json = "[]"  # Default empty array
            
            if "ip_addresses" in interface_data and isinstance(interface_data["ip_addresses"], list):
                # Simpan SEMUA IPs sebagai JSON
                all_ips_json = json.dumps(interface_data["ip_addresses"])
                print(f"[DB-AUTO-DEBUG] Saving {len(interface_data['ip_addresses'])} IPs to all_ips: {all_ips_json}")
            elif "address" in interface_data and interface_data["address"]:
                # Jika format lama (single IP), buat array dengan IP tersebut
                single_ip = interface_data["address"]
                if ip_netmask:
                    all_ips_json = json.dumps([f"{single_ip}/{ip_netmask}"])
                else:
                    all_ips_json = json.dumps([single_ip])
                print(f"[DB-AUTO-DEBUG] Saving single IP to all_ips: {all_ips_json}")
            
            # 3. MAC address
            mac_address = interface_data.get("mac_address") or interface_data.get("mac", "unknown")
            
            # 4. Broadcast (hitung dari IP pertama)
            ip_broadcast = interface_data.get("ip_broadcast") or interface_data.get("broadcast", "")
            
            # Hitung broadcast jika tidak ada
            if not ip_broadcast and ip_address and ip_netmask:
                try:
                    import ipaddress
                    if "." in ip_netmask:
                        # Subnet mask format
                        mask_parts = ip_netmask.split(".")
                        prefix = sum(bin(int(x)).count('1') for x in mask_parts)
                        cidr = f"{ip_address}/{prefix}"
                    elif ip_netmask.startswith("/"):
                        # Already prefix format
                        cidr = f"{ip_address}{ip_netmask}"
                    else:
                        # Prefix without slash
                        cidr = f"{ip_address}/{ip_netmask}"
                    
                    network = ipaddress.IPv4Network(cidr, strict=False)
                    ip_broadcast = str(network.broadcast_address)
                    print(f"[DB-AUTO-DEBUG] Calculated broadcast: {ip_broadcast}")
                except Exception as e:
                    print(f"[DB-AUTO-DEBUG] Cannot calculate broadcast: {e}")
            
            print(f"[DB-AUTO-DEBUG] Final values - IP: {ip_address}, Netmask: {ip_netmask}, MAC: {mac_address}")
            print(f"[DB-AUTO-DEBUG] All IPs JSON: {all_ips_json}")
            
            # Cek jika kolom all_ips ada di tabel
            try:
                cursor.execute("SHOW COLUMNS FROM server_interfaces LIKE 'all_ips'")
                has_all_ips = cursor.fetchone() is not None
            except:
                has_all_ips = False
            
            if has_all_ips:
                # SQL DENGAN all_ips
                sql = """
                    INSERT INTO server_interfaces 
                    (server_id, interface_name, interface_status, mac_address, ip_address, ip_netmask, ip_broadcast, 
                    all_ips, ip_version, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        mac_address = IF(VALUES(mac_address) != '', VALUES(mac_address), mac_address),
                        ip_address = IF(VALUES(ip_address) != '', VALUES(ip_address), ip_address),
                        ip_netmask = IF(VALUES(ip_netmask) != '', VALUES(ip_netmask), ip_netmask),
                        ip_broadcast = IF(VALUES(ip_broadcast) != '', VALUES(ip_broadcast), ip_broadcast),
                        all_ips = VALUES(all_ips),
                        interface_status = VALUES(interface_status),
                        updated_at = NOW()
                """
                
                cursor.execute(sql, (
                    server_id,
                    interface_name,
                    interface_status,
                    mac_address,
                    ip_address,
                    ip_netmask,
                    ip_broadcast,
                    all_ips_json,  # SEMUA IPs sebagai JSON
                    "ipv4"
                ))
            else:
                # SQL TANPA all_ips (backward compatibility)
                print(f"[DB-AUTO-WARNING] Kolom 'all_ips' tidak ada di tabel server_interfaces!")
                print(f"[DB-AUTO-WARNING] Jalankan: ALTER TABLE server_interfaces ADD COLUMN all_ips TEXT DEFAULT NULL")
                
                sql = """
                    INSERT INTO server_interfaces 
                    (server_id, interface_name, interface_status, mac_address, ip_address, ip_netmask, ip_broadcast, 
                    ip_version, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        mac_address = IF(VALUES(mac_address) != '', VALUES(mac_address), mac_address),
                        ip_address = IF(VALUES(ip_address) != '', VALUES(ip_address), ip_address),
                        ip_netmask = IF(VALUES(ip_netmask) != '', VALUES(ip_netmask), ip_netmask),
                        ip_broadcast = IF(VALUES(ip_broadcast) != '', VALUES(ip_broadcast), ip_broadcast),
                        updated_at = NOW()
                """
                
                cursor.execute(sql, (
                    server_id,
                    interface_name,
                    mac_address,
                    ip_address,
                    ip_netmask,
                    ip_broadcast,
                    "ipv4"
                ))
            
            conn.commit()
            print(f"[DB-AUTO-SUCCESS] Updated interface {interface_name} for {device_id}")
            
            # Verifikasi update berhasil
            cursor.execute("""
                SELECT interface_name, interface_status, ip_address, all_ips 
                FROM server_interfaces 
                WHERE server_id = %s AND interface_name = %s
            """, (server_id, interface_name))
            
            updated_row = cursor.fetchone()
            if updated_row:
                print(f"[DB-AUTO-VERIFY] After update: {updated_row}")
            
            return True
            
        except Exception as e:
            print(f"[DB-AUTO-ERROR] Database error: {e}")
            import traceback
            print(f"[DB-AUTO-ERROR] Traceback: {traceback.format_exc()}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()