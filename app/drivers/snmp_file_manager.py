import yaml, json, subprocess, os

class SNMPFileManager:
    def __init__(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prometheus'))
        self.snmp_yml_path = os.path.join(base_dir, 'snmp.yml')
        self.snmp_targets_path = os.path.join(base_dir, 'snmp_targets.json')

    # === DEVICE MANAGEMENT ===
    def add_device(self, data):
        """
        data = {
            "ip": "10.10.10.1",
            "module": "mikrotik",
            "device_name": "Router-Branch",
            "location": "Branch1"
        }
        """
        with open(self.snmp_targets_path, "r") as f:
            targets = json.load(f)

        new_target = {
            "targets": [data["ip"]],
            "labels": {
                "module": data["module"],
                "device_name": data["device_name"],
                "location": data["location"]
            }
        }

        # Hindari duplikasi
        for t in targets:
            if t["targets"] == [data["ip"]]:
                raise Exception(f"Device {data['ip']} already exists in targets")

        targets.append(new_target)

        with open(self.snmp_targets_path, "w") as f:
            json.dump(targets, f, indent=2)

        # Restart Prometheus karena target baru
        self.restart_prometheus()
        return new_target

    # === METRIC MANAGEMENT ===
    def add_metric(self, module, metric):
        with open(self.snmp_yml_path, "r") as f:
            yml = yaml.safe_load(f)

        if "modules" not in yml or module not in yml["modules"]:
            raise Exception(f"Module {module} not found in snmp.yml")

        mod = yml["modules"][module]

        # Tambah ke walk
        if metric["type"] == "walk":
            if "walk" not in mod:
                mod["walk"] = []
            mod["walk"].append(metric["oid"])

        # Tambah ke metrics
        elif metric["type"] == "metrics":
            if "metrics" not in mod:
                mod["metrics"] = []

            new_entry = {
                "name": metric["name"],
                "oid": metric["oid"],
                "type": metric["datatype"]
            }
            if "help" in metric:
                new_entry["help"] = metric["help"]
            if "indexes" in metric:
                new_entry["indexes"] = metric["indexes"]
            if "lookups" in metric:
                new_entry["lookups"] = metric["lookups"]

            mod["metrics"].append(new_entry)

        else:
            raise Exception("Invalid metric type (use 'walk' or 'metrics')")

        with open(self.snmp_yml_path, "w") as f:
            yaml.dump(yml, f, sort_keys=False)

        # Restart SNMP Exporter karena ada perubahan metric
        self.restart_snmp_exporter()
        return metric

    # === Restart Functions ===
    def restart_snmp_exporter(self):
        try:
            subprocess.run(["docker", "restart", "snmp_exporter"], check=True)
        except Exception as e:
            raise Exception(f"Failed to restart snmp_exporter: {str(e)}")

    def restart_prometheus(self):
        try:
            subprocess.run(["docker", "restart", "prometheus"], check=True)
        except Exception as e:
            raise Exception(f"Failed to restart prometheus: {str(e)}")

    # === SNMP Tester ===
    def test_snmp(self, ip, community, oid, version=None):
        if not version:
            version = "2c"
        try:
            cmd = ["snmpget", f"-v{version}", "-c", community, ip, oid]
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=5)
            return {
                "status": "success",
                "ip": ip,
                "oid": oid,
                "output": result.decode().strip()
            }
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": e.output.decode().strip()}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "SNMP request timed out"}
        except Exception as e:
            return {"status": "error", "message": str(e)}