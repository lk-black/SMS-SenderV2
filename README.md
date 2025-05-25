# 📱 SMS Sender - Sistema de Recuperação de Vendas

Sistema Django/DRF para envio automático de SMS de recuperação de vendas via Twilio, integrado com webhooks da TriboPay.

## 🎯 Funcionalidades

- **Recepção de Webhooks**: Endpoint para receber notificações da TriboPay
- **Processamento Inteligente**: Filtra pagamentos PIX aguardando processamento
- **SMS Automático**: Envia SMS de recuperação após 10 minutos se pagamento não for confirmado
- **Monitoramento**: Interface admin e API para auditoria de webhooks e SMS enviados
- **Tratamento de Erros**: Retry automático e logs detalhados

## 🛠️ Tecnologias

- **Backend**: Python 3.12, Django 5.0, Django REST Framework
- **Task Queue**: Celery com Redis
- **SMS**: Twilio API
- **Banco de Dados**: PostgreSQL (produção) / SQLite (desenvolvimento)
- **Containerização**: Docker & Docker Compose

## 📦 Instalação

### Pré-requisitos

- Python 3.12+
- Redis
- PostgreSQL (opcional, para produção)
- Conta Twilio com credenciais

### 1. Clone e Configure o Ambiente

```bash
# Clone o repositório
git clone <repository-url>
cd SMS-Sender

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt
```

### 2. Configuração das Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Twilio
ACCOUNT_SID=your_twilio_account_sid
AUTH_TOKEN=your_twilio_auth_token
PHONE_NUMBER=your_twilio_phone_number

# Django
SECRET_KEY=your_secret_key
DEBUG=True

# Celery/Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Database (opcional para produção)
DATABASE_URL=postgresql://user:password@localhost:5432/sms_sender_db
```

### 3. Configuração do Banco de Dados

```bash
# Criar migrações
python manage.py makemigrations

# Aplicar migrações
python manage.py migrate

# Criar superusuário (opcional)
python manage.py createsuperuser
```

### 4. Executar com Docker (Recomendado)

```bash
# Subir todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar serviços
docker-compose down
```

### 5. Executar Manualmente

```bash
# Terminal 1 - Django
python manage.py runserver

# Terminal 2 - Celery Worker
celery -A sms_sender worker --loglevel=info

# Terminal 3 - Celery Beat (opcional)
celery -A sms_sender beat --loglevel=info
```

## 🚀 Uso

### Endpoints da API

#### Webhook Principal (TriboPay)
```
POST /api/webhooks/tribopay/
```

Exemplo de payload:
```json
{
  "id": "payment_123",
  "payment_method": "pix",
  "payment_status": "waiting_payment",
  "amount": 5000,
  "created_at": "2025-05-24T10:00:00Z",
  "updated_at": "2025-05-24T10:00:00Z",
  "customer": {
    "phone_number": "+5511999999999",
    "name": "João Silva",
    "email": "joao@email.com"
  }
}
```

#### Monitoramento

```bash
# Listar webhooks recebidos
GET /api/webhooks/events/

# Detalhes de um webhook
GET /api/webhooks/events/{id}/

# Listar SMS enviados
GET /api/webhooks/sms-logs/

# Teste de SMS
POST /api/webhooks/test-sms/
{
  "phone_number": "+5511999999999",
  "message": "Mensagem de teste"
}
```

### Comandos de Administração

```bash
# Testar envio de SMS
python manage.py test_sms --phone +5511999999999 --name "João" --amount 5000

# Simular webhook
python manage.py simulate_webhook --phone +5511999999999 --status waiting_payment --amount 5000
```

### Interface Admin

Acesse `http://localhost:8000/admin/` para:
- Visualizar webhooks recebidos
- Monitorar SMS enviados
- Gerenciar configurações

## 📋 Fluxo de Funcionamento

1. **Recepção**: TriboPay envia webhook para `/api/webhooks/tribopay/`
2. **Validação**: Sistema valida dados e evita duplicatas
3. **Filtragem**: Processa apenas PIX com status `waiting_payment`
4. **Agendamento**: Agenda task Celery para executar em 10 minutos
5. **Verificação**: Após 10 minutos, verifica se status ainda é `waiting_payment`
6. **SMS**: Se ainda pendente, envia SMS de recuperação via Twilio
7. **Log**: Registra resultado do envio no banco de dados

## 🔧 Configuração do Twilio

1. Crie uma conta em [twilio.com](https://twilio.com)
2. Obtenha suas credenciais:
   - Account SID
   - Auth Token
   - Número de telefone Twilio
3. Configure no arquivo `.env`

## 📊 Monitoramento e Logs

### Logs do Sistema
- `logs/sms_sender.log` - Log geral do sistema
- `logs/webhooks.log` - Log específico de webhooks
- `logs/sms.log` - Log específico de SMS
- `logs/celery.log` - Log das tasks Celery

### Métricas Importantes
- Taxa de entrega de SMS
- Tempo de processamento de webhooks
- Erros de integração com Twilio
- Performance das tasks Celery

## 🧪 Testes

```bash
# Executar todos os testes
python manage.py test

# Testes específicos
python manage.py test webhooks.tests

# Testes com coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

## 🔒 Segurança

- Validação de dados de entrada
- Logs de auditoria
- Rate limiting (recomendado para produção)
- HTTPS obrigatório em produção
- Validação de origem do webhook (implementar se necessário)

## 📈 Deploy na Render

### 🚀 Deploy Automático (Recomendado)

1. **Prepare o deploy**:
```bash
./prepare_deploy.sh
```

2. **Push para GitHub**:
```bash
git add .
git commit -m "Preparar para deploy na Render"
git push origin main
```

3. **Deploy na Render**:
   - Acesse [dashboard.render.com](https://dashboard.render.com)
   - Clique em "New +" → "Blueprint"
   - Conecte seu repositório GitHub
   - O arquivo `render.yaml` será detectado automaticamente

4. **Configure as variáveis de ambiente**:
   - `TWILIO_ACCOUNT_SID` - Seu Account SID do Twilio
   - `TWILIO_AUTH_TOKEN` - Seu Auth Token do Twilio
   - `TWILIO_PHONE_NUMBER` - Seu número do Twilio
   - `SECRET_KEY` - Gere uma nova chave secreta
   - `ALLOWED_HOSTS` - `seu-app.onrender.com`

### 📋 Checklist de Deploy

- [x] ✅ Arquivos de configuração criados (`build.sh`, `Procfile`, `render.yaml`)
- [x] ✅ Settings ajustados para produção
- [x] ✅ WhiteNoise configurado para arquivos estáticos
- [x] ✅ PostgreSQL configurado
- [x] ✅ Redis configurado para Celery
- [x] ✅ Health check endpoint criado
- [x] ✅ Logs configurados
- [x] ✅ Segurança HTTPS habilitada

### 🔧 Configuração Manual (Alternativa)

Consulte o arquivo `DEPLOY_GUIDE.md` para instruções detalhadas de configuração manual.

### 🧪 Testando Após Deploy

```bash
# Health check
curl https://seu-app.onrender.com/api/webhooks/health/

# Teste de webhook
curl -X POST https://seu-app.onrender.com/api/webhooks/tribopay/ \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test_payment_123",
    "payment_method": "pix",
    "payment_status": "waiting_payment",
    "amount": 5000,
    "customer": {
      "phone_number": "+5511999999999",
      "name": "João Silva"
    }
  }'
```

### 📊 Monitoramento

- **Admin**: `https://seu-app.onrender.com/admin/`
- **Webhooks**: `https://seu-app.onrender.com/api/webhooks/events/`
- **SMS Logs**: `https://seu-app.onrender.com/api/webhooks/sms-logs/`
- **Health**: `https://seu-app.onrender.com/api/webhooks/health/`

## 📈 Produção

### Checklist de Deploy

- [x] Configurar variáveis de ambiente
- [x] Usar PostgreSQL
- [x] Configurar Redis
- [x] Configurar HTTPS
- [x] Configurar logs rotativos
- [x] Monitoramento (health checks)
- [x] Backup do banco de dados
- [x] Static files (WhiteNoise)

### Exemplo de Deploy com Docker

```bash
# Build da imagem
docker build -t sms-sender .

# Deploy com docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📞 Suporte

Para dúvidas ou problemas:
- Abra uma issue no GitHub
- Entre em contato via email

## 📚 Documentação Adicional

- [API da TriboPay](https://docs.tribopay.com.br)
- [Twilio Python SDK](https://www.twilio.com/docs/python)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)

---

⚡ **Desenvolvimento por**: Sua Equipe de Desenvolvimento
# SMS-SenderV2
