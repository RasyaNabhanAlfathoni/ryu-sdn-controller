import requests
import datetime
import urllib3

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

class WazuhIndexerAPI:
    def __init__(self, base_url: str, username: str, password: str, logger=None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.logger = logger
        self.session = requests.Session()
        self.session.verify = False

    def _log(self, msg):
        if self.logger:
            self.logger.info(msg) if hasattr(self.logger, "info") else self.logger(msg)
        else:
            print(f"[WazuhIndexer] {msg}")

    def _headers(self):
        return {"Content-Type": "application/json"}

    def _auth(self):
        return (self.username, self.password)

    def search(self, index: str, query: dict) -> dict:
        url = f"{self.base_url}/{index}/_search"
        self._log(f"POST {url}")
        resp = self.session.post(
            url,
            auth=self._auth(),
            headers=self._headers(),
            json=query,
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()
    
    # === THREAT HUNTING === #
    def threat_summary(self, hours=24):
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": 0,
                "query": {
                    "range": {"@timestamp": {"gte": f"now-{hours}h"}}
                },
                "aggs": {
                    "by_level": {
                        "terms": {"field": "rule.level"}
                    }
                }
            }
        )
    def threat_events(self, hours=24, size=100):
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": size,
                "sort": [{"@timestamp": {"order": "desc"}}],
                "query": {
                    "range": {"@timestamp": {"gte": f"now-{hours}h"}}
                }
            }
        )
    def threat_failed_logins(self, hours=24):
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "query": {
                    "bool": {
                        "filter": [
                            {"match": {"rule.groups": "authentication_failed"}},
                            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}}
                        ]
                    }
                }
            }
        )
    def threat_success_logins(self, hours=24):
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "query": {
                    "bool": {
                        "filter": [
                            {"match": {"rule.groups": "authentication_success"}},
                            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}}
                        ]
                    }
                }
            }
        )

    # === FILE INTEGRITY MONITORING === #
    def fim_events(self, agent_id, hours=24):
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"agent.id": agent_id}},
                            {"match": {"rule.groups": "syscheck"}},
                            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}}
                        ]
                    }
                }
            }
        )
    def fim_timeline(self, agent_id, hours=24):
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"agent.id": agent_id}},
                            {"match": {"rule.groups": "syscheck"}},
                            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}}
                        ]
                    }
                },
                "aggs": {
                    "timeline": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "fixed_interval": "30m"
                        }
                    }
                }
            }
        )
    
    # === SECURITY CONFIGURATION ASSESSMENT === #
    def sca_events(self, agent_id, hours=24):
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"agent.id": agent_id}},
                            {"match": {"rule.groups": "sca"}},
                            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}}
                        ]
                    }
                }
            }
        )

    # === DISCOVER LOGS === #
    def discover_logs(self, index="wazuh-alerts-*", keyword=None, hours=24, size=100):
        query = {"match_all": {}}
        if keyword:
            query = {"query_string": {"query": keyword}}

        return self.search(
            index,
            {
                "size": size,
                "sort": [{"@timestamp": {"order": "desc"}}],
                "query": {
                    "bool": {
                        "filter": [
                            query,
                            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}}
                        ]
                    }
                }
            }
        )

