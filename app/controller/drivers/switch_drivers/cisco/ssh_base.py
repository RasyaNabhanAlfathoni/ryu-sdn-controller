import paramiko
import re
import time
import json
from datetime import datetime
import threading
from queue import Queue
import socket

class CiscoSSHBase:
    """SSH base class untuk Cisco"""

    def __init__(self, config):
        self.config = config
        self.ssh_client = None
        self.shell = None
        self.connected = False
        self.lock = threading.Lock()
        self._capabilities = None
        self._transport = None

    def connect(self):
        try:
            print(f"[SSH-BASE] Connecting to {self.config['ip']}:{self.config.get('port', 22)}")

            username = self.config.get('username')
            password = self.config.get('password')

            if not username or not password:
                raise Exception("Username / password not provided")

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect((self.config['ip'], self.config.get('port', 22)))

            self._transport = paramiko.Transport(sock)

            self._transport.get_security_options().kex = [
                'diffie-hellman-group-exchange-sha1',
                'diffie-hellman-group14-sha1',
                'diffie-hellman-group1-sha1'
            ]

            self._transport.get_security_options().ciphers = [
                'aes128-cbc', 'aes256-cbc', '3des-cbc'
            ]

            self._transport.start_client()
            self._transport.set_keepalive(10)

            self._transport.auth_password(
                username=str(username),
                password=str(password)
            )

            self.ssh_client = paramiko.SSHClient()
            self.ssh_client._transport = self._transport

            self.shell = self._transport.open_session()
            self.shell.invoke_shell()
            self.shell.settimeout(10)

            time.sleep(1)
            self._clear_buffer_safe()

            if self.config.get('enable', True):
                enable_pass = self.config.get('enable_password') or password
                self.shell.send("enable\n")
                time.sleep(0.8)

                buff = ""
                for _ in range(3):
                    if self.shell.recv_ready():
                        buff += self.shell.recv(4096).decode(errors="ignore")
                    time.sleep(0.3)

                if "password" in buff.lower():
                    self.shell.send(enable_pass + "\n")
                    time.sleep(1)

                self._clear_buffer_safe()

            self.connected = True
            print(f"[SSH-BASE] Connected successfully to {self.config['ip']}")
            return True

        except Exception as e:
            self.connected = False
            try:
                if self._transport:
                    self._transport.close()
            except:
                pass
            self._transport = None
            self.shell = None
            self.ssh_client = None
            raise Exception(f"Connection failed: {e}")

    def _clear_buffer_safe(self):
        if not self.shell:
            return
        try:
            while self.shell.recv_ready():
                self.shell.recv(4096)
        except:
            pass

    def execute_command(self, command, enable_mode=True, timeout=10):
        try:
            with self.lock:
                if not self.connected or not self.shell:
                    return "ERROR: SSH not connected"

                self.shell.settimeout(timeout)
                self._clear_buffer_safe()

                print(f"[SSH-BASE] Executing command: {command}")
                self.shell.send(command + "\n")

                output = ""
                start = time.time()

                while time.time() - start < timeout:
                    try:
                        if self.shell.recv_ready():
                            chunk = self.shell.recv(4096).decode(errors="ignore")
                            output += chunk
                            if re.search(r'\n\S+[>#]\s*$', output):
                                break
                        else:
                            time.sleep(0.1)
                    except socket.timeout:
                        break
                    except Exception:
                        break

                lines = output.splitlines()
                cleaned = []

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if command in line and len(line) <= len(command) + 5:
                        continue
                    if line.endswith('#') or line.endswith('>'):
                        continue
                    if '^' in line or '%' in line:
                        continue
                    if 'invalid input' in line.lower():
                        continue
                    if 'translating' in line.lower():
                        continue
                    cleaned.append(line)

                result = '\n'.join(cleaned).strip()
                print(f"[SSH-BASE] Command output cleaned: {len(result)} chars")
                return result

        except Exception as e:
            return f"ERROR: {e}"

    def save_configuration(self):
        result = self.execute_command("write memory", enable_mode=True)
        return {
            'status': 'success' if "ERROR" not in result else 'error',
            'result': result
        }

    def _detect_capabilities(self):
        self._capabilities = {
            'stp': True,
            'qos': True,
            'port_security': True,
            'lldp': True,
            'snmp': True
        }
        return self._capabilities

    def get_capabilities(self):
        if not self._capabilities:
            self._detect_capabilities()
        return self._capabilities or {}

    def disconnect(self):
        try:
            if self._transport and self._transport.is_active():
                self._transport.close()
        except:
            pass
        self.connected = False
        self._transport = None
        self.shell = None
        self.ssh_client = None
        print("[SSH-BASE] Disconnected")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
