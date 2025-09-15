#!/usr/bin/env python3
"""
Script to debug and fix AI bot stats issues
"""

import json
import os
import requests
import time

def check_current_stats():
    """Check current bot stats"""
    print("📊 Current Bot Stats")
    print("=" * 50)
    
    if os.path.exists('bot_stats.json'):
        with open('bot_stats.json', 'r') as f:
            stats = json.load(f)
        
        if 'aibot' in stats:
            aibot_stats = stats['aibot']
            print(f"AI Bot Status: {aibot_stats.get('status', 'Unknown')}")
            print(f"Applications Submitted: {aibot_stats.get('applications_submitted', 0)}")
            print(f"Jobs Applied: {aibot_stats.get('jobs_applied', 0)}")
            print(f"Jobs Failed: {aibot_stats.get('jobs_failed', 0)}")
            print(f"Success Rate: {aibot_stats.get('success_rate', 0)}%")
            print(f"Start Time: {aibot_stats.get('start_time', 'Not set')}")
            print(f"Runtime: {aibot_stats.get('runtime', '0:00:00')}")
            
            return aibot_stats
        else:
            print("❌ No AI bot stats found")
            return None
    else:
        print("❌ bot_stats.json not found")
        return None

def check_application_files():
    """Check for application history files"""
    print("\n📂 Application Files Status")
    print("=" * 50)
    
    file_paths = [
        'all excels/all_applied_applications_history.csv',
        'all excels/all_failed_applications_history.csv',
        'all_applied_applications_history.csv',
        'all_failed_applications_history.csv',
        'logs/applied_applications.csv',
        'logs/failed_applications.csv'
    ]
    
    found_files = []
    for file_path in file_paths:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    count = len(lines) - 1 if len(lines) > 1 else 0  # Exclude header
                found_files.append((file_path, count))
                print(f"✅ Found: {file_path} ({count} entries)")
            except Exception as e:
                print(f"⚠️ Error reading {file_path}: {e}")
        else:
            print(f"❌ Missing: {file_path}")
    
    return found_files

def reset_stats_via_api():
    """Reset AI bot stats via API"""
    print("\n🔄 Resetting AI Bot Stats via API")
    print("=" * 50)
    
    try:
        response = requests.post('http://localhost:5000/api/reset-aibot-stats')
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ AI bot stats reset successfully via API")
                return True
            else:
                print(f"❌ API error: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("⚠️ Dashboard server not running - cannot reset via API")
        return False
    except Exception as e:
        print(f"❌ Error calling API: {e}")
        return False

def manual_stats_reset():
    """Manually reset stats in the JSON file"""
    print("\n🛠️ Manual Stats Reset")
    print("=" * 50)
    
    try:
        if os.path.exists('bot_stats.json'):
            with open('bot_stats.json', 'r') as f:
                stats = json.load(f)
            
            if 'aibot' in stats:
                # Reset AI bot stats
                stats['aibot']['applications_submitted'] = 0
                stats['aibot']['jobs_applied'] = 0
                stats['aibot']['jobs_failed'] = 0
                stats['aibot']['success_rate'] = 0
                stats['aibot']['runtime'] = "0:00:00"
                stats['aibot']['start_time'] = None
                stats['aibot']['last_activity'] = None
                
                # Save updated stats
                with open('bot_stats.json', 'w') as f:
                    json.dump(stats, f, indent=2)
                
                print("✅ AI bot stats reset manually in bot_stats.json")
                return True
            else:
                print("❌ No AI bot section found in stats")
                return False
        else:
            print("❌ bot_stats.json not found")
            return False
            
    except Exception as e:
        print(f"❌ Error resetting stats manually: {e}")
        return False

def create_test_application_files():
    """Create test application files to verify stats update"""
    print("\n🧪 Creating Test Application Files")
    print("=" * 50)
    
    try:
        # Ensure all excels directory exists
        os.makedirs('all excels', exist_ok=True)
        
        # Create test applied applications file
        applied_file = 'all excels/all_applied_applications_history.csv'
        with open(applied_file, 'w', encoding='utf-8') as f:
            f.write("Date,Company,Position,Status\n")
            f.write("2025-09-15,Test Company 1,React Developer,Applied\n")
            f.write("2025-09-15,Test Company 2,Frontend Developer,Applied\n")
        
        # Create test failed applications file
        failed_file = 'all excels/all_failed_applications_history.csv'
        with open(failed_file, 'w', encoding='utf-8') as f:
            f.write("Date,Company,Position,Error\n")
            f.write("2025-09-15,Test Company 3,Backend Developer,Application failed\n")
        
        print(f"✅ Created test files:")
        print(f"   - {applied_file} (2 applications)")
        print(f"   - {failed_file} (1 failed)")
        print(f"💡 Stats should now show: 2 applied, 1 failed, 66.7% success rate")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating test files: {e}")
        return False

def main():
    """Main function"""
    print("🔧 AI Bot Stats Debugger and Fixer")
    print("=" * 80)
    
    # Check current stats
    current_stats = check_current_stats()
    
    # Check application files
    found_files = check_application_files()
    
    # Analyze the issue
    print(f"\n🔍 Issue Analysis")
    print("=" * 50)
    
    if current_stats:
        if current_stats.get('applications_submitted', 0) > 0 and not found_files:
            print("🎯 ISSUE IDENTIFIED: Static counter with no application files")
            print("   The counter is stuck because application files don't exist")
            print("   Solutions:")
            print("   1. Reset the stats to start fresh")
            print("   2. Start the AI bot to generate new applications")
            
        elif found_files:
            total_applied = sum(count for path, count in found_files if 'applied' in path)
            print(f"📊 Found {len(found_files)} application files with {total_applied} total applications")
            print("   Stats should update automatically if dashboard is running")
            
        else:
            print("⚠️ No application files found - AI bot hasn't run yet")
    
    # Offer solutions
    print(f"\n💡 Available Solutions")
    print("=" * 50)
    print("1. Reset stats via API (if dashboard is running)")
    print("2. Reset stats manually in JSON file")
    print("3. Create test application files to verify stats update")
    print("4. Check all files and exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        reset_stats_via_api()
    elif choice == '2':
        manual_stats_reset()
    elif choice == '3':
        create_test_application_files()
    elif choice == '4':
        print("✅ Check completed")
    else:
        print("❌ Invalid choice")
    
    # Final status check
    print(f"\n📊 Final Stats Check")
    print("=" * 50)
    time.sleep(1)  # Give time for updates
    check_current_stats()

if __name__ == "__main__":
    main()
