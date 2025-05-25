# Deploy na Render - Guia Completo

## 🚀 Deploy Automático via Blueprint

1. **Faça fork/clone do repositório**
2. **Conecte no Render**: https://dashboard.render.com
3. **Crie um novo Blueprint**:
   - Clique em "New +"
   - Selecione "Blueprint"
   - Conecte seu repositório GitHub
   - O arquivo `render.yaml` será detectado automaticamente

## 🔧 Configuração Manual (Alternativa)

### 1. PostgreSQL Database
```
Name: sms-sender-db
Database: sms_sender_db
User: sms_user
Region: Oregon (US West)
```

### 2. Redis Instance
```
Name: sms-sender-redis
Plan: Free
Region: Oregon (US West)
```

### 3. Web Service
```
Name: sms-sender-web
Runtime: Python 3
Build Command: ./build.sh
Start Command: gunicorn sms_sender.wsgi:application
```

### 4. Worker Service (Celery)
```
Name: sms-sender-worker
Runtime: Python 3
Build Command: ./build.sh
Start Command: celery -A sms_sender worker --loglevel=info
```

### 5. Beat Service (Scheduler)
```
Name: sms-sender-beat
Runtime: Python 3
Build Command: ./build.sh
Start Command: celery -A sms_sender beat --loglevel=info
```

## 📋 Variáveis de Ambiente Obrigatórias

Configure estas variáveis em cada serviço:

### Web Service
```
DEBUG=false
SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=your-app-name.onrender.com
DATABASE_URL=postgresql://user:password@host:port/db
REDIS_URL=redis://user:password@host:port
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number
```

### Worker & Beat Services
```
DATABASE_URL=postgresql://user:password@host:port/db
REDIS_URL=redis://user:password@host:port
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number
```

## 🔗 Como Obter as URLs dos Serviços

### PostgreSQL
- Vá em Database → Connect → External Connections
- Copie a `External Database URL`

### Redis
- Vá em Redis → Connect
- Copie a `Redis URL`

## 🧪 Testando Após Deploy

### 1. Webhook Endpoint
```bash
curl -X POST https://your-app.onrender.com/api/webhooks/tribopay/ \
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

### 2. Admin Interface
- Acesse: `https://your-app.onrender.com/admin/`
- Crie um superusuário via Render Shell

### 3. Monitoring
- `https://your-app.onrender.com/api/webhooks/events/`
- `https://your-app.onrender.com/api/webhooks/sms-logs/`

## 🛠️ Comandos Úteis no Render Shell

```bash
# Criar superusuário
python manage.py createsuperuser

# Verificar migrações
python manage.py showmigrations

# Coletar arquivos estáticos
python manage.py collectstatic --noinput

# Testar Celery
python manage.py shell
>>> from webhooks.tasks import schedule_sms_recovery
>>> schedule_sms_recovery.delay(1)
```

## 🔍 Monitoramento e Logs

### Logs de Aplicação
- Acesse o dashboard do serviço
- Vá em "Logs" para ver os logs em tempo real

### Métricas
- CPU e Memory usage
- Response times
- Error rates

## 🚨 Troubleshooting

### Problema 1: Build Falha
```bash
# Verifique se build.sh tem permissões
chmod +x build.sh

# Teste localmente
./build.sh
```

### Problema 2: Celery não conecta
- Verifique se REDIS_URL está correto
- Teste conexão Redis no shell

### Problema 3: Database Connection
- Verifique DATABASE_URL
- Teste: `python manage.py dbshell`

### Problema 4: Static Files
- Verifique STATIC_ROOT nas settings
- Execute: `python manage.py collectstatic`

## 💡 Dicas de Performance

### 1. Health Checks
```python
# Adicione endpoint de health check
# views.py
def health_check(request):
    return JsonResponse({'status': 'healthy'})
```

### 2. Logging
- Use logs estruturados
- Configure diferentes níveis por ambiente

### 3. Monitoring
- Configure alertas para erros
- Monitore taxa de entrega de SMS

## 🔐 Segurança

### 1. Variáveis Sensíveis
- Use os Environment Variables do Render
- Nunca comite credenciais no código

### 2. ALLOWED_HOSTS
- Configure apenas domínios necessários
- Use wildcards com cuidado

### 3. HTTPS
- Render fornece HTTPS automaticamente
- Force SSL em produção
