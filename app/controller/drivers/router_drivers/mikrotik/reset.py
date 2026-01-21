class MikroTikRouterResetDriver:
    name = "mikrotikrouter_reset"
    
    def __init__(self, core):
        self.core = core
        
        # Resource paths
        self.RESOURCES = {
            "system": "/system",
            "backup": "/system/backup",
            "export": "/export",
            "script": "/system/script",
            "scheduler": "/system/scheduler",
            "reboot": "/system/reboot",
            "reset": "/system/reset-configuration"
        }

    def backup_configuration(self, p, logger=print):
        """
        Backup current configuration to file
        
        Parameters:
        - filename: Nama file backup (optional, default: backup_YYYYMMDD_HHMMSS)
        - password: Password untuk encrypt backup (optional)
        """
        pool, api = self.core.get_api()
        try:
            # Generate filename jika tidak diberikan
            from datetime import datetime
            if not p.get("filename"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"backup_{timestamp}"
            else:
                filename = p["filename"]
            
            # Remove .backup extension if provided
            if filename.endswith('.backup'):
                filename = filename[:-7]
            
            # Build parameters
            backup_params = {"name": filename}
            
            # Add password if provided
            if p.get("password"):
                backup_params["password"] = p["password"]
            
            # Create backup
            res = api.get_resource(self.RESOURCES["backup"])
            result = res.call("save", backup_params)
            
            logger(f"Configuration backed up to: {filename}.backup")
            return {
                "status": "success",
                "action": "backup",
                "filename": f"{filename}.backup",
                "message": "Configuration backup created successfully"
            }
            
        except Exception as e:
            logger(f"Backup failed: {str(e)}")
            raise Exception(f"Backup failed: {str(e)}")
        finally:
            pool.disconnect()

    def restore_configuration(self, p, logger=print):
        """
        Restore configuration from backup file
        
        Parameters:
        - filename: Nama file backup (tanpa .backup extension)
        - password: Password jika backup encrypted (optional)
        """
        pool, api = self.core.get_api()
        try:
            if not p.get("filename"):
                raise Exception("Filename is required")
            
            filename = p["filename"]
            
            # Remove .backup extension if provided
            if filename.endswith('.backup'):
                filename = filename[:-7]
            
            # Build parameters
            restore_params = {"name": filename}
            
            # Add password if provided
            if p.get("password"):
                restore_params["password"] = p["password"]
            
            # Restore backup
            res = api.get_resource(self.RESOURCES["backup"])
            result = res.call("load", restore_params)
            
            logger(f"Configuration restored from: {filename}.backup")
            return {
                "status": "success",
                "action": "restore",
                "filename": f"{filename}.backup",
                "message": "Configuration restored successfully"
            }
            
        except Exception as e:
            logger(f"Restore failed: {str(e)}")
            raise Exception(f"Restore failed: {str(e)}")
        finally:
            pool.disconnect()

    def export_configuration(self, p, logger=print):
        """
        Export configuration to text file (rsc format)
        
        Parameters:
        - filename: Nama file export (optional)
        - include_passwords: Include passwords in export (default: False)
        """
        pool, api = self.core.get_api()
        try:
            # Generate filename jika tidak diberikan
            from datetime import datetime
            if not p.get("filename"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"export_{timestamp}.rsc"
            else:
                filename = p["filename"]
                if not filename.endswith('.rsc'):
                    filename += '.rsc'
            
            # Export configuration
            res = api.get_resource(self.RESOURCES["export"])
            
            export_params = {}
            if p.get("include_passwords", False):
                export_params["show-sensitive"] = "yes"
            else:
                export_params["show-sensitive"] = "no"
            
            # Get export data
            export_data = res.call("", export_params)
            
            if export_data and len(export_data) > 0:
                config_text = export_data[0]
                
                logger(f"Configuration exported to: {filename}")
                return {
                    "status": "success",
                    "action": "export",
                    "filename": filename,
                    "config_size": len(config_text),
                    "config_preview": config_text[:500] + "..." if len(config_text) > 500 else config_text
                }
            else:
                raise Exception("Failed to get export data")
            
        except Exception as e:
            logger(f"Export failed: {str(e)}")
            raise Exception(f"Export failed: {str(e)}")
        finally:
            pool.disconnect()

    def reset_configuration(self, p, logger=print):
        """
        Reset MikroTik configuration with options
        
        Parameters (4 checkboxes):
        - skip_backup: boolean (default: False) - Skip backup before reset
        - keep_users: boolean (default: False) - Keep existing users
        - no_defaults: boolean (default: False) - Don't set defaults after reset
        - archive_backup: boolean (default: False) - Create archive backup
        
        Additional:
        - backup_filename: Nama file backup (optional)
        - run_after_reset: Nama file script/setup untuk dijalankan setelah reset (optional)
        """
        pool, api = self.core.get_api()
        try:
            # 1 Backup before reset (if not skipped)
            if not p.get("skip_backup", False):
                backup_params = {}
                if p.get("backup_filename"):
                    backup_params["filename"] = p["backup_filename"]
                
                if p.get("archive_backup", False):
                    # Archive backup requires special handling
                    logger("Creating archive backup...")
                    # Archive backup dibuat dengan cara yang berbeda
                
                self.backup_configuration(backup_params, logger)
            
            # 2 Prepare reset parameters
            reset_params = {}
            
            # Map checkbox options to MikroTik parameters
            if p.get("keep_users", False):
                reset_params["keep-users"] = "yes"
            else:
                reset_params["keep-users"] = "no"
            
            if p.get("no_defaults", False):
                reset_params["no-defaults"] = "yes"
            else:
                reset_params["no-defaults"] = "no"
            
            if p.get("skip_backup", False):
                reset_params["skip-backup"] = "yes"
            else:
                reset_params["skip-backup"] = "no"
            
            # 3 Create post-reset script jika diperlukan
            if p.get("run_after_reset"):
                self._create_post_reset_script(p["run_after_reset"], api, logger)
        
            # 4 Execute reset
            logger("Executing reset configuration...")
            res = api.get_resource(self.RESOURCES["reset"])
            result = res.call("", reset_params)
            
            logger("Reset configuration command sent successfully")
            return {
                "status": "success",
                "action": "reset_configuration",
                "options": {
                    "skip_backup": p.get("skip_backup", False),
                    "keep_users": p.get("keep_users", False),
                    "no_defaults": p.get("no_defaults", False),
                    "archive_backup": p.get("archive_backup", False)
                },
                "message": "Configuration reset initiated. Device will reboot.",
                "note": "Device will reboot automatically after reset"
            }
            
        except Exception as e:
            logger(f"Reset failed: {str(e)}")
            raise Exception(f"Reset failed: {str(e)}")
        finally:
            pool.disconnect()

    def reboot_device(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            delay = p.get("delay", 0)

            res = api.get_resource("/system")

            if delay > 0:
                res.call("reboot", {"delay": str(delay)})
                logger(f"Reboot scheduled in {delay} seconds")
            else:
                res.call("reboot")
                logger("Reboot initiated immediately")

            return {
                "status": "success",
                "action": "reboot",
                "delay": delay,
            }

        except Exception as e:
            logger(f"Reboot failed: {str(e)}")
            raise Exception(f"Reboot failed: {str(e)}")
        finally:
            pool.disconnect()

    def list_backups(self, p=None, logger=print):
        """
        List all backup files on device
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCES["backup"])
            backups = res.get()
            
            backup_list = []
            for backup in backups:
                backup_list.append({
                    "name": backup.get("name", ""),
                    "size": backup.get("size", ""),
                    "creation_time": backup.get("creation-time", ""),
                    "_id": backup.get(".id", "")
                })
            
            logger(f"Found {len(backup_list)} backup files")
            return backup_list
            
        except Exception as e:
            logger(f"Failed to list backups: {str(e)}")
            raise Exception(f"Failed to list backups: {str(e)}")
        finally:
            pool.disconnect()

    def delete_backup(self, p, logger=print):
        """
        Delete backup file
        
        Parameters:
        - filename: Nama file backup (tanpa .backup extension)
        """
        pool, api = self.core.get_api()
        try:
            if not p.get("filename"):
                raise Exception("Filename is required")
            
            filename = p["filename"]
            
            # Remove .backup extension if provided
            if filename.endswith('.backup'):
                filename = filename[:-7]
            
            res = api.get_resource(self.RESOURCES["backup"])
            res.remove(numbers=filename)
            
            logger(f"Backup file '{filename}.backup' deleted")
            return {
                "status": "success",
                "action": "delete_backup",
                "filename": f"{filename}.backup",
                "message": "Backup file deleted successfully"
            }
            
        except Exception as e:
            logger(f"Failed to delete backup: {str(e)}")
            raise Exception(f"Failed to delete backup: {str(e)}")
        finally:
            pool.disconnect()

    def factory_reset(self, p=None, logger=print):
        """
        Complete factory reset (hard reset)
        Equivalent to holding reset button
        """
        logger("WARNING: Performing factory reset (hard reset)...")
        
        confirmation = p.get("confirmed", False)
        if not confirmation:
            raise Exception("Factory reset requires explicit confirmation")
        
        pool, api = self.core.get_api()
        try:
            reset_params = {
                "keep-users": "no",
                "no-defaults": "no",
                "skip-backup": "no"
            }
            
            res = api.get_resource(self.RESOURCES["reset"])
            result = res.call("", reset_params)
            
            logger("Factory reset initiated")
            return {
                "status": "success",
                "action": "factory_reset",
                "message": "Factory reset initiated. Device will reboot to factory defaults.",
                "warning": "ALL configuration will be erased!"
            }
            
        except Exception as e:
            logger(f"Factory reset failed: {str(e)}")
            raise Exception(f"Factory reset failed: {str(e)}")
        finally:
            pool.disconnect()