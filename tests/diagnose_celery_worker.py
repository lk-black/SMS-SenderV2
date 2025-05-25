#!/usr/bin/env python3
"""
Script para diagnosticar problemas do Celery worker em produção
"""

import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "https://sms-senderv2.onrender.com/api/webhooks"

def check_celery_status():
    """Verifica status completo do Celery"""
    print("🔍 DIAGNÓSTICO COMPLETO DO CELERY WORKER")
    print("=" * 50)
    
    # 1. Health check geral
    print("\n1️⃣ Health Check Geral:")
    try:
        response = requests.get(f"{BASE_URL}/health/", timeout=10)
        health = response.json()
        print(f"   Status: {health.get('status')}")
        print(f"   Database: {health.get('database')}")
        print(f"   Cache: {health.get('cache')}")
        print(f"   Redis: {health.get('sms_scheduler', {}).get('redis_available')}")
        print(f"   Celery: {health.get('sms_scheduler', {}).get('celery_available')}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 2. Status específico do scheduler
    print("\n2️⃣ Status SMS Scheduler:")
    try:
        response = requests.get(f"{BASE_URL}/sms-scheduler-status/", timeout=10)
        scheduler = response.json()
        print(f"   Status: {scheduler.get('status')}")
        print(f"   Message: {scheduler.get('message')}")
        if 'scheduler_status' in scheduler:
            for key, value in scheduler['scheduler_status'].items():
                print(f"   {key}: {value}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 3. Criar task de teste
    print("\n3️⃣ Teste de Task Celery:")
    try:
        response = requests.post(f"{BASE_URL}/test-celery-task/", 
                               json={}, timeout=10)
        task_result = response.json()
        print(f"   Status: {task_result.get('status')}")
        print(f"   Task ID: {task_result.get('task_id')}")
        print(f"   Task State: {task_result.get('task_state')}")
        
        task_id = task_result.get('task_id')
        
        # Aguardar um pouco e verificar se a task foi processada
        print(f"\n   Aguardando 10 segundos para verificar processamento...")
        time.sleep(10)
        
        # Verificar se há logs de erro ou sucesso
        print(f"   Task ID {task_id} - Verificar logs do worker para detalhes")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 4. Criar SMS de teste imediato
    print("\n4️⃣ Teste de SMS Imediato (1 minuto):")
    try:
        response = requests.post(f"{BASE_URL}/test-immediate-sms/", 
                               json={}, timeout=10)
        sms_result = response.json()
        print(f"   Status: {sms_result.get('status')}")
        print(f"   Webhook ID: {sms_result.get('webhook_id')}")
        print(f"   Task ID: {sms_result.get('task_id')}")
        print(f"   Countdown: {sms_result.get('countdown_seconds')} segundos")
        
        webhook_id = sms_result.get('webhook_id')
        
        # Aguardar 70 segundos e verificar se foi processado
        print(f"\n   Aguardando 70 segundos para verificar processamento automático...")
        time.sleep(70)
        
        # Verificar se o webhook foi processado
        response = requests.get(f"{BASE_URL}/events/", timeout=10)
        events = response.json()
        
        test_webhook = None
        for event in events:
            if event['id'] == webhook_id:
                test_webhook = event
                break
        
        if test_webhook:
            print(f"   Webhook {webhook_id}:")
            print(f"   - Processed: {test_webhook.get('processed')}")
            print(f"   - SMS Scheduled: {test_webhook.get('sms_scheduled')}")
            
            if test_webhook.get('processed'):
                print("   ✅ SMS foi processado automaticamente!")
            else:
                print("   ❌ SMS NÃO foi processado automaticamente")
                print("   🔧 Problema confirmado: Worker não está processando tasks")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 5. Verificar SMS pendentes
    print("\n5️⃣ SMS Pendentes:")
    try:
        response = requests.get(f"{BASE_URL}/pending-sms/", timeout=10)
        pending = response.json()
        print(f"   Count: {pending.get('count', 0)}")
        if pending.get('count', 0) > 0:
            print("   ⚠️ Há SMS pendentes - Worker não está processando")
        else:
            print("   ✅ Nenhum SMS pendente")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 6. Resumo e diagnóstico
    print("\n" + "=" * 50)
    print("📋 RESUMO DO DIAGNÓSTICO:")
    print("=" * 50)
    
    print("\n🔍 POSSÍVEIS CAUSAS DO PROBLEMA:")
    print("1. Worker do Celery não está rodando no Render")
    print("2. Worker não consegue se conectar ao Redis")
    print("3. Worker está rodando mas não está pegando as tasks")
    print("4. Problema de configuração no environment do worker")
    print("5. Worker está crashando silenciosamente")
    
    print("\n🛠️ PRÓXIMOS PASSOS PARA INVESTIGAÇÃO:")
    print("1. Verificar logs do worker no dashboard do Render")
    print("2. Verificar se o Redis está acessível pelo worker")
    print("3. Verificar variáveis de ambiente do worker")
    print("4. Testar conexão Redis diretamente do worker")
    print("5. Verificar se há erros de importação no worker")

if __name__ == "__main__":
    check_celery_status()
