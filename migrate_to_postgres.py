#!/usr/bin/env python
"""
Script para migrar dados do SQLite para PostgreSQL
Execute após configurar a DATABASE_URL para PostgreSQL
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()

from django.db import connection
from webhooks.models import WebhookEvent, SMSLog

def check_database_connection():
    """Verifica se a conexão com o banco está funcionando"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print(f"✅ Conexão com banco de dados: {connection.settings_dict['ENGINE']}")
            print(f"✅ Host: {connection.settings_dict.get('HOST', 'N/A')}")
            print(f"✅ Nome do banco: {connection.settings_dict['NAME']}")
            return True
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def run_migrations():
    """Executa as migrações no PostgreSQL"""
    try:
        print("\n🔄 Executando migrações...")
        
        # Fazer migrate
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrações executadas com sucesso!")
        
        return True
    except Exception as e:
        print(f"❌ Erro nas migrações: {e}")
        return False

def check_tables():
    """Verifica se as tabelas foram criadas corretamente"""
    try:
        print("\n🔍 Verificando tabelas...")
        
        # Verificar tabela webhook_events
        webhook_count = WebhookEvent.objects.count()
        print(f"✅ Tabela webhook_events: {webhook_count} registros")
        
        # Verificar tabela sms_logs
        sms_count = SMSLog.objects.count()
        print(f"✅ Tabela sms_logs: {sms_count} registros")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao verificar tabelas: {e}")
        return False

def create_test_data():
    """Cria dados de teste para verificar se está funcionando"""
    try:
        print("\n🧪 Criando dados de teste...")
        
        # Criar um webhook de teste
        test_webhook = WebhookEvent.objects.create(
            payment_id="test_postgres_migration",
            customer_name="Teste PostgreSQL",
            customer_phone="+5511999999999",
            customer_email="teste@postgres.com",
            amount=1000,
            payment_method="pix",
            payment_status="waiting_payment",
            raw_data={"test": "postgres_migration"}
        )
        
        print(f"✅ Webhook de teste criado: ID {test_webhook.id}")
        
        # Criar um log de SMS de teste
        test_sms = SMSLog.objects.create(
            webhook_event=test_webhook,
            phone_number="+5511999999999",
            message="Teste de migração para PostgreSQL",
            status="sent"
        )
        
        print(f"✅ SMS Log de teste criado: ID {test_sms.id}")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao criar dados de teste: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 MIGRAÇÃO PARA POSTGRESQL NO RENDER")
    print("=" * 50)
    
    # 1. Verificar conexão
    if not check_database_connection():
        sys.exit(1)
    
    # 2. Executar migrações
    if not run_migrations():
        sys.exit(1)
    
    # 3. Verificar tabelas
    if not check_tables():
        sys.exit(1)
    
    # 4. Criar dados de teste
    if not create_test_data():
        sys.exit(1)
    
    print("\n🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("✅ PostgreSQL configurado e funcionando")
    print("✅ Tabelas criadas")
    print("✅ Dados de teste inseridos")
    print("\nAgora você pode:")
    print("1. Fazer commit e push das mudanças")
    print("2. Deploy no Render irá usar PostgreSQL")
    print("3. Worker e aplicação web usarão o mesmo banco")

if __name__ == "__main__":
    main()
