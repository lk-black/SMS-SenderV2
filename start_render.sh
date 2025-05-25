#!/bin/bash
set -e

echo "🚀 Iniciando Aplicação SMS-Sender..."

SERVICE_TYPE=${SERVICE_TYPE:-"web"}

echo "🔍 Aguardando serviços essenciais..."
./wait_for_db.sh

echo "🎯 Tipo de serviço detectado: $SERVICE_TYPE"

case "$SERVICE_TYPE" in
    "web")
        echo "🌐 Iniciando serviço WEB..."
        echo "🔄 Aplicando migrações..."
        python manage.py migrate --noinput
        
        echo "📁 Coletando arquivos estáticos..."
        python manage.py collectstatic --noinput --clear
        
        echo "🔧 Verificando configuração..."
        python manage.py check --deploy
        
        echo "🚀 Iniciando Gunicorn..."
        exec gunicorn \
            --bind 0.0.0.0:8000 \
            --workers 3 \
            --worker-class sync \
            --timeout 120 \
            --keep-alive 5 \
            --max-requests 1000 \
            --max-requests-jitter 100 \
            --access-logfile - \
            --error-logfile - \
            --log-level info \
            sms_sender.wsgi:application
        ;;
        
    "worker")
        echo "⚙️ Iniciando WORKER Celery..."
        
        echo "🔧 Verificando configuração do Celery..."
        python -c "
import os
import django
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()
from sms_sender.celery import app
print(f'✅ App: {app.main}')
print(f'✅ Broker: {app.conf.broker_url}')
print(f'✅ Backend: {app.conf.result_backend}')
print('✅ Configuração do Celery válida!')
"
        
        echo "📋 Verificando tasks registradas..."
        python -c "
import os
import django
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()
from sms_sender.celery import app
from webhooks import tasks
tasks_list = [name for name in app.tasks if not name.startswith('celery.')]
print(f'✅ Tasks encontradas: {len(tasks_list)}')
for task in tasks_list:
    print(f'  - {task}')
"
        
        echo "🎯 Iniciando Celery Worker..."
        
        export C_FORCE_ROOT=1
        export CELERY_TASK_ALWAYS_EAGER=False
        
        exec celery -A sms_sender worker \
            --loglevel=info \
            --pool=solo \
            --concurrency=1 \
            --without-gossip \
            --without-mingle \
            --without-heartbeat \
            --optimization=fair
        ;;
        
    "beat")
        echo "⏰ Iniciando Celery Beat..."
        
        echo "🔧 Verificando configuração do Celery Beat..."
        python -c "
import os
import django
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()
from sms_sender.celery import app
print(f'✅ App: {app.main}')
print(f'✅ Broker: {app.conf.broker_url}')
print(f'✅ Backend: {app.conf.result_backend}')
print('✅ Configuração do Celery Beat válida!')
"
        
        echo "🔄 Verificando migrações do django-celery-beat..."
        python manage.py migrate django_celery_beat --noinput 2>/dev/null || echo "⚠️ Migrações do beat podem não estar disponíveis"
        
        echo "🧹 Limpando arquivos antigos..."
        rm -f celerybeat.pid celerybeat-schedule celerybeat-schedule.db
        
        echo "⏰ Iniciando Celery Beat..."
        
        export C_FORCE_ROOT=1
        
        exec celery -A sms_sender beat \
            --loglevel=info \
            --pidfile=celerybeat.pid \
            --schedule=celerybeat-schedule
        ;;
        
    *)
        echo "❌ Tipo de serviço não reconhecido: $SERVICE_TYPE"
        echo "Use: web, worker, ou beat"
        exit 1
        ;;
esac
