#!/usr/bin/env python3
"""
Script simples para testar Redis
"""

import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
sys.path.append('/home/lkdev/workspace/projects/Marketing-Digital-Projects/SMS-Sender')
django.setup()

def test_simple():
    """Teste simples"""
    print("🔍 Testando Redis...")
    
    from django.conf import settings
    from django.core.cache import cache
    
    print(f"REDIS_URL: {os.environ.get('REDIS_URL', 'Not set')}")
    print(f"Cache backend: {settings.CACHES['default']['BACKEND']}")
    
    try:
        # Teste básico
        cache.set('test', 'value', 30)
        result = cache.get('test')
        print(f"Cache test: {'✅ OK' if result == 'value' else '❌ FAIL'}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        print(f"Tipo: {type(e).__name__}")

if __name__ == '__main__':
    test_simple()
