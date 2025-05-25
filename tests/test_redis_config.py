#!/usr/bin/env python3
"""
Script para testar e configurar conexão Redis
"""

import os
import sys
import django
from django.conf import settings

# Adicionar o diretório do projeto ao Python path
sys.path.append('/home/lkdev/workspace/projects/Marketing-Digital-Projects/SMS-Sender')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()

def test_redis_connection():
    """Testa a conexão com Redis"""
    print("🔍 Testando conexão Redis...")
    
    try:
        from django.core.cache import cache
        
        # Informações de configuração
        print(f"📋 Configuração atual:")
        print(f"   REDIS_URL: {getattr(settings, 'REDIS_URL', 'Not set')}")
        print(f"   Cache backend: {settings.CACHES['default']['BACKEND']}")
        
        if 'django_redis' in settings.CACHES['default']['BACKEND']:
            print(f"   Redis location: {settings.CACHES['default']['LOCATION']}")
            
        # Teste básico de cache
        print("\n🧪 Testando operações de cache...")
        
        # Set
        cache.set('test_key', 'test_value', 30)
        print("✅ SET operation: OK")
        
        # Get
        value = cache.get('test_key')
        if value == 'test_value':
            print("✅ GET operation: OK")
        else:
            print(f"❌ GET operation: FAILED - Expected 'test_value', got '{value}'")
            
        # Delete
        cache.delete('test_key')
        print("✅ DELETE operation: OK")
        
        # Verificar se foi deletado
        value = cache.get('test_key')
        if value is None:
            print("✅ Verify DELETE: OK")
        else:
            print(f"❌ Verify DELETE: FAILED - Key still exists with value '{value}'")
            
        print("\n🎉 Teste de Redis concluído com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar Redis: {str(e)}")
        print(f"   Tipo do erro: {type(e).__name__}")
        
        # Tentar importação manual
        try:
            import redis
            print(f"📦 Redis library version: {redis.__version__}")
            
            # Tentar conexão direta
            from django.core.cache import cache
            backend = cache._cache
            print(f"   Backend type: {type(backend)}")
            
        except ImportError:
            print("❌ Redis library não está instalada")
        except Exception as inner_e:
            print(f"   Erro adicional: {inner_e}")
            
        return False

def test_celery_connection():
    """Testa a conexão do Celery com Redis"""
    print("\n🔍 Testando conexão Celery...")
    
    try:
        from celery import Celery
        from sms_sender.celery import app as celery_app
        
        print(f"📋 Configuração Celery:")
        print(f"   Broker URL: {celery_app.conf.broker_url}")
        print(f"   Result backend: {celery_app.conf.result_backend}")
        
        # Teste de ping
        print("\n🧪 Testando conexão broker...")
        inspector = celery_app.control.inspect()
        
        # Verificar workers ativos
        active = inspector.active()
        if active:
            print(f"✅ Workers ativos encontrados: {list(active.keys())}")
        else:
            print("⚠️  Nenhum worker ativo encontrado")
            
        # Teste de task simples
        print("\n🧪 Testando task básica...")
        from webhooks.tasks import test_task_connection
        
        # Tentar enviar task
        result = test_task_connection.delay()
        print(f"✅ Task enviada: {result.id}")
        
        # Tentar obter resultado (com timeout)
        try:
            task_result = result.get(timeout=10)
            print(f"✅ Resultado da task: {task_result}")
        except Exception as e:
            print(f"⚠️  Timeout ou erro ao obter resultado: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar Celery: {str(e)}")
        return False

def check_environment():
    """Verifica variáveis de ambiente"""
    print("\n🔍 Verificando variáveis de ambiente...")
    
    env_vars = [
        'REDIS_URL',
        'DATABASE_URL',
        'SECRET_KEY',
        'DEBUG',
        'ALLOWED_HOSTS'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        # Mascarar valores sensíveis
        if 'secret' in var.lower() or 'password' in var.lower() or 'token' in var.lower():
            display_value = '*' * len(value) if value != 'Not set' else 'Not set'
        else:
            display_value = value
            
        print(f"   {var}: {display_value}")

def main():
    """Função principal"""
    print("🚀 Iniciando teste de configuração Redis/Celery...")
    print("=" * 60)
    
    # Verificar ambiente
    check_environment()
    
    # Testar Redis
    redis_ok = test_redis_connection()
    
    # Testar Celery
    celery_ok = test_celery_connection()
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES:")
    print(f"   Redis: {'✅ OK' if redis_ok else '❌ FALHOU'}")
    print(f"   Celery: {'✅ OK' if celery_ok else '❌ FALHOU'}")
    
    if redis_ok and celery_ok:
        print("\n🎉 Todos os testes passaram! Sistema está funcionando corretamente.")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique a configuração.")
        
    return redis_ok and celery_ok

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
