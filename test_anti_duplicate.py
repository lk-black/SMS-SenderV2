#!/usr/bin/env python
"""
Script para testar a funcionalidade de prevenção de duplicatas SMS
"""
import os
import django
import sys
from datetime import datetime, timedelta

# Configurar Django
sys.path.append('/home/lkdev/workspace/projects/Marketing-Digital-Projects/SMS-Sender')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()

from webhooks.models import WebhookEvent, SMSLog
from django.utils import timezone

def create_test_webhook(phone="11999887766", amount=1000, payment_method="pix", payment_status="waiting_payment"):
    """Cria um webhook de teste"""
    raw_data = {
        "paymentId": f"test_{datetime.now().timestamp()}",
        "customer": {
            "phone": phone,
            "name": "Cliente Teste"
        },
        "amount": amount,
        "method": payment_method,
        "status": payment_status,
        "timestamp": datetime.now().isoformat()
    }
    
    webhook = WebhookEvent.objects.create(
        payment_id=raw_data["paymentId"],
        payment_method=payment_method,
        payment_status=payment_status,
        amount=amount,
        customer_phone=phone,
        customer_name="Cliente Teste",
        raw_data=raw_data
    )
    
    print(f"✅ Webhook criado: ID {webhook.id}, Hash: {webhook.webhook_hash[:8]}, Duplicate Key: {webhook.duplicate_key}")
    return webhook

def test_duplicate_key_generation():
    """Testa a geração de chave de duplicata"""
    print("\n🔧 TESTE: Geração de Chave de Duplicata")
    print("=" * 50)
    
    # Criar dois webhooks com os mesmos dados
    webhook1 = create_test_webhook(phone="11999887766", amount=1000)
    webhook2 = create_test_webhook(phone="11999887766", amount=1000)
    
    print(f"Webhook 1 - Duplicate Key: {webhook1.duplicate_key}")
    print(f"Webhook 2 - Duplicate Key: {webhook2.duplicate_key}")
    
    if webhook1.duplicate_key == webhook2.duplicate_key:
        print("✅ Chaves de duplicata iguais - correto!")
    else:
        print("❌ Chaves de duplicata diferentes - erro!")
    
    # Webhook com telefone diferente
    webhook3 = create_test_webhook(phone="11888776655", amount=1000)
    print(f"Webhook 3 (telefone diferente) - Duplicate Key: {webhook3.duplicate_key}")
    
    if webhook1.duplicate_key != webhook3.duplicate_key:
        print("✅ Chaves diferentes para telefones diferentes - correto!")
    else:
        print("❌ Chaves iguais para telefones diferentes - erro!")

def test_sms_duplicate_prevention():
    """Testa a prevenção de SMS duplicados"""
    print("\n🚫 TESTE: Prevenção de SMS Duplicados")
    print("=" * 50)
    
    # Criar webhook
    webhook = create_test_webhook(phone="11777666555", amount=2000)
    
    # Teste 1: Primeiro SMS deve ser permitido
    can_send, reason = webhook.can_send_sms()
    print(f"Primeiro SMS - Pode enviar: {can_send}, Razão: {reason}")
    
    if can_send:
        print("✅ Primeiro SMS permitido - correto!")
        # Simular envio do SMS
        webhook.record_sms_sent()
        print(f"📱 SMS registrado. Count: {webhook.sms_sent_count}, Último: {webhook.last_sms_sent_at}")
    else:
        print("❌ Primeiro SMS bloqueado - erro!")
    
    # Teste 2: Segundo SMS imediato deve ser bloqueado
    can_send, reason = webhook.can_send_sms()
    print(f"Segundo SMS (imediato) - Pode enviar: {can_send}, Razão: {reason}")
    
    if not can_send:
        print("✅ Segundo SMS bloqueado - correto!")
    else:
        print("❌ Segundo SMS permitido - erro!")

def test_similar_webhooks_detection():
    """Testa detecção de webhooks similares"""
    print("\n🔍 TESTE: Detecção de Webhooks Similares")
    print("=" * 50)
    
    phone = "11555444333"
    amount = 5000
    
    # Criar webhook base
    webhook1 = create_test_webhook(phone=phone, amount=amount)
    webhook1.record_sms_sent()
    
    # Criar webhook similar (mesmo telefone, valor e método)
    webhook2 = create_test_webhook(phone=phone, amount=amount)
    
    # Verificar se detecta webhooks similares
    similar_webhooks = webhook2.get_similar_recent_webhooks(hours=24)
    print(f"Webhooks similares encontrados: {len(similar_webhooks)}")
    
    for w in similar_webhooks:
        print(f"  - Webhook {w.id}: SMS Count: {w.sms_sent_count}, Último SMS: {w.last_sms_sent_at}")
    
    # Testar se o segundo webhook pode enviar SMS
    can_send, reason = webhook2.can_send_sms()
    print(f"Webhook 2 pode enviar SMS: {can_send}, Razão: {reason}")
    
    if not can_send:
        print("✅ SMS bloqueado por webhook similar - correto!")
    else:
        print("❌ SMS permitido apesar de webhook similar - erro!")

def test_sms_log_duplicate_recording():
    """Testa registro de tentativas de SMS duplicado"""
    print("\n📝 TESTE: Registro de Tentativas Duplicadas")
    print("=" * 50)
    
    # Criar webhook e simular tentativa duplicada
    webhook = create_test_webhook(phone="11333222111", amount=3000)
    webhook.record_sms_sent()
    
    # Tentar enviar SMS novamente (deve ser bloqueado)
    can_send, reason = webhook.can_send_sms()
    
    if not can_send:
        # Registrar tentativa bloqueada
        sms_log = SMSLog.create_blocked_duplicate(
            webhook_event=webhook,
            phone_number=webhook.customer_phone,
            reason=reason
        )
        
        print(f"✅ SMS duplicado registrado: ID {sms_log.id}")
        print(f"   Status: {sms_log.status}")
        print(f"   É duplicata: {sms_log.is_duplicate_attempt}")
        print(f"   Razão: {sms_log.duplicate_reason}")
    else:
        print("❌ SMS não foi bloqueado - erro!")

def test_force_sms():
    """Testa envio forçado de SMS"""
    print("\n🔓 TESTE: Envio Forçado de SMS")
    print("=" * 50)
    
    # Criar webhook e enviar SMS
    webhook = create_test_webhook(phone="11222111000", amount=4000)
    webhook.record_sms_sent()
    
    # Tentar envio normal (deve ser bloqueado)
    can_send, reason = webhook.can_send_sms()
    print(f"Envio normal - Pode enviar: {can_send}, Razão: {reason}")
    
    # Tentar envio forçado (deve ser permitido)
    can_send_forced, reason_forced = webhook.can_send_sms(force=True)
    print(f"Envio forçado - Pode enviar: {can_send_forced}, Razão: {reason_forced}")
    
    if not can_send and can_send_forced:
        print("✅ Envio forçado funcionando - correto!")
    else:
        print("❌ Envio forçado não funcionando - erro!")

def cleanup_test_data():
    """Limpa dados de teste"""
    print("\n🧹 Limpando dados de teste...")
    
    # Deletar webhooks de teste
    test_webhooks = WebhookEvent.objects.filter(
        customer_name="Cliente Teste"
    )
    count = test_webhooks.count()
    test_webhooks.delete()
    
    print(f"✅ {count} webhooks de teste removidos")

def main():
    """Executa todos os testes"""
    print("🧪 INICIANDO TESTES DE PREVENÇÃO DE DUPLICATAS SMS")
    print("=" * 60)
    
    # Limpar dados anteriores
    cleanup_test_data()
    
    try:
        # Executar testes
        test_duplicate_key_generation()
        test_sms_duplicate_prevention()
        test_similar_webhooks_detection()
        test_sms_log_duplicate_recording()
        test_force_sms()
        
        print("\n🎉 TODOS OS TESTES CONCLUÍDOS!")
        print("=" * 60)
        
        # Mostrar estatísticas finais
        total_webhooks = WebhookEvent.objects.filter(customer_name="Cliente Teste").count()
        total_sms_logs = SMSLog.objects.filter(webhook_event__customer_name="Cliente Teste").count()
        duplicate_logs = SMSLog.objects.filter(
            webhook_event__customer_name="Cliente Teste",
            is_duplicate_attempt=True
        ).count()
        
        print(f"📊 Estatísticas:")
        print(f"   Webhooks criados: {total_webhooks}")
        print(f"   SMS logs criados: {total_sms_logs}")
        print(f"   Tentativas duplicadas: {duplicate_logs}")
        
    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Limpar dados de teste
        cleanup_test_data()

if __name__ == "__main__":
    main()
