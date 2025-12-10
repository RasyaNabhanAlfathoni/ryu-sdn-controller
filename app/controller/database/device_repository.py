from database.db_connection import DBConnection
import json

class DeviceRepository:

    @staticmethod
    def insert_network_device(dev):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

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
        new_id = cursor.lastrowid

        cursor.close()
        conn.close()
        return new_id

    # UPDATE TABEL GLOBAL devices
    @staticmethod
    def update_network_device(device_id, data):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

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
        cursor.close()
        conn.close()

    # CEK DOUBLE REGISTER (BERDASARKAN SERIAL_NUMBER) - Untuk routers saja
    @staticmethod
    def find_by_serial(serial):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT 'router' AS type, r.device_id
            FROM routers r
            WHERE r.serial_number=%s
        """

        cursor.execute(sql, (serial,))
        row = cursor.fetchone()

        cursor.close()
        conn.close()
        return row

    # FIND DEVICE BY device_id
    @staticmethod
    def find_by_device_id(device_id):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True)

        # 1. Cek di tabel servers terlebih dahulu
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

        if server_row:
            cursor.close()
            conn.close()
            return server_row

        # 2. Jika bukan server, cek di routers
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

        cursor.close()
        conn.close()
        return router_row

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
        new_id = cursor.lastrowid

        cursor.close()
        conn.close()
        return new_id

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
        cursor.close()
        conn.close()

    # GET ALL SERVERS
    @staticmethod
    def get_all_servers():
        """
        Get all servers dengan SEMUA field
        """
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True)

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

        cursor.close()
        conn.close()
        return rows

    # GET ALL ROUTERS
    @staticmethod
    def get_all_routers():
        """
        Get all routers dengan SEMUA field
        """
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True)

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

        cursor.close()
        conn.close()
        return rows

    # LIST ALL DEVICES (gabungkan servers dan routers)
    @staticmethod
    def list_all():
        """
        List semua devices dengan menggabungkan servers dan routers
        """
        servers = DeviceRepository.get_all_servers()
        routers = DeviceRepository.get_all_routers()
        
        # Gabungkan dan sort by last_seen
        all_devices = servers + routers
        all_devices.sort(key=lambda x: x.get('last_seen', ''), reverse=True)
        
        return all_devices

    # DELETE DEVICE
    @staticmethod
    def delete_device(device_id):
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

        try:
            # 1. Hapus dari tabel dependent dulu
            # Tidak perlu hapus server_interface_ips karena sudah merged
            
            # Hapus server_firewalls
            sql_delete_firewalls = """
                DELETE sf FROM server_firewalls sf
                INNER JOIN servers s ON sf.server_id = s.id
                WHERE s.device_id = %s
            """
            cursor.execute(sql_delete_firewalls, (device_id,))
            
            # Hapus server_interfaces
            sql_delete_interfaces = """
                DELETE si FROM server_interfaces si
                INNER JOIN servers s ON si.server_id = s.id
                WHERE s.device_id = %s
            """
            cursor.execute(sql_delete_interfaces, (device_id,))
            
            # 2. Hapus dari tabel utama
            sql_delete_server = "DELETE FROM servers WHERE device_id=%s"
            cursor.execute(sql_delete_server, (device_id,))
            server_deleted = cursor.rowcount > 0
            
            if not server_deleted:
                sql_delete_router = "DELETE FROM routers WHERE device_id=%s"
                cursor.execute(sql_delete_router, (device_id,))
                router_deleted = cursor.rowcount > 0
            
            # 3. Hapus dari tabel devices
            sql_delete_device = "DELETE FROM devices WHERE device_id=%s"
            cursor.execute(sql_delete_device, (device_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            raise e

    # GET SERVER INTERFACES
    @staticmethod
    def get_server_interfaces(device_id):
        """
        Get interfaces for a server by device_id
        Returns: list of interfaces with IP data
        """
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True)

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
        interfaces = cursor.fetchall()

        cursor.close()
        conn.close()
        return interfaces

    # GET SERVER FIREWALL
    @staticmethod
    def get_server_firewall(device_id):
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True)

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
        firewall = cursor.fetchone()

        cursor.close()
        conn.close()
        return firewall

    # INSERT SERVER INTERFACE
    @staticmethod
    def insert_server_interface(data):
        """
        Insert a server interface dengan semua data IP
        data: {
            "server_id": int (ID dari tabel servers, bukan device_id),
            "interface_name": str,
            "mac_address": str,
            "ip_address": str,
            "ip_netmask": str,
            "ip_broadcast": str,
            "ip_version": str
        }
        """
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

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

        interface_id = cursor.lastrowid
        conn.commit()
        
        cursor.close()
        conn.close()
        return interface_id

    # UPSERT SERVER FIREWALL
    @staticmethod
    def upsert_server_firewall(data):
        """
        Insert or update server firewall
        data: {
            "server_id": int (ID dari tabel servers, bukan device_id),
            "firewall_type": str,
            "status": str,
            "default_zone": str,
            "active_zones": str (JSON string),
            "rules_count": int,
            "last_checked": datetime string
        }
        """
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

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
        cursor.close()
        conn.close()

    # GET SERVER ID BY DEVICE_ID
    @staticmethod
    def get_server_id(device_id):
        """
        Get server ID (primary key) from device_id
        """
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

        sql = "SELECT id FROM servers WHERE device_id = %s"
        cursor.execute(sql, (device_id,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()
        
        if result:
            return result[0]  # Return server.id
        return None

    # DELETE SERVER INTERFACES (untuk controller.py)
    @staticmethod
    def delete_server_interfaces(device_id):
        """
        Delete all interfaces for a server by device_id
        """
        conn = DBConnection.get_conn()
        cursor = conn.cursor()

        try:
            # 1. Get server id first
            server_id = DeviceRepository.get_server_id(device_id)
            if not server_id:
                return False
            
            # 2. Delete interfaces (tidak perlu delete IPs terpisah lagi)
            sql_delete_interfaces = "DELETE FROM server_interfaces WHERE server_id = %s"
            cursor.execute(sql_delete_interfaces, (server_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            raise e