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
        self._transport = None  # Tambahkan transport reference
        
    def connect(self):
        """Connect ke Cisco device via SSH"""
        try:
            print(f"[SSH-BASE] Connecting to {self.config['ip']}:{self.config.get('port', 22)}")
            
            username = self.config.get('username')
            password = self.config.get('password')
            
            if not username:
                raise Exception("Username not provided in config")
            if not password:
                raise Exception("Password not provided in config")

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect((self.config['ip'], self.config.get('port', 22)))
            
            # Create transport dengan manual configuration
            self._transport = paramiko.Transport(sock)
            
            # FORCE CISCO COMPATIBLE ALGORITHMS
            self._transport.get_security_options().kex = [
                'diffie-hellman-group-exchange-sha1',
                'diffie-hellman-group14-sha1',
                'diffie-hellman-group1-sha1'
            ]
            
            self._transport.get_security_options().ciphers = [
                'aes128-cbc', 'aes256-cbc', '3des-cbc'
            ]
            
            self._transport.start_client()
            
            # Authentication
            self._transport.auth_password(
                username=str(username), 
                password=str(password)
            )
            
            # Create SSH client wrapper
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client._transport = self._transport
            
            # Create interactive shell
            self.shell = self._transport.open_session()
            self.shell.invoke_shell()
            self.shell.settimeout(15)
            
            time.sleep(2)
            
            # Clear initial buffer
            self._clear_buffer_completely()
            
            # ==========================================
            # Masuk Enable Mode
            if self.config.get('enable', True):
                print("[SSH-BASE] Entering enable mode...")
                enable_pass = self.config.get('enable_password') or self.config.get('password')
                
                # Send enable command
                self.shell.send("enable\n")
                time.sleep(1)
                
                # Check if password required
                enable_check = ""
                for _ in range(3):
                    if self.shell.recv_ready():
                        enable_check += self.shell.recv(4096).decode('utf-8', errors='ignore')
                    time.sleep(0.5)
                
                if "Password:" in enable_check or "password" in enable_check.lower():
                    self.shell.send(enable_pass + "\n")
                    time.sleep(1)
                
                # Wait for enable prompt (#)
                time.sleep(2)
                self._clear_buffer_completely()
                
                # Send enter to check prompt
                self.shell.send("\n")
                time.sleep(1)
            
            self.connected = True
            print(f"[SSH-BASE] ✓ Connected successfully to {self.config['ip']}")
            
            return True
            
        except paramiko.AuthenticationException as e:
            print(f"[SSH-BASE] Authentication failed: {e}")
            self.connected = False
            raise Exception(f"Authentication failed: {str(e)}")
        except Exception as e:
            print(f"[SSH-BASE] Connection failed: {e}")
            self.connected = False
            # Cleanup
            if self._transport:
                try:
                    self._transport.close()
                except:
                    pass
            self._transport = None
            self.shell = None
            self.ssh_client = None
            raise Exception(f"Connection failed: {str(e)}")
    
    def _clear_buffer_completely(self):
        """Clear shell buffer completely"""
        if not self.shell:
            return
        
        try:
            # Small timeout untuk clear buffer
            original_timeout = self.shell.gettimeout()
            self.shell.settimeout(0.1)
            
            cleared = 0
            while True:
                try:
                    data = self.shell.recv(4096)
                    if not data:
                        break
                    cleared += len(data)
                except socket.timeout:
                    break
                except:
                    break
            
            if cleared > 0:
                print(f"[SSH-BASE] Cleared {cleared} bytes from buffer")
            
            self.shell.settimeout(original_timeout)
        except:
            pass
    
    def execute_command(self, command, enable_mode=True, timeout=10):
        """Execute single command - FIXED CLEANING VERSION"""
        try:
            with self.lock:
                print(f"[SSH-BASE] Executing command: {command}")
                
                if not self.connected or not self.shell:
                    return f"ERROR: SSH not properly connected"
                
                original_timeout = self.shell.gettimeout()
                self.shell.settimeout(timeout)
                
                try:
                    # Clear buffer sebelum kirim command
                    time.sleep(0.5)
                    self._clear_buffer_completely()
                    
                    # Kirim command
                    self.shell.send(command + "\n")
                    
                    # Tunggu output
                    time.sleep(2)
                    
                    # Baca output
                    output = ""
                    start_time = time.time()
                    
                    while time.time() - start_time < timeout:
                        try:
                            if self.shell.recv_ready():
                                chunk = self.shell.recv(4096).decode('utf-8', errors='ignore')
                                output += chunk
                                
                                # Cek jika sudah dapat prompt
                                if '#' in chunk or '>' in chunk:
                                    time.sleep(0.5)
                                    continue
                            else:
                                if time.time() - start_time > timeout:
                                    break
                                time.sleep(0.1)
                        except socket.timeout:
                            break
                        except Exception as e:
                            print(f"[SSH-BASE] Read error: {e}")
                            break
                    
                    # === PERBAIKAN BESAR: CLEANING OUTPUT YANG LEBIH BAIK ===
                    lines = output.split('\n')
                    cleaned_lines = []
                    
                    for line in lines:
                        # Bersihkan karakter control
                        line = line.strip('\r').strip()
                        
                        # Skip empty lines
                        if not line:
                            continue
                        
                        # HAPUS SEMUA LINE YANG MENGANDUNG ERROR MARKER
                        if '^' in line or '%' in line:
                            continue
                        
                        # HAPUS PROMPT LINES (Switch#, Router#)
                        if line.endswith('#') or line.endswith('>'):
                            # Jika hanya prompt tanpa data, skip
                            if len(line) < 10:
                                continue
                            # Jika ada data setelah prompt, ambil data saja
                            prompt_pos = max(line.rfind('#'), line.rfind('>'))
                            if prompt_pos != -1:
                                line = line[prompt_pos+1:].strip()
                        
                        # HAPUS COMMAND ECHO
                        if command in line and len(line) < len(command) + 5:
                            continue
                        
                        # HAPUS LINES DENGAN "Invalid input"
                        if 'invalid input' in line.lower():
                            continue
                        
                        # HAPUS LINES DENGAN "Translating"
                        if 'translating' in line.lower():
                            continue
                        
                        # Simpan line yang sudah dibersihkan
                        if line:  # Pastikan tidak empty setelah cleaning
                            cleaned_lines.append(line)
                    
                    # Join kembali
                    cleaned_output = '\n'.join(cleaned_lines)
                    
                    # Final cleanup: hapus whitespace berlebih
                    cleaned_output = re.sub(r'\n\s*\n', '\n', cleaned_output)  # Hapus empty lines
                    cleaned_output = cleaned_output.strip()
                    
                    print(f"[SSH-BASE] Command output cleaned: {len(cleaned_output)} chars")
                    if cleaned_output and len(cleaned_output) < 200:
                        print(f"[SSH-BASE] Clean output preview: '{cleaned_output[:100]}'")
                    
                    return cleaned_output
                    
                except Exception as e:
                    print(f"[SSH-BASE] Command execution error: {e}")
                    return f"ERROR: {str(e)}"
                finally:
                    self.shell.settimeout(original_timeout)
                    
        except Exception as e:
            print(f"[SSH-BASE] Outer execute_command error: {e}")
            return f"ERROR: {str(e)}"
    
    def _detect_capabilities(self):
        """Detect capabilities - SIMPLIFIED"""
        try:
            self._capabilities = {
                'stp': True,
                'qos': True,
                'port_security': True,
                'lldp': True,
                'snmp': True,
                'model': 'Unknown',
                'ios_version': 'Unknown',
                'device_family': 'Cisco Switch',
                'is_virtual': False,
                'is_iosxe': False,
                'is_nexus': False
            }
            
            # Get basic info
            version_output = self.execute_command("show version")
            
            if version_output and "ERROR" not in version_output:
                # Simple parsing
                lines = version_output.split('\n')
                for line in lines:
                    line_lower = line.lower()
                    
                    if 'version' in line_lower and 'ios' in line_lower:
                        # Try to extract version
                        version_match = re.search(r'[Vv]ersion\s+([^,\s]+)', line)
                        if version_match:
                            self._capabilities['ios_version'] = version_match.group(1)
                    
                    if 'cisco' in line_lower and ('2960' in line_lower or '3560' in line_lower or '3750' in line_lower):
                        model_match = re.search(r'[Cc]isco\s+(\S+)', line)
                        if model_match:
                            self._capabilities['model'] = model_match.group(1)
            
            print(f"[SSH-BASE] Capabilities: {self._capabilities}")
            return self._capabilities
            
        except Exception as e:
            print(f"[SSH-BASE] Capability detection error: {e}")
            return self._capabilities
    
    def get_capabilities(self):
        """Return device capabilities"""
        if not self._capabilities:
            self._detect_capabilities()
        return self._capabilities or {}
    
    def disconnect(self):
        """Close SSH connection"""
        try:
            if self._transport and self._transport.is_active():
                self._transport.close()
        except:
            pass
        
        self.connected = False
        self._transport = None
        self.shell = None
        self.ssh_client = None
        print(f"[SSH-BASE] Disconnected")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()