#!/usr/bin/env python
"""
Script para testar se o Celery worker consegue se conectar e processar tarefas
"""
import os
import sys
import django
from pathlib import Path

# Adicionar o diretório do projeto ao path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()

def test_celery_connection():
    """Testa a conexão do Celery"""
    try:
        from celery import current_app
        from webhooks.tasks import test_task_connection
        
        print("🔍 Testando conexão Celery...")
        
        # Testar conexão Redis
        try:
            broker = current_app.broker_connection()
            broker.ensure_connection(max_retries=3)
            print("✅ Conexão com Redis Broker: OK")
        except Exception as e:
            print(f"❌ Erro na conexão Redis Broker: {e}")
            return False
        
        # Testar backend de resultados
        try:
            backend = current_app.backend
            if hasattr(backend, 'client'):
                backend.client.ping()
                print("✅ Conexão com Redis Backend: OK")
            else:
                print("⚠️  Backend não suporta ping")
        except Exception as e:
            print(f"❌ Erro na conexão Redis Backend: {e}")
        
        # Testar se consegue criar uma tarefa
        try:
            result = test_task_connection.delay()
            print(f"✅ Tarefa criada com ID: {result.id}")
            
            # Verificar status da tarefa
            status = result.status
            print(f"📊 Status da tarefa: {status}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar tarefa: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Erro geral no Celery: {e}")
        return False

def test_worker_status():
    """Testa o status dos workers"""
    try:
        from celery import current_app
        
        print("\n🔍 Verificando workers online...")
        
        inspect = current_app.control.inspect()
        
        # Verificar workers ativos
        active = inspect.active()
        if active:
            print(f"✅ Workers ativos encontrados: {list(active.keys())}")
            for worker, tasks in active.items():
                print(f"  - {worker}: {len(tasks)} tarefas ativas")
        else:
            print("❌ Nenhum worker ativo encontrado")
        
        # Verificar workers registrados
        stats = inspect.stats()
        if stats:
            print(f"✅ Workers registrados: {list(stats.keys())}")
        else:
            print("❌ Nenhum worker registrado")
            
        # Verificar tarefas registradas
        registered = inspect.registered()
        if registered:
            print("✅ Tarefas registradas nos workers:")
            for worker, tasks in registered.items():
                print(f"  - {worker}: {len(tasks)} tarefas")
        else:
            print("❌ Nenhuma tarefa registrada nos workers")
            
    except Exception as e:
        print(f"❌ Erro ao verificar workers: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando diagnóstico do Celery Worker...")
    print("=" * 50)
    
    success = test_celery_connection()
    test_worker_status()
    
    print("=" * 50)
    if success:
        print("✅ Teste de conexão Celery: SUCESSO")
    else:
        print("❌ Teste de conexão Celery: FALHOU")
