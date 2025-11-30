import requests
import json
import base64
from typing import Dict, List, Optional
import urllib3
import ssl
import sys
import datetime
from drivers.server_drivers.server_api import ServerAPI

# Workaround untuk SSL recursion error di Python 3.9
def patch_ssl():
    """Patch SSL context untuk menghindari recursion error"""
    try:
        # Method 1: Disable SSL verification completely
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
    except:
        pass
    
    # Method 2: Disable urllib3 warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Method 3: Patch untuk Python 3.9 SSL recursion bug
    try:
        import urllib3.util.ssl_ as ssl_
        original_create_urllib3_context = ssl_.create_urllib3_context
        
        def patched_create_urllib3_context():
            context = original_create_urllib3_context()
            # Skip problematic minimum_version setting
            return context
            
        ssl_.create_urllib3_context = patched_create_urllib3_context
    except Exception as e:
        print(f"SSL context patch 2 warning: {e}")

# Apply patch saat module load
patch_ssl()

class WazuhAPI:
    def __init__(self, base_url: str, username: str, password: str, core=None, logger=None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.core = core
        self.logger = logger
        self.token_expiry = None
        
        # Buat custom session dengan SSL workaround
        self.session = self._create_secure_session()
        self.token = self._authenticate(username, password)
    
    def _log(self, message: str):
        """Helper logging yang handle both function dan object logger"""
        if self.logger:
            if callable(self.logger):  # Jika logger adalah function
                self.logger(message)
            else:  # Jika logger adalah object (Ryu logger)
                self.logger.info(message)
        else:
            print(f"[WazuhAPI] {message}")

    def _create_secure_session(self):
        """Create session dengan SSL workarounds"""
        session = requests.Session()
        
        # Disable SSL verification
        session.verify = False
        
        # Custom adapter dengan retry strategy
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _is_token_expired(self):
        """Check if token is expired"""
        if not self.token_expiry:
            return True
        return datetime.datetime.now() >= self.token_expiry
    
    def _ensure_valid_token(self):
        """Ensure token is valid, refresh jika dibutuhkan"""
        if self._is_token_expired():
            self._log("Token expired, refreshing...")
            self.token = self._authenticate(self.username, self.password)
        
    def _authenticate(self, username: str, password: str) -> str:
        """Authenticate dengan Wazuh API"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                auth_url = f"{self.base_url}/security/user/authenticate"
                
                self._log(f"Wazuh auth attempt {attempt + 1}/{max_retries}")
                
                response = self.session.post(
                    auth_url,
                    auth=(username, password),
                    timeout=10,  # Shorter timeout
                    verify=False  # Explicitly disable verification
                )
                
                response.raise_for_status()
                token_data = response.json()['data']
                token = token_data['token']

                # Setiap 5 menit ganti token
                self.token_expiry = datetime.datetime.now() + datetime.timedelta(minutes=5) 
                
                self._log("Wazuh authentication successful")
                return token
                
            except requests.exceptions.SSLError as e:
                self._log(f"SSL Error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                continue
                    
            except requests.exceptions.ConnectTimeout:
                self._log(f"Connection timeout (attempt {attempt + 1})")
                if attempt == max_retries - 1:
                    raise
                continue
                    
            except Exception as e:
                self._log(f"Auth failed (attempt {attempt + 1}): {e}")
                raise
        
        raise Exception("All authentication attempts failed")
    
    
    def _get_headers(self) -> Dict:
        """Get headers dengan token"""
        self._ensure_valid_token()
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def install_agent(self, device_id: str, manager_ip: str, logger=None) -> Dict:
        """COMPLETE Wazuh installation flow: Register + Trigger Agent Installation"""
        log = logger or self._log
        
        # Get device info
        device = self.core.devices.get(device_id) if self.core and hasattr(self.core, 'devices') else None
        if not device:
            return {"status": "error", "error": f"Device {device_id} not found"}
        
        agent_name = device.get('hostname', f"device-{device_id}")
        agent_ip = device.get('ip') or device.get('main_ip_address', 'unknown')
        
        log(f"Starting COMPLETE Wazuh installation for {agent_name}...")
        
        try:
            #  Register agent di Wazuh Manager
            log(f"Registering agent in Wazuh manager: {agent_name}")
            agent_info = self.add_agent(agent_name, agent_ip)
            agent_id = agent_info['id']
            agent_key_encoded = self.get_agent_key(agent_id)
            
            # Decode base64 agent key
            import base64
            agent_key_decoded = agent_key_encoded
            try:
                agent_key_decoded = base64.b64decode(agent_key_encoded).decode('utf-8')
                log(f"Agent registered in Wazuh manager: {agent_id}")
                log(f"Agent key (decoded): {agent_key_decoded}")
            except Exception as e:
                log(f"Failed to decode agent key: {e}")
                log(f"Using agent key as-is: {agent_key_decoded}")

            # Update device metadata
            device["meta"] = device.get("meta", {})
            device["meta"].update({
                "wazuh_agent_id": agent_id,
                "wazuh_agent_name": agent_name,
                "wazuh_manager_ip": manager_ip,
                "wazuh_agent_key": agent_key_decoded,
                "wazuh_registered_at": datetime.datetime.now().isoformat()
            })
            
            # Trigger agent side installation via ServerAPI 
            log(f"Triggering agent side installation for {agent_name}...")
            
            # Gunakan ServerAPI untuk komunikasi dengan agent
            server_api = ServerAPI(device)
            installation_result = server_api.wazuh_install(
                manager_ip=manager_ip,
                agent_key=agent_key_decoded, 
                agent_name=agent_name,
                logger=log
            )
            
            log(f"Agent side installation result: {installation_result}")
            
            # Return comprehensive result
            result = {
                "status": "success",
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_key": agent_key_decoded,
                "manager_ip": manager_ip,
                "message": f"Wazuh agent installation process completed for {agent_name}",
                "steps": [
                    f"✓ Agent registered in Wazuh manager (ID: {agent_id})",
                    f"✓ Agent authentication key obtained",
                    f"✓ Agent side installation triggered",
                    f"→ Agent should connect to manager shortly"
                ],
                "installation_result": installation_result
            }
            
            log(f"Wazuh installation process completed for {agent_name}")
            return result
            
        except Exception as e:
            error_msg = f"Wazuh installation failed: {str(e)}"
            log(f"{error_msg}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            return {"status": "error", "error": error_msg}

    def uninstall_agent(self, device_id: str, logger=None) -> Dict:
        """COMPLETE Wazuh uninstallation flow"""
        log = logger or self._log
        
        device = self.core.devices.get(device_id) if self.core else None
        if not device:
            return {"status": "error", "error": f"Device {device_id} not found"}
        
        agent_id = device.get("meta", {}).get("wazuh_agent_id")
        agent_name = device.get("meta", {}).get("wazuh_agent_name", "unknown")
        
        log(f"Starting Wazuh uninstall for {agent_name}...")
        
        try:
            # === STEP 1: Trigger agent side uninstallation ===
            log("Triggering agent side uninstallation...")
            server_api = ServerAPI(device)
            uninstall_result = server_api.wazuh_uninstall(logger=log)
            
            # === STEP 2: Remove agent dari Wazuh manager ===
            if agent_id:
                try:
                    self.delete_agent(agent_id)
                    log(f"Agent {agent_id} removed from Wazuh manager")
                except Exception as e:
                    log(f"Failed to remove agent from manager: {e}")
            
            # === STEP 3: Clear device metadata ===
            if "meta" in device:
                device["meta"].pop("wazuh_agent_id", None)
                device["meta"].pop("wazuh_agent_name", None)
                device["meta"].pop("wazuh_manager_ip", None)
                device["meta"].pop("wazuh_agent_key", None)
                device["meta"].pop("wazuh_registered_at", None)
            
            result = {
                "status": "success",
                "agent_id": agent_id,
                "agent_name": agent_name,
                "message": f"Wazuh agent uninstall process completed for {agent_name}",
                "uninstall_result": uninstall_result
            }
            
            log(f"Wazuh uninstall process completed for {agent_name}")
            return result
            
        except Exception as e:
            error_msg = f"Wazuh uninstall failed: {str(e)}"
            log(f"{error_msg}")
            return {"status": "error", "error": error_msg}
    
    def get_agent_status(self, device_id: str, logger=None) -> Dict:
        """Get agent status"""
        log = logger or self._log
        
        device = self.core.devices.get(device_id) if self.core else None
        if not device:
            return {"status": "error", "error": f"Device {device_id} not found"}
        
        agent_id = device.get("meta", {}).get("wazuh_agent_id")
        
        status = {
            "device_id": device_id,
            "device_name": device.get('hostname'),
            "registered": bool(agent_id),
            "agent_id": agent_id,
            "manager_status": None,
            "installation_status": "unknown"  # Akan di-update oleh ryu-agent
        }
        
        # Check Wazuh manager status
        if agent_id:
            try:
                agents = self.get_agents()
                manager_agent = next((a for a in agents if a['id'] == agent_id), None)
                
                if manager_agent:
                    status["manager_status"] = {
                        "status": manager_agent.get('status', 'unknown'),
                        "connected": manager_agent.get('status') == 'active',
                        "last_keepalive": manager_agent.get('lastKeepAlive'),
                        "version": manager_agent.get('version'),
                        "ip": manager_agent.get('ip')
                    }
                    log(f"Agent {agent_id} status: {manager_agent.get('status')}")
                else:
                    status["manager_status"] = {"status": "not_found"}
                    log(f"Agent {agent_id} not found in Wazuh manager")
                    
            except Exception as e:
                status["manager_status"] = {"error": str(e)}
                log(f"Error checking manager status: {e}")
        
        return status
    
    def get_security_overview(self, device_id: str, logger=None) -> Dict:
        """Get security overview"""
        log = logger or self._log
        
        device = self.core.devices.get(device_id) if self.core else None
        if not device:
            return {"status": "error", "error": f"Device {device_id} not found"}
        
        agent_id = device.get("meta", {}).get("wazuh_agent_id")
        if not agent_id:
            return {"status": "error", "error": "Device not registered with Wazuh"}
        
        log(f"Getting security overview for agent {agent_id}...")
        
        try:
            vulnerabilities = self.get_vulnerabilities(agent_id)
            fim_data = self.get_fim_data(agent_id)
            syscollector_data = self.get_agent_security_events(agent_id, limit=50)
            
            # Calculate risk level
            critical_vulns = [v for v in vulnerabilities if v.get('severity', '').lower() == 'critical']
            high_vulns = [v for v in vulnerabilities if v.get('severity', '').lower() == 'high']
            total_risk = (len(critical_vulns) * 3) + (len(high_vulns) * 2) + len(fim_data)
            
            risk_level = "CRITICAL" if total_risk >= 10 else "HIGH" if total_risk >= 5 else "MEDIUM" if total_risk >= 2 else "LOW"
            
            overview = {
                "status": "success",
                "agent_id": agent_id,
                "device_name": device.get('hostname'),
                "summary": {
                    "vulnerabilities": len(vulnerabilities),
                    "critical_vulnerabilities": len(critical_vulns),
                    "high_vulnerabilities": len(high_vulns),
                    "fim_alerts": len(fim_data),
                    "system_inventory": len(syscollector_data)
                },
                "risk_level": risk_level,
                "last_updated": datetime.datetime.now().isoformat()
            }
            
            log(f"Security overview generated for {agent_id}")
            return overview
            
        except Exception as e:
            error_msg = f"Failed to get security overview: {str(e)}"
            log(f"{error_msg}")
            return {"status": "error", "error": error_msg}
    
    # Only Register, nanti dipanggil pada function install_agent()
    def add_agent(self, agent_name: str, agent_ip: str) -> Dict:
        """Add new agent ke Wazuh"""
        try:
            url = f"{self.base_url}/agents"
            payload = {
                "name": agent_name
            }
            
            self._log(f"🔍 DEBUG - URL: {url}")
            self._log(f"🔍 DEBUG - Payload: {payload}")
            self._log(f"🔍 DEBUG - Headers: {self._get_headers()}")
            self._log(f"🔍 DEBUG - Token: {self.token[:50]}...")  # Log partial token
            
            # Test dengan requests langsung dulu
            self._log("🔍 DEBUG - Testing with direct requests...")
            response_direct = requests.post(
                url, 
                headers=self._get_headers(),
                json=payload,
                verify=False,
                timeout=30
            )
            self._log(f"🔍 DEBUG - Direct requests status: {response_direct.status_code}")
            self._log(f"🔍 DEBUG - Direct requests response: {response_direct.text}")
            
            # Test dengan session
            self._log("🔍 DEBUG - Testing with session...")
            response_session = self.session.post(
                url, 
                headers=self._get_headers(),
                json=payload,
                verify=False,
                timeout=30
            )
            self._log(f"🔍 DEBUG - Session status: {response_session.status_code}")
            self._log(f"🔍 DEBUG - Session response: {response_session.text}")
            
            # Gunakan yang berhasil
            if response_direct.status_code == 200:
                self._log("Using direct requests (SUCCESS)")
                agent_data = response_direct.json()['data']
            elif response_session.status_code == 200:
                self._log("Using session (SUCCESS)")
                agent_data = response_session.json()['data']
            else:
                self._log("Both methods failed")
                raise Exception(f"Direct: {response_direct.status_code} - {response_direct.text}, Session: {response_session.status_code} - {response_session.text}")
            
            self._log(f"Wazuh agent added: {agent_data}")
            return agent_data
            
        except Exception as e:
            self._log(f"Failed to add Wazuh agent: {e}")
            import traceback
            self._log(f"Traceback: {traceback.format_exc()}")
            raise
    
    # Only Deregister, nanti dipanggil pada function uninstall_agent()
    def delete_agent(self, agent_id: str) -> Dict:
        """Delete agent dari Wazuh Manager"""
        try:
            url = f"{self.base_url}/agents/{agent_id}"
            response = self.session.delete(url, headers=self._get_headers())
            response.raise_for_status()
            
            self._log(f"Agent {agent_id} deleted from Wazuh manager")
            return {"status": "success", "message": f"Agent {agent_id} deleted"}
            
        except Exception as e:
            self._log(f"Failed to delete agent: {e}")
            raise

    def get_agent_config(self, agent_id: str) -> Dict:
        """Get agent configuration untuk download"""
        try:
            url = f"{self.base_url}/agents/{agent_id}/config"
            response = requests.get(
                url,
                headers=self._get_headers(),
                verify=False
            )
            response.raise_for_status()
            return response.json()['data']
        except Exception as e:
            self._log(f"Failed to get agent config: {e}")
            raise
    
    def get_agent_key(self, agent_id: str) -> str:
        """Get agent authentication key"""
        try:
            url = f"{self.base_url}/agents/{agent_id}/key"
            response = self.session.get(
                url,
                headers=self._get_headers(),
                verify=False,
                timeout=30
            )
            
            self._log(f"Key response status: {response.status_code}")
            self._log(f"Key response text: {response.text}")
            
            if response.status_code != 200:
                self._log(f"Error getting key: {response.text}")
                response.raise_for_status()
            
            response_data = response.json()
            self._log(f"Key response data: {response_data}")
            
            # Handle new response format
            if ('data' in response_data and 
                'affected_items' in response_data['data'] and 
                len(response_data['data']['affected_items']) > 0):
                
                affected_item = response_data['data']['affected_items'][0]
                
                if 'key' in affected_item:
                    key = affected_item['key']
                    self._log(f"Agent key obtained (new format): {key}")
                    return key
                else:
                    self._log(f"No 'key' field in affected_items: {affected_item}")
                    raise Exception(f"No 'key' field in response: {affected_item}")
            
            # Fallback untuk format lama
            elif 'data' in response_data and 'key' in response_data['data']:
                key = response_data['data']['key']
                self._log(f"Agent key obtained (old format): {key}")
                return key
            
            elif 'key' in response_data:
                key = response_data['key']
                self._log(f"Agent key obtained (direct): {key}")
                return key
            
            else:
                self._log(f"Unexpected key response format: {response_data}")
                raise Exception(f"Unexpected key response format: {response_data}")
        except Exception as e:
            self._log(f"Failed to get agent key: {e}")
            raise
    
    def get_agents(self) -> List[Dict]:
        """Get semua agents dari Wazuh"""
        try:
            url = f"{self.base_url}/agents"
            response = requests.get(
                url,
                headers=self._get_headers(),
                verify=False
            )
            response.raise_for_status()
            return response.json()['data']['affected_items']
        except Exception as e:
            self._log(f"Failed to get agents: {e}")
            return []
    
    def get_agent_security_events(self, agent_id: str, limit: int = 100) -> List[Dict]:
        """Get security events dari agent"""
        try:
            url = f"{self.base_url}/syscollector/{agent_id}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                verify=False
            )
            response.raise_for_status()
            return response.json()['data']['affected_items'][:limit]
        except Exception as e:
            self._log(f"Failed to get security events: {e}")
            return []
    
    def get_vulnerabilities(self, agent_id: str) -> List[Dict]:
        """Get vulnerability assessment data"""
        try:
            url = f"{self.base_url}/vulnerability/{agent_id}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                verify=False
            )
            response.raise_for_status()
            return response.json()['data']['affected_items']
        except Exception as e:
            self._log(f"Failed to get vulnerabilities: {e}")
            return []
    
    def get_fim_data(self, agent_id: str) -> List[Dict]:
        """Get File Integrity Monitoring data"""
        try:
            url = f"{self.base_url}/fim/{agent_id}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                verify=False
            )
            response.raise_for_status()
            return response.json()['data']['affected_items']
        except Exception as e:
            self._log(f"Failed to get FIM data: {e}")
            return []