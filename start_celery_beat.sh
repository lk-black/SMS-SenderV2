#!/usr/bin/env bash
# Script específico para iniciar o BEAT Celery
set -e

echo "⏰ Iniciando Celery Beat..."

# Aguardar serviços essenciais (sem migração - beat não precisa aplicar migrations principais)
./wait_for_db.sh

# Verificar configuração do Celery
echo "🔧 Verificando configuração do Celery Beat..."
python -c "
from sms_sender.celery import app
print(f'✅ App: {app.main}')
print(f'✅ Broker: {app.conf.broker_url}')
print(f'✅ Backend: {app.conf.result_backend}')
print('✅ Configuração do Celery Beat válida!')
"

# Garantir que as migrações estão aplicadas
echo "🔄 Verificando migrações do django-celery-beat..."
python manage.py migrate django_celery_beat --noinput 2>/dev/null || echo "⚠️ Migrações do beat podem não estar disponíveis"

# Remover arquivos de lock antigos se existirem
echo "🧹 Limpando arquivos antigos..."
rm -f celerybeat.pid celerybeat-schedule celerybeat-schedule.db

# Função para cleanup em caso de interrupção
cleanup() {
    echo '🔄 Recebido sinal de parada, finalizando beat...'
    kill -TERM "\$child" 2>/dev/null || true
    wait "\$child" 2>/dev/null || true
    rm -f celerybeat.pid celerybeat-schedule celerybeat-schedule.db
    exit 0
}

# Capturar sinais para cleanup graceful
trap cleanup SIGTERM SIGINT

echo "⏰ Iniciando Celery Beat..."

# Configurações específicas para o Render
export C_FORCE_ROOT=1

# Iniciar beat com configurações otimizadas
exec celery -A sms_sender beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --pidfile=celerybeat.pid
