from database.db_connection import DBConnection
import json
import datetime
import psycopg2.extras

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
                    (device_id, device_type, southbound, status, created_at, updated_at, last_seen)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), NOW())
                    ON CONFLICT (device_id)
                    DO UPDATE SET
                        device_type = EXCLUDED.device_type,
                        southbound = EXCLUDED.southbound,
                        status = EXCLUDED.status,
                        updated_at = NOW(),
                        last_seen = NOW()
                    RETURNING id
                """

                cursor.execute(sql, (
                    dev["device_id"],
                    dev.get("device_type"),
                    dev.get("southbound"),
                    dev.get("status", "active")
                ))

                row_id = cursor.fetchone()[0]
                conn.commit()
                return row_id

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
            cursor = conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )
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
            cursor = conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )

            try:
                # SERVERS
                cursor.execute("""
                    SELECT 
                        s.*,
                        'server' AS device_type,
                        s.created_at AS global_created_at,
                        s.updated_at AS global_updated_at
                    FROM servers s
                    WHERE s.device_id=%s
                """, (device_id,))
                row = cursor.fetchone()
                if row:
                    return row

                # ROUTERS
                cursor.execute("""
                    SELECT 
                        r.*,
                        'router' AS device_type,
                        r.created_at AS global_created_at,
                        r.updated_at AS global_updated_at
                    FROM routers r
                    WHERE r.device_id=%s
                """, (device_id,))
                row = cursor.fetchone()
                if row:
                    return row

                # SWITCHES
                cursor.execute("""
                    SELECT 
                        sw.*,
                        'switch' AS device_type,
                        sw.created_at AS global_created_at,
                        sw.updated_at AS global_updated_at
                    FROM switchs sw
                    WHERE sw.device_id=%s
                """, (device_id,))
                row = cursor.fetchone()
                if row:
                    return row

                # ACCESS POINTS
                cursor.execute("""
                    SELECT 
                        ap.*,
                        'access_point' AS device_type,
                        ap.created_at AS global_created_at,
                        ap.updated_at AS global_updated_at
                    FROM access_points ap
                    WHERE ap.device_id=%s
                """, (device_id,))
                return cursor.fetchone()

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
                    RETURNING id
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

                server_id = cursor.fetchone()[0]
                conn.commit()
                return server_id

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
                    SET hostname=%s, main_username=%s, os_version=%s, architecture=%s,
                        architecture_bits=%s, processor_type=%s, vendor=%s,
                        main_ip_address=%s, main_mac_address=%s, main_interface=%s,
                        southbound=%s, status=%s, virtualization=%s,
                        updated_at=NOW(), last_seen=NOW()
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
    # GET SERVER ID
    # ============================
    @staticmethod
    def get_server_id(device_id):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT id FROM servers WHERE device_id=%s",
                    (device_id,)
                )
                row = cursor.fetchone()
                return row[0] if row else None

            finally:
                cursor.close()

    # ============================
    # GET ALL SERVERS
    # ============================
    @staticmethod
    def get_all_servers():
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            try:
                cursor.execute("""
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
                """)
                return cursor.fetchall()

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
                    RETURNING id
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

                router_id = cursor.fetchone()[0]
                conn.commit()
                return router_id
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
                    SET username=%s, password=%s, identity=%s, os_version=%s,
                        model=%s, serial_number=%s, vendor=%s,
                        main_ip_address=%s, main_mac_address=%s,
                        main_interface=%s, southbound=%s, status=%s,
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
                    dev.get("main_interface", "ether1"),
                    dev.get("southbound", "routeros_api"),
                    dev.get("status", "active"),
                    device_id
                ))

                conn.commit()

            finally:
                cursor.close()

    # ============================
    # GET ALL ROUTERS
    # ============================
    @staticmethod
    def get_all_routers():
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )
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
    # FIND SWITCH BY DEVICE ID
    # ============================
    @staticmethod
    def find_switch(device_id):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            try:
                sql = """
                    SELECT 
                        ns.*,
                        'switch' AS device_type,
                        ns.southbound,
                        ns.status,
                        ns.created_at AS global_created_at,
                        ns.updated_at AS global_updated_at,
                        ns.last_seen
                    FROM switchs ns
                    WHERE ns.device_id = %s
                """
                cursor.execute(sql, (device_id,))
                return cursor.fetchone()

            finally:
                cursor.close()
            
    # ============================
    # INSERT SWITCH
    # ============================
    @staticmethod
    def insert_switch(dev):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    INSERT INTO switchs
                    (device_id, username, password, identity, os_version,
                    model, serial_number, vendor, main_ip_address,
                    main_mac_address, main_interface, southbound, status,
                    created_at, updated_at, last_seen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            NOW(), NOW(), NOW())
                    RETURNING id
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

                switch_id = cursor.fetchone()[0]
                conn.commit()
                return switch_id
            finally:
                cursor.close()

    # ============================
    # UPDATE SWITCH
    # ============================
    @staticmethod
    def update_switch(device_id, dev):
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    UPDATE switchs 
                    SET username=%s, password=%s, identity=%s, os_version=%s,
                        model=%s, serial_number=%s, vendor=%s,
                        main_ip_address=%s, main_mac_address=%s,
                        main_interface=%s, southbound=%s, status=%s,
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

    # ============================
    # GET ALL SWITCHES
    # ============================
    @staticmethod
    def get_all_switches():
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            try:
                sql = """
                    SELECT 
                        ns.device_id,
                        'switch' AS device_type,
                        ns.identity,
                        ns.username,
                        ns.password,
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
                return cursor.fetchall()

            finally:
                cursor.close()

    # ============================
    # INSERT ACCESS POINT
    # ============================
    @staticmethod
    def insert_access_point(dev):
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
                    RETURNING id
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

                ap_id = cursor.fetchone()[0]
                conn.commit()
                return ap_id

            finally:
                cursor.close()

    # ============================
    # UPDATE ACCESS POINT
    # ============================
    @staticmethod
    def update_access_point(device_id, dev):
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
                    dev.get("model", ""),
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
            cursor = conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            try:
                sql = """
                    SELECT 
                        ap.device_id,
                        'access_point' AS device_type,
                        ap.identity AS hostname,
                        ap.username AS main_username,
                        ap.os_version,
                        ap.model,
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
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM devices WHERE device_id=%s", (device_id,))

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
        with DBConnection.get_conn() as conn:
            cursor = conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )

            try:
                last_seen_val = last_seen or datetime.datetime.now()

                cursor.execute("""
                    UPDATE devices
                    SET status=%s,
                        last_seen=%s,
                        updated_at=NOW()
                    WHERE device_id=%s
                """, (status, last_seen_val, device_id))

                cursor.execute("""
                    SELECT device_type FROM devices WHERE device_id=%s
                """, (device_id,))
                device = cursor.fetchone()

                if not device:
                    conn.commit()
                    return True

                table_map = {
                    "server": "servers",
                    "router": "routers",
                    "switch": "switchs",
                    "access_point": "access_points"
                }

                table = table_map.get(device["device_type"])
                if table:
                    cursor.execute(f"""
                        UPDATE {table}
                        SET status=%s,
                            last_seen=%s,
                            updated_at=NOW()
                        WHERE device_id=%s
                    """, (status, last_seen_val, device_id))

                conn.commit()
                return True

            finally:
                cursor.close()