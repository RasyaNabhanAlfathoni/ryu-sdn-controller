from database.db_connection import DBConnection
import json
import datetime

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

            # 3. Check switches
            sql_switch = """
                SELECT 
                    ns.*,
                    'switch' as device_type,
                    ns.southbound,
                    ns.status,
                    ns.created_at as global_created_at,
                    ns.updated_at as global_updated_at,
                    ns.last_seen
                FROM switchs ns
                WHERE ns.device_id=%s
            """
            cursor.execute(sql_switch, (device_id,))
            switch_row = cursor.fetchone()
            cursor.fetchall()

            if switch_row:
                return switch_row

            # 4. Check access points
            sql_ap = """
                SELECT 
                    ap.*,
                    'access_point' as device_type,
                    ap.southbound,
                    ap.status,
                    ap.created_at as global_created_at,
                    ap.updated_at as global_updated_at,
                    ap.last_seen
                FROM access_points ap
                WHERE ap.device_id=%s
            """
            cursor.execute(sql_ap, (device_id,))
            ap_row = cursor.fetchone()
            cursor.fetchall()

            return ap_row

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
    # FIND SWITCH BY DEVICE ID
    # ============================
    @staticmethod
    def find_switch(device_id):
        """Find switch by device_id"""
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True, buffered=True)

        try:
            sql = """
                SELECT 
                    ns.*,
                    'switch' as device_type,
                    ns.southbound,
                    ns.status,
                    ns.created_at as global_created_at,
                    ns.updated_at as global_updated_at,
                    ns.last_seen
                FROM switchs ns
                WHERE ns.device_id=%s
            """
            cursor.execute(sql, (device_id,))
            row = cursor.fetchone()
            cursor.fetchall()  
            return row

        finally:
            cursor.close()
            conn.close()
            
    # ============================
    # INSERT SWITCH
    # ============================
    @staticmethod
    def insert_switch(dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql = """
                INSERT INTO switchs
                (device_id, username, password, identity, os_version,
                model, serial_number, vendor, main_ip_address,
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
                dev.get("model", ""),
                dev.get("serial_number", ""),
                dev.get("vendor", "unknown"),
                dev.get("main_ip_address", ""),
                dev.get("main_mac_address", ""),
                dev.get("main_interface", "GigabitEthernet0/0"),
                dev.get("southbound", "paramiko"),
                dev.get("status", "active")
            ))

            conn.commit()

        finally:
            cursor.close()
            conn.close()

    # ============================
    # UPDATE SWITCH
    # ============================
    @staticmethod
    def update_switch(device_id, dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(buffered=True)

        try:
            sql = """
                UPDATE switchs 
                SET username=%s, password=%s, identity=%s, os_version=%s,
                    model=%s, serial_number=%s, vendor=%s, main_ip_address=%s,
                    main_mac_address=%s, main_interface=%s, southbound=%s, status=%s,
                    updated_at=NOW(), last_seen=NOW()
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
                dev.get("main_interface", "GigabitEthernet0/0"),
                dev.get("southbound", "paramiko"),
                dev.get("status", "active"),
                device_id
            ))

            conn.commit()

        finally:
            cursor.close()
            conn.close()

    # ============================
    # GET ALL SWITCHES
    # ============================
    @staticmethod
    def get_all_switches():
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True, buffered=True)

        try:
            sql = """
                SELECT 
                    ns.device_id,
                    'switch' as device_type,
                    ns.identity as identity,
                    ns.username as username,
                    ns.password as password,
                    ns.os_version,
                    ns.vendor,
                    ns.model,
                    ns.serial_number,
                    ns.main_ip_address,
                    ns.main_mac_address,
                    ns.main_interface,
                    ns.southbound,
                    ns.status,
                    ns.last_seen,
                    ns.created_at,
                    ns.updated_at
                FROM switchs ns
                ORDER BY ns.last_seen DESC
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
        switches = DeviceRepository.get_all_switches()
        access_points = DeviceRepository.get_all_access_points()
        devices = servers + routers + switches + access_points

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
    # HEALTHCHECK DEVICES
    # ============================
    @staticmethod
    def update_device_status(device_id, status, last_seen=None):
        """Update device status and last_seen timestamp"""
        try:
            conn = DBConnection.get_conn()
            cursor = conn.cursor(dictionary=True)
            
            update_query = """
                UPDATE devices 
                SET status = %s, 
                    last_seen = %s,
                    updated_at = NOW()
                WHERE device_id = %s
            """
            last_seen_val = last_seen if last_seen else datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(update_query, (status, last_seen_val, device_id))
            
            # Juga update table specific (servers/routers)
            cursor.execute("SELECT device_type FROM devices WHERE device_id = %s", (device_id,))
            device = cursor.fetchone()
            
            if device and device['device_type'] == 'server':
                cursor.execute("""
                    UPDATE servers 
                    SET status = %s, 
                        last_seen = %s,
                        updated_at = NOW()
                    WHERE device_id = %s
                """, (status, last_seen_val, device_id))

            elif device and device['device_type'] == 'router':
                cursor.execute("""
                    UPDATE routers 
                    SET status = %s, 
                        last_seen = %s,
                        updated_at = NOW()
                    WHERE device_id = %s
                """, (status, last_seen_val, device_id))

            elif device and device['device_type'] == 'switch':
                cursor.execute("""
                    UPDATE switchs 
                    SET status = %s, 
                        last_seen = %s,
                        updated_at = NOW()
                    WHERE device_id = %s
                """, (status, last_seen_val, device_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error updating device status: {e}")
            return False

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
                    model, serial_number, vendor, main_ip_address,
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
                    dev.get("model", ""),
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
                        model=%s,
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
                    dev.get("model", dev.get("model", "")),
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
                        ap.model AS model,
                        ap.serial_number,
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