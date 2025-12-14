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
        """Get server interfaces dengan semua IPs"""
        conn = DBConnection.get_conn()
        cursor = conn.cursor(dictionary=True, buffered=True)

        try:
            sql = """
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
            """
            
            cursor.execute(sql, (device_id,))
            interfaces = cursor.fetchall()
            
            # Parse all_ips JSON untuk setiap interface
            for iface in interfaces:
                if iface.get("all_ips"):
                    try:
                        iface["all_ips"] = json.loads(iface["all_ips"])
                        iface["ip_addresses"] = iface["all_ips"]  # Alias untuk response API
                    except:
                        iface["all_ips"] = []
                        iface["ip_addresses"] = []
                else:
                    iface["all_ips"] = []
                    iface["ip_addresses"] = []
                    
                    # Jika ada ip_address tapi tidak ada all_ips, buat array dari ip_address
                    if iface.get("ip_address"):
                        ip_str = iface["ip_address"]
                        if iface.get("ip_netmask"):
                            ip_str += f"/{iface['ip_netmask']}"
                        iface["all_ips"] = [ip_str]
                        iface["ip_addresses"] = [ip_str]
            
            return interfaces

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
                (server_id, interface_name, interface_status, mac_address,
                ip_address, ip_netmask, ip_broadcast, ip_version,
                created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """

            cursor.execute(sql, (
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
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error updating device status: {e}")
            return False

    # ============================
    # SIMPLE AUTO-UPDATE METHODS
    # ============================
    @staticmethod
    def update_server_firewall_state(device_id, firewall_state):
        """Update firewall state ke database setelah action"""
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
            
            # DEBUG: Print firewall state yang diterima
            print(f"[DB-AUTO-DEBUG] Firewall state received: {firewall_state}")
            print(f"[DB-AUTO-DEBUG] Type: {type(firewall_state)}")
            
            # Deteksi firewall type
            firewall_type = firewall_state.get("detected_firewall", "unknown")
            if not firewall_type or firewall_type == "unknown":
                firewall_type = firewall_state.get("firewall_type", "unknown")
            
            # Default values
            status = "unknown"
            rules_count = 0
            
            # Parse status berdasarkan firewall type
            if firewall_type == "ufw":
                # Parse ufw_status dari response agent
                ufw_status_raw = firewall_state.get("ufw_status", "")
                print(f"[DB-AUTO-DEBUG] ufw_status raw: {ufw_status_raw}")
                
                if "Status: active" in str(ufw_status_raw):
                    status = "active"
                elif "Status: inactive" in str(ufw_status_raw):
                    status = "inactive"
                else:
                    # Coba parsing lain
                    if "inactive" in str(ufw_status_raw).lower():
                        status = "inactive"
                    elif "active" in str(ufw_status_raw).lower():
                        status = "active"
                
                # Hitung rules (dari iptables_filter)
                iptables_filter = firewall_state.get("iptables_filter", "")
                if iptables_filter:
                    # Hitung baris yang mengandung "ACCEPT" atau "DROP" atau "REJECT"
                    lines = iptables_filter.split('\n')
                    for line in lines:
                        if "ACCEPT" in line or "DROP" in line or "REJECT" in line:
                            rules_count += 1
            
            elif firewall_type == "firewalld":
                # Parse firewalld status
                status = firewall_state.get("status", "unknown")
                # Rules count bisa dari output firewall-cmd --list-all
            
            elif firewall_type == "iptables":
                # Parse iptables rules count
                iptables_filter = firewall_state.get("iptables_filter", "")
                if iptables_filter:
                    lines = iptables_filter.split('\n')
                    for line in lines:
                        if "ACCEPT" in line or "DROP" in line or "REJECT" in line:
                            rules_count += 1
                    status = "active" if rules_count > 0 else "inactive"
            
            print(f"[DB-AUTO-DEBUG] Parsed values - Type: {firewall_type}, Status: {status}, Rules: {rules_count}")
            
            # Update atau insert firewall data
            sql = """
                INSERT INTO server_firewalls 
                (server_id, firewall_type, status, default_zone, active_zones, 
                rules_count, last_checked, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    firewall_type = VALUES(firewall_type),
                    status = VALUES(status),
                    default_zone = VALUES(default_zone),
                    active_zones = VALUES(active_zones),
                    rules_count = VALUES(rules_count),
                    last_checked = VALUES(last_checked),
                    updated_at = NOW()
            """
            
            # Default values untuk zone
            default_zone = "N/A"
            active_zones = "[]"
            
            cursor.execute(sql, (
                server_id,
                firewall_type,
                status,
                default_zone,
                active_zones,
                rules_count
            ))
            
            conn.commit()
            print(f"[DB-AUTO-SUCCESS] Updated firewall for {device_id}: {firewall_type} - {status}")
            
            # Verify update
            cursor.execute("""
                SELECT firewall_type, status, rules_count 
                FROM server_firewalls 
                WHERE server_id = %s
            """, (server_id,))
            
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

    @staticmethod
    def update_interface_state(device_id, interface_name, interface_data):
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