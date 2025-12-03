from database.db_connection import DBConnection

class DeviceRepository:

    # CEK DOUBLE REGISTER (BERDASARKAN SERIAL_NUMBER) - Untuk routers saja
    @staticmethod
    def find_by_serial(serial):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT 'router' AS type, nd.device_id
            FROM routers r
            JOIN network_devices nd ON r.device_id = nd.device_id
            WHERE r.serial_number=%s

            UNION

            SELECT 'server' AS type, nd.device_id
            FROM servers s
            JOIN network_devices nd ON s.device_id = nd.device_id
            WHERE s.serial_number=%s
        """

        cursor.execute(sql, (serial, serial))
        row = cursor.fetchone()

        cursor.close()
        conn.close()
        return row

    # FIND DEVICE BY device_id
    @staticmethod
    def find_by_device_id(device_id):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True)

        # 1. Ambil dari tabel global network_devices
        sql_global = "SELECT * FROM network_devices WHERE device_id=%s"
        cursor.execute(sql_global, (device_id,))
        global_row = cursor.fetchone()

        if not global_row:
            cursor.close()
            conn.close()
            return None

        dtype = global_row["device_type"]

        # 2. Tentukan tabel detail berdasarkan device_type
        table_map = {
            "router": "routers",
            "server": "servers",
            "switch": "switchs",
            "access_point": "access_points"
        }
        
        table = table_map.get(dtype, "routers")

        sql_detail = f"SELECT * FROM {table} WHERE device_id=%s"
        cursor.execute(sql_detail, (device_id,))
        detail_row = cursor.fetchone()

        cursor.close()
        conn.close()

        if not detail_row:
            return global_row

        # 3. Gabungkan dua row menjadi satu dict
        return {
            **global_row,
            **detail_row
        }

    # INSERT KE TABEL GLOBAL network_devices
    @staticmethod
    def insert_network_device(dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

        sql = """
            INSERT INTO network_devices
            (device_id, device_type, southbound, status, created_at, updated_at, last_seen)
            VALUES (%s, %s, %s, %s, NOW(), NOW(), NOW())
        """

        cursor.execute(sql, (
            dev["device_id"],
            dev["device_type"],
            dev["southbound"],
            dev.get("status", "active")
        ))

        conn.commit()
        new_id = cursor.lastrowid

        cursor.close()
        conn.close()
        return new_id

    # UPDATE TABEL GLOBAL network_devices
    @staticmethod
    def update_network_device(device_id, data):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

        sql = """
            UPDATE network_devices 
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
        cursor.close()
        conn.close()

    # INSERT SERVER
    @staticmethod
    def insert_server(dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

        sql = """
            INSERT INTO servers
            (device_id, hostname, main_username, os_version, architecture,
             architecture_bits, processor_type, vendor, main_ip_address,
             main_mac_address, main_interface, southbound, status,
             cpu_cores, memory_total, disk_total, virtualization,
             created_at, updated_at, last_seen)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
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
            dev.get("cpu_cores", 0),
            dev.get("memory_total", 0),
            dev.get("disk_total", 0),
            dev.get("virtualization", "physical")
        ))

        conn.commit()
        cursor.close()
        conn.close()

    # UPDATE SERVER
    @staticmethod
    def update_server(device_id, dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

        sql = """
            UPDATE servers 
            SET hostname=%s, main_username=%s, os_version=%s, architecture=%s,
                architecture_bits=%s, processor_type=%s, vendor=%s, main_ip_address=%s,
                main_mac_address=%s, main_interface=%s, southbound=%s, status=%s,
                cpu_cores=%s, memory_total=%s, disk_total=%s, virtualization=%s,
                updated_at=NOW(), last_seen=%s
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
            dev.get("cpu_cores", 0),
            dev.get("memory_total", 0),
            dev.get("disk_total", 0),
            dev.get("virtualization", "physical"),
            dev.get("last_seen"),
            device_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

    # INSERT ROUTER
    @staticmethod
    def insert_router(dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

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
        cursor.close()
        conn.close()

    # UPDATE ROUTER
    @staticmethod
    def update_router(device_id, dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

        sql = """
            UPDATE routers 
            SET username=%s, password=%s, identity=%s, os_version=%s,
                board=%s, serial_number=%s, vendor=%s, main_ip_address=%s,
                main_mac_address=%s, main_interface=%s, southbound=%s, status=%s,
                updated_at=NOW(), last_seen=%s
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
            dev.get("last_seen", ""),
            device_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

    # INSERT SWITCH
    @staticmethod
    def insert_switch(global_id, dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

        sql = """
            INSERT INTO switchs
            (network_device_id, username, password, identity, os_version,
             board, serial_number, vendor, main_ip_address,
             main_mac_address, main_interface, status, last_seen)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW())
        """

        cursor.execute(sql, (
            global_id,
            dev.get("username"),
            dev.get("password"),
            dev.get("identity"),
            dev.get("version"),
            dev.get("board"),
            dev.get("serial_number"),
            dev.get("vendor"),
            dev.get("ip"),
            dev.get("mac_address"),
            dev.get("main_interface"),
            "connected"
        ))

        conn.commit()
        cursor.close()
        conn.close()

    # INSERT ACCESS POINT
    @staticmethod
    def insert_access_point(global_id, dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

        sql = """
            INSERT INTO access_points
            (network_device_id, username, password, identity, os_version,
             board, serial_number, vendor, main_ip_address,
             main_mac_address, main_interface, status, last_seen)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW())
        """

        cursor.execute(sql, (
            global_id,
            dev.get("username"),
            dev.get("password"),
            dev.get("identity"),
            dev.get("version"),
            dev.get("board"),
            dev.get("serial_number"),
            dev.get("vendor"),
            dev.get("ip"),
            dev.get("mac_address"),
            dev.get("main_interface"),
            "connected"
        ))

        conn.commit()
        cursor.close()
        conn.close()

    # LIST ALL GLOBAL DEVICES
    @staticmethod
    def list_all():
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM network_devices")
        rows = cursor.fetchall()

        cursor.close()
        conn.close()
        return rows

    # DELETE DEVICE
    @staticmethod
    def delete_device(device_id):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

        try:
            # Cari device_type dulu
            sql_get_type = "SELECT device_type FROM network_devices WHERE device_id=%s"
            cursor.execute(sql_get_type, (device_id,))
            result = cursor.fetchone()
            
            if result:
                device_type = result[0]
                
                # Hapus dari tabel detail
                table_map = {
                    "server": "servers",
                    "router": "routers",
                    "switch": "switchs", 
                    "access_point": "access_points"
                }
                
                table = table_map.get(device_type)
                if table:
                    sql_delete_detail = f"DELETE FROM {table} WHERE device_id=%s"
                    cursor.execute(sql_delete_detail, (device_id,))
                
                # Hapus dari network_devices
                sql_delete_network = "DELETE FROM network_devices WHERE device_id=%s"
                cursor.execute(sql_delete_network, (device_id,))
                
                conn.commit()
                cursor.close()
                conn.close()
                return True
            
            return False
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            raise e