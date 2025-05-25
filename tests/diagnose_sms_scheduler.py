#!/usr/bin/env python3
"""
Script para diagnosticar o sistema de agendamento de SMS
"""
import os
import sys
import django
from datetime import datetime, timedelta
import json

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()

from webhooks.models import WebhookEvent, SMSLog
from webhooks.sms_scheduler import SMSSchedulerService
from django.utils import timezone

def diagnose_sms_scheduler():
    print("🔍 DIAGNÓSTICO DO SISTEMA DE AGENDAMENTO DE SMS")
    print("=" * 60)
    
    # 1. Verificar status do scheduler
    print("\n1️⃣ STATUS DO SCHEDULER:")
    try:
        scheduler = SMSSchedulerService()
        status = scheduler.get_status()
        print(f"   ✅ Redis disponível: {status['redis_available']}")
        print(f"   ✅ Celery disponível: {status['celery_available']}")
        print(f"   ✅ SMS Recovery habilitado: {status['sms_recovery_enabled']}")
        print(f"   ✅ Modo fallback: {status['fallback_mode']}")
        print(f"   ⏰ Delay em minutos: {status['delay_minutes']}")
    except Exception as e:
        print(f"   ❌ Erro ao verificar scheduler: {e}")
    
    # 2. Verificar webhooks com PIX pendentes
    print("\n2️⃣ WEBHOOKS COM PIX PENDENTES:")
    pix_pending = WebhookEvent.objects.filter(
        payment_method='pix',
        payment_status__in=['waiting_payment', 'pending', 'waiting']
    ).order_by('-webhook_received_at')
    
    print(f"   📊 Total de PIX pendentes: {pix_pending.count()}")
    
    for webhook in pix_pending[:5]:  # Mostrar apenas os 5 mais recentes
        time_since = timezone.now() - webhook.webhook_received_at
        hours_since = time_since.total_seconds() / 3600
        
        print(f"   🔸 ID: {webhook.id} | Phone: {webhook.customer_phone} | "
              f"Recebido há: {hours_since:.1f}h | SMS agendado: {webhook.sms_scheduled}")
        
        # Verificar se deveria ter enviado SMS
        if webhook.sms_scheduled and hours_since > 0.17:  # 10 minutos = 0.17 horas
            print(f"      ⚠️  SMS deveria ter sido enviado há {(hours_since - 0.17):.1f}h")
    
    # 3. Verificar SMS logs
    print("\n3️⃣ LOGS DE SMS:")
    total_sms = SMSLog.objects.count()
    recent_sms = SMSLog.objects.filter(
        sent_at__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-sent_at')
    
    print(f"   📊 Total de SMS registrados: {total_sms}")
    print(f"   📊 SMS nas últimas 24h: {recent_sms.count()}")
    
    if recent_sms:
        print("   📝 SMS recentes:")
        for sms in recent_sms[:3]:
            print(f"      🔸 {sms.phone_number} | Status: {sms.status} | "
                  f"Enviado: {sms.sent_at.strftime('%H:%M:%S')}")
    else:
        print("   ⚠️  Nenhum SMS encontrado nas últimas 24h")
    
    # 4. Verificar SMS pendentes
    print("\n4️⃣ SMS PENDENTES:")
    try:
        pending_sms = scheduler.get_pending_sms()
        print(f"   📊 SMS pendentes para envio: {len(pending_sms)}")
        
        if pending_sms:
            for sms in pending_sms[:3]:
                print(f"      🔸 {sms}")
    except Exception as e:
        print(f"   ❌ Erro ao verificar SMS pendentes: {e}")
    
    # 5. Testar agendamento manual
    print("\n5️⃣ TESTE DE AGENDAMENTO:")
    
    # Encontrar um webhook elegível para teste
    test_webhook = WebhookEvent.objects.filter(
        payment_method='pix',
        payment_status__in=['waiting_payment', 'pending', 'waiting']
    ).first()
    
    if test_webhook:
        print(f"   🧪 Testando com webhook ID: {test_webhook.id}")
        
        try:
            success, message = scheduler.schedule_sms_recovery(test_webhook.id, force=True)
            print(f"   📤 Resultado do agendamento: {success}")
            print(f"   📝 Mensagem: {message}")
        except Exception as e:
            print(f"   ❌ Erro no teste de agendamento: {e}")
    else:
        print("   ⚠️  Nenhum webhook elegível para teste encontrado")
    
    # 6. Verificar tarefas Celery ativas
    print("\n6️⃣ TAREFAS CELERY:")
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        
        # Verificar tarefas ativas
        active_tasks = inspect.active()
        if active_tasks:
            print(f"   📊 Tarefas ativas: {len(active_tasks)}")
        else:
            print("   📊 Nenhuma tarefa ativa encontrada")
        
        # Verificar tarefas agendadas
        scheduled_tasks = inspect.scheduled()
        if scheduled_tasks:
            print(f"   📊 Tarefas agendadas: {len(scheduled_tasks)}")
        else:
            print("   📊 Nenhuma tarefa agendada encontrada")
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar Celery: {e}")
    
    print("\n" + "=" * 60)
    print("✅ DIAGNÓSTICO CONCLUÍDO")

if __name__ == "__main__":
    diagnose_sms_scheduler()
