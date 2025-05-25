#!/usr/bin/env bash
# Script simplificado para testar Docker sem docker-compose
set -e

echo "🐳 Testando Dockerfile standalone"
echo "=" * 40

# Limpar containers existentes
echo "🧹 Limpando containers antigos..."
docker stop sms-sender-test 2>/dev/null || true
docker rm sms-sender-test 2>/dev/null || true

# Build da imagem
echo "🔨 Construindo imagem..."
docker build -t sms-sender:test .

echo "✅ Imagem construída com sucesso!"
echo "📋 Informações da imagem:"
docker images | grep sms-sender

# Testar se a imagem foi criada corretamente
echo "📋 Verificando estrutura da imagem..."
docker run --rm sms-sender:test ls -la /app

echo "📋 Verificando se os scripts estão executáveis..."
docker run --rm sms-sender:test ls -la /app/*.sh

echo "📋 Verificando dependências Python..."
docker run --rm sms-sender:test pip list | grep -E "(celery|django|redis|decouple)"

echo "✅ Teste do Dockerfile concluído com sucesso!"
