#!/bin/bash

# SMS Sender - Script de Inicialização
# Este script facilita a execução do sistema de recuperação de vendas

set -e

echo "🚀 SMS Sender - Sistema de Recuperação de Vendas"
echo "================================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para verificar se comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verificar dependências
echo -e "\n${BLUE}📋 Verificando dependências...${NC}"

if ! command_exists python; then
    echo -e "${RED}❌ Python não encontrado${NC}"
    exit 1
fi

if ! command_exists pip; then
    echo -e "${RED}❌ pip não encontrado${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python e pip encontrados${NC}"

# Verificar arquivo .env
if [ ! -f .env ]; then
    echo -e "\n${YELLOW}⚠️  Arquivo .env não encontrado${NC}"
    echo "Criando arquivo .env de exemplo..."
    
    cat > .env << EOF
# Twilio Settings
ACCOUNT_SID=your_twilio_account_sid
AUTH_TOKEN=your_twilio_auth_token
PHONE_NUMBER=your_twilio_phone_number

# Django Settings
SECRET_KEY=django-insecure-example-key-change-this-in-production
DEBUG=True

# Celery/Redis Settings
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
EOF
    
    echo -e "${YELLOW}📝 Configure as credenciais do Twilio no arquivo .env${NC}"
    echo -e "${YELLOW}   Depois execute novamente este script${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Arquivo .env encontrado${NC}"

# Instalar dependências
echo -e "\n${BLUE}📦 Instalando dependências...${NC}"
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✅ Dependências instaladas${NC}"

# Executar migrações
echo -e "\n${BLUE}🗄️  Configurando banco de dados...${NC}"
python manage.py makemigrations > /dev/null 2>&1
python manage.py migrate > /dev/null 2>&1
echo -e "${GREEN}✅ Banco de dados configurado${NC}"

# Verificar sistema
echo -e "\n${BLUE}🔍 Verificando configuração...${NC}"
python manage.py check > /dev/null 2>&1
echo -e "${GREEN}✅ Sistema configurado corretamente${NC}"

# Menu de opções
echo -e "\n${BLUE}🎯 Escolha uma opção:${NC}"
echo "1) Iniciar servidor Django (desenvolvimento)"
echo "2) Testar envio de SMS"
echo "3) Simular webhook da TriboPay"
echo "4) Iniciar com Docker Compose"
echo "5) Executar testes"
echo "6) Criar superusuário"
echo "0) Sair"

read -p "Digite sua opção (0-6): " choice

case $choice in
    1)
        echo -e "\n${GREEN}🚀 Iniciando servidor Django...${NC}"
        echo -e "${YELLOW}📱 Acesse: http://localhost:8000${NC}"
        echo -e "${YELLOW}🔧 Admin: http://localhost:8000/admin/${NC}"
        echo -e "${YELLOW}📡 API: http://localhost:8000/api/webhooks/${NC}"
        echo -e "${YELLOW}⏹️  Para parar: Ctrl+C${NC}\n"
        python manage.py runserver
        ;;
    2)
        echo -e "\n${GREEN}📱 Teste de SMS${NC}"
        read -p "Digite o número de telefone (ex: +5511999999999): " phone
        read -p "Digite o nome do cliente: " name
        read -p "Digite o valor em centavos (ex: 5000 = R$ 50,00): " amount
        
        python manage.py test_sms --phone "$phone" --name "$name" --amount "$amount"
        ;;
    3)
        echo -e "\n${GREEN}🔄 Simulação de Webhook${NC}"
        read -p "Digite o número de telefone (ex: +5511999999999): " phone
        read -p "Digite o valor em centavos (ex: 5000 = R$ 50,00): " amount
        
        echo -e "\n${BLUE}🚀 Iniciando servidor temporário...${NC}"
        python manage.py runserver &
        SERVER_PID=$!
        
        sleep 3
        
        echo -e "${BLUE}📤 Enviando webhook...${NC}"
        python manage.py simulate_webhook --phone "$phone" --amount "$amount"
        
        echo -e "\n${YELLOW}⏹️  Parando servidor...${NC}"
        kill $SERVER_PID
        ;;
    4)
        echo -e "\n${GREEN}🐳 Iniciando com Docker Compose...${NC}"
        if command_exists docker-compose; then
            docker-compose up
        elif command_exists docker && docker compose version >/dev/null 2>&1; then
            docker compose up
        else
            echo -e "${RED}❌ Docker Compose não encontrado${NC}"
            echo -e "${YELLOW}Instale o Docker Compose e tente novamente${NC}"
        fi
        ;;
    5)
        echo -e "\n${GREEN}🧪 Executando testes...${NC}"
        python manage.py test
        ;;
    6)
        echo -e "\n${GREEN}👤 Criando superusuário...${NC}"
        python manage.py createsuperuser
        ;;
    0)
        echo -e "\n${GREEN}👋 Até logo!${NC}"
        exit 0
        ;;
    *)
        echo -e "\n${RED}❌ Opção inválida${NC}"
        exit 1
        ;;
esac
