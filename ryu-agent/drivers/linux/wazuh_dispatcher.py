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
            
        elif action == "server.wazuh.security.overview":
            return self.wazuh_driver.get_security_overview(
                agent_id=params.get("agent_id")
            )
            
        elif action == "server.wazuh.security.vulnerabilities":
            return self.wazuh_driver.get_vulnerabilities(
                agent_id=params.get("agent_id"),
                limit=params.get("limit", 50)
            )
            
        elif action == "server.wazuh.security.fim":
            return self.wazuh_driver.get_fim_data(
                agent_id=params.get("agent_id")
            )
            
        elif action == "server.wazuh.security.events":
            return self.wazuh_driver.get_agent_security_events(
                agent_id=params.get("agent_id"),
                limit=params.get("limit", 50)
            )
            
        elif action == "wazuh.agent.list":
            return self.wazuh_driver.get_agents()
            
        else:
            return {"error": f"Unknown Wazuh action: {action}"}