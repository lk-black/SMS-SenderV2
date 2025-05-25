#!/usr/bin/env bash
# Script para testar a aplicação Docker completa
set -e

echo "🚀 Testando aplicação SMS-Sender com Docker"
echo "=" * 50

# Função para cleanup
cleanup() {
    echo "🧹 Limpando recursos..."
    docker-compose down --volumes --remove-orphans 2>/dev/null || true
}

# Capturar sinais para cleanup
trap cleanup EXIT

# Usar docker-compose de desenvolvimento
COMPOSE_FILE="docker-compose.dev.yml"

echo "📋 1. Parando containers existentes..."
docker-compose -f $COMPOSE_FILE down --volumes --remove-orphans

echo "📋 2. Construindo imagens..."
docker-compose -f $COMPOSE_FILE build --no-cache

echo "📋 3. Iniciando serviços..."
docker-compose -f $COMPOSE_FILE up -d

echo "📋 4. Aguardando serviços ficarem prontos..."
sleep 30

# Verificar se os serviços estão rodando
echo "📋 5. Verificando status dos serviços..."
docker-compose -f $COMPOSE_FILE ps

# Testar conectividade dos serviços
echo "📋 6. Testando conectividade..."

# Testar Redis
echo "🔴 Testando Redis..."
docker-compose -f $COMPOSE_FILE exec redis redis-cli ping

# Testar PostgreSQL
echo "🐘 Testando PostgreSQL..."
docker-compose -f $COMPOSE_FILE exec db pg_isready -U sms_dev_user -d sms_sender_dev_db

# Aguardar web app ficar pronto
echo "📋 7. Aguardando web app ficar pronto..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/webhooks/health/ >/dev/null 2>&1; then
        echo "✅ Web app está respondendo!"
        break
    fi
    echo "⏳ Tentativa $i/30..."
    sleep 2
done

# Testar endpoints principais
echo "📋 8. Testando endpoints..."

echo "🏥 Health Check:"
curl -s http://localhost:8000/api/webhooks/health/ | python -m json.tool

echo -e "\n🔧 Worker Diagnosis:"
curl -s http://localhost:8000/api/webhooks/worker-diagnosis/ | python -m json.tool

echo -e "\n📋 9. Verificando logs dos workers..."
echo "📊 Logs do Celery Worker:"
docker-compose -f $COMPOSE_FILE logs --tail=20 celery

echo -e "\n⏰ Logs do Celery Beat:"
docker-compose -f $COMPOSE_FILE logs --tail=20 celery-beat

# Testar criação de task
echo -e "\n📋 10. Testando criação de task..."
echo "🔄 Criando task de teste..."
docker-compose -f $COMPOSE_FILE exec web python -c "
from webhooks.tasks import test_task_connection
result = test_task_connection.delay('Teste Docker')
print(f'✅ Task criada: {result.id}')
print(f'✅ Status: {result.status}')
"

# Verificar Flower (se disponível)
echo -e "\n📋 11. Verificando Flower..."
if curl -s http://localhost:5555/ >/dev/null 2>&1; then
    echo "✅ Flower está disponível em http://localhost:5555"
else
    echo "⚠️ Flower não está disponível"
fi

echo -e "\n📋 12. Resumo final..."
echo "🌐 Web App: http://localhost:8000"
echo "🌸 Flower: http://localhost:5555"
echo "🔴 Redis: localhost:6379"
echo "🐘 PostgreSQL: localhost:5432"

echo -e "\n✅ Teste completo finalizado!"
echo "💡 Para ver logs em tempo real: docker-compose -f $COMPOSE_FILE logs -f"
echo "💡 Para parar: docker-compose -f $COMPOSE_FILE down"
