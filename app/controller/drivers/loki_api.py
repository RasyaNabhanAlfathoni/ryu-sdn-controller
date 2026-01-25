# loki_api.py
import requests
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class LokiAPI:
    def __init__(self, base_url: str = None, device_repository=None, logger=None):
        """
        Initialize Loki API client dengan DeviceRepository untuk validai
        """
        self.base_url = base_url or "http://localhost:3100"
        self.base_url = self.base_url.rstrip('/')
        self.timeout = 30
        self.logger = logger or (lambda msg: print(f"[Loki] {msg}"))
        self.device_repository = device_repository
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to Loki server"""
        try:
            response = requests.get(
                f"{self.base_url}/ready",
                timeout=5
            )
            if response.status_code == 200:
                self.logger(f"Connected to Loki at {self.base_url}")
                return True
            else:
                self.logger(f"Loki returned status {response.status_code}")
                return False
        except Exception as e:
            self.logger(f"Cannot connect to Loki: {e}")
            return False
    
    def _call_loki(self, endpoint: str, params: Dict = None) -> Dict:
        """Generic call to Loki API"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Cannot connect to Loki server"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _extract_level(self, log_line: str, labels: Dict) -> str:
        """Extract log level dari log line atau labels"""
        if log_line:
            match = re.search(r'\blevel=(debug|info|warning|warn|error|critical|fatal)\b', log_line, re.IGNORECASE)
            if match:
                level = match.group(1).lower()
                return "warning" if level == "warn" else level

        for key in ("severity", "detected_level", "level"):
            if key in labels:
                return labels[key].lower()

        return "info"
    
    def _level_to_weight(self, level: str) -> int:
        """Convert level ke weight untuk filtering"""
        mapping = {
            "debug": 10,
            "info": 20,
            "warning": 30,
            "error": 40,
            "critical": 50
        }
        return mapping.get(level, 20)
    
    def query_range(self, query: str, limit: int = 100, hours: int = 1) -> Dict:
        """
        Generic query range ke Loki
        
        Args:
            query: LogQL query
            limit: Max number of logs
            hours: Hours to look back
        """
        end_ns = int(time.time() * 1_000_000_000)
        start_ns = end_ns - (hours * 3600 * 1_000_000_000)
        
        params = {
            'query': query,
            'limit': str(limit),
            'start': str(start_ns),
            'end': str(end_ns),
            'direction': 'BACKWARD'
        }
        
        self.logger(f"Querying Loki: {query} (limit: {limit}, hours: {hours})")
        
        result = self._call_loki("/loki/api/v1/query_range", params)
        
        # Parse response
        if result.get("status") == "success":
            logs = []
            data = result.get("data", {})
            
            for stream_result in data.get("result", []):
                stream = stream_result.get("stream", {})
                values = stream_result.get("values", [])
                
                for timestamp_ns, log_line in values:
                    timestamp_sec = int(timestamp_ns) / 1_000_000_000
                    log_time = datetime.fromtimestamp(timestamp_sec)
                    
                    extracted_level = self._extract_level(log_line, stream)

                    logs.append({
                        "timestamp": log_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "message": log_line,
                        "hostname": stream.get("hostname", "unknown"),
                        "level": extracted_level,
                        "job": stream.get("job", "unknown"),
                        "component": stream.get("component", "unknown"),
                        "labels": stream
                    })

            return {
                "status": "success",
                "total": len(logs),
                "logs": logs,
                "query": query
            }
        
        return result
    
    def search_logs(self, params: Dict, logger=None) -> Dict:
        if logger:
            logger(f"Searching logs with params: {params}")

        label_filters = []

        # ===== WAJIB =====
        job = params.get("job")
        job_match = params.get("job_match", "=")

        if not job:
            return {
                "status": "error",
                "error": "job is required for Loki query"
            }

        if job_match == "=":
            label_filters.append(f'job="{job}"')
        else:
            label_filters.append(f'job=~"{job}"')

        # ===== OPTIONAL =====
        hostname = params.get("hostname")
        if hostname:
            label_filters.append(f'hostname="{hostname}"')

        device_id = params.get("device_id")
        if device_id:
            label_filters.append(f'device_id="{device_id}"')

        level = params.get("level")

        label_query = "{" + ",".join(label_filters) + "}"

        pipeline = []

        if level:
            # match severity OR detected_level
            pipeline.append(
                f'|~ "(?i)severity={level}|detected_level={level}"'
            )

        keyword = params.get("keyword")
        if keyword:
            pipeline.append(f'|= "{keyword}"')

        query = " ".join([label_query] + pipeline)


        label_query = "{" + ",".join(label_filters) + "}"

        keyword = params.get("keyword")
        if keyword:
            query = f'{label_query} |= "{keyword}"'
        else:
            query = label_query

        limit = params.get("limit", 100)
        hours = params.get("hours", 24)

        return self.query_range(query, limit=limit, hours=hours)

    def health(self, params: Dict = None, logger=None) -> Dict:
        """Check Loki health"""
        try:
            response = requests.get(
                f"{self.base_url}/ready",
                timeout=5
            )
            result = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "loki_url": self.base_url
            }
            
            if logger:
                logger(f"Loki health check: {result}")
                
            return result
            
        except Exception as e:
            error_msg = f"Loki health check failed: {str(e)}"
            if logger:
                logger(error_msg)
            return {"status": "error", "error": error_msg}
