#!/usr/bin/env python3
"""
Comprehensive monitoring script for SMS-Sender Celery worker
Monitors worker status, task processing, and system health
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "https://sms-senderv2.onrender.com/api/webhooks"

def check_health():
    """Check system health"""
    try:
        response = requests.get(f"{BASE_URL}/health/", timeout=10)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        return False, str(e)

def test_celery_task():
    """Test Celery task creation"""
    try:
        response = requests.post(f"{BASE_URL}/test-celery-task/", timeout=10)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        return False, str(e)

def check_pending_sms():
    """Check for pending SMS"""
    try:
        response = requests.get(f"{BASE_URL}/pending-sms/", timeout=10)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        return False, str(e)

def test_sms_creation():
    """Create a test SMS to verify end-to-end functionality"""
    try:
        test_payload = {
            "transaction_id": f"TEST_{int(time.time())}",
            "amount": 100.00,
            "status": "approved",
            "customer": {
                "phone": "+5511999999999",
                "name": "Test Customer"
            }
        }
        response = requests.post(f"{BASE_URL}/test-immediate-sms/", 
                               json=test_payload, 
                               headers={"Content-Type": "application/json"},
                               timeout=10)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        return False, str(e)

def force_process_pending():
    """Force process pending SMS tasks"""
    try:
        response = requests.post(f"{BASE_URL}/force-process-pending-sms/", timeout=30)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        return False, str(e)

def monitor_worker_status():
    """Main monitoring function"""
    print("🚀 SMS-Sender Worker Monitoring Started")
    print("=" * 60)
    
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n⏰ {timestamp}")
        print("-" * 40)
        
        # 1. Health Check
        health_ok, health_data = check_health()
        if health_ok:
            print("✅ Health Check: PASSED")
            if health_data:
                redis_status = health_data.get('cache', 'unknown')
                celery_status = health_data.get('sms_scheduler', {}).get('celery_available', False)
                print(f"   📡 Redis: {redis_status}")
                print(f"   🔄 Celery: {'✅ Available' if celery_status else '❌ Unavailable'}")
        else:
            print(f"❌ Health Check: FAILED - {health_data}")
            
        # 2. Test Celery Task
        task_ok, task_data = test_celery_task()
        if task_ok and task_data:
            print(f"✅ Celery Task Test: PASSED")
            print(f"   📝 Task ID: {task_data.get('task_id', 'N/A')}")
            print(f"   📊 State: {task_data.get('task_state', 'N/A')}")
        else:
            print(f"❌ Celery Task Test: FAILED - {task_data}")
            
        # 3. Check Pending SMS
        pending_ok, pending_data = check_pending_sms()
        if pending_ok and pending_data:
            count = pending_data.get('count', 0)
            print(f"📋 Pending SMS: {count}")
            if count > 0:
                print("   ⚠️  Found pending SMS tasks!")
                # Force process if there are pending tasks
                print("   🔧 Attempting to force process...")
                force_ok, force_data = force_process_pending()
                if force_ok:
                    print(f"   ✅ Force Process: {force_data.get('message', 'Success')}")
                else:
                    print(f"   ❌ Force Process: FAILED - {force_data}")
        else:
            print(f"❌ Pending SMS Check: FAILED - {pending_data}")
            
        # 4. Test SMS Creation (every 5th iteration)
        if int(time.time()) % 300 < 60:  # Every 5 minutes
            print("🧪 Testing SMS Creation...")
            sms_ok, sms_data = test_sms_creation()
            if sms_ok:
                print("✅ SMS Creation Test: PASSED")
                if sms_data:
                    scheduled = sms_data.get('sms_scheduled', False)
                    print(f"   📅 SMS Scheduled: {'Yes' if scheduled else 'No'}")
            else:
                print(f"❌ SMS Creation Test: FAILED - {sms_data}")
        
        print(f"\n💤 Waiting 60 seconds for next check...")
        time.sleep(60)

if __name__ == "__main__":
    try:
        monitor_worker_status()
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Monitoring error: {e}")
