#!/usr/bin/env bash
# Beat startup script with comprehensive health checks
set -e

echo "🕐 Iniciando Celery Beat com verificações de saúde..."

# Aguardar serviços essenciais
./wait_for_db.sh echo "Serviços prontos para beat"

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
python manage.py migrate django_celery_beat --noinput || echo "⚠️ Migrações do beat podem não estar disponíveis"

# Remover arquivo de lock antigo se existir
if [ -f "celerybeat.pid" ]; then
    echo "🧹 Removendo arquivo PID antigo..."
    rm -f celerybeat.pid
fi

if [ -f "celerybeat-schedule" ]; then
    echo "🧹 Removendo schedule antigo..."
    rm -f celerybeat-schedule
fi

# Função para cleanup em caso de interrupção
cleanup() {
    echo '🔄 Recebido sinal de parada, finalizando beat...'
    kill -TERM "\$child" 2>/dev/null
    wait "\$child"
    rm -f celerybeat.pid celerybeat-schedule
    exit 0
}

# Capturar sinais para cleanup graceful
trap cleanup SIGTERM SIGINT

echo "⏰ Iniciando Celery Beat..."

# Iniciar beat com configurações otimizadas
celery -A sms_sender beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --pidfile=celerybeat.pid &

child=\$!
wait "\$child"
        time.sleep(2)
"

# Wait for database to be available
echo "Checking database connection..."
python manage.py check --database default

echo "Starting Celery beat..."
celery -A sms_sender beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
