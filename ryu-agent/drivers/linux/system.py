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
from utils import detect_os_family, execute_command, execute_on_host, execute_on_ssh

class ServerSystemDriver:
    def __init__(self, logger=print):
        self.logger = logger
        self.os_family = detect_os_family()
        self._execute_on_host = execute_on_host
        self._execute_on_ssh = execute_on_ssh
        self._execute_command = execute_command
        self.logger(f"Detected OS: {self.os_family}")

    def _execute(self, cmd, use_ssh=False, shell=False, timeout=30):
        """Wrapper untuk execute command dengan fallback"""
        try:
            if use_ssh:
                return self._execute_on_ssh(cmd)
            else:
                return self._execute_on_host(cmd)
        except Exception as e:
            self.logger(f"Error executing command: {e}")
            return {"success": False, "error": str(e)}

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
            # Gunakan getent passwd dari host
            result = self._execute("getent passwd")
            if not result["success"]:
                return {"success": False, "error": result.get("stderr", "Failed to get users")}
            
            users = []
            for line in result["stdout"].strip().split('\n'):
                if line:
                    parts = line.split(':')
                    if len(parts) >= 7:
                        username = parts[0]
                        uid = int(parts[2])
                        gid = int(parts[3])
                        
                        # Filter: hanya user dengan UID >= 1000 atau root
                        if uid >= 1000 or username == "root":
                            # Skip nobody dan user system lain
                            if username not in ["nobody", "nogroup", "daemon", "bin", "sys"]:
                                # Skip user dengan shell nologin/false (kecuali root)
                                if username == "root" or ('nologin' not in parts[6] and 'false' not in parts[6]):
                                    users.append({
                                        "username": username,
                                        "uid": uid,
                                        "gid": gid,
                                        "fullname": parts[4],
                                        "home": parts[5],
                                        "shell": parts[6]
                                    })
            
            # Sort by username
            users.sort(key=lambda x: x['username'])
            
            return {"success": True, "users": users}
            
        except Exception as e:
            self.logger(f"Error getting users: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user_info(self, username):
        """Get detailed information about a specific user"""
        try:
            # Gunakan getent passwd
            result = self._execute(f"getent passwd {username}")
            if not result["success"]:
                return {"success": False, "error": f"User '{username}' not found"}
            
            parts = result["stdout"].strip().split(':')
            if len(parts) < 7:
                return {"success": False, "error": f"Invalid user entry for '{username}'"}
            
            # Get groups user belongs to
            groups_result = self._execute(f"id -Gn {username}")
            groups = groups_result["stdout"].strip().split() if groups_result["success"] else []
            
            return {
                "success": True,
                "user": {
                    "username": parts[0],
                    "uid": int(parts[2]),
                    "gid": int(parts[3]),
                    "fullname": parts[4],
                    "home": parts[5],
                    "shell": parts[6],
                    "groups": groups
                }
            }
            
        except Exception as e:
            self.logger(f"Error getting user info: {e}")
            return {"success": False, "error": str(e)}
    
    def create_user(self, username, password=None, shell="/bin/bash", home_dir=None, use_ssh=True):
        """Create a new system user"""
        try:
            # Build command
            cmd = f"useradd -m"
            
            if shell:
                cmd += f" -s {shell}"
            
            if home_dir:
                cmd += f" -d {home_dir}"
            else:
                cmd += f" -d /home/{username}"
            
            # Add username
            cmd += f" {username}"
            
            # Execute command (gunakan SSH untuk user management)
            result = self._execute(cmd, use_ssh=use_ssh)
            
            if result["success"]:
                # Set password if provided
                if password:
                    pwd_result = self._set_password(username, password, use_ssh)
                    if not pwd_result:
                        return {"success": False, "error": f"User created but failed to set password"}
                
                return {
                    "success": True,
                    "message": f"User '{username}' created successfully",
                    "details": result["stdout"]
                }
            else:
                # Check if user already exists
                check_result = self._execute(f"id {username}")
                if check_result["success"]:
                    return {"success": False, "error": f"User '{username}' already exists"}
                else:
                    return {"success": False, "error": result.get("stderr", result.get("error", "Unknown error"))}
                
        except Exception as e:
            self.logger(f"Error creating user: {e}")
            return {"success": False, "error": str(e)}
    
    def _set_password(self, username, password, use_ssh=True):
        """Set password for user using chpasswd"""
        try:
            # Escape special characters in password
            escaped_password = password.replace("'", "'\"'\"'")
            cmd = f"echo '{username}:{escaped_password}' | chpasswd"
            
            result = self._execute(cmd, use_ssh=use_ssh, shell=True)
            return result["success"]
            
        except Exception as e:
            self.logger(f"Error setting password: {e}")
            return False
    
    def delete_user(self, username, remove_home=False, use_ssh=True):
        """Delete a system user"""
        try:
            # Check if user exists first
            check_result = self._execute(f"id {username}")
            if not check_result["success"]:
                return {"success": False, "error": f"User '{username}' does not exist"}
            
            cmd = f"userdel"
            if remove_home:
                cmd += " -r"
            cmd += f" {username}"
            
            result = self._execute(cmd, use_ssh=use_ssh)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"User '{username}' deleted successfully"
                }
            else:
                return {"success": False, "error": result.get("stderr", result.get("error", "Unknown error"))}
                
        except Exception as e:
            self.logger(f"Error deleting user: {e}")
            return {"success": False, "error": str(e)}
    
    def modify_user(self, username, shell=None, home_dir=None, use_ssh=True):
        """Modify user properties"""
        try:
            # Check if user exists
            check_result = self._execute(f"id {username}")
            if not check_result["success"]:
                return {"success": False, "error": f"User '{username}' does not exist"}
            
            cmd = f"usermod"
            
            if shell:
                cmd += f" -s {shell}"
            
            if home_dir:
                cmd += f" -d {home_dir}"
                cmd += f" -m"  # Move contents to new home
            
            cmd += f" {username}"
            
            result = self._execute(cmd, use_ssh=use_ssh)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"User '{username}' modified successfully"
                }
            else:
                return {"success": False, "error": result.get("stderr", result.get("error", "Unknown error"))}
                
        except Exception as e:
            self.logger(f"Error modifying user: {e}")
            return {"success": False, "error": str(e)}
    
    def change_user_password(self, username, password, use_ssh=True):
        """Change user password"""
        try:
            result = {
                "success": self._set_password(username, password, use_ssh),
                "message": f"Password for '{username}' changed successfully"
            }
            
            if not result["success"]:
                result["error"] = "Failed to change password"
                
            return result
            
        except Exception as e:
            self.logger(f"Error changing password: {e}")
            return {"success": False, "error": str(e)}
    
    def add_user_to_group(self, username, group, use_ssh=True):
        """Add user to group"""
        try:
            # Check if user exists
            user_check = self._execute(f"id {username}")
            if not user_check["success"]:
                return {"success": False, "error": f"User '{username}' does not exist"}
            
            # Check if group exists
            group_check = self._execute(f"getent group {group}")
            if not group_check["success"]:
                # Create group if it doesn't exist
                create_result = self._execute(f"groupadd {group}", use_ssh=use_ssh)
                if not create_result["success"]:
                    return {"success": False, "error": f"Group '{group}' doesn't exist and failed to create"}
            
            cmd = f"usermod -a -G {group} {username}"
            result = self._execute(cmd, use_ssh=use_ssh)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"User '{username}' added to group '{group}'"
                }
            else:
                return {"success": False, "error": result.get("stderr", result.get("error", "Unknown error"))}
                
        except Exception as e:
            self.logger(f"Error adding user to group: {e}")
            return {"success": False, "error": str(e)}
    
    def remove_user_from_group(self, username, group, use_ssh=True):
        """Remove user from group"""
        try:
            # Get current groups
            result = self._execute(f"groups {username}")
            if not result["success"]:
                return {"success": False, "error": result.get("stderr", "User not found or command failed")}
            
            # Parse groups
            output = result["stdout"].strip()
            if ':' in output:
                groups = output.split(':')[1].strip().split()
            else:
                groups = output.split()
            
            # Check if user is in group
            if group not in groups:
                return {"success": False, "error": f"User '{username}' is not in group '{group}'"}
            
            # Remove the group
            groups.remove(group)
            
            # Re-set groups if any left
            if groups:
                groups_str = ",".join(groups)
                cmd = f"usermod -G {groups_str} {username}"
                result = self._execute(cmd, use_ssh=use_ssh)
                
                if result["success"]:
                    return {
                        "success": True,
                        "message": f"User '{username}' removed from group '{group}'"
                    }
                else:
                    return {"success": False, "error": result.get("stderr", result.get("error", "Unknown error"))}
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
            result = self._execute("getent group")
            if not result["success"]:
                return {"success": False, "error": result.get("stderr", "Failed to get groups")}
            
            groups = []
            for line in result["stdout"].strip().split('\n'):
                if line:
                    parts = line.split(':')
                    if len(parts) >= 3:
                        groupname = parts[0]
                        gid = int(parts[2])
                        members = parts[3].split(',') if len(parts) > 3 and parts[3] else []
                        
                        # Skip system groups (GID < 1000)
                        if gid >= 1000:
                            groups.append({
                                "groupname": groupname,
                                "gid": gid,
                                "members": members
                            })
            
            return {"success": True, "groups": groups}
            
        except Exception as e:
            self.logger(f"Error getting groups: {e}")
            return {"success": False, "error": str(e)}
    
    def create_group(self, group_name, use_ssh=True):
        """Create a new system group"""
        try:
            # Check if group exists
            check_result = self._execute(f"getent group {group_name}")
            if check_result["success"]:
                return {"success": False, "error": f"Group '{group_name}' already exists"}
            
            cmd = f"groupadd {group_name}"
            result = self._execute(cmd, use_ssh=use_ssh)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Group '{group_name}' created successfully"
                }
            else:
                return {"success": False, "error": result.get("stderr", result.get("error", "Unknown error"))}
                
        except Exception as e:
            self.logger(f"Error creating group: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_group(self, group_name, use_ssh=True):
        """Delete a system group"""
        try:
            # Check if group exists
            check_result = self._execute(f"getent group {group_name}")
            if not check_result["success"]:
                return {"success": False, "error": f"Group '{group_name}' does not exist"}
            
            cmd = f"groupdel {group_name}"
            result = self._execute(cmd, use_ssh=use_ssh)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Group '{group_name}' deleted successfully"
                }
            else:
                return {"success": False, "error": result.get("stderr", result.get("error", "Unknown error"))}
                
        except Exception as e:
            self.logger(f"Error deleting group: {e}")
            return {"success": False, "error": str(e)}
    
    def get_hostname(self):
        """Get current hostname"""
        try:
            result = self._execute("hostname")
            if result["success"]:
                hostname = result["stdout"].strip()
                # Also get FQDN if available
                fqdn_result = self._execute("hostname -f")
                fqdn = fqdn_result["stdout"].strip() if fqdn_result["success"] else hostname
                
                return {
                    "success": True,
                    "hostname": hostname,
                    "fqdn": fqdn,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"success": False, "error": result.get("stderr", result.get("error", "Unknown error"))}
        except Exception as e:
            self.logger(f"Error getting hostname: {e}")
            return {"success": False, "error": str(e)}
    
    def set_hostname(self, hostname, use_ssh=True):
        """Set new hostname"""
        try:
            # Temporary change
            temp_cmd = f"hostname {hostname}"
            temp_result = self._execute(temp_cmd, use_ssh=use_ssh)
            
            if not temp_result["success"]:
                return {"success": False, "error": temp_result.get("stderr", temp_result.get("error", "Unknown error"))}
            
            # Permanent change
            hostname_file = "/etc/hostname"
            echo_cmd = f"echo '{hostname}' > {hostname_file}"
            echo_result = self._execute(echo_cmd, use_ssh=use_ssh)
            
            if not echo_result["success"]:
                return {"success": False, "error": echo_result.get("stderr", echo_result.get("error", "Unknown error"))}
            
            # Update /etc/hosts
            update_result = self._update_hosts_file(hostname, use_ssh)
            
            return {
                "success": True,
                "message": f"Hostname changed to '{hostname}'",
                "requires_reboot": True,
                "note": "Hostname change will be fully applied after reboot",
                "hosts_updated": update_result
            }
                
        except Exception as e:
            self.logger(f"Error setting hostname: {e}")
            return {"success": False, "error": str(e)}
    
    def _update_hosts_file(self, new_hostname, use_ssh=True):
        """Update /etc/hosts with new hostname"""
        try:
            # Get current hostname
            old_result = self._execute("hostname")
            if not old_result["success"]:
                return False
            
            old_hostname = old_result["stdout"].strip()
            
            # Read current /etc/hosts
            read_result = self._execute("cat /etc/hosts")
            if not read_result["success"]:
                return False
            
            lines = read_result["stdout"].splitlines()
            updated_lines = []
            
            for line in lines:
                # Replace old hostname with new in localhost lines
                if '127.0.0.1' in line or '::1' in line:
                    line = line.replace(old_hostname, new_hostname)
                updated_lines.append(line)
            
            # Write back
            temp_file = "/tmp/hosts.tmp"
            content = "\n".join(updated_lines)
            write_cmd = f"echo '{content}' > {temp_file} && mv {temp_file} /etc/hosts && chmod 644 /etc/hosts"
            write_result = self._execute(write_cmd, use_ssh=use_ssh, shell=True)
            
            return write_result["success"]
            
        except Exception as e:
            self.logger(f"Warning: Could not update /etc/hosts: {e}")
            return False
    
    def reboot(self, delay_seconds=0, use_ssh=True):
        """Reboot the system - MENGGUNAKAN SSH"""
        try:
            if delay_seconds > 0:
                cmd = f"shutdown -r +{delay_seconds//60}"
                message = f"System will reboot in {delay_seconds} seconds"
            else:
                cmd = "reboot now"
                message = "System rebooting now"
            
            result = self._execute(cmd, use_ssh=use_ssh, timeout=5)
            
            if result["success"] or "reboot scheduled" in result.get("stderr", "").lower():
                return {
                    "success": True,
                    "message": message,
                    "scheduled": delay_seconds > 0
                }
            else:
                return {"success": False, "error": result.get("stderr", result.get("error", "Unknown error"))}
                
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