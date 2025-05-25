#!/usr/bin/env bash
# Script específico para iniciar o serviço WEB com Gunicorn
set -e

echo "🌐 Iniciando Serviço WEB (Gunicorn)..."

# Aguardar serviços essenciais E aplicar migrações automaticamente
./wait_for_db.sh --migrate

# Coletar arquivos estáticos
echo "📁 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear

# Verificar se a aplicação está funcionando
echo "🔧 Verificando configuração..."
python manage.py check --deploy

echo "🚀 Iniciando Gunicorn..."

# Iniciar Gunicorn com configurações otimizadas
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class sync \
    --timeout 120 \
    --keepalive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output \
    sms_sender.wsgi:application
