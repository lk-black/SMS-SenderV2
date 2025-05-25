#!/usr/bin/env python
"""
Script para investigar por que SMS agendados não estão sendo enviados automaticamente.
Verifica workers Celery, tarefas agendadas e status do Redis.
"""
import requests
import json
from datetime import datetime, timedelta

def check_production_status():
    """Verifica status completo do sistema em produção"""
    base_url = "https://sms-senderv2.onrender.com/api/webhooks"
    
    print("🔍 Investigação de Workers Celery - Sistema de SMS Agendados")
    print("=" * 60)
    
    # 1. Health Check Geral
    print("\n1. 🔍 Health Check Geral")
    try:
        response = requests.get(f"{base_url}/health/")
        health_data = response.json()
        print(f"   Status: {health_data.get('status')}")
        print(f"   Database: {health_data.get('database')}")
        print(f"   Cache: {health_data.get('cache')}")
        
        sms_scheduler = health_data.get('sms_scheduler', {})
        print(f"   Redis Available: {sms_scheduler.get('redis_available')}")
        print(f"   Celery Available: {sms_scheduler.get('celery_available')}")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 2. Status SMS Scheduler
    print("\n2. 📱 Status SMS Scheduler")
    try:
        response = requests.get(f"{base_url}/sms-scheduler-status/")
        scheduler_data = response.json()
        scheduler_status = scheduler_data.get('scheduler_status', {})
        
        print(f"   Redis Available: {scheduler_status.get('redis_available')}")
        print(f"   Celery Available: {scheduler_status.get('celery_available')}")
        print(f"   SMS Recovery Enabled: {scheduler_status.get('sms_recovery_enabled')}")
        print(f"   Fallback Mode: {scheduler_status.get('fallback_mode')}")
        print(f"   Delay Minutes: {scheduler_status.get('delay_minutes')}")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 3. Webhooks Recentes
    print("\n3. 📋 Webhooks Recentes")
    try:
        response = requests.get(f"{base_url}/events/")
        events = response.json()
        
        print(f"   Total de eventos: {len(events)}")
        
        for event in events[-5:]:  # Últimos 5 eventos
            event_id = event.get('id')
            payment_id = event.get('payment_id')
            method = event.get('payment_method')
            status = event.get('payment_status')
            sms_scheduled = event.get('sms_scheduled')
            webhook_time = event.get('webhook_received_at')
            
            print(f"   📝 Evento {event_id}: {payment_id}")
            print(f"      Método: {method} | Status: {status}")
            print(f"      SMS Agendado: {sms_scheduled}")
            print(f"      Recebido em: {webhook_time}")
            print()
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 4. SMS Logs
    print("\n4. 📱 Logs de SMS")
    try:
        response = requests.get(f"{base_url}/sms-logs/")
        sms_logs = response.json()
        
        print(f"   Total de SMS logs: {len(sms_logs)}")
        
        for log in sms_logs[-3:]:  # Últimos 3 SMS
            log_id = log.get('id')
            phone = log.get('phone_number')
            status = log.get('status')
            sent_at = log.get('sent_at')
            message_sid = log.get('message_sid')
            
            print(f"   📱 SMS {log_id}: {phone}")
            print(f"      Status: {status}")
            print(f"      Enviado em: {sent_at}")
            print(f"      Message SID: {message_sid}")
            print()
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 5. Teste de Agendamento Manual
    print("\n5. 🧪 Teste de Agendamento Manual")
    print("   Criando webhook de teste para verificar agendamento...")
    
    test_payload = {
        "paymentId": f"debug_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "status": "PENDING", 
        "paymentMethod": "PIX",
        "totalValue": 5000,
        "customer": {
            "name": "Debug Test User",
            "phone": "+5511999999999",
            "email": "debug@test.com"
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/ghostpay/",
            json=test_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("   ✅ Webhook de teste enviado com sucesso")
            
            # Aguardar alguns segundos e verificar se foi criado
            import time
            time.sleep(2)
            
            response = requests.get(f"{base_url}/events/")
            events = response.json()
            latest_event = events[-1] if events else None
            
            if latest_event and latest_event.get('payment_id') == test_payload['paymentId']:
                print(f"   ✅ Evento criado: ID {latest_event.get('id')}")
                print(f"   📱 SMS Agendado: {latest_event.get('sms_scheduled')}")
            else:
                print("   ⚠️ Evento não encontrado")
                
        else:
            print(f"   ❌ Erro ao enviar webhook: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 6. Análise de Timing
    print("\n6. ⏰ Análise de Timing")
    try:
        response = requests.get(f"{base_url}/events/")
        events = response.json()
        
        pix_pending_events = [
            e for e in events 
            if e.get('payment_method') == 'pix' 
            and e.get('payment_status') == 'waiting_payment'
            and e.get('sms_scheduled') == True
        ]
        
        print(f"   PIX pendentes com SMS agendado: {len(pix_pending_events)}")
        
        for event in pix_pending_events:
            webhook_time = event.get('webhook_received_at')
            event_id = event.get('id')
            payment_id = event.get('payment_id')
            
            print(f"   📅 Evento {event_id} ({payment_id})")
            print(f"      Webhook recebido: {webhook_time}")
            
            # Calcular quando o SMS deveria ter sido enviado (10 minutos depois)
            if webhook_time:
                try:
                    import pytz
                    
                    # Parse do timestamp
                    if webhook_time.endswith('Z'):
                        webhook_dt = datetime.fromisoformat(webhook_time.replace('Z', '+00:00'))
                    else:
                        webhook_dt = datetime.fromisoformat(webhook_time)
                    
                    # Adicionar 10 minutos
                    sms_should_send_at = webhook_dt + timedelta(minutes=10)
                    now = datetime.now(pytz.UTC)
                    
                    print(f"      SMS deveria enviar: {sms_should_send_at}")
                    print(f"      Agora: {now}")
                    
                    if now > sms_should_send_at:
                        time_passed = now - sms_should_send_at
                        print(f"      ⚠️ ATRASADO por: {time_passed}")
                    else:
                        time_remaining = sms_should_send_at - now
                        print(f"      ⏳ Falta: {time_remaining}")
                        
                except Exception as parse_error:
                    print(f"      ❌ Erro ao parsear data: {parse_error}")
            print()
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print("\n" + "=" * 60)
    print("🔍 Investigação Concluída")
    print("\n💡 Próximos passos sugeridos:")
    print("   1. Verificar logs do Celery worker em produção")
    print("   2. Confirmar se as tarefas estão sendo enfileiradas no Redis")
    print("   3. Investigar se há workers Celery ativos processando as tarefas")
    print("   4. Verificar configurações de timezone")
    print("   5. Analisar logs de aplicação para erros de agendamento")

if __name__ == "__main__":
    check_production_status()
