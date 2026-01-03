import requests
import datetime
import urllib3
from typing import Optional

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
    def threat_events(self, agent_id: Optional[str] = None, hours=24, size=100):
        query_filter = [
            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
        ]
        
        if agent_id:
            query_filter.append({"term": {"agent.id": agent_id}})
        
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": size,
                "sort": [{"@timestamp": {"order": "desc"}}],
                "query": {
                    "bool": {
                        "filter": query_filter
                    }
                }
            }
        )
    def threat_failed_logins(self, agent_id: Optional[str] = None, hours=24):
        query_filter = [
            {"match": {"rule.groups": "authentication_failed"}},
            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}}
        ]
        
        if agent_id:
            query_filter.append({"term": {"agent.id": agent_id}})
        
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": query_filter
                    }
                },
                "aggs": {
                    "by_user": {
                        "terms": {"field": "data.win.eventdata.targetUserName"}
                    },
                    "by_source": {
                        "terms": {"field": "data.win.eventdata.ipAddress"}
                    },
                    "timeline": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "fixed_interval": "30m"
                        }
                    }
                }
            }
        )
    def threat_success_logins(self, agent_id: Optional[str] = None, hours=24):
        query_filter = [
            {"match": {"rule.groups": "authentication_success"}},
            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}}
        ]
        
        if agent_id:
            query_filter.append({"term": {"agent.id": agent_id}})
        
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": query_filter
                    }
                },
                "aggs": {
                    "by_user": {
                        "terms": {"field": "data.win.eventdata.targetUserName"}
                    },
                    "by_logon_type": {
                        "terms": {"field": "data.win.eventdata.logonType"}
                    },
                    "timeline": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "fixed_interval": "1h"
                        }
                    }
                }
            }
        )
    def threat_high_level(self, agent_id: Optional[str] = None, hours: int = 24):
        query_filter = [
            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
            {"range": {"rule.level": {"gte": 10}}}
        ]
        
        if agent_id:
            query_filter.append({"term": {"agent.id": agent_id}})
        
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": query_filter
                    }
                },
                "aggs": {
                    "by_severity": {
                        "terms": {"field": "rule.level", "size": 10}
                    },
                    "by_rule": {
                        "terms": {"field": "rule.description.keyword", "size": 20}
                    },
                    "by_agent": {
                        "terms": {"field": "agent.name.keyword", "size": 10}
                    },
                    "timeline": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "fixed_interval": "1h"
                        }
                    }
                }
            }
        )
    def top_mitre_attacks(self, agent_id: Optional[str] = None, hours: int = 24, top: int = 10):
        query_filter = [
            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
            {"exists": {"field": "rule.mitre.id"}}
        ]
        
        if agent_id:
            query_filter.append({"term": {"agent.id": agent_id}})
        
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": query_filter
                    }
                },
                "aggs": {
                    "top_mitre_techniques": {
                        "terms": {
                            "field": "rule.mitre.id",
                            "size": top,
                            "order": {"_count": "desc"}
                        },
                        "aggs": {
                            "technique_names": {
                                "terms": {"field": "rule.mitre.technique"}
                            },
                            "severity_stats": {
                                "stats": {"field": "rule.level"}
                            }
                        }
                    },
                    "by_technique": {
                        "terms": {
                            "field": "rule.mitre.technique",
                            "size": 10
                        }
                    }
                }
            }
        )
    def top_threat_agents(self, hours: int = 24, top: int = 5):
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": [
                            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
                            {"range": {"rule.level": {"gte": 5}}}
                        ]
                    }
                },
                "aggs": {
                    "top_agents": {
                        "terms": {
                            "field": "agent.name",
                            "size": top,
                            "order": {"_count": "desc"}
                        },
                        "aggs": {
                            "severity_stats": {
                                "stats": {"field": "rule.level"}
                            },
                            "top_rules": {
                                "terms": {
                                    "field": "rule.description.keyword",
                                    "size": 5
                                }
                            }
                        }
                    }
                }
            }
        )

    # === FILE INTEGRITY MONITORING === #
    def fim_events(self, agent_id: Optional[str] = None, hours=24):
        query_filter = [
            {"match": {"rule.groups": "syscheck"}},
            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}}
        ]
        
        if agent_id:
            query_filter.append({"term": {"agent.id": agent_id}})
        
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "query": {
                    "bool": {
                        "filter": query_filter
                    }
                },
                "sort": [{"@timestamp": {"order": "desc"}}],
                "size": 100
            }
        )
    def fim_timeline(self, agent_id: Optional[str] = None, hours=24):
        query_filter = [
            {"match": {"rule.groups": "syscheck"}},
            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}}
        ]
        
        if agent_id:
            query_filter.append({"term": {"agent.id": agent_id}})
        
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": query_filter
                    }
                },
                "aggs": {
                    "timeline": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "fixed_interval": "30m",
                            "aggs": {
                                "by_action": {
                                    "terms": {"field": "syscheck.event"}
                                }
                            }
                        }
                    }
                }
            }
        )
    def fim_action_summary(self, agent_id: Optional[str] = None, hours: int = 24):
        query_filter = [
            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
            {"match": {"rule.groups": "syscheck"}}
        ]
        
        if agent_id:
            query_filter.append({"term": {"agent.id": agent_id}})
        
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": query_filter
                    }
                },
                "aggs": {
                    "actions": {
                        "terms": {"field": "syscheck.event", "size": 5}
                    }
                }
            }
        )
    def fim_most_active_agents(self, hours: int = 24, top: int = 5):
        return self.search(
            "wazuh-alerts-4.x-*",
            {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": [
                            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
                            {"match": {"rule.groups": "syscheck"}}
                        ]
                    }
                },
                "aggs": {
                    "active_agents": {
                        "terms": {
                            "field": "agent.name",
                            "size": top,
                            "order": {"_count": "desc"}
                        },
                        "aggs": {
                            "by_action": {
                                "terms": {"field": "syscheck.event"}
                            },
                            "top_files": {
                                "terms": {"field": "syscheck.path", "size": 10}
                            }
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

