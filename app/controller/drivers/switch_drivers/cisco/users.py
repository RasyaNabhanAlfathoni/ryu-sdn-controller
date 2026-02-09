import re
import logging

class CiscoUserManagement:
    def __init__(self, config):
        self.config = config
        self.base = None
        self.logger = logging.getLogger(__name__)
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base
    
    def get_user_list(self, logger=None):
        """Get list of all configured users"""
        try:
            if logger:
                logger("Fetching user list...")
            
            # Get AAA configuration
            output = self.base.execute_command("enable", enable_mode=False)
            output = self.base.execute_command("show running-config | section username", enable_mode=True)
            
            users = []
            lines = output.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('username'):
                    user_info = self._parse_user_line(line)
                    if user_info:
                        users.append(user_info)
            
            # Get privilege level information
            privilege_output = self.base.execute_command("enable", enable_mode=False)
            privilege_output = self.base.execute_command("show privilege", enable_mode=True)
            
            return {
                'status': 'success',
                'total_users': len(users),
                'users': users,
                'privilege_summary': self._parse_privilege_summary(privilege_output)
            }
            
        except Exception as e:
            error_msg = f"Error fetching user list: {str(e)}"
            if logger:
                logger(error_msg)
            self.logger.error(error_msg)
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def create_user(self, username, password, privilege_level=1, logger=None):
        """Create a new user"""
        try:
            if logger:
                logger(f"Creating user: {username}")
            
            # Validate username
            if not username or len(username) < 3:
                raise ValueError("Username must be at least 3 characters")
            
            # Validate privilege level
            privilege_level = int(privilege_level)
            if privilege_level < 1 or privilege_level > 15:
                raise ValueError("Privilege level must be between 1 and 15")
            
            # Check if user exists
            users = self.get_user_list(logger)
            existing_users = [u['username'] for u in users.get('users', [])]
            
            if username in existing_users:
                raise ValueError(f"User '{username}' already exists")
            
            # Execute commands to create user
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"username {username} privilege {privilege_level} secret {password}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            self.base.execute_command("write memory", enable_mode=True)
            
            if logger:
                logger(f"User '{username}' created successfully with privilege level {privilege_level}")
            
            return {
                'status': 'success',
                'message': f"User '{username}' created successfully",
                'username': username,
                'privilege_level': privilege_level
            }
            
        except Exception as e:
            error_msg = f"Error creating user '{username}': {str(e)}"
            if logger:
                logger(error_msg)
            self.logger.error(error_msg)
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def update_user_password(self, username, new_password, logger=None):
        """Update user password"""
        try:
            if logger:
                logger(f"Updating password for user: {username}")
            
            # Check if user exists
            users = self.get_user_list(logger)
            existing_users = [u['username'] for u in users.get('users', [])]
            
            if username not in existing_users:
                raise ValueError(f"User '{username}' does not exist")
            
            # Update password
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"username {username} secret {new_password}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            self.base.execute_command("write memory", enable_mode=True)
            
            if logger:
                logger(f"Password updated for user '{username}'")
            
            return {
                'status': 'success',
                'message': f"Password updated for user '{username}'",
                'username': username
            }
            
        except Exception as e:
            error_msg = f"Error updating password for '{username}': {str(e)}"
            if logger:
                logger(error_msg)
            self.logger.error(error_msg)
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def update_user_privilege(self, username, privilege_level, logger=None):
        """Update user privilege level"""
        try:
            if logger:
                logger(f"Updating privilege for user: {username} to level {privilege_level}")
            
            # Validate privilege level
            privilege_level = int(privilege_level)
            if privilege_level < 1 or privilege_level > 15:
                raise ValueError("Privilege level must be between 1 and 15")
            
            # Check if user exists
            users = self.get_user_list(logger)
            user_exists = any(u['username'] == username for u in users.get('users', []))
            
            if not user_exists:
                raise ValueError(f"User '{username}' does not exist")
            
            # Update privilege
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"username {username} privilege {privilege_level}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            self.base.execute_command("write memory", enable_mode=True)
            
            if logger:
                logger(f"Privilege updated for user '{username}' to level {privilege_level}")
            
            return {
                'status': 'success',
                'message': f"Privilege updated for user '{username}' to level {privilege_level}",
                'username': username,
                'privilege_level': privilege_level
            }
            
        except Exception as e:
            error_msg = f"Error updating privilege for '{username}': {str(e)}"
            if logger:
                logger(error_msg)
            self.logger.error(error_msg)
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def delete_user(self, username, logger=None):
        """Delete a user with confirmation handling"""
        try:
            if logger:
                logger(f"Deleting user: {username}")

            # Protect critical users
            protected_users = ["admin", "root", "cisco"]
            if username.lower() in protected_users:
                raise ValueError(f"User '{username}' is protected and cannot be deleted")

            # Check if user exists
            users = self.get_user_list(logger)
            user_exists = any(u['username'] == username for u in users.get('users', []))

            if not user_exists:
                raise ValueError(f"User '{username}' does not exist")

            # Enter config mode
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)

            # Send delete command
            output = self.base.execute_command(
                f"no username {username}",
                enable_mode=True
            )

            # Handle Cisco confirmation prompt
            if "confirm" in output.lower():
                if logger:
                    logger("Confirmation required, sending ENTER to confirm deletion")
                self.base.execute_command("", enable_mode=True)  # Biar ke Enter saat validasi 

            # Exit config mode
            self.base.execute_command("end", enable_mode=True)

            # Save config
            self.base.execute_command("write memory", enable_mode=True)

            # Verify deletion
            verify = self.base.execute_command("enable", enable_mode=False)
            verify = self.base.execute_command(
                "show running-config | section username",
                enable_mode=True
            )

            if f"username {username}" in verify:
                raise RuntimeError("User deletion verification failed")

            if logger:
                logger(f"User '{username}' deleted successfully")

            return {
                'status': 'success',
                'message': f"User '{username}' deleted successfully",
                'username': username
            }

        except Exception as e:
            error_msg = f"Error deleting user '{username}': {str(e)}"
            if logger:
                logger(error_msg)
            self.logger.error(error_msg)

            return {
                'status': 'error',
                'error': str(e),
                'username': username
            }
    
    def _parse_user_line(self, line):
        """Parse username configuration line"""
        try:
            pattern = r'username\s+(\S+)(?:\s+privilege\s+(\d+))?(?:\s+.*secret\s+.*)?'
            match = re.search(pattern, line)
            
            if match:
                return {
                    'username': match.group(1),
                    'privilege_level': int(match.group(2)) if match.group(2) else 1,
                    'has_password': 'secret' in line.lower() or 'password' in line.lower()
                }
            return None
        except:
            return None
    
    def _parse_privilege_summary(self, output):
        """Parse privilege summary"""
        summary = {
            'current_level': 1,
            'available_levels': list(range(1, 16))
        }
        
        for line in output.split('\n'):
            if 'Current privilege level' in line:
                match = re.search(r'Current privilege level is (\d+)', line)
                if match:
                    summary['current_level'] = int(match.group(1))
        
        return summary