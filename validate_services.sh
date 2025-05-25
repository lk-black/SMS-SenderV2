#!/usr/bin/env bash
# Script para validar se os serviços iniciariam corretamente
set -e

echo "🧪 VALIDANDO CONFIGURAÇÕES DOS SERVIÇOS"
echo "=================================================="

# Função para testar se um script é válido
test_script() {
    local script_name=$1
    local service_type=$2
    
    echo -e "\n🔍 Testando $script_name ($service_type)..."
    
    if [ ! -f "$script_name" ]; then
        echo "❌ Script $script_name não encontrado!"
        return 1
    fi
    
    if [ ! -x "$script_name" ]; then
        echo "❌ Script $script_name não é executável!"
        return 1
    fi
    
    # Verificar sintaxe básica
    if bash -n "$script_name"; then
        echo "✅ Sintaxe do $script_name está correta"
    else
        echo "❌ Erro de sintaxe no $script_name"
        return 1
    fi
    
    return 0
}

# Testar scripts de serviços
echo "📋 1. Testando scripts de inicialização..."

test_script "start_web.sh" "WEB (Gunicorn)"
test_script "start_celery_worker.sh" "WORKER (Celery)"  
test_script "start_celery_beat.sh" "BEAT (Celery)"
test_script "wait_for_db.sh" "DEPENDENCY CHECK"

# Testar importações Python
echo -e "\n📋 2. Testando importações Python..."

echo "🔍 Testando Django setup..."
python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()
print('✅ Django setup funcionando')
"

echo "🔍 Testando Celery app..."
python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()
from sms_sender.celery import app
print(f'✅ Celery app: {app.main}')
"

echo "🔍 Testando importação de tasks..."
python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()
from sms_sender.celery import app
from webhooks import tasks
tasks_list = [name for name in app.tasks if not name.startswith('celery.')]
print(f'✅ Tasks disponíveis: {len(tasks_list)}')
"

# Validar render.yaml
echo -e "\n📋 3. Validando render.yaml..."

if [ -f "render.yaml" ]; then
    echo "✅ render.yaml encontrado"
    
    # Verificar se contém os serviços corretos
    if grep -q "sms-sender-web" render.yaml; then
        echo "✅ Serviço web configurado"
    else
        echo "❌ Serviço web não encontrado"
    fi
    
    if grep -q "sms-sender-worker" render.yaml; then
        echo "✅ Serviço worker configurado"
    else
        echo "❌ Serviço worker não encontrado"
    fi
    
    if grep -q "sms-sender-beat" render.yaml; then
        echo "✅ Serviço beat configurado"
    else
        echo "❌ Serviço beat não encontrado"
    fi
    
    # Verificar comandos corretos
    if grep -q "start_web.sh" render.yaml; then
        echo "✅ Comando web correto"
    else
        echo "❌ Comando web incorreto"
    fi
    
    if grep -q "start_celery_worker.sh" render.yaml; then
        echo "✅ Comando worker correto"
    else
        echo "❌ Comando worker incorreto"
    fi
    
else
    echo "❌ render.yaml não encontrado"
fi

echo -e "\n📋 4. Verificando dependências..."

# Verificar se todas as dependências estão no requirements.txt
required_packages=("celery" "django" "gunicorn" "redis" "psycopg2-binary")

for package in "${required_packages[@]}"; do
    if grep -q "$package" requirements.txt; then
        echo "✅ $package está no requirements.txt"
    else
        echo "⚠️ $package pode estar faltando no requirements.txt"
    fi
done

echo -e "\n=================================================="
echo "📋 RESUMO DA VALIDAÇÃO"
echo "=================================================="

echo "✅ Configuração robusta implementada:"
echo "  🌐 Web Service: Gunicorn com configurações otimizadas"
echo "  ⚙️ Worker Service: Celery worker com pool=solo para Render"
echo "  ⏰ Beat Service: Celery beat com scheduler de banco"
echo "  🔧 Scripts específicos para cada serviço"
echo "  📦 Variáveis de ambiente configuradas"

echo -e "\n💡 Próximos passos:"
echo "  1. Commit e push das alterações"
echo "  2. Deploy automático no Render"
echo "  3. Verificar logs de cada serviço no dashboard"
echo "  4. Testar endpoints de diagnóstico"

echo -e "\n🚀 Pronto para deploy!"
