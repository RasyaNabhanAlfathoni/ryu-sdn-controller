import requests
import json
import base64
from typing import Dict, List, Optional
import urllib3
import ssl
import sys
import datetime

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
        self.token = None
    
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

    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """Generic request handler"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = self._get_headers()
            
            self._log(f"Request: {method} {url}")
            
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, params=params, verify=False, timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, json=data, params=params, verify=False, timeout=30)
            elif method.upper() == 'PUT':
                response = self.session.put(url, headers=headers, json=data, params=params, verify=False, timeout=30)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers, params=params, verify=False, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._log(f"Request failed: {e}")
            raise

    def install_agent(self, device_id: str, manager_ip: str, logger=None) -> Dict:
        """COMPLETE Wazuh installation flow: Register + Trigger Agent Installation"""
        log = logger or self._log
        
        # Get device info - IMPORTANT: Get from database, not just memory
        device = None
        
        # Coba dari memory registry dulu
        if self.core and hasattr(self.core, 'devices'):
            device = self.core.devices.get(device_id)
        
        # Jika tidak ada di memory, coba dari database
        if not device:
            try:
                from controller.database.device_repository import DeviceRepository
                dev_row = DeviceRepository.find_by_device_id(device_id)
                if dev_row:
                    device = {
                        "id": dev_row["device_id"],
                        "device_id": dev_row["device_id"],
                        "ip": dev_row.get("main_ip_address"),
                        "main_ip_address": dev_row.get("main_ip_address"),
                        "hostname": dev_row.get("hostname", f"{device_id}"),
                        "meta": dev_row.get("meta", {})
                    }
                    log(f"DEBUG: Found device in database: {device.get('hostname')}")
            except Exception as e:
                log(f"DEBUG: Database lookup failed: {e}")
        
        if not device:
            return {"status": "error", "error": f"Device {device_id} not found"}
        
        agent_name = device.get('hostname', f"device-{device_id}")
        agent_ip = device.get('ip') or device.get('main_ip_address', 'unknown')
        
        log(f"Starting COMPLETE Wazuh installation for {agent_name}...")
        
        try:
            # Register agent di Wazuh Manager
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

            # === SIMPAN METADATA KE DATABASE ===
            try:
                from controller.database.device_repository import DeviceRepository
                
                # Prepare metadata update
                new_meta = device.get("meta", {})
                new_meta.update({
                    "wazuh_agent_id": agent_id,
                    "wazuh_agent_name": agent_name,
                    "wazuh_manager_ip": manager_ip,
                    "wazuh_agent_key": agent_key_decoded,
                    "wazuh_registered_at": datetime.datetime.now().isoformat()
                })
                
                # Update database
                update_result = DeviceRepository.update_device_meta(device_id, new_meta)
                log(f"DEBUG: Database metadata update result: {update_result}")
                
            except Exception as db_error:
                log(f"WARNING: Failed to save metadata to database: {db_error}")
            
            # === SIMPAN METADATA KE MEMORY REGISTRY ===
            if self.core and hasattr(self.core, 'devices'):
                # Pastikan device ada di memory registry
                memory_device = self.core.devices.get(device_id)
                if memory_device:
                    if "meta" not in memory_device:
                        memory_device["meta"] = {}
                    
                    memory_device["meta"].update({
                        "wazuh_agent_id": agent_id,
                        "wazuh_agent_name": agent_name,
                        "wazuh_manager_ip": manager_ip,
                        "wazuh_agent_key": agent_key_decoded,
                        "wazuh_registered_at": datetime.datetime.now().isoformat()
                    })
                    log(f"DEBUG: Updated metadata in memory registry")
                else:
                    # Jika device tidak ada di memory, tambahkan
                    device["meta"] = new_meta
                    try:
                        self.core.devices.create(device)
                        log(f"DEBUG: Added device to memory registry with metadata")
                    except:
                        pass
            
            # Trigger agent side installation
            log(f"Triggering agent side installation for {agent_name}...")
            try:
                # IMPORT ServerAPI hanya saat diperlukan
                from drivers.server_drivers.server_api import ServerAPI
                
                # Buat instance ServerAPI
                server_api = ServerAPI(device)
                
                # Trigger installation
                installation_result = server_api.wazuh_install(
                    manager_ip=manager_ip,
                    agent_key=agent_key_decoded, 
                    agent_name=agent_name,
                    logger=log
                )
                
                log(f"Agent side installation result: {installation_result}")
                
            except ImportError as e:
                log(f"ERROR: Cannot import ServerAPI: {e}")
                installation_result = {"error": f"ServerAPI not available: {str(e)}"}
            except Exception as e:
                log(f"ERROR: Failed to trigger agent installation: {e}")
                import traceback
                log(f"Traceback: {traceback.format_exc()}")
                installation_result = {"error": str(e)}
            
            # Return result
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
            try:
                # LAZY IMPORT ServerAPI
                from drivers.server_drivers.server_api import ServerAPI
                server_api = ServerAPI(device)
                uninstall_result = server_api.wazuh_uninstall(logger=log)
                
            except ImportError as e:
                log(f"WARNING: Cannot import ServerAPI: {e}")
                uninstall_result = {"error": f"ServerAPI not available: {str(e)}"}
            except Exception as e:
                log(f"ERROR: Failed to trigger agent uninstallation: {e}")
                uninstall_result = {"error": str(e)}
            
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

    # Only Register, nanti dipanggil pada function install_agent()
    def add_agent(self, agent_name: str, agent_ip: str, logger=None) -> Dict:
        """Add new agent ke Wazuh"""
        log = logger or self._log
        try:
            url = f"{self.base_url}/agents"
            payload = {
                "name": agent_name
            }
            
            log(f"DEBUG - URL: {url}")
            log(f"DEBUG - Payload: {payload}")
            log(f"DEBUG - Headers: {self._get_headers()}")
            log(f"DEBUG - Token: {self.token[:50]}...")  # Log partial token
            
            # Test dengan requests langsung dulu
            log("DEBUG - Testing with direct requests...")
            response_direct = requests.post(
                url, 
                headers=self._get_headers(),
                json=payload,
                verify=False,
                timeout=30
            )
            log(f"DEBUG - Direct requests status: {response_direct.status_code}")
            log(f"DEBUG - Direct requests response: {response_direct.text}")
            
            # Test dengan session
            log("DEBUG - Testing with session...")
            response_session = self.session.post(
                url, 
                headers=self._get_headers(),
                json=payload,
                verify=False,
                timeout=30
            )
            log(f"DEBUG - Session status: {response_session.status_code}")
            log(f"DEBUG - Session response: {response_session.text}")
            
            # Gunakan yang berhasil
            if response_direct.status_code == 200:
                log("Using direct requests (SUCCESS)")
                agent_data = response_direct.json()['data']
            elif response_session.status_code == 200:
                log("Using session (SUCCESS)")
                agent_data = response_session.json()['data']
            else:
                log("Both methods failed")
                raise Exception(f"Direct: {response_direct.status_code} - {response_direct.text}, Session: {response_session.status_code} - {response_session.text}")
            
            log(f"Wazuh agent added: {agent_data}")
            return agent_data
            
        except Exception as e:
            log(f"Failed to add Wazuh agent: {e}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            raise
    
    # Only Deregister, nanti dipanggil pada function uninstall_agent()
    def delete_agent(self, agent_id: str, logger=None) -> Dict:
        """Delete agent dari Wazuh Manager"""
        log = logger or self._log
        try:
            url = f"{self.base_url}/agents/{agent_id}"
            response = self.session.delete(url, headers=self._get_headers())
            response.raise_for_status()
            
            log(f"Agent {agent_id} deleted from Wazuh manager")
            return {"status": "success", "message": f"Agent {agent_id} deleted"}
            
        except Exception as e:
            log(f"Failed to delete agent: {e}")
            raise
    
    def get_agent_key(self, agent_id: str, logger=None) -> str:
        """Get agent authentication key"""
        log = logger or self._log
        try:
            url = f"{self.base_url}/agents/{agent_id}/key"
            response = self.session.get(
                url,
                headers=self._get_headers(),
                verify=False,
                timeout=30
            )
            
            log(f"Key response status: {response.status_code}")
            log(f"Key response text: {response.text}")
            
            if response.status_code != 200:
                log(f"Error getting key: {response.text}")
                response.raise_for_status()
            
            response_data = response.json()
            log(f"Key response data: {response_data}")
            
            # Handle new response format
            if ('data' in response_data and 
                'affected_items' in response_data['data'] and 
                len(response_data['data']['affected_items']) > 0):
                
                affected_item = response_data['data']['affected_items'][0]
                
                if 'key' in affected_item:
                    key = affected_item['key']
                    log(f"Agent key obtained (new format): {key}")
                    return key
                else:
                    log(f"No 'key' field in affected_items: {affected_item}")
                    raise Exception(f"No 'key' field in response: {affected_item}")
            
            # Fallback untuk format lama
            elif 'data' in response_data and 'key' in response_data['data']:
                key = response_data['data']['key']
                log(f"Agent key obtained (old format): {key}")
                return key
            
            elif 'key' in response_data:
                key = response_data['key']
                log(f"Agent key obtained (direct): {key}")
                return key
            
            else:
                log(f"Unexpected key response format: {response_data}")
                raise Exception(f"Unexpected key response format: {response_data}")
        except Exception as e:
            log(f"Failed to get agent key: {e}")
            raise
    
    def get_manager_info(self, logger=None) -> Dict:
        """Get Wazuh manager information"""
        log = logger or self._log
        log("Getting manager info...")
        
        try:
            result = self._make_request('GET', '/manager/status')
            return {
                "status": "success",
                "manager": result.get('data', {}),
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_manager_stats(self, logger=None) -> Dict:
        """Get manager statistics"""
        log = logger or self._log
        log("Getting manager stats...")
        
        try:
            result = self._make_request('GET', '/manager/stats')
            return {
                "status": "success",
                "stats": result.get('data', {}),
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
        
    def get_manager_configuration(self, logger=None) -> Dict:
        """Get configuration assessment"""
        log = logger or self._log
        log("Getting configuration assessment...")
        
        try:
            # Get manager configuration
            manager_config = self._make_request('GET', '/manager/configuration')
            
            # Get active configuration
            active_config = self._make_request('GET', '/manager/configuration?active=true')
            
            return {
                "status": "success",
                "config_assessment": {
                    "manager_config": manager_config.get('data', {}),
                    "active_config": active_config.get('data', {}),
                    "assessment_time": datetime.datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_agents(self, filters: Dict = None, logger=None) -> Dict:
        """Get all agents with optional filtering"""
        log = logger or self._log
        log("Getting agents...")
        
        try:
            params = filters or {}
            result = self._make_request('GET', '/agents', params=params)
            
            agents = result.get('data', {}).get('affected_items', [])
            
            summary = {
                "total": len(agents),
                "active": len([a for a in agents if a.get('status') == 'active']),
                "disconnected": len([a for a in agents if a.get('status') == 'disconnected']),
                "never_connected": len([a for a in agents if a.get('status') == 'never_connected']),
                "pending": len([a for a in agents if a.get('status') == 'pending'])
            }
            
            return {
                "status": "success",
                "agents": agents,
                "summary": summary,
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_agent_detail(self, agent_id: str, logger=None) -> Dict:
        """Get detailed information for specific agent"""
        log = logger or self._log
        log(f"Getting agent detail for {agent_id}...")
        
        try:
            result = self._make_request('GET', f'/agents/{agent_id}/stats/agent')
            return {
                "status": "success",
                "agent": result.get('data', {}),
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
        
    def get_agent_status(self, agent_id: str, logger=None) -> Dict:
        """Get agent status FROM WAZUH MANAGER (not local)"""
        log = logger or self._log
        
        if not agent_id:
            return {
                "status": "error",
                "error": "agent_id parameter is required",
                "source": "wazuh_manager"
            }
        
        log(f"Checking agent {agent_id} status in Wazuh manager...")
        
        try:
            # Get agents response
            agents_response = self.get_agents()
            
            # Check if response is successful
            if agents_response.get("status") != "success":
                return {
                    "status": "error",
                    "error": f"Failed to get agents list: {agents_response.get('error', 'Unknown error')}",
                    "source": "wazuh_manager"
                }
            
            # Extract agents list from response
            agents_list = agents_response.get("agents", [])
            
            if not agents_list:
                return {
                    "status": "error",
                    "error": "No agents found in Wazuh manager",
                    "source": "wazuh_manager"
                }
            
            # Find the specific agent
            manager_agent = None
            for agent in agents_list:
                # Agent ID bisa string atau integer di response Wazuh
                agent_id_str = str(agent.get('id', ''))
                if agent_id_str == str(agent_id):
                    manager_agent = agent
                    break
            
            if not manager_agent:
                # Coba lagi dengan pencarian case-insensitive
                for agent in agents_list:
                    agent_id_str = str(agent.get('id', '')).lower()
                    if agent_id_str == str(agent_id).lower():
                        manager_agent = agent
                        break
            
            if not manager_agent:
                return {
                    "status": "error",
                    "error": f"Agent {agent_id} not found in Wazuh manager. Total agents: {len(agents_list)}",
                    "source": "wazuh_manager",
                    "available_agents": [{"id": str(a.get('id')), "name": a.get('name')} for a in agents_list[:10]]
                }
            
            # Format response
            return {
                "status": "success",
                "source": "wazuh_manager",
                "agent_id": str(agent_id),
                "manager_status": {
                    "status": manager_agent.get('status', 'unknown'),
                    "connected": manager_agent.get('status') == 'active',
                    "last_keepalive": manager_agent.get('lastKeepAlive'),
                    "version": manager_agent.get('version', 'unknown'),
                    "ip": manager_agent.get('ip', 'unknown'),
                    "name": manager_agent.get('name', 'unknown'),
                    "node_name": manager_agent.get('node_name'),
                    "os_name": manager_agent.get('os', {}).get('name', 'unknown'),
                    "os_platform": manager_agent.get('os', {}).get('platform', 'unknown'),
                    "os_version": manager_agent.get('os', {}).get('version', 'unknown'),
                    "date_add": manager_agent.get('dateAdd'),
                    "last_ack": manager_agent.get('lastACK')
                },
                "timestamp": datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Failed to check agent status: {str(e)}"
            log(f"{error_msg}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            return {"status": "error", "error": error_msg}

    def get_agent_config(self, agent_id: str, logger=None) -> Dict:
        """Get agent configuration untuk download"""
        log = logger or self._log
        try:
            url = f"{self.base_url}/agents/{agent_id}/config/syscheck/syscheck"
            response = requests.get(
                url,
                headers=self._get_headers(),
                verify=False
            )
            response.raise_for_status()
            return response.json()['data']
        except Exception as e:
            log(f"Failed to get agent config: {e}")
            raise
    
    def get_security_configuration_assessment(self, agent_id: str, logger=None) -> Dict:
        """Get Security Configuration Assessment (SCA)"""
        log = logger or self._log
        log(f"Getting SCA for agent {agent_id}...")
        
        try:
            result = self._make_request('GET', f'/sca/{agent_id}')
            data = result.get('data', {}).get('affected_items', [])
            
            # Calculate compliance score
            total_checks = len(data)
            passed_checks = len([d for d in data if d.get('result') == 'passed'])
            failed_checks = len([d for d in data if d.get('result') == 'failed'])
            
            compliance_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
            
            return {
                "status": "success",
                "sca": data,
                "summary": {
                    "total_checks": total_checks,
                    "passed": passed_checks,
                    "failed": failed_checks,
                    "compliance_score": round(compliance_score, 2)
                },
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_fim_data(self, agent_id: str, filters: Dict = None, logger=None) -> Dict:
        """Get File Integrity Monitoring data"""
        log = logger or self._log
        log(f"Getting FIM data for agent {agent_id}...")
        
        try:
            params = filters or {}
            result = self._make_request('GET', f'/syscheck/{agent_id}', params=params)
            data = result.get('data', {}).get('affected_items', [])
            
            return {
                "status": "success",
                "fim": data,
                "summary": {
                    "total_files": len(data),
                    "alerts": len([d for d in data if d.get('alert')]),
                    "modified": len([d for d in data if d.get('type') == 'modified']),
                    "added": len([d for d in data if d.get('type') == 'added']),
                    "deleted": len([d for d in data if d.get('type') == 'deleted'])
                },
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_syscollector_hardware(self, agent_id: str, logger=None) -> Dict:
        """Get system hardware information"""
        log = logger or self._log
        log(f"Getting hardware info for agent {agent_id}...")
        
        try:
            result = self._make_request('GET', f'/syscollector/{agent_id}/hardware')
            data = result.get('data', {}).get('affected_items', [])
            
            hardware_info = {}
            if data:
                hardware_info = data[0]  # Usually only one hardware entry per agent
            
            return {
                "status": "success",
                "hardware": hardware_info,
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_syscollector_processes(self, agent_id: str, filters: Dict = None, logger=None) -> Dict:
        """Get running processes"""
        log = logger or self._log
        log(f"Getting processes for agent {agent_id}...")
        
        try:
            params = filters or {}
            result = self._make_request('GET', f'/syscollector/{agent_id}/processes', params=params)
            data = result.get('data', {}).get('affected_items', [])
            
            # Process analysis
            process_users = {}
            for proc in data:
                user = proc.get('euser', 'unknown')
                process_users[user] = process_users.get(user, 0) + 1
            
            return {
                "status": "success",
                "processes": data,
                "analysis": {
                    "total_processes": len(data),
                    "unique_users": len(process_users),
                    "processes_by_user": process_users
                },
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}