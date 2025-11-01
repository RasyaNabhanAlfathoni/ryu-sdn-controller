from ryu.base import app_manager
import paramiko
import time

class RouterController(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(RouterController, self).__init__(*args, **kwargs)
        self.logger.info("Starting Router Controller via SSH (Paramiko)")
        self.manage_router()

    def manage_router(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            router_ip = "9.9.9.1"
            username = "admin"
            password = "1"  # ganti sesuai router lo

            ssh.connect(router_ip, username=username, password=password)
            self.logger.info("Connected to Router: %s", router_ip)

            # Contoh: ambil daftar interface
            command = "/interface print"
            stdin, stdout, stderr = ssh.exec_command(command)
            time.sleep(1)
            output = stdout.read().decode()

            self.logger.info("=== Router Interface List ===")
            self.logger.info(output)

            # Contoh: buat konfigurasi baru
            cmd2 = "/system identity set name=SDN-Router"
            ssh.exec_command(cmd2)
            self.logger.info("Router identity updated!")

            ssh.close()
        except Exception as e:
            self.logger.error("Error connecting to router: %s", str(e))
