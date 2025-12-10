from database.db_connection import DBConnection
import json

class DeviceRepository:

    # ============================
    # INSERT NETWORK DEVICE
    # ============================
    @staticmethod
    def insert_network_device(dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql = """
                INSERT INTO devices
                (device_id, device_type, southbound, status, created_at, updated_at, last_seen)
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
            conn.close()

    # ============================
    # UPDATE NETWORK DEVICE
    # ============================
    @staticmethod
    def update_network_device(device_id, data):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql = """
                UPDATE devices 
                SET device_type=%s, southbound=%s, status=%s, last_seen=%s, updated_at=NOW()
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
            conn.close()

    # ============================
    # FIND BY SERIAL (ROUTER)
    # ============================
    @staticmethod
    def find_by_serial(serial):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True, buffered=True)

        try:
            sql = """
                SELECT 'router' AS type, r.device_id
                FROM routers r
                WHERE r.serial_number=%s
            """
            cursor.execute(sql, (serial,))
            row = cursor.fetchone()
            cursor.fetchall()  # consume remainder
            return row

        finally:
            cursor.close()
            conn.close()

    # ============================
    # FIND DEVICE BY device_id
    # ============================
    @staticmethod
    def find_by_device_id(device_id):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True, buffered=True)

        try:
            # 1. Check servers
            sql_server = """
                SELECT 
                    s.*,
                    'server' as device_type,
                    s.southbound,
                    s.status,
                    s.created_at as global_created_at,
                    s.updated_at as global_updated_at,
                    s.last_seen
                FROM servers s
                WHERE s.device_id=%s
            """

            cursor.execute(sql_server, (device_id,))
            server_row = cursor.fetchone()
            cursor.fetchall()   # IMPORTANT FIX

            if server_row:
                return server_row

            # 2. Check routers
            sql_router = """
                SELECT 
                    r.*,
                    'router' as device_type,
                    r.southbound,
                    r.status,
                    r.created_at as global_created_at,
                    r.updated_at as global_updated_at,
                    r.last_seen
                FROM routers r
                WHERE r.device_id=%s
            """
            cursor.execute(sql_router, (device_id,))
            router_row = cursor.fetchone()
            cursor.fetchall()   # IMPORTANT FIX

            return router_row

        finally:
            cursor.close()
            conn.close()

    # ============================
    # INSERT SERVER
    # ============================
    @staticmethod
    def insert_server(dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql = """
                INSERT INTO servers
                (device_id, hostname, main_username, os_version, architecture,
                 architecture_bits, processor_type, vendor, main_ip_address,
                 main_mac_address, main_interface, southbound, status,
                 virtualization, created_at, updated_at, last_seen)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
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
            conn.close()

    # ============================
    # UPDATE SERVER
    # ============================
    @staticmethod
    def update_server(device_id, dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql = """
                UPDATE servers 
                SET hostname=%s, main_username=%s, os_version=%s, architecture=%s,
                    architecture_bits=%s, processor_type=%s, vendor=%s, main_ip_address=%s,
                    main_mac_address=%s, main_interface=%s, southbound=%s, status=%s,
                    virtualization=%s, updated_at=NOW(), last_seen=NOW()
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
            conn.close()

    # ============================
    # INSERT ROUTER
    # ============================
    @staticmethod
    def insert_router(dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql = """
                INSERT INTO routers
                (device_id, username, password, identity, os_version,
                board, serial_number, vendor, main_ip_address,
                main_mac_address, main_interface, southbound, status,
                created_at, updated_at, last_seen)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
            """

            cursor.execute(sql, (
                dev["device_id"],
                dev.get("username", "admin"),
                dev.get("password", ""),
                dev.get("identity", "unknown"),
                dev.get("os_version", "unknown"),
                dev.get("board", ""),
                dev.get("serial_number", ""),
                dev.get("vendor", "unknown"),
                dev.get("main_ip_address", ""),
                dev.get("main_mac_address", ""),
                dev.get("main_interface", "ether1"),
                dev.get("southbound", "routeros_api"),
                dev.get("status", "active")
            ))

            conn.commit()

        finally:
            cursor.close()
            conn.close()

    # ============================
    # UPDATE ROUTER
    # ============================
    @staticmethod
    def update_router(device_id, dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql = """
                UPDATE routers 
                SET username=%s, password=%s, identity=%s, os_version=%s,
                    board=%s, serial_number=%s, vendor=%s, main_ip_address=%s,
                    main_mac_address=%s, main_interface=%s, southbound=%s, status=%s,
                    updated_at=NOW(), last_seen=NOW()
                WHERE device_id=%s
            """

            cursor.execute(sql, (
                dev.get("username", "admin"),
                dev.get("password", ""),
                dev.get("identity", "unknown"),
                dev.get("os_version", "unknown"),
                dev.get("board", ""),
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
            conn.close()

    # ============================
    # GET ALL SERVERS
    # ============================
    @staticmethod
    def get_all_servers():
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True, buffered=True)

        try:
            sql = """
                SELECT 
                    s.device_id,
                    'server' as device_type,
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
            rows = cursor.fetchall()
            return rows

        finally:
            cursor.close()
            conn.close()

    # ============================
    # GET ALL ROUTERS
    # ============================
    @staticmethod
    def get_all_routers():
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True, buffered=True)

        try:
            sql = """
                SELECT 
                    r.device_id,
                    'router' as device_type,
                    r.identity as hostname,
                    r.username as main_username,
                    r.os_version,
                    NULL as architecture,
                    NULL as architecture_bits,
                    NULL as processor_type,
                    r.vendor,
                    r.main_ip_address,
                    r.main_mac_address,
                    r.main_interface,
                    r.southbound,
                    r.status,
                    NULL as virtualization,
                    r.last_seen,
                    r.created_at,
                    r.updated_at
                FROM routers r
                ORDER BY r.last_seen DESC
            """
            
            cursor.execute(sql)
            rows = cursor.fetchall()
            return rows

        finally:
            cursor.close()
            conn.close()

    # ============================
    # LIST ALL DEVICES
    # ============================
    @staticmethod
    def list_all():
        servers = DeviceRepository.get_all_servers()
        routers = DeviceRepository.get_all_routers()
        devices = servers + routers

        devices.sort(key=lambda x: x.get('last_seen', ''), reverse=True)
        return devices

    # ============================
    # DELETE DEVICE
    # ============================
    @staticmethod
    def delete_device(device_id):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql_delete_firewalls = """
                DELETE sf FROM server_firewalls sf
                INNER JOIN servers s ON sf.server_id = s.id
                WHERE s.device_id = %s
            """
            cursor.execute(sql_delete_firewalls, (device_id,))

            sql_delete_interfaces = """
                DELETE si FROM server_interfaces si
                INNER JOIN servers s ON si.server_id = s.id
                WHERE s.device_id = %s
            """
            cursor.execute(sql_delete_interfaces, (device_id,))

            cursor.execute("DELETE FROM servers WHERE device_id=%s", (device_id,))
            if cursor.rowcount == 0:
                cursor.execute("DELETE FROM routers WHERE device_id=%s", (device_id,))

            cursor.execute("DELETE FROM devices WHERE device_id=%s", (device_id,))
            conn.commit()
            return True

        except:
            conn.rollback()
            raise

        finally:
            cursor.close()
            conn.close()

    # ============================
    # GET SERVER INTERFACES
    # ============================
    @staticmethod
    def get_server_interfaces(device_id):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True, buffered=True)

        try:
            sql = """
                SELECT 
                    si.id,
                    si.interface_name,
                    si.mac_address,
                    si.ip_address,
                    si.ip_netmask,
                    si.ip_broadcast,
                    si.ip_version,
                    si.created_at,
                    si.updated_at
                FROM server_interfaces si
                INNER JOIN servers s ON si.server_id = s.id
                WHERE s.device_id = %s
                ORDER BY si.interface_name
            """
            
            cursor.execute(sql, (device_id,))
            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()

    # ============================
    # GET SERVER FIREWALL
    # ============================
    @staticmethod
    def get_server_firewall(device_id):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True, buffered=True)

        try:
            sql = """
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
            """
            cursor.execute(sql, (device_id,))
            row = cursor.fetchone()
            cursor.fetchall()
            return row

        finally:
            cursor.close()
            conn.close()

    # ============================
    # INSERT SERVER INTERFACE
    # ============================
    @staticmethod
    def insert_server_interface(data):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql = """
                INSERT INTO server_interfaces
                (server_id, interface_name, mac_address,
                ip_address, ip_netmask, ip_broadcast, ip_version,
                created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """

            cursor.execute(sql, (
                data.get("server_id"),
                data.get("interface_name"),
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
            conn.close()

    # ============================
    # UPSERT SERVER FIREWALL
    # ============================
    @staticmethod
    def upsert_server_firewall(data):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql = """
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
            """

            cursor.execute(sql, (
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
            conn.close()

    # ============================
    # GET SERVER ID
    # ============================
    @staticmethod
    def get_server_id(device_id):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql = "SELECT id FROM servers WHERE device_id = %s"
            cursor.execute(sql, (device_id,))
            row = cursor.fetchone()
            cursor.fetchall()
            return row[0] if row else None

        finally:
            cursor.close()
            conn.close()

    # ============================
    # DELETE SERVER INTERFACES
    # ============================
    @staticmethod
    def delete_server_interfaces(device_id):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            server_id = DeviceRepository.get_server_id(device_id)
            if not server_id:
                return False

            cursor.execute("DELETE FROM server_interfaces WHERE server_id=%s", (server_id,))
            conn.commit()
            return True

        except:
            conn.rollback()
            raise

        finally:
            cursor.close()
            conn.close()