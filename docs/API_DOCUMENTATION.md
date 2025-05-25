# 📋 SMS-Sender API Documentation

## 🌐 Base URL
```
https://sms-senderv2.onrender.com/api/webhooks/
```

---

## 📚 Documentação Completa

📖 **Guias Disponíveis:**
- [📋 Documentação Completa](./API_COMPLETE_DOCUMENTATION.md) - Todos os endpoints detalhados
- [🚀 Guia Rápido](./API_QUICK_REFERENCE.md) - Comandos essenciais
- [🛠️ Exemplos Práticos](./API_PRACTICAL_EXAMPLES.md) - Códigos em várias linguagens

---

## 🎯 Visão Geral

O SMS Recovery Service é uma API REST que processa webhooks da TriboPay e GhostPay, detecta pagamentos PIX pendentes e agenda SMS de recuperação após 10 minutos.

## 🔗 Endpoints

### 1. Health Check
**Endpoint**: `GET /health/`  
**Descrição**: Verifica o status do serviço  
**Autenticação**: Não requerida

**Exemplo de Resposta**:
```json
{
  "status": "healthy",
  "service": "SMS Sender",
  "database": "connected",
  "cache": "connected"
}
```

---

### 2. Webhook Principal TriboPay
**Endpoint**: `POST /tribopay/`  
**Descrição**: Endpoint principal para receber webhooks da TriboPay  
**Autenticação**: Não requerida  
**Content-Type**: `application/json`

**Exemplo de Payload**:
```json
{
  "token": "webhook_token_123",
  "event": "payment.created",
  "status": "waiting",
  "method": "pix",
  "created_at": "2024-01-15T10:30:00Z",
  "platform": "web",
  "customer": {
    "name": "João Silva",
    "email": "joao@example.com",
    "phone_number": "+5511999999999"
  },
  "transaction": {
    "id": "trx_123456789",
    "amount": 5000
  }
}
```

**Resposta de Sucesso**:
```json
{
  "status": "ok"
}
```

**Comportamento**:
- ✅ **PIX + Status "waiting"**: Agenda SMS após 10 minutos
- ❌ **Outros métodos/status**: Apenas registra, não agenda SMS

---

### 3. Teste de Formato TriboPay
**Endpoint**: `POST /tribopay-test/`  
**Descrição**: Valida formato TriboPay sem salvar no banco de dados  
**Autenticação**: Não requerida  
**Content-Type**: `application/json`

**Exemplo de Payload**:
```json
{
  "status": "waiting",
  "method": "pix",
  "customer": {
    "name": "João Silva",
    "phone_number": "+5511999999999"
  },
  "transaction": {
    "id": "trx_test_001",
    "amount": 7500
  }
}
```

**Resposta de Sucesso**:
```json
{
  "status": "success",
  "message": "Formato TriboPay validado com sucesso",
  "data": {
    "payment_id": "trx_test_001",
    "payment_method": "pix",
    "payment_status": "waiting",
    "amount": 7500,
    "amount_in_real": 75.0,
    "customer_phone": "+5511999999999",
    "customer_name": "João Silva",
    "is_pix_waiting": true,
    "would_schedule_sms": true
  }
}
```

---

### 4. Webhook Flexível
**Endpoint**: `POST /tribopay-flex/`  
**Descrição**: Endpoint flexível que aceita diferentes formatos de webhook  
**Autenticação**: Não requerida

**Resposta de Sucesso**:
```json
{
  "status": "ok",
  "id": 123
}
```

---

### 5. Lista de Eventos de Webhook
**Endpoint**: `GET /events/`  
**Descrição**: Lista todos os eventos de webhook processados  
**Autenticação**: Não requerida

**Parâmetros de Query** (opcionais):
- `payment_method`: Filtrar por método de pagamento (ex: `pix`, `credit_card`)
- `payment_status`: Filtrar por status (ex: `waiting`, `paid`)
- `processed`: Filtrar por processados (`true`/`false`)

**Exemplo de Resposta**:
```json
[
  {
    "id": 1,
    "webhook_hash": "abc123...",
    "payment_id": "trx_123456789",
    "payment_method": "pix",
    "payment_status": "waiting",
    "amount": 5000,
    "amount_in_real": 50.0,
    "customer_phone": "+5511999999999",
    "customer_name": "João Silva",
    "customer_email": "joao@example.com",
    "payment_created_at": "2024-01-15T10:30:00Z",
    "webhook_received_at": "2024-01-15T10:30:15Z",
    "processed": true,
    "sms_scheduled": true
  }
]
```

---

### 6. Detalhes de Evento de Webhook
**Endpoint**: `GET /events/{id}/`  
**Descrição**: Detalhes de um evento específico  
**Autenticação**: Não requerida

---

### 7. Lista de SMS Logs
**Endpoint**: `GET /sms-logs/`  
**Descrição**: Lista todos os SMS enviados  
**Autenticação**: Não requerida

**Parâmetros de Query** (opcionais):
- `status`: Filtrar por status do SMS
- `webhook_event`: Filtrar por ID do evento de webhook

**Exemplo de Resposta**:
```json
[
  {
    "id": 1,
    "webhook_event_id": 1,
    "phone_number": "+5511999999999",
    "message": "Seu PIX de R$ 50,00 ainda está pendente...",
    "twilio_sid": "SM123456789",
    "status": "delivered",
    "error_message": null,
    "sent_at": "2024-01-15T10:40:00Z",
    "delivered_at": "2024-01-15T10:40:05Z",
    "price": "0.075",
    "price_unit": "USD"
  }
]
```

---

### 8. Teste de SMS
**Endpoint**: `POST /test-sms/`  
**Descrição**: Testa envio de SMS via Twilio  
**Autenticação**: Não requerida  
**Content-Type**: `application/json`

**Exemplo de Payload**:
```json
{
  "phone_number": "+5511999999999",
  "message": "Teste de SMS do sistema"
}
```

**Resposta de Sucesso**:
```json
{
  "status": "success",
  "message_sid": "SM123456789",
  "phone_number": "+5511999999999",
  "message": "Teste de SMS do sistema"
}
```

---

### 9. Debug do Banco de Dados
**Endpoint**: `GET /debug/`  
**Descrição**: Verifica status das tabelas do banco de dados  
**Autenticação**: Não requerida

**Exemplo de Resposta**:
```json
{
  "status": "debug",
  "database": "connected",
  "tables": {
    "webhook_events": "Table exists, 5 records",
    "sms_logs": "Table exists, 3 records"
  }
}
```

---

### 10. Forçar Migração (Manual)
**Endpoint**: `POST /force-migrate/`  
**Descrição**: Executa migrações do banco de dados manualmente (backup - migrações são automáticas no deploy)  
**Autenticação**: Não requerida

**Resposta de Sucesso**:
```json
{
  "status": "success",
  "message": "Migrations executadas com sucesso",
  "output": "Operations to perform:\n  Apply all migrations..."
}
```

**Nota**: ⚠️ Este endpoint é para casos de emergência. As migrações são executadas automaticamente a cada deploy através do sistema de `release phase` do Render.

---

### 11. Debug Raw TriboPay
**Endpoint**: `POST /tribopay-debug/`  
**Descrição**: Captura dados brutos para debug  
**Autenticação**: Não requerida

**Resposta**: `OK` (200) ou `ERROR` (500)

---

## 🔄 Fluxo do Sistema

```
1. TriboPay → POST /tribopay/ (webhook)
2. Sistema valida formato e dados
3. Se PIX + status "waiting":
   ├── Salva evento no banco
   ├── Agenda SMS para 10 minutos
   └── Marca como processado
4. Celery executa SMS após delay
5. Twilio envia SMS
6. Log do SMS é salvo
```

## 📊 Status Codes

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso |
| 400 | Dados inválidos |
| 404 | Endpoint não encontrado |
| 500 | Erro interno do servidor |

## 🔧 Configuração

### Migração Automática 🔄
O sistema executa migrações automaticamente a cada deploy:
- **Build Phase**: Migrações básicas durante o build
- **Release Phase**: Verificação e aplicação com retry automático
- **Verificação**: Aguarda banco estar disponível antes de migrar
- **Logs**: Processo completo logado para debugging

### Variáveis de Ambiente (Twilio)
```bash
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_number
```

### Webhook TriboPay
Configure na TriboPay o endpoint:
```
https://sms-senderv2.onrender.com/api/webhooks/tribopay/
```

## 🧪 Exemplo de Teste Completo

```bash
# 1. Verificar saúde
curl https://sms-senderv2.onrender.com/api/webhooks/health/

# 2. Testar formato PIX (deve agendar SMS)
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/tribopay-test/ \
  -H "Content-Type: application/json" \
  -d '{
    "status": "waiting",
    "method": "pix",
    "customer": {"name": "Teste", "phone_number": "+5511999999999"},
    "transaction": {"id": "test_001", "amount": 5000}
  }'

# 3. Ver eventos processados
curl https://sms-senderv2.onrender.com/api/webhooks/events/

# 4. Ver logs de SMS
curl https://sms-senderv2.onrender.com/api/webhooks/sms-logs/
```

## ⚡ Características

- ✅ **Alta Disponibilidade**: Deployed on Render
- ✅ **Detecção Inteligente**: Apenas PIX + waiting status
- ✅ **Prevenção de Duplicatas**: Hash de webhook único
- ✅ **Monitoramento**: Endpoints de debug e health
- ✅ **Logs Completos**: Rastreamento de todos os SMS
- ✅ **Validação Robusta**: Formato TriboPay real
