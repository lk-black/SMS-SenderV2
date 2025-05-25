#!/usr/bin/env bash
# Script específico para iniciar o WORKER Celery
set -e

echo "⚙️ Iniciando WORKER Celery..."

# Aguardar serviços essenciais (sem migração - worker não precisa aplicar migrations)
./wait_for_db.sh

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
from webhooks import tasks  # Forçar importação das tasks
tasks_list = [name for name in app.tasks if not name.startswith('celery.')]
print(f'✅ Tasks encontradas: {len(tasks_list)}')
for task in tasks_list:
    print(f'  - {task}')
"

# Função para cleanup em caso de interrupção
cleanup() {
    echo '🔄 Recebido sinal de parada, finalizando worker...'
    kill -TERM "\$child" 2>/dev/null || true
    wait "\$child" 2>/dev/null || true
    exit 0
}

# Capturar sinais para cleanup graceful
trap cleanup SIGTERM SIGINT

echo "🎯 Iniciando Celery Worker..."

# Configurações específicas para o Render
export C_FORCE_ROOT=1
export CELERY_TASK_ALWAYS_EAGER=False

# Iniciar worker com configurações otimizadas para Render
exec celery -A sms_sender worker \
    --loglevel=info \
    --pool=solo \
    --concurrency=1 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    --optimization=fair
