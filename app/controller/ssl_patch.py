# ssl_patch.py
"""
Monkey patch untuk mengatasi SSL recursion bug di Python 3.9
Harus di-import SEBELUM modul lain yang menggunakan requests/urllib3
"""
import sys
import ssl
import urllib3

def apply_ssl_patch():
    """Apply semua patch untuk SSL recursion bug"""
    print("[SSL_PATCH] Applying SSL recursion bug patches...")
    
    # Patch 1: Disable SSL verification completely
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        print("[SSL_PATCH] Disabled SSL verification")
    except:
        pass
    
    # Patch 2: Disable urllib3 warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    print("[SSL_PATCH] Disabled urllib3 warnings")
    
    # Patch 3: Monkey patch urllib3 untuk menghindari recursion
    try:
        import urllib3.util.ssl_ as ssl_
        
        # Simpan original function
        original_create_urllib3_context = ssl_.create_urllib3_context
        
        # Buat patched version
        def patched_create_urllib3_context():
            """Patched version yang skip problematic attributes"""
            context = original_create_urllib3_context()
            
            # Skip setting minimum_version jika ada recursion bug
            try:
                # Coba set dengan try-except
                context.minimum_version = ssl.TLSVersion.TLSv1_2
            except RecursionError:
                # Jika terjadi recursion, skip setting ini
                print("[SSL_PATCH] Skipping minimum_version due to recursion bug")
                pass
            except AttributeError:
                # Jika attribute tidak ada, ignore
                pass
                
            return context
        
        # Apply patch
        ssl_.create_urllib3_context = patched_create_urllib3_context
        print("[SSL_PATCH] Patched urllib3 SSL context creation")
        
    except Exception as e:
        print(f"[SSL_PATCH] Warning: Could not patch urllib3: {e}")
    
    # Patch 4: Patch SSLContext langsung
    try:
        original_setattr = ssl.SSLContext.__setattr__
        
        def patched_setattr(self, name, value):
            """Patched __setattr__ untuk handle recursion"""
            if name == 'minimum_version':
                try:
                    # Coba set dengan protection
                    return original_setattr(self, name, value)
                except RecursionError:
                    print(f"[SSL_PATCH] Skipping SSLContext.minimum_version due to recursion")
                    return
            return original_setattr(self, name, value)
        
        ssl.SSLContext.__setattr__ = patched_setattr
        print("[SSL_PATCH] Patched SSLContext.__setattr__")
        
    except Exception as e:
        print(f"[SSL_PATCH] Warning: Could not patch SSLContext: {e}")
    
    print("[SSL_PATCH] All patches applied")

# Apply patch saat module di-import
apply_ssl_patch()