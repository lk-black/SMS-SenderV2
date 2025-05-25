# 🚀 Guia Rápido - API SMS-Sender

## ⚡ Endpoints Essenciais

### 🔥 **Mais Utilizados**

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/health/` | GET | ✅ Status do sistema |
| `/ghostpay/` | POST | 📨 Webhook GhostPay |
| `/force-process-pending-sms/` | POST | 🔄 Forçar envio SMS |
| `/test-immediate-sms/` | POST | ⚡ Teste rápido SMS |

### 📋 **Comandos Rápidos**

```bash
# Base URL
BASE_URL="https://sms-senderv2.onrender.com/api/webhooks"

# Verificar saúde
curl "$BASE_URL/health/"

# Teste de SMS (1 minuto)
curl -X POST "$BASE_URL/test-immediate-sms/" -H "Content-Type: application/json" -d '{}'

# Processar SMS pendentes
curl -X POST "$BASE_URL/force-process-pending-sms/" -H "Content-Type: application/json" -d '{}'

# Webhook GhostPay
curl -X POST "$BASE_URL/ghostpay/" \
  -H "Content-Type: application/json" \
  -d '{"id":"test123","status":"PENDING","payment_method":"PIX","amount":50.00,"customer":{"name":"João","phone":"+5511999999999"}}'
```

---

## 🔄 **Fluxo de Teste Completo**

### 1️⃣ **Verificar Sistema**
```bash
curl https://sms-senderv2.onrender.com/api/webhooks/health/
```
✅ Deve retornar `"status": "healthy"`

### 2️⃣ **Criar Webhook de Teste**
```bash
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/test-immediate-sms/ \
  -H "Content-Type: application/json" -d '{}'
```
✅ Deve retornar task_id e countdown_seconds: 60

### 3️⃣ **Aguardar 1 Minuto**
```bash
sleep 70
```

### 4️⃣ **Processar SMS Pendentes**
```bash
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/force-process-pending-sms/ \
  -H "Content-Type: application/json" -d '{}'
```
✅ Deve retornar `"sms_sent": 1`

---

## 📊 **Status Codes**

| Code | Status | Significado |
|------|--------|-------------|
| 200 | ✅ OK | Sucesso |
| 400 | ❌ Bad Request | Dados inválidos |
| 500 | 🔥 Server Error | Erro interno |

---

## 🚨 **Troubleshooting Rápido**

### ❌ **SMS não enviado?**
```bash
# 1. Verificar saúde
curl https://sms-senderv2.onrender.com/api/webhooks/health/

# 2. Forçar processamento
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/force-process-pending-sms/ \
  -H "Content-Type: application/json" -d '{}'

# 3. Verificar logs
curl https://sms-senderv2.onrender.com/api/webhooks/sms-logs/
```

### ❌ **Webhook não funciona?**
```bash
# 1. Testar formato
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/ghostpay-test/ \
  -H "Content-Type: application/json" -d '{"id":"test","status":"PENDING"}'

# 2. Verificar banco
curl https://sms-senderv2.onrender.com/api/webhooks/debug/

# 3. Migrar se necessário
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/force-migrate/ \
  -H "Content-Type: application/json" -d '{}'
```

---

## 🎯 **Payload Examples**

### **GhostPay Webhook**
```json
{
  "id": "pay_123456789",
  "status": "PENDING",
  "payment_method": "PIX",
  "amount": 100.50,
  "customer": {
    "name": "João Silva",
    "phone": "+5511999999999",
    "email": "joao@email.com"
  },
  "created_at": "2025-05-25T19:00:00Z"
}
```

### **TriboPay Webhook**
```json
{
  "transaction": {
    "id": "trans_123456789",
    "status": "waiting_payment",
    "payment_method": "pix",
    "amount": 100.50
  },
  "customer": {
    "name": "João Silva",
    "phone": "+5511999999999"
  }
}
```

---

## 🔧 **Monitoramento**

### **Métricas Importantes**
```bash
# Status geral
curl https://sms-senderv2.onrender.com/api/webhooks/health/

# SMS pendentes
curl https://sms-senderv2.onrender.com/api/webhooks/pending-sms/

# Últimos eventos
curl https://sms-senderv2.onrender.com/api/webhooks/events/

# Logs de SMS
curl https://sms-senderv2.onrender.com/api/webhooks/sms-logs/
```

---

## 🎨 **Response Examples**

### ✅ **Sucesso**
```json
{
  "status": "success",
  "message": "SMS enviado com sucesso",
  "sms_sent": 1
}
```

### ❌ **Erro**
```json
{
  "status": "error",
  "message": "Erro ao enviar SMS",
  "error_details": "Phone number invalid"
}
```

### 📊 **Health Check**
```json
{
  "status": "healthy",
  "database": "connected",
  "cache": "connected",
  "sms_scheduler": {
    "redis_available": true,
    "celery_available": true
  }
}
```

---

## 🏃‍♂️ **Quick Start (30 segundos)**

```bash
# 1. Teste o sistema
curl https://sms-senderv2.onrender.com/api/webhooks/health/

# 2. Envie um webhook teste
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/test-immediate-sms/ \
  -H "Content-Type: application/json" -d '{}'

# 3. Aguarde 1 minuto e processe
sleep 70 && curl -X POST https://sms-senderv2.onrender.com/api/webhooks/force-process-pending-sms/ \
  -H "Content-Type: application/json" -d '{}'
```

**🎉 Se retornar `"sms_sent": 1`, o sistema está 100% funcional!**

---

**💡 Tip:** Salve este guia para referência rápida durante desenvolvimento e produção.
