# 🔧 Guia de Configuração Redis no Render

## 📋 Configuração Correta do Redis para SMS Sender

### 1. 🏗️ Serviços Necessários no Render

Para o sistema funcionar completamente, você precisa dos seguintes serviços:

1. **Web Service** (sms-sender-web) - Aplicação Django
2. **Worker Service** (sms-sender-worker) - Celery Worker
3. **Beat Service** (sms-sender-beat) - Celery Beat Scheduler
4. **PostgreSQL Database** (sms-sender-db)
5. **Redis Instance** (sms-sender-redis)

### 2. 🔗 Configuração das Variáveis de Ambiente

No painel do Render, configure as seguintes variáveis de ambiente para TODOS os serviços:

#### Variáveis Obrigatórias:
```env
# Database (auto-configurado pelo Render)
DATABASE_URL=postgresql://user:password@host:port/database

# Redis - IMPORTANTE: Configure manualmente
REDIS_URL=redis://red-xxxxxxxxx:6379/0

# Twilio (configure com suas credenciais)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Django
SECRET_KEY=your-secret-key
DEBUG=false
ALLOWED_HOSTS=*.onrender.com,your-domain.com

# SMS Recovery
SMS_RECOVERY_ENABLED=true
SMS_RECOVERY_DELAY_MINUTES=10
```

### 3. 🎯 Como Obter a REDIS_URL

1. **Criar o serviço Redis:**
   - No dashboard do Render, clique em "New +"
   - Selecione "Redis"
   - Escolha o plano (Free está ok para testes)
   - Nome: `sms-sender-redis`

2. **Obter a URL de conexão:**
   - Acesse o serviço Redis criado
   - Na aba "Connect", copie a URL interna do Redis
   - Formato: `redis://red-xxxxxxxxx:6379/0`

3. **Configurar nos serviços:**
   - Adicione a variável `REDIS_URL` em TODOS os serviços:
     - sms-sender-web
     - sms-sender-worker  
     - sms-sender-beat

### 4. 🚀 Ordem de Deploy

1. **Primeiro:** Criar Redis e Database
2. **Segundo:** Configurar variáveis de ambiente
3. **Terceiro:** Deploy dos serviços na ordem:
   - Web Service (principal)
   - Worker Service
   - Beat Service

### 5. ✅ Verificação da Configuração

Após o deploy, teste os endpoints:

```bash
# Health Check - Deve mostrar cache connected
curl https://your-app.onrender.com/api/webhooks/health/

# Deve retornar algo como:
{
  "status": "healthy",
  "database": "connected",
  "cache": "connected",
  "cache_backend": "RedisCache",
  "redis_url_configured": true,
  "sms_scheduler": {
    "redis_available": true,
    "celery_available": true
  }
}
```

### 6. 🔧 Troubleshooting

#### Problema: Cache usando LocMemCache
**Solução:** REDIS_URL não configurada ou incorreta

#### Problema: Celery não conecta
**Solução:** Verificar se Worker e Beat services têm a mesma REDIS_URL

#### Problema: SMS não agenda
**Solução:** Verificar se Worker service está rodando e Redis conectado

### 7. 📱 Configuração do Twilio

Para enviar SMS reais, configure:

1. **Criar conta Twilio:** https://www.twilio.com/
2. **Obter credenciais:**
   - Account SID
   - Auth Token
   - Phone Number (comprar um número Twilio)
3. **Configurar variáveis:**
   ```env
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxx
   TWILIO_PHONE_NUMBER=+1234567890
   ```

### 8. 🎮 Teste Completo

```bash
# 1. Webhook TriboPay
curl -X POST https://your-app.onrender.com/api/webhooks/tribopay/ \
  -H "Content-Type: application/json" \
  -d '{
    "status": "waiting",
    "method": "pix",
    "customer": {"phone_number": "+5511999999999"},
    "transaction": {"id": "test123", "amount": 5000}
  }'

# 2. Verificar se SMS foi agendado
curl https://your-app.onrender.com/api/webhooks/events/

# 3. Teste manual de SMS (opcional)
curl -X POST https://your-app.onrender.com/api/webhooks/test-sms/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+5511999999999", "message": "Teste SMS"}'
```

### 9. 📊 Monitoramento

- **Logs:** Acompanhe os logs dos serviços no dashboard Render
- **Health Check:** Use o endpoint `/api/webhooks/health/` para monitoramento
- **Webhooks:** Monitore `/api/webhooks/events/` para ver eventos processados

---

## ⚠️ Pontos Importantes

1. **Redis é ESSENCIAL** para agendamento de SMS
2. **Todos os serviços** devem ter a mesma REDIS_URL
3. **Worker service** deve estar rodando para processar SMS
4. **Variáveis de ambiente** devem ser configuradas antes do deploy
5. **Twilio** é necessário apenas para envio real de SMS (pode testar sem)

Com essa configuração, seu sistema estará completamente funcional! 🎉
