#!/usr/bin/env python
"""
Script para resetar o worker Celery e aplicar migrations
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
    django.setup()
    
    print("🔄 Resetando worker e aplicando migrations...")
    
    # Aplicar migrations
    print("📊 Aplicando migrations...")
    execute_from_command_line(['manage.py', 'migrate', '--verbosity=2'])
    
    # Verificar se as tabelas existem
    print("🔍 Verificando tabelas...")
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%webhook%';")
        tables = cursor.fetchall()
        print(f"Tabelas encontradas: {tables}")
    
    # Testar importação do model
    print("📦 Testando importação dos models...")
    try:
        from webhooks.models import WebhookEvent, SMSLog
        print(f"✅ Models importados com sucesso")
        print(f"📋 Tabela WebhookEvent: {WebhookEvent._meta.db_table}")
        print(f"📋 Tabela SMSLog: {SMSLog._meta.db_table}")
        
        # Verificar se consegue contar registros
        webhook_count = WebhookEvent.objects.count()
        sms_count = SMSLog.objects.count()
        print(f"📊 Webhooks: {webhook_count}, SMS Logs: {sms_count}")
        
    except Exception as e:
        print(f"❌ Erro ao importar models: {e}")
    
    print("✅ Reset concluído!")
