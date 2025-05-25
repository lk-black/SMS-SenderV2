#!/usr/bin/env python3
"""
Monitor em tempo real do sistema SMS
"""
import requests
import time
import json
from datetime import datetime

def monitor_sms_system():
    """Monitora o sistema SMS em tempo real"""
    base_url = "https://sms-senderv2.onrender.com/api/webhooks"
    
    print("🔍 MONITOR SMS EM TEMPO REAL")
    print("=" * 60)
    print(f"📅 Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    check_count = 0
    
    while True:
        check_count += 1
        current_time = datetime.now().strftime('%H:%M:%S')
        
        try:
            # 1. Verificar health
            health_response = requests.get(f"{base_url}/health/")
            health = health_response.json()
            
            # 2. Verificar debug (contadores)
            debug_response = requests.get(f"{base_url}/debug/")
            debug = debug_response.json()
            
            webhook_count = debug['tables']['webhook_events'].split(',')[1].strip().split(' ')[0]
            sms_count = debug['tables']['sms_logs'].split(',')[1].strip().split(' ')[0]
            
            # 3. Mostrar status
            print(f"\n📊 Check #{check_count} - {current_time}")
            print(f"   🟢 System: {health['status']}")
            print(f"   🗄️  Database: {health['database']}")
            print(f"   🔴 Redis: {'✅' if health['sms_scheduler']['redis_available'] else '❌'}")
            print(f"   🐰 Celery: {'✅' if health['sms_scheduler']['celery_available'] else '❌'}")
            print(f"   📨 Webhooks: {webhook_count}")
            print(f"   📱 SMS: {sms_count}")
            
            # 4. Verificar se houve mudança nos SMS
            if int(sms_count) > 0:
                print(f"\n🎉 SMS DETECTADO! Total: {sms_count}")
                break
                
        except Exception as e:
            print(f"❌ Erro no check #{check_count}: {e}")
        
        # Aguardar 30 segundos
        time.sleep(30)
        
        # Parar após 20 checks (10 minutos)
        if check_count >= 20:
            print("\n⏰ Timeout atingido (10 minutos)")
            break
    
    print("\n" + "=" * 60)
    print("✅ MONITORAMENTO CONCLUÍDO")

if __name__ == "__main__":
    monitor_sms_system()
