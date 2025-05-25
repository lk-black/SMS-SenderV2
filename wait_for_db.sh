#!/usr/bin/env bash
# Script robusto para verificar se o banco de dados e Redis estão prontos

set -e

echo "🔍 Verificando se os serviços estão prontos..."

# Função para aguardar PostgreSQL
wait_for_postgres() {
    echo "🐘 Aguardando PostgreSQL..."
    MAX_ATTEMPTS=60
    ATTEMPT=1

    while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
        echo "Tentativa $ATTEMPT/$MAX_ATTEMPTS (PostgreSQL)..."
        
        if python manage.py check --database default >/dev/null 2>&1; then
            echo "✅ PostgreSQL está pronto!"
            return 0
        fi
        
        echo "⏳ PostgreSQL ainda não está pronto, aguardando..."
        sleep 2
        ATTEMPT=$((ATTEMPT + 1))
    done

    echo "❌ Timeout: PostgreSQL não ficou pronto em tempo hábil"
    return 1
}

# Função para aguardar Redis
wait_for_redis() {
    echo "🔴 Aguardando Redis..."
    MAX_ATTEMPTS=30
    ATTEMPT=1

    while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
        echo "Tentativa $ATTEMPT/$MAX_ATTEMPTS (Redis)..."
        
        if python -c "
import redis
import os
from decouple import config
try:
    redis_url = config('REDIS_URL', default='redis://redis:6379/0')
    r = redis.from_url(redis_url)
    r.ping()
    print('✅ Redis conectado!')
    exit(0)
except Exception as e:
    print(f'❌ Redis erro: {e}')
    exit(1)
" 2>/dev/null; then
            echo "✅ Redis está pronto!"
            return 0
        fi
        
        echo "⏳ Redis ainda não está pronto, aguardando..."
        sleep 2
        ATTEMPT=$((ATTEMPT + 1))
    done

    echo "❌ Timeout: Redis não ficou pronto em tempo hábil"
    return 1
}

# Aguardar serviços
wait_for_postgres
wait_for_redis

echo "🚀 Todos os serviços estão prontos! Executando comando..."

# Executar comando passado como argumentos
exec "$@"
