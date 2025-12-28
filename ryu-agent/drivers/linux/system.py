import psutil
import platform
import subprocess
import os
import pwd
import grp
import spwd
import crypt
import getpass
import socket
from datetime import datetime
from utils import detect_os_family, execute_command

class ServerSystemDriver:
    def __init__(self, logger=print):
        self.logger = logger
        self.os_family = detect_os_family()
        self._execute_command = execute_command
        self.logger(f"Detected OS: {self.os_family}")

    def health_check(self, detailed=False):
        """Basic health check untuk server agent"""
        try:            
            # Uptime
            uptime_seconds = psutil.boot_time()
            uptime_str = str(datetime.timedelta(seconds=uptime_seconds))
            
            # 3. Determine overall status
            overall_status = "healthy"
            issues = []
            
            # 4. Basic response (untuk detailed=False)
            if not detailed:
                return {
                    "status": "ok",
                    "health": overall_status,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "uptime": uptime_str,
                    "issues": issues if issues else None
                }
            

        except ImportError:
            # Jika psutil tidak tersedia
            return {
                "status": "error",
                "health": "unknown",
                "timestamp": datetime.datetime.now().isoformat(),
                "error": "psutil module not available",
                "message": "Install psutil: pip install psutil"
            }
            
        except Exception as e:
            self.logger(f"Health check error: {e}")
            return {
                "status": "error",
                "health": "unknown",
                "timestamp": datetime.datetime.now().isoformat(),
                "error": str(e)
            }
        
    def get_users(self):
        """Get list of all system users"""
        try:
            users = []
            for p in pwd.getpwall():
                # Skip system users (UID < 1000 on Linux, varies by distro)
                if p.pw_uid >= 1000 and p.pw_name != "nobody":
                    users.append({
                        "username": p.pw_name,
                        "uid": p.pw_uid,
                        "gid": p.pw_gid,
                        "fullname": p.pw_gecos,
                        "home": p.pw_dir,
                        "shell": p.pw_shell
                    })
            return {"success": True, "users": users}
        except Exception as e:
            self.logger(f"Error getting users: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user_info(self, username):
        """Get detailed information about a specific user"""
        try:
            user_info = pwd.getpwnam(username)
            # Get groups user belongs to
            groups = []
            for group in grp.getgrall():
                if username in group.gr_mem:
                    groups.append(group.gr_name)
            
            return {
                "success": True,
                "user": {
                    "username": user_info.pw_name,
                    "uid": user_info.pw_uid,
                    "gid": user_info.pw_gid,
                    "fullname": user_info.pw_gecos,
                    "home": user_info.pw_dir,
                    "shell": user_info.pw_shell,
                    "groups": groups
                }
            }
        except KeyError:
            return {"success": False, "error": f"User '{username}' not found"}
        except Exception as e:
            self.logger(f"Error getting user info: {e}")
            return {"success": False, "error": str(e)}
    
    def create_user(self, username, password=None, shell="/bin/bash", home_dir=None):
        """Create a new system user"""
        try:
            # Build command
            cmd = f"sudo useradd -m"
            
            if shell:
                cmd += f" -s {shell}"
            
            if home_dir:
                cmd += f" -d {home_dir}"
            else:
                cmd += f" -d /home/{username}"
            
            # Add username
            cmd += f" {username}"
            
            # Execute command
            result = self._execute_command(cmd)
            
            if result["success"]:
                # Set password if provided
                if password:
                    self._set_password(username, password)
                
                return {
                    "success": True,
                    "message": f"User '{username}' created successfully",
                    "details": result["stdout"]
                }
            else:
                return {"success": False, "error": result["stderr"]}
                
        except Exception as e:
            self.logger(f"Error creating user: {e}")
            return {"success": False, "error": str(e)}
    
    def _set_password(self, username, password):
        """Set password for user using chpasswd"""
        try:
            # Use echo and chpasswd to set password
            cmd = f"echo '{username}:{password}' | sudo chpasswd"
            result = self._execute_command(cmd, shell=True)
            return result["success"]
        except Exception as e:
            self.logger(f"Error setting password: {e}")
            return False
    
    def delete_user(self, username, remove_home=False):
        """Delete a system user"""
        try:
            cmd = f"sudo userdel"
            if remove_home:
                cmd += " -r"
            cmd += f" {username}"
            
            result = self._execute_command(cmd)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"User '{username}' deleted successfully"
                }
            else:
                return {"success": False, "error": result["stderr"]}
                
        except Exception as e:
            self.logger(f"Error deleting user: {e}")
            return {"success": False, "error": str(e)}
    
    def modify_user(self, username, shell=None, home_dir=None):
        """Modify user properties"""
        try:
            cmd = f"sudo usermod"
            
            if shell:
                cmd += f" -s {shell}"
            
            if home_dir:
                cmd += f" -d {home_dir}"
                cmd += f" -m"  # Move contents to new home
            
            cmd += f" {username}"
            
            result = self._execute_command(cmd)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"User '{username}' modified successfully"
                }
            else:
                return {"success": False, "error": result["stderr"]}
                
        except Exception as e:
            self.logger(f"Error modifying user: {e}")
            return {"success": False, "error": str(e)}
    
    def change_user_password(self, username, password):
        """Change user password"""
        try:
            return {
                "success": self._set_password(username, password),
                "message": f"Password for '{username}' changed successfully"
            }
        except Exception as e:
            self.logger(f"Error changing password: {e}")
            return {"success": False, "error": str(e)}
    
    def add_user_to_group(self, username, group):
        """Add user to group"""
        try:
            cmd = f"sudo usermod -a -G {group} {username}"
            result = self._execute_command(cmd)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"User '{username}' added to group '{group}'"
                }
            else:
                return {"success": False, "error": result["stderr"]}
                
        except Exception as e:
            self.logger(f"Error adding user to group: {e}")
            return {"success": False, "error": str(e)}
    
    def remove_user_from_group(self, username, group):
        """Remove user from group"""
        try:
            # Get current groups for user
            cmd = f"groups {username}"
            result = self._execute_command(cmd)
            
            if not result["success"]:
                return {"success": False, "error": result["stderr"]}
            
            # Parse groups and remove the specified one
            groups_line = result["stdout"].strip()
            if ":" in groups_line:
                groups = groups_line.split(":")[1].strip().split()
            else:
                groups = groups_line.split()
            
            # Remove the specified group
            if group in groups:
                groups.remove(group)
            
            # Re-set groups
            if groups:
                groups_str = ",".join(groups)
                cmd = f"sudo usermod -G {groups_str} {username}"
                result = self._execute_command(cmd)
                
                if result["success"]:
                    return {
                        "success": True,
                        "message": f"User '{username}' removed from group '{group}'"
                    }
                else:
                    return {"success": False, "error": result["stderr"]}
            else:
                # If no groups left, user will only have primary group
                return {
                    "success": True,
                    "message": f"User '{username}' removed from group '{group}' (now has only primary group)"
                }
                
        except Exception as e:
            self.logger(f"Error removing user from group: {e}")
            return {"success": False, "error": str(e)}
    
    def get_groups(self):
        """Get list of all system groups"""
        try:
            groups = []
            for g in grp.getgrall():
                # Skip system groups (GID < 1000)
                if g.gr_gid >= 1000:
                    groups.append({
                        "groupname": g.gr_name,
                        "gid": g.gr_gid,
                        "members": g.gr_mem
                    })
            return {"success": True, "groups": groups}
        except Exception as e:
            self.logger(f"Error getting groups: {e}")
            return {"success": False, "error": str(e)}
    
    def create_group(self, group_name):
        """Create a new system group"""
        try:
            cmd = f"sudo groupadd {group_name}"
            result = self._execute_command(cmd)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Group '{group_name}' created successfully"
                }
            else:
                return {"success": False, "error": result["stderr"]}
                
        except Exception as e:
            self.logger(f"Error creating group: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_group(self, group_name):
        """Delete a system group"""
        try:
            cmd = f"sudo groupdel {group_name}"
            result = self._execute_command(cmd)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Group '{group_name}' deleted successfully"
                }
            else:
                return {"success": False, "error": result["stderr"]}
                
        except Exception as e:
            self.logger(f"Error deleting group: {e}")
            return {"success": False, "error": str(e)}
    
    def get_hostname(self):
        """Get current hostname"""
        try:
            result = self._execute_command("hostname")
            if result["success"]:
                hostname = result["stdout"].strip()
                # Also get FQDN if available
                fqdn_result = self._execute_command("hostname -f")
                fqdn = fqdn_result["stdout"].strip() if fqdn_result["success"] else hostname
                
                return {
                    "success": True,
                    "hostname": hostname,
                    "fqdn": fqdn,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"success": False, "error": result["stderr"]}
        except Exception as e:
            self.logger(f"Error getting hostname: {e}")
            return {"success": False, "error": str(e)}
    
    def set_hostname(self, hostname):
        """Set new hostname"""
        try:
            # Temporary change
            temp_cmd = f"sudo hostname {hostname}"
            temp_result = self._execute_command(temp_cmd)
            
            if not temp_result["success"]:
                return {"success": False, "error": temp_result["stderr"]}
            
            # Permanent change - different files for different distros
            hostname_file = "/etc/hostname"
            if os.path.exists(hostname_file):
                # Update /etc/hostname
                echo_cmd = f"echo '{hostname}' | sudo tee {hostname_file}"
                echo_result = self._execute_command(echo_cmd, shell=True)
                
                if not echo_result["success"]:
                    return {"success": False, "error": echo_result["stderr"]}
            
            # Update /etc/hosts if needed
            self._update_hosts_file(hostname)
            
            return {
                "success": True,
                "message": f"Hostname changed to '{hostname}'",
                "requires_reboot": True,
                "note": "Hostname change will be fully applied after reboot"
            }
                
        except Exception as e:
            self.logger(f"Error setting hostname: {e}")
            return {"success": False, "error": str(e)}
    
    def _update_hosts_file(self, new_hostname):
        """Update /etc/hosts with new hostname"""
        try:
            # Get current IP address
            ip_result = self._execute_command("hostname -I | awk '{print $1}'")
            if ip_result["success"]:
                ip_address = ip_result["stdout"].strip()
                if ip_address:
                    # Read current /etc/hosts
                    with open("/etc/hosts", "r") as f:
                        lines = f.readlines()
                    
                    # Update lines containing old hostname
                    updated_lines = []
                    old_hostname = socket.gethostname()
                    
                    for line in lines:
                        if ip_address in line and old_hostname in line:
                            # Replace old hostname with new
                            line = line.replace(old_hostname, new_hostname)
                        updated_lines.append(line)
                    
                    # Write back
                    temp_file = "/tmp/hosts.tmp"
                    with open(temp_file, "w") as f:
                        f.writelines(updated_lines)
                    
                    # Move to /etc/hosts
                    self._execute_command(f"sudo mv {temp_file} /etc/hosts")
                    self._execute_command("sudo chmod 644 /etc/hosts")
        except Exception as e:
            self.logger(f"Warning: Could not update /etc/hosts: {e}")
    
    def reboot(self, delay_seconds=0):
        """Reboot the system"""
        try:
            if delay_seconds > 0:
                cmd = f"sudo shutdown -r +{delay_seconds//60}"
                message = f"System will reboot in {delay_seconds} seconds"
            else:
                cmd = "sudo reboot now"
                message = "System rebooting now"
            
            result = self._execute_command(cmd, timeout=5)
            
            if result["success"] or "reboot scheduled" in result.get("stderr", "").lower():
                return {
                    "success": True,
                    "message": message,
                    "scheduled": delay_seconds > 0
                }
            else:
                return {"success": False, "error": result["stderr"]}
                
        except Exception as e:
            self.logger(f"Error initiating reboot: {e}")
            return {"success": False, "error": str(e)}

    def get_system_logs(self, n=50):
        """Get system logs - compatible dengan berbagai distro"""
        log_files = []
        
        # Determine log file based on OS
        if self.os_family in ['debian', 'ubuntu']:
            log_files = ["/var/log/syslog", "/var/log/messages"]
        elif self.os_family in ['rhel', 'centos', 'fedora']:
            log_files = ["/var/log/messages", "/var/log/syslog"]
        elif self.os_family == 'suse':
            log_files = ["/var/log/messages"]
        else:
            log_files = ["/var/log/syslog", "/var/log/messages"]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    result = self._execute_command(f"tail -n {n} {log_file}")
                    if result["success"]:
                        return result["stdout"].splitlines()
                except Exception:
                    continue
        
        # Fallback to journalctl if available
        try:
            result = self._execute_command(f"journalctl -n {n} --no-pager")
            if result["success"]:
                return result["stdout"].splitlines()
        except Exception:
            pass
        
        return {"error": "Could not access system logs"}

    def get_dmesg_logs(self, n=50):
        """Get kernel logs"""
        try:
            result = self._execute_command(f"dmesg -T | tail -n {n}")
            if result["success"]:
                return result["stdout"].splitlines()
            else:
                # Fallback without -T flag
                result = self._execute_command(f"dmesg | tail -n {n}")
                if result["success"]:
                    return result["stdout"].splitlines()
                else:
                    return {"error": result.get("error", result["stderr"])}
        except Exception as e:
            self.logger(f"Error getting dmesg logs: {e}")
            return {"error": str(e)}