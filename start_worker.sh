#!/usr/bin/env bash
# Worker startup script with comprehensive health checks
set -e

echo "🚀 Iniciando Celery Worker com verificações de saúde..."

# Aguardar serviços essenciais
./wait_for_db.sh echo "Serviços prontos para worker"

# Verificar configuração do Celery
echo "🔧 Verificando configuração do Celery..."
python -c "
from sms_sender.celery import app
print(f'✅ App: {app.main}')
print(f'✅ Broker: {app.conf.broker_url}')
print(f'✅ Backend: {app.conf.result_backend}')
print('✅ Configuração do Celery válida!')
"

# Verificar se as tasks estão registradas
echo "📋 Verificando tasks registradas..."
python -c "
from sms_sender.celery import app
tasks = [name for name in app.tasks if not name.startswith('celery.')]
print(f'✅ Tasks encontradas: {len(tasks)}')
for task in tasks:
    print(f'  - {task}')
"

# Função para cleanup em caso de interrupção
cleanup() {
    echo '🔄 Recebido sinal de parada, finalizando worker...'
    kill -TERM "\$child" 2>/dev/null
    wait "\$child"
    exit 0
}

# Capturar sinais para cleanup graceful
trap cleanup SIGTERM SIGINT

echo "🎯 Iniciando Celery Worker..."

# Iniciar worker com configurações otimizadas
celery -A sms_sender worker \
    --loglevel=info \
    --concurrency=4 \
    --pool=prefork \
    --max-tasks-per-child=1000 \
    --time-limit=300 \
    --soft-time-limit=240 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat &

child=\$!
wait "\$child"
        time.sleep(2)
"

# Wait for database to be available
echo "Checking database connection..."
python manage.py check --database default

echo "Starting Celery worker..."
# Use solo pool for better compatibility on single-core systems
celery -A sms_sender worker --loglevel=info --concurrency=1 --pool=solo --without-gossip --without-mingle --without-heartbeat
