#!/usr/bin/env python
"""
Script para testar diretamente tarefas Celery em produção via API
"""
import requests
import json
import time

def test_celery_task():
    """Testa uma tarefa Celery simples"""
    base_url = "https://sms-senderv2.onrender.com/api/webhooks"
    
    print("🧪 Testando Tarefa Celery Diretamente")
    print("=" * 50)
    
    # 1. Criar um webhook PIX pendente
    print("\n1. 📝 Criando webhook PIX pendente...")
    
    payload = {
        "paymentId": f"celery_test_{int(time.time())}",
        "status": "PENDING", 
        "paymentMethod": "PIX",
        "totalValue": 2000,
        "customer": {
            "name": "Teste Celery Worker",
            "phone": "+5511999999999",
            "email": "celery.test@email.com"
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/ghostpay/",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("   ✅ Webhook criado com sucesso")
            
            # Aguardar 2 segundos e buscar o evento
            time.sleep(2)
            
            events_response = requests.get(f"{base_url}/events/")
            events = events_response.json()
            
            # Encontrar o evento criado
            test_event = None
            for event in events:
                if event.get('payment_id') == payload['paymentId']:
                    test_event = event
                    break
            
            if test_event:
                print(f"   📋 Evento encontrado: ID {test_event.get('id')}")
                print(f"   📱 SMS Agendado: {test_event.get('sms_scheduled')}")
                
                # Aguardar 30 segundos e verificar se SMS foi enviado
                print("\n2. ⏳ Aguardando 30 segundos para verificar processamento...")
                
                for i in range(6):  # 6 verificações de 5 segundos cada
                    time.sleep(5)
                    print(f"   Verificação {i+1}/6...")
                    
                    # Verificar logs de SMS
                    sms_logs_response = requests.get(f"{base_url}/sms-logs/")
                    sms_logs = sms_logs_response.json()
                    
                    # Verificar se algum SMS foi enviado para este evento
                    for log in sms_logs:
                        if log.get('webhook_event') == test_event.get('id'):
                            print(f"   ✅ SMS ENCONTRADO!")
                            print(f"      Status: {log.get('status')}")
                            print(f"      Telefone: {log.get('phone_number')}")
                            print(f"      Enviado em: {log.get('sent_at')}")
                            print(f"      Message SID: {log.get('message_sid')}")
                            return True
                
                print("   ❌ Nenhum SMS foi enviado após 30 segundos")
                
                # Verificar eventos novamente para ver se ainda está agendado
                events_response = requests.get(f"{base_url}/events/")
                events = events_response.json()
                
                for event in events:
                    if event.get('id') == test_event.get('id'):
                        print(f"   📋 Status atual do evento:")
                        print(f"      SMS Agendado: {event.get('sms_scheduled')}")
                        print(f"      Status Pagamento: {event.get('payment_status')}")
                        break
                
                return False
            else:
                print("   ❌ Evento não encontrado após criação")
                return False
        else:
            print(f"   ❌ Erro ao criar webhook: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return False

def check_render_processes():
    """Verifica se há processos worker no Render"""
    print("\n3. 🔍 Diagnóstico de Workers")
    print("   Possíveis causas da falha:")
    print("   • Render.com não tem worker Celery configurado")
    print("   • Worker Celery não está consumindo a fila")
    print("   • Problema de configuração de timezone")
    print("   • Redis não está persistindo as tarefas agendadas")
    print("   • Configuração CELERY_TASK_ALWAYS_EAGER pode estar True")
    
    print("\n4. 💡 Próximos passos:")
    print("   1. Verificar se há um processo 'worker' no Render.com")
    print("   2. Adicionar comando para iniciar worker Celery") 
    print("   3. Verificar logs do worker em produção")
    print("   4. Testar agendamento com countdown menor (1 minuto)")

if __name__ == "__main__":
    success = test_celery_task()
    check_render_processes()
    
    if not success:
        print("\n❌ PROBLEMA IDENTIFICADO:")
        print("   Workers Celery não estão processando tarefas agendadas")
        print("   Necessário configurar worker no Render.com")
    else:
        print("\n✅ Sistema funcionando corretamente!")
