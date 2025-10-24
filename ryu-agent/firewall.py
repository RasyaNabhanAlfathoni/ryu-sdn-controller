import subprocess
import json
import re

class FirewallDriver:
    def __init__(self, logger=print):
        self.logger = logger
        self.firewall_type = self.detect_firewall()

    def detect_firewall(self):
        # Deteksi sistem firewall aktif pada Agent
        try:
            subprocess.run(["ufw", "status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.logger("Detected UFW firewall")
            return "ufw"
        except FileNotFoundError:
            pass

        try:
            subprocess.run(["firewall-cmd", "--state"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.logger("Detected Firewalld")
            return "firewalld"
        except FileNotFoundError:
            pass

        return None

    # === UFW Section ===
    def ufw(self, *args):
        return subprocess.getoutput(f"ufw {' '.join(args)}")

    def ufw_enable(self):
        return self.ufw("enable")

    def ufw_disable(self):
        return self.ufw("disable")

    def ufw_reload(self):
        return self.ufw("reload")

    def ufw_reset(self):
        return self.ufw("reset")

    def ufw_allow(self, port_proto):
        return self.ufw("allow", port_proto)

    def ufw_deny(self, port_proto):
        return self.ufw("deny", port_proto)

    def ufw_delete(self, rule):
        return self.ufw("delete", rule)

    def ufw_status(self):
        return self.ufw("status")

    # === Firewalld Section ===
    def firewall_cmd(self, *args):
        return subprocess.getoutput(f"firewall-cmd {' '.join(args)}")

    def firewall_reload(self):
        return self.firewall_cmd("--reload")

    def firewall_add_port(self, port_proto):
        return self.firewall_cmd(f"--add-port={port_proto} --permanent")

    def firewall_remove_port(self, port_proto):
        return self.firewall_cmd(f"--remove-port={port_proto} --permanent")

    def firewall_enable_masquerade(self):
        return self.firewall_cmd("--add-masquerade --permanent")

    def firewall_disable_masquerade(self):
        return self.firewall_cmd("--remove-masquerade --permanent")

    def firewall_status(self):
        return self.firewall_cmd("--list-all")

    # === NAT Section ===
    def setup_nat(self, out_interface):
        # Menyiapkan NAT menggunakan iptables (fallback untuk sistem tanpa firewalld)
        try:
            self.logger(f"Setting up NAT on {out_interface}")
            subprocess.run(
                ["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", out_interface, "-j", "MASQUERADE"],
                check=True
            )
            subprocess.run(["iptables-save"], check=True)
            return {"status": "success", "message": f"NAT enabled on {out_interface}"}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": str(e)}

    def clear_nat(self):
        # Hapus semua aturan NAT
        subprocess.run(["iptables", "-t", "nat", "-F"])
        return {"status": "cleared", "message": "All NAT rules cleared"}

    # === All Status Section ===
    def status_all(self):
        result = {}
        if self.firewall_type == "ufw":
            result["ufw"] = self.ufw_status()
        elif self.firewall_type == "firewalld":
            result["firewalld"] = self.firewall_status()

        result["nat_rules"] = subprocess.getoutput("iptables -t nat -L POSTROUTING -n -v")
        return result

