#!/usr/bin/env bash
# Script para executar antes de iniciar a aplicação
# Garante que as migrações sejam sempre aplicadas

echo "🔄 Iniciando processo de migração automática..."

# Verificar se o banco de dados está pronto
./wait_for_db.sh

# Executar migrações com retry automático
echo "📊 Executando migrações do banco de dados com retry..."
python manage.py auto_migrate --max-retries=5 --retry-delay=3

echo "🚀 Migrações concluídas! Aplicação pronta para iniciar..."
