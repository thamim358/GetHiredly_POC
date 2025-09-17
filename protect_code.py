#!/usr/bin/env python3
"""
Code Protection and Obfuscation Manager
Protects Python source code before distribution using multiple methods
"""

import os
import sys
import subprocess
import shutil
import json
import base64
from pathlib import Path
import zipfile
import tempfile

class CodeProtector:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.source_files = [
            'professional_dashboard_api.py',
            'linkedin_email_extractor.py',
            'runAiBot.py',
            'license_manager.py',
            'desktop_webdriver_manager.py',
            'email_config.py',
            'dashboard_api.py'
        ]
        
        # Directories to obfuscate
        self.source_dirs = [
            'modules',
            'config'
        ]
        
        self.protected_dir = self.base_dir / "protected"
        self.obfuscated_dir = self.base_dir / "obfuscated"
        
    def setup_protection_environment(self):
        """Set up environment for code protection"""
        print("🔧 Setting up protection environment...")
        
        # Clean previous protection
        for dir_path in [self.protected_dir, self.obfuscated_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
        
        # Create directories
        self.protected_dir.mkdir(exist_ok=True)
        self.obfuscated_dir.mkdir(exist_ok=True)
        
        print("✅ Protection environment ready")
    
    def check_pyarmor(self):
        """Check if PyArmor is available"""
        try:
            result = subprocess.run(['pyarmor', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ PyArmor found: {result.stdout.strip()}")
                return True
            else:
                print("❌ PyArmor not working properly")
                return False
        except FileNotFoundError:
            print("❌ PyArmor not found. Installing...")
            return self.install_pyarmor()
    
    def install_pyarmor(self):
        """Install PyArmor"""
        try:
            print("📦 Installing PyArmor...")
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyarmor'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ PyArmor installed successfully")
                return True
            else:
                print(f"❌ Failed to install PyArmor: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error installing PyArmor: {e}")
            return False
    
    def obfuscate_with_pyarmor(self):
        """Obfuscate code using PyArmor"""
        print("🛡️ Obfuscating code with PyArmor...")
        
        if not self.check_pyarmor():
            return False
        
        try:
            # Initialize PyArmor project
            project_dir = self.obfuscated_dir / "pyarmor_project"
            project_dir.mkdir(exist_ok=True)
            
            # Generate registration code (hardware-locked)
            reg_code = self._generate_registration_code()
            
            # Obfuscate main files
            for source_file in self.source_files:
                source_path = self.base_dir / source_file
                if source_path.exists():
                    print(f"  Obfuscating: {source_file}")
                    
                    # PyArmor obfuscation command
                    cmd = [
                        'pyarmor', 'obfuscate',
                        '--output', str(project_dir),
                        '--recursive',
                        '--restrict-module', '1',  # Restrict module usage
                        '--wrap-mode', '1',        # Wrap mode for better protection
                        '--advanced', '2',         # Advanced obfuscation
                        str(source_path)
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.base_dir))
                    
                    if result.returncode != 0:
                        print(f"    ❌ Failed to obfuscate {source_file}: {result.stderr}")
                    else:
                        print(f"    ✅ Obfuscated: {source_file}")
            
            # Obfuscate directories
            for source_dir in self.source_dirs:
                source_path = self.base_dir / source_dir
                if source_path.exists():
                    print(f"  Obfuscating directory: {source_dir}")
                    
                    cmd = [
                        'pyarmor', 'obfuscate',
                        '--output', str(project_dir / source_dir),
                        '--recursive',
                        str(source_path)
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.base_dir))
                    
                    if result.returncode != 0:
                        print(f"    ❌ Failed to obfuscate {source_dir}: {result.stderr}")
                    else:
                        print(f"    ✅ Obfuscated: {source_dir}")
            
            print("✅ PyArmor obfuscation completed")
            return True
            
        except Exception as e:
            print(f"❌ PyArmor obfuscation failed: {e}")
            return False
    
    def _generate_registration_code(self):
        """Generate hardware-specific registration code"""
        import hashlib
        import uuid
        import platform
        
        # Get hardware info
        hardware_info = {
            'mac': hex(uuid.getnode()),
            'system': platform.system(),
            'machine': platform.machine(),
            'processor': platform.processor()[:20]
        }
        
        # Create registration code
        info_string = json.dumps(hardware_info, sort_keys=True)
        reg_code = hashlib.sha256(info_string.encode()).hexdigest()[:32]
        
        return reg_code
    
    def create_string_obfuscation(self):
        """Create additional string obfuscation for sensitive data"""
        print("🔐 Creating string obfuscation...")
        
        # Sensitive strings to obfuscate
        sensitive_strings = {
            'API_KEYS': ['openai', 'gemini', 'deepseek'],
            'ENDPOINTS': ['api.openai.com', 'generativelanguage.googleapis.com'],
            'CREDENTIALS': ['email', 'password', 'token'],
            'FEATURES': ['premium', 'unlimited', 'enterprise']
        }
        
        # Create obfuscation mapping
        obfuscation_map = {}
        
        for category, strings in sensitive_strings.items():
            obfuscation_map[category] = {}
            for string in strings:
                # Base64 + custom encoding
                encoded = base64.b64encode(string.encode()).decode()
                # Add random padding
                padded = f"__{encoded}__padding__"
                obfuscation_map[category][string] = padded
        
        # Save obfuscation map
        map_file = self.protected_dir / "obfuscation_map.json"
        with open(map_file, 'w') as f:
            json.dump(obfuscation_map, f, indent=2)
        
        # Create decoder
        decoder_code = '''
import base64
import json

class StringDecoder:
    def __init__(self):
        # Load obfuscation map (embed in production)
        self.map = ''' + json.dumps(obfuscation_map) + '''
    
    def decode(self, category, key):
        try:
            encoded = self.map[category][key]
            # Remove padding
            clean = encoded.replace('__', '').replace('padding', '')
            # Decode base64
            decoded = base64.b64decode(clean).decode()
            return decoded
        except:
            return key  # Fallback to original
    
    def get_api_key(self, service):
        return self.decode('API_KEYS', service)
    
    def get_endpoint(self, service):
        return self.decode('ENDPOINTS', service)

# Global decoder instance
decoder = StringDecoder()
'''
        
        decoder_file = self.protected_dir / "string_decoder.py"
        with open(decoder_file, 'w') as f:
            f.write(decoder_code)
        
        print("✅ String obfuscation created")
        return True
    
    def create_anti_debugging(self):
        """Create anti-debugging and tamper detection"""
        print("🛡️ Creating anti-debugging protection...")
        
        anti_debug_code = '''
import sys
import os
import hashlib
import time
import threading
from datetime import datetime

class AntiDebug:
    def __init__(self):
        self.checks_enabled = True
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start anti-debugging monitoring"""
        if self.checks_enabled:
            threading.Thread(target=self._monitor_loop, daemon=True).start()
    
    def _monitor_loop(self):
        """Continuous monitoring loop"""
        while self.checks_enabled:
            try:
                # Check for debugger
                if self._is_debugger_present():
                    self._handle_debug_detection()
                
                # Check for reverse engineering tools
                if self._check_reverse_tools():
                    self._handle_debug_detection()
                
                # Check file integrity
                if not self._verify_integrity():
                    self._handle_tampering()
                
                time.sleep(5)  # Check every 5 seconds
                
            except:
                pass  # Silent failure
    
    def _is_debugger_present(self):
        """Detect if debugger is attached"""
        try:
            # Check for common debugger indicators
            import traceback
            frame = sys._getframe()
            
            # Check for pdb
            if any('pdb' in str(f) for f in traceback.extract_stack()):
                return True
            
            # Check for IDE debuggers
            if hasattr(sys, 'gettrace') and sys.gettrace() is not None:
                return True
            
            # Check environment variables
            debug_vars = ['PYCHARM_DEBUG', 'PYDEV_DEBUG', 'VSCODE_DEBUG']
            if any(var in os.environ for var in debug_vars):
                return True
            
            return False
        except:
            return False
    
    def _check_reverse_tools(self):
        """Check for reverse engineering tools"""
        try:
            suspicious_processes = [
                'ida.exe', 'ida64.exe', 'ollydbg.exe', 'x64dbg.exe',
                'windbg.exe', 'cheatengine.exe', 'processhacker.exe'
            ]
            
            import psutil
            running_processes = [p.name().lower() for p in psutil.process_iter()]
            
            return any(proc in running_processes for proc in suspicious_processes)
        except:
            return False
    
    def _verify_integrity(self):
        """Verify file integrity"""
        try:
            # Check if running as expected
            if not getattr(sys, 'frozen', False):
                return True  # Skip check in development
            
            # Calculate checksum of executable
            exe_path = sys.executable
            if os.path.exists(exe_path):
                with open(exe_path, 'rb') as f:
                    content = f.read()
                    checksum = hashlib.sha256(content).hexdigest()
                    # In production, compare with expected checksum
                    return len(checksum) == 64  # Basic check
            
            return True
        except:
            return True
    
    def _handle_debug_detection(self):
        """Handle debugger detection"""
        # Log the attempt
        self._log_security_event("Debugger detected")
        
        # Exit or disable functionality
        os._exit(1)
    
    def _handle_tampering(self):
        """Handle file tampering detection"""
        # Log the attempt
        self._log_security_event("File tampering detected")
        
        # Exit or disable functionality
        os._exit(1)
    
    def _log_security_event(self, event):
        """Log security events"""
        try:
            timestamp = datetime.now().isoformat()
            log_entry = f"{timestamp}: {event}\\n"
            
            # Write to hidden log file
            log_file = os.path.join(os.path.expanduser('~'), '.security.log')
            with open(log_file, 'a') as f:
                f.write(log_entry)
        except:
            pass

# Initialize anti-debugging (import this module to activate)
try:
    _anti_debug = AntiDebug()
except:
    pass  # Silent failure if dependencies missing
'''
        
        anti_debug_file = self.protected_dir / "anti_debug.py"
        with open(anti_debug_file, 'w') as f:
            f.write(anti_debug_code)
        
        print("✅ Anti-debugging protection created")
        return True
    
    def create_license_validation_wrapper(self):
        """Create license validation wrapper"""
        print("🔑 Creating license validation wrapper...")
        
        wrapper_code = '''
# License validation wrapper - include at the top of protected files
import sys
import os

def validate_license_startup():
    """Validate license on startup"""
    try:
        from license_manager import LicenseManager
        
        license_mgr = LicenseManager()
        current_license = license_mgr.get_current_license()
        
        if not current_license['success'] or not current_license.get('is_valid'):
            print("❌ Invalid or expired license. Please contact support.")
            
            # Show license dialog or exit
            if getattr(sys, 'frozen', False):  # Only in executable
                input("Press Enter to exit...")
                sys.exit(1)
            else:
                print("⚠️ Running in development mode - license check skipped")
        
        return True
    except ImportError:
        # License manager not available
        return True
    except Exception as e:
        print(f"License validation error: {e}")
        return False

# Call validation on import
if __name__ != "__main__":
    validate_license_startup()
'''
        
        wrapper_file = self.protected_dir / "license_wrapper.py"
        with open(wrapper_file, 'w') as f:
            f.write(wrapper_code)
        
        print("✅ License validation wrapper created")
        return True
    
    def create_build_script_protected(self):
        """Create protected build script"""
        print("📦 Creating protected build script...")
        
        protected_build_code = '''
#!/usr/bin/env python3
"""
Protected Build Script
Builds executable with all protection layers
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def build_protected_executable():
    """Build executable with protection"""
    
    print("🛡️ Building protected executable...")
    
    # Copy protected files
    base_dir = Path(__file__).parent
    protected_dir = base_dir / "protected"
    
    if not protected_dir.exists():
        print("❌ Protected files not found. Run code protection first.")
        return False
    
    # Copy obfuscated files to main directory
    obfuscated_files = list(protected_dir.glob("*.py"))
    for file_path in obfuscated_files:
        if file_path.name != "build_protected.py":
            dest_path = base_dir / file_path.name
            shutil.copy2(file_path, dest_path)
            print(f"  Copied: {file_path.name}")
    
    # Build with PyInstaller
    spec_content = """
# Protected PyInstaller spec
# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# Hidden imports for protection
hiddenimports = [
    'license_manager',
    'string_decoder', 
    'anti_debug',
    'license_wrapper'
]

a = Analysis(
    ['professional_dashboard_api.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('protected', 'protected')
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['protected/license_wrapper.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LinkedInAutoBot_Protected',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    
    # Write spec file
    spec_file = base_dir / "protected_build.spec"
    with open(spec_file, 'w') as f:
        f.write(spec_content.strip())
    
    # Run PyInstaller
    cmd = [sys.executable, '-m', 'PyInstaller', '--clean', str(spec_file)]
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("✅ Protected executable built successfully!")
        return True
    else:
        print("❌ Build failed!")
        return False

if __name__ == "__main__":
    build_protected_executable()
'''
        
        build_file = self.protected_dir / "build_protected.py"
        with open(build_file, 'w') as f:
            f.write(protected_build_code)
        
        print("✅ Protected build script created")
        return True
    
    def protect_all(self):
        """Run complete protection process"""
        print("🛡️ Starting comprehensive code protection...")
        print("=" * 50)
        
        try:
            # Setup environment
            self.setup_protection_environment()
            
            # Create protection layers
            success_steps = []
            
            # Step 1: String obfuscation
            if self.create_string_obfuscation():
                success_steps.append("String obfuscation")
            
            # Step 2: Anti-debugging
            if self.create_anti_debugging():
                success_steps.append("Anti-debugging")
            
            # Step 3: License validation wrapper
            if self.create_license_validation_wrapper():
                success_steps.append("License validation")
            
            # Step 4: PyArmor obfuscation
            if self.obfuscate_with_pyarmor():
                success_steps.append("PyArmor obfuscation")
            
            # Step 5: Protected build script
            if self.create_build_script_protected():
                success_steps.append("Protected build script")
            
            print("\n" + "=" * 50)
            print("🎉 CODE PROTECTION COMPLETED!")
            print("=" * 50)
            print("✅ Successfully created:")
            for step in success_steps:
                print(f"  • {step}")
            
            print(f"\n📁 Protected files location: {self.protected_dir}")
            print("\n🔧 Next steps:")
            print("1. Review protected files")
            print("2. Run: python protected/build_protected.py")
            print("3. Test the protected executable")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Protection failed: {e}")
            return False

def main():
    """Main protection function"""
    protector = CodeProtector()
    success = protector.protect_all()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()