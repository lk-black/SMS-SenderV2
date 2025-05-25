#!/usr/bin/env python
"""
Script para diagnosticar problemas do worker Celery no Render
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()

from celery import Celery
from sms_sender.celery import app
import redis
from decouple import config

def test_redis_connection():
    """Testa conexão com Redis"""
    try:
        redis_url = config('REDIS_URL', default='redis://localhost:6379/0')
        print(f"🔄 Testando Redis: {redis_url}")
        
        r = redis.from_url(redis_url)
        r.ping()
        
        # Teste básico de set/get
        r.set('test_key', 'test_value', ex=10)
        value = r.get('test_key')
        
        print("✅ Redis conectado com sucesso")
        print(f"✅ Teste set/get: {value.decode() if value else 'ERRO'}")
        return True
    except Exception as e:
        print(f"❌ Erro no Redis: {e}")
        return False

def test_celery_config():
    """Testa configuração do Celery"""
    try:
        print("🔄 Testando configuração do Celery...")
        
        print(f"✅ App name: {app.main}")
        print(f"✅ Broker URL: {app.conf.broker_url}")
        print(f"✅ Result backend: {app.conf.result_backend}")
        print(f"✅ Task serializer: {app.conf.task_serializer}")
        
        # Verificar se as tasks estão registradas
        print("\n📋 Tasks registradas:")
        for task_name in app.tasks:
            if not task_name.startswith('celery.'):
                print(f"  - {task_name}")
        
        return True
    except Exception as e:
        print(f"❌ Erro na configuração do Celery: {e}")
        return False

def test_task_creation():
    """Testa criação de task"""
    try:
        print("🔄 Testando criação de task...")
        
        # Importar tasks
        from webhooks.tasks import send_sms_task, debug_task
        
        # Criar task de debug
        result = debug_task.delay("Teste de diagnóstico")
        
        print(f"✅ Task criada: {result.id}")
        print(f"✅ Task state: {result.state}")
        
        # Verificar na fila Redis
        redis_url = config('REDIS_URL', default='redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        
        # Verificar filas do Celery
        queue_length = r.llen('celery')
        print(f"✅ Itens na fila 'celery': {queue_length}")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao criar task: {e}")
        return False

def test_worker_inspection():
    """Testa inspeção do worker"""
    try:
        print("🔄 Testando inspeção do worker...")
        
        i = app.control.inspect()
        
        # Verificar workers ativos
        active_workers = i.active()
        print(f"👥 Workers ativos: {active_workers}")
        
        # Verificar estatísticas
        stats = i.stats()
        print(f"📊 Estatísticas: {stats}")
        
        # Verificar workers registrados
        registered = i.registered()
        print(f"📝 Tasks registradas nos workers: {registered}")
        
        return True
    except Exception as e:
        print(f"❌ Erro na inspeção: {e}")
        return False

def main():
    print("🚀 Diagnóstico do Worker Celery - Render")
    print("=" * 50)
    
    # Mostrar variáveis de ambiente relevantes
    print("\n🔧 Variáveis de ambiente:")
    env_vars = ['REDIS_URL', 'DATABASE_URL', 'DEBUG', 'CELERY_TASK_ALWAYS_EAGER']
    for var in env_vars:
        value = os.environ.get(var, 'NÃO DEFINIDA')
        # Ocultar valores sensíveis
        if 'URL' in var and value != 'NÃO DEFINIDA':
            value = value[:20] + "..." if len(value) > 20 else value
        print(f"  {var}: {value}")
    
    print("\n" + "=" * 50)
    
    # Executar testes
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Celery Config", test_celery_config),
        ("Task Creation", test_task_creation),
        ("Worker Inspection", test_worker_inspection),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 30)
        results[test_name] = test_func()
    
    # Resumo
    print("\n" + "=" * 50)
    print("📋 RESUMO DO DIAGNÓSTICO")
    print("=" * 50)
    
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    # Sugestões baseadas nos resultados
    print("\n💡 SUGESTÕES:")
    
    if not results.get("Redis Connection"):
        print("- Verificar se o Redis está rodando e acessível")
        print("- Verificar REDIS_URL no Render")
    
    if not results.get("Worker Inspection"):
        print("- Worker provavelmente não está rodando")
        print("- Verificar logs do worker no Render dashboard")
        print("- Verificar se o comando de start está correto")
    
    if results.get("Task Creation") and not results.get("Worker Inspection"):
        print("- Tasks estão sendo criadas mas não processadas")
        print("- Problema específico do worker, não da configuração")

if __name__ == "__main__":
    main()
