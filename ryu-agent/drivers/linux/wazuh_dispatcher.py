import sys
import os

# Add drivers path
# sys.path.append(os.path.join(os.path.dirname(__file__), 'drivers', 'linux'))
from .wazuh import WazuhDriver

class WazuhDispatcher:
    def __init__(self, logger=print):
        self.logger = logger
        self.wazuh_driver = WazuhDriver(logger=logger)
        
    def dispatch(self, action: str, params: dict) -> dict:
        """Dispatch commands to appropriate handlers"""
        self.logger(f"[WazuhDispatcher] Dispatching action: {action} with params: {params}")

        # Validasi params
        if not isinstance(params, dict):
            self.logger(f"[WazuhDispatcher] ERROR: params is not dict, it's {type(params)}")
            return {"success": False, "error": f"Invalid params type: {type(params)}"}
        
        if action == "server.wazuh.install":
            return self.wazuh_driver.install_wazuh_agent(
                manager_ip=params.get("manager_ip"),
                agent_key=params.get("agent_key"),
                agent_name=params.get("agent_name")
            )
            
        elif action == "server.wazuh.uninstall":
            return self.wazuh_driver.uninstall_wazuh_agent()
            
        elif action == "server.wazuh.status":
            return self.wazuh_driver.get_wazuh_agent_status()
        
        elif action == "server.wazuh.start":
            return self.wazuh_driver.get_wazuh_agent_start()
        
        elif action == "server.wazuh.stop":
            return self.wazuh_driver.get_wazuh_agent_stop()
        
        elif action == "server.wazuh.agent.config.get":
            return self.wazuh_driver.get_ossec_config()
        
        elif action == "server.wazuh.agent.config.update":
            return self.wazuh_driver.update_ossec_config(params.get("config_content"))
            
        else:
            return {"error": f"Unknown Wazuh action: {action}"}