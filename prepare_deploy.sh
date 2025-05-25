#!/bin/bash

# SMS Sender - Script de Deploy para Render
# Este script prepara e valida a aplicação para deploy

set -e

echo "🚀 SMS Sender - Preparação para Deploy na Render"
echo "=================================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Verificar se estamos no diretório correto
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Execute este script no diretório raiz do projeto${NC}"
    exit 1
fi

echo -e "\n${BLUE}📋 Validando arquivos necessários...${NC}"

# Verificar arquivos obrigatórios
required_files=("build.sh" "Procfile" "runtime.txt" "requirements.txt" "render.yaml")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ $file não encontrado${NC}"
        exit 1
    fi
done

echo -e "\n${BLUE}🔍 Verificando configurações...${NC}"

# Verificar se build.sh é executável
if [ -x "build.sh" ]; then
    echo -e "${GREEN}✅ build.sh é executável${NC}"
else
    echo -e "${YELLOW}⚠️  Tornando build.sh executável...${NC}"
    chmod +x build.sh
fi

# Testar build localmente
echo -e "\n${BLUE}🛠️  Testando build local...${NC}"
pip install -r requirements.txt > /dev/null 2>&1
python manage.py check --deploy > /dev/null 2>&1
echo -e "${GREEN}✅ Build teste passou${NC}"

# Verificar migrações
echo -e "\n${BLUE}📊 Verificando migrações...${NC}"
python manage.py makemigrations --dry-run --check > /dev/null 2>&1
echo -e "${GREEN}✅ Migrações estão atualizadas${NC}"

# Verificar static files
echo -e "\n${BLUE}📁 Testando coleta de arquivos estáticos...${NC}"
python manage.py collectstatic --noinput --dry-run > /dev/null 2>&1
echo -e "${GREEN}✅ Arquivos estáticos OK${NC}"

# Verificar imports e sintaxe
echo -e "\n${BLUE}🐍 Verificando sintaxe Python...${NC}"
python -m py_compile sms_sender/settings.py
python -m py_compile sms_sender/wsgi.py
echo -e "${GREEN}✅ Sintaxe OK${NC}"

echo -e "\n${GREEN}🎉 Aplicação pronta para deploy!${NC}"
echo -e "\n${BLUE}📝 Próximos passos:${NC}"
echo "1. Commit e push para seu repositório GitHub"
echo "2. Acesse https://dashboard.render.com"
echo "3. Crie um novo Blueprint e conecte seu repositório"
echo "4. Configure as variáveis de ambiente:"
echo "   - TWILIO_ACCOUNT_SID"
echo "   - TWILIO_AUTH_TOKEN" 
echo "   - TWILIO_PHONE_NUMBER"
echo "   - SECRET_KEY (gere uma nova)"
echo "   - ALLOWED_HOSTS (seu-app.onrender.com)"
echo -e "\n${YELLOW}📖 Consulte DEPLOY_GUIDE.md para instruções detalhadas${NC}"

# Gerar SECRET_KEY se solicitado
read -p "Deseja gerar uma nova SECRET_KEY? (y/n): " generate_key
if [ "$generate_key" = "y" ] || [ "$generate_key" = "Y" ]; then
    echo -e "\n${BLUE}🔑 Nova SECRET_KEY gerada:${NC}"
    python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
fi

echo -e "\n${GREEN}✨ Deploy preparado com sucesso!${NC}"
