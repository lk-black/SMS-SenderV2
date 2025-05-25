#!/usr/bin/env bash
# Script para verificar se o banco de dados está pronto

echo "🔍 Verificando se o banco de dados está pronto..."

MAX_ATTEMPTS=30
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    echo "Tentativa $ATTEMPT/$MAX_ATTEMPTS..."
    
    if python manage.py check --database default >/dev/null 2>&1; then
        echo "✅ Banco de dados está pronto!"
        exit 0
    fi
    
    echo "⏳ Banco ainda não está pronto, aguardando..."
    sleep 2
    ATTEMPT=$((ATTEMPT + 1))
done

echo "❌ Timeout: Banco de dados não ficou pronto em tempo hábil"
exit 1
