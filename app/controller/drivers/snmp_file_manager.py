import yaml, json, subprocess, os

class SNMPFileManager:
    def __init__(self):
        BASE_PROM_DIR = os.getenv("PROMETHEUS_DIR", "/home/student/ryu/ryu/prometheus")

        self.snmp_yml_path = os.path.join(BASE_PROM_DIR, "snmp.yml")
        self.snmp_targets_path = os.path.join(BASE_PROM_DIR, "snmp_targets.json")

    # === DEVICE MANAGEMENT ===
    def add_device(self, data):
        with open(self.snmp_targets_path, "r") as f:
            targets = json.load(f)

        # Cek apakah device_id sudah ada
        for t in targets:
            if t["labels"].get("id") == data["device_id"]:
                raise Exception(f"Device {data['device_id']} already exists in SNMP targets")

        new_target = {
            "targets": [data["ip"]],
            "labels": {
                "id": data["device_id"],
                "module": data["module"],
                "device_name": data["device_name"],
                "location": data["location"]
            }
        }
        
        if "community" in data:
            new_target["labels"]["community"] = data["community"]

        # Append device baru ke array
        targets.append(new_target)

        with open(self.snmp_targets_path, "w") as f:
            json.dump(targets, f, indent=2)

        # self.restart_prometheus()
        return new_target


    def delete_device(self, device_id):
        with open(self.snmp_targets_path, "r") as f:
            targets = json.load(f)

        new_targets = [t for t in targets if t["id"] != device_id]

        if len(new_targets) == len(targets):
            raise Exception(f"Device ID {device_id} not found")

        with open(self.snmp_targets_path, "w") as f:
            json.dump(new_targets, f, indent=2)

        # self.restart_prometheus()
        return True

    def edit_device(self, device_id, new_data):
        with open(self.snmp_targets_path, "r") as f:
            targets = json.load(f)

        found = False

        for t in targets:
            if t["id"] == device_id:
                if "ip" in new_data:
                    t["targets"] = [new_data["ip"]]
                if "module" in new_data:
                    t["labels"]["module"] = new_data["module"]
                if "device_name" in new_data:
                    t["labels"]["device_name"] = new_data["device_name"]
                if "location" in new_data:
                    t["labels"]["location"] = new_data["location"]
                found = True

        if not found:
            raise Exception(f"Device ID {device_id} not found in SNMP targets")

        with open(self.snmp_targets_path, "w") as f:
            json.dump(targets, f, indent=2)

        # self.restart_prometheus()
        return True

    # === METRIC MANAGEMENT ===
    def add_metric(self, module, metric):
        with open(self.snmp_yml_path, "r") as f:
            yml = yaml.safe_load(f)

        if "modules" not in yml or module not in yml["modules"]:
            raise Exception(f"Module {module} not found in snmp.yml")

        mod = yml["modules"][module]

        # === TYPE: WALK ===
        if metric["type"] == "walk":
            if "walk" not in mod:
                mod["walk"] = []

            # avoid duplicate OID on walk
            if metric["oid"] in mod["walk"]:
                raise Exception(f"OID {metric['oid']} already exists in walk of module {module}")

            mod["walk"].append(metric["oid"])

        # === TYPE: METRICS ===
        elif metric["type"] == "metrics":

            if "metrics" not in mod:
                mod["metrics"] = []

            # Duplicate check (same module + same name)
            for m in mod["metrics"]:
                if m["name"] == metric["name"]:
                    raise Exception(f"Metric '{metric['name']}' already exists in module '{module}'")

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

        # SAVE FILE
        with open(self.snmp_yml_path, "w") as f:
            yaml.dump(yml, f, sort_keys=False)

        # self.restart_snmp_exporter()
        return metric

    def delete_metric(self, module, name):
        with open(self.snmp_yml_path, "r") as f:
            yml = yaml.safe_load(f)

        # Module exist check
        if "modules" not in yml or module not in yml["modules"]:
            raise Exception(f"Module '{module}' does not exist")

        mod = yml["modules"][module]

        if "metrics" not in mod:
            raise Exception(f"Module '{module}' has no metrics section")

        before = len(mod["metrics"])

        # Keep only metrics whose name != name
        mod["metrics"] = [m for m in mod["metrics"] if m.get("name") != name]

        if len(mod["metrics"]) == before:
            raise Exception(f"Metric '{name}' not found in module '{module}'")

        with open(self.snmp_yml_path, "w") as f:
            yaml.dump(yml, f, sort_keys=False)

        # self.restart_snmp_exporter()
        return True

    def edit_metric(self, module, name, new_values):
        with open(self.snmp_yml_path, "r") as f:
            yml = yaml.safe_load(f)

        if module not in yml["modules"]:
            raise Exception(f"Module '{module}' not found")

        mod = yml["modules"][module]
        metrics = mod.get("metrics", [])

        found = False

        for m in metrics:
            if m["name"] == name:
                # Update existing fields
                for k, v in new_values.items():
                    m[k] = v
                found = True

        if not found:
            raise Exception(f"Metric '{name}' not found in module '{module}'")

        with open(self.snmp_yml_path, "w") as f:
            yaml.dump(yml, f, sort_keys=False)

        # self.restart_snmp_exporter()
        return True

    # # === Restart Functions ===
    # def restart_snmp_exporter(self):
    #     try:
    #         subprocess.run(["docker", "restart", "snmp_exporter"], check=True)
    #     except Exception as e:
    #         raise Exception(f"Failed to restart snmp_exporter: {str(e)}")

    # def restart_prometheus(self):
    #     try:
    #         subprocess.run(["docker", "restart", "prometheus"], check=True)
    #     except Exception as e:
    #         raise Exception(f"Failed to restart prometheus: {str(e)}")

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