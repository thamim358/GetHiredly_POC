#!/usr/bin/env python3
"""
LinkedIn AutoBot License Manager
Hardware-based licensing system with trial functionality
"""

import hashlib
import platform
import uuid
import json
import os
import sys
from datetime import datetime, timedelta
import base64
import hmac
import requests
from pathlib import Path

class LicenseManager:
    def __init__(self, license_server_url=None):
        self.hardware_id = self._generate_hardware_id()
        self.license_server = license_server_url or "https://your-license-server.com"
        self.license_file = "license.json"
        self.app_name = "LinkedIn AutoBot Professional"
        self.version = "2.0"
        
        # Secret key for offline validation (change this in production)
        self.secret_key = "your-secret-key-change-in-production"
        
    def _generate_hardware_id(self):
        """Generate unique hardware fingerprint"""
        try:
            # Get MAC address
            mac = hex(uuid.getnode())[2:].upper()
            
            # Get system information
            system_info = {
                'system': platform.system(),
                'machine': platform.machine(),
                'processor': platform.processor()[:50],  # Limit length
                'mac': mac
            }
            
            # Create hardware fingerprint
            hw_string = json.dumps(system_info, sort_keys=True)
            hardware_id = hashlib.sha256(hw_string.encode()).hexdigest()[:16]
            
            return hardware_id
            
        except Exception as e:
            # Fallback to simpler method
            fallback = f"{platform.system()}{platform.machine()}{uuid.getnode()}"
            return hashlib.md5(fallback.encode()).hexdigest()[:16]
    
    def generate_trial_license(self, trial_days=7):
        """Generate a trial license"""
        try:
            trial_end = datetime.now() + timedelta(days=trial_days)
            
            license_data = {
                'license_type': 'trial',
                'hardware_id': self.hardware_id,
                'valid_until': trial_end.isoformat(),
                'features': {
                    'max_applications_per_day': 50,
                    'max_emails_per_day': 100,
                    'export_enabled': True,
                    'ai_features': False
                },
                'generated_at': datetime.now().isoformat(),
                'version': self.version
            }
            
            # Create signature for offline validation
            license_data['signature'] = self._create_signature(license_data)
            
            # Save license
            self._save_license(license_data)
            
            return {
                'success': True,
                'message': f'Trial license generated for {trial_days} days',
                'trial_end': trial_end.strftime('%Y-%m-%d %H:%M:%S'),
                'hardware_id': self.hardware_id
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def validate_license_key(self, license_key):
        """Validate a license key online and offline"""
        try:
            # First try online validation
            online_result = self._online_validate(license_key)
            if online_result['success']:
                return online_result
            
            # If online fails, try offline validation
            return self._offline_validate(license_key)
            
        except Exception as e:
            return {'success': False, 'error': f'License validation failed: {str(e)}'}
    
    def _online_validate(self, license_key):
        """Validate license with online server"""
        try:
            payload = {
                'license_key': license_key,
                'hardware_id': self.hardware_id,
                'app_name': self.app_name,
                'version': self.version
            }
            
            response = requests.post(
                f"{self.license_server}/api/validate",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('valid'):
                    # Save valid license locally
                    license_data = result.get('license_data', {})
                    license_data['last_validated'] = datetime.now().isoformat()
                    license_data['validation_method'] = 'online'
                    self._save_license(license_data)
                    
                    return {
                        'success': True,
                        'license_type': license_data.get('license_type', 'unknown'),
                        'valid_until': license_data.get('valid_until'),
                        'features': license_data.get('features', {}),
                        'message': 'License validated online'
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('message', 'Invalid license key')
                    }
            else:
                return {'success': False, 'error': f'Server error: {response.status_code}'}
                
        except requests.exceptions.RequestException:
            return {'success': False, 'error': 'Cannot connect to license server'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _offline_validate(self, license_key):
        """Validate license offline using stored data"""
        try:
            # Decode license key (base64 encoded JSON)
            try:
                decoded = base64.b64decode(license_key).decode('utf-8')
                license_data = json.loads(decoded)
            except:
                return {'success': False, 'error': 'Invalid license key format'}
            
            # Verify signature
            if not self._verify_signature(license_data):
                return {'success': False, 'error': 'License signature invalid'}
            
            # Check hardware ID
            if license_data.get('hardware_id') != self.hardware_id:
                return {'success': False, 'error': 'License not valid for this machine'}
            
            # Check expiration
            valid_until = datetime.fromisoformat(license_data.get('valid_until', ''))
            if datetime.now() > valid_until:
                return {'success': False, 'error': 'License has expired'}
            
            # Save valid license
            license_data['last_validated'] = datetime.now().isoformat()
            license_data['validation_method'] = 'offline'
            self._save_license(license_data)
            
            return {
                'success': True,
                'license_type': license_data.get('license_type', 'unknown'),
                'valid_until': license_data.get('valid_until'),
                'features': license_data.get('features', {}),
                'message': 'License validated offline'
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Offline validation failed: {str(e)}'}
    
    def get_current_license(self):
        """Get current license information"""
        try:
            if not os.path.exists(self.license_file):
                return {'success': False, 'error': 'No license found'}
            
            with open(self.license_file, 'r') as f:
                license_data = json.load(f)
            
            # Check if license is still valid
            valid_until = datetime.fromisoformat(license_data.get('valid_until', ''))
            is_valid = datetime.now() <= valid_until
            
            # Calculate days remaining
            days_remaining = (valid_until - datetime.now()).days if is_valid else 0
            
            return {
                'success': True,
                'license_type': license_data.get('license_type', 'unknown'),
                'valid_until': license_data.get('valid_until'),
                'days_remaining': max(0, days_remaining),
                'is_valid': is_valid,
                'features': license_data.get('features', {}),
                'hardware_id': self.hardware_id,
                'last_validated': license_data.get('last_validated'),
                'validation_method': license_data.get('validation_method', 'unknown')
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_feature_access(self, feature_name):
        """Check if a specific feature is available"""
        license_info = self.get_current_license()
        
        if not license_info['success'] or not license_info.get('is_valid'):
            return False
        
        features = license_info.get('features', {})
        return features.get(feature_name, False)
    
    def get_usage_limits(self):
        """Get current usage limits"""
        license_info = self.get_current_license()
        
        if not license_info['success'] or not license_info.get('is_valid'):
            return {
                'max_applications_per_day': 0,
                'max_emails_per_day': 0,
                'export_enabled': False,
                'ai_features': False
            }
        
        return license_info.get('features', {})
    
    def _create_signature(self, license_data):
        """Create signature for license data"""
        # Remove signature if it exists
        data_copy = license_data.copy()
        data_copy.pop('signature', None)
        
        # Create signature
        data_string = json.dumps(data_copy, sort_keys=True)
        signature = hmac.new(
            self.secret_key.encode(),
            data_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _verify_signature(self, license_data):
        """Verify license signature"""
        stored_signature = license_data.get('signature')
        if not stored_signature:
            return False
        
        calculated_signature = self._create_signature(license_data)
        return hmac.compare_digest(stored_signature, calculated_signature)
    
    def _save_license(self, license_data):
        """Save license data to file"""
        with open(self.license_file, 'w') as f:
            json.dump(license_data, f, indent=2)
    
    def generate_license_key(self, license_type, duration_days, features):
        """Generate a license key (for license server use)"""
        valid_until = datetime.now() + timedelta(days=duration_days)
        
        license_data = {
            'license_type': license_type,
            'hardware_id': self.hardware_id,
            'valid_until': valid_until.isoformat(),
            'features': features,
            'generated_at': datetime.now().isoformat(),
            'version': self.version
        }
        
        # Create signature
        license_data['signature'] = self._create_signature(license_data)
        
        # Encode as base64
        license_json = json.dumps(license_data)
        license_key = base64.b64encode(license_json.encode()).decode()
        
        return license_key
    
    def revoke_license(self):
        """Revoke current license"""
        try:
            if os.path.exists(self.license_file):
                os.remove(self.license_file)
            return {'success': True, 'message': 'License revoked'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class LicenseValidator:
    """Decorator and utility class for license validation"""
    
    def __init__(self, license_manager):
        self.license_manager = license_manager
    
    def require_valid_license(self, func):
        """Decorator to require valid license"""
        def wrapper(*args, **kwargs):
            license_info = self.license_manager.get_current_license()
            
            if not license_info['success'] or not license_info.get('is_valid'):
                return {
                    'success': False,
                    'error': 'Valid license required',
                    'license_status': license_info
                }
            
            return func(*args, **kwargs)
        
        return wrapper
    
    def require_feature(self, feature_name):
        """Decorator to require specific feature"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                if not self.license_manager.check_feature_access(feature_name):
                    return {
                        'success': False,
                        'error': f'Feature "{feature_name}" not available in current license'
                    }
                
                return func(*args, **kwargs)
            
            return wrapper
        return decorator


# Example usage and testing
def main():
    """Test the license manager"""
    print("🔐 LinkedIn AutoBot License Manager Test")
    print("=" * 50)
    
    # Initialize license manager
    license_mgr = LicenseManager()
    
    print(f"Hardware ID: {license_mgr.hardware_id}")
    print()
    
    # Generate trial license
    print("📝 Generating trial license...")
    trial_result = license_mgr.generate_trial_license(7)
    print(f"Result: {trial_result}")
    print()
    
    # Check current license
    print("📋 Checking current license...")
    current_license = license_mgr.get_current_license()
    print(f"License Info: {json.dumps(current_license, indent=2)}")
    print()
    
    # Test feature access
    print("🔍 Testing feature access...")
    features_to_test = ['export_enabled', 'ai_features', 'unlimited_applications']
    for feature in features_to_test:
        has_access = license_mgr.check_feature_access(feature)
        print(f"  {feature}: {'✅' if has_access else '❌'}")
    
    print()
    print("✅ License manager test completed!")


if __name__ == "__main__":
    main()