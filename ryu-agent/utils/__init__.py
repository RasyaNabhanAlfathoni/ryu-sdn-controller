# ryu-agent/utils/__init__.py
import os
import subprocess

def detect_os_family():
    """Detect OS family - LEBIH DETAIL"""
    try:
        with open("/etc/os-release") as f:
            content = f.read().lower()
            
            # UBAH LOGIC JADI LEBIH SPECIFIC
            if 'ubuntu' in content:
                return 'ubuntu'
            elif 'debian' in content:
                return 'debian'
            elif 'centos' in content:
                return 'centos'      # CENTOS SPECIFIC
            elif 'rhel' in content or 'red hat' in content:
                return 'rhel'        # RED HAT ENTERPRISE
            elif 'fedora' in content:
                return 'fedora'
            elif 'suse' in content or 'opensuse' in content:
                return 'suse'
                
    except Exception:
        pass
    
    # FALLBACK DETECTION - LEBIH SPECIFIC
    try:
        if os.path.exists("/etc/centos-release"):
            with open("/etc/centos-release") as f:
                if 'centos' in f.read().lower():
                    return 'centos'
    except:
        pass
        
    try:
        if os.path.exists("/etc/redhat-release"):
            with open("/etc/redhat-release") as f:
                content = f.read().lower()
                if 'centos' in content:
                    return 'centos'
                elif 'red hat' in content:
                    return 'rhel'
                elif 'fedora' in content:
                    return 'fedora'
    except:
        pass
    
    if os.path.exists("/etc/debian_version"):
        return 'debian'
    
    return 'unknown'

def execute_command(cmd, timeout=30):
    """Execute command - Dipakai Semua Drivers"""
    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timeout after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}