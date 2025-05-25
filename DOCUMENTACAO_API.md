# 📱 SMS Recovery API - Documentação Completa

**🌐 URL Base**: `https://sms-senderv2.onrender.com/api/webhooks/`

## 🎯 O que faz?

Sistema que recebe webhooks da TriboPay, detecta PIX pendentes e envia SMS de recuperação após 10 minutos.

**Fluxo**: TriboPay → Webhook → Sistema → Detecta PIX waiting → Agenda SMS → Envia após 10min

---

## 🚀 Endpoints Principais

### 1. 🔍 Health Check
```http
GET /health/
```
Verifica se o sistema está funcionando.

**Resposta**:
```json
{
  "status": "healthy",
  "database": "connected",
  "cache": "connected"
}
```

---

### 2. 📞 Webhook TriboPay (Principal)
```http
POST /tribopay/
Content-Type: application/json
```

**Payload Esperado**:
```json
{
  "status": "waiting",           // waiting, paid, cancelled
  "method": "pix",              // pix, credit_card, boleto  
  "customer": {
    "name": "João Silva",
    "phone_number": "17992666990"  // formato brasileiro
  },
  "transaction": {
    "id": "trx_123456",
    "amount": 5000               // centavos (R$ 50,00)
  }
}
```

**Comportamento**:
- ✅ **PIX + waiting** = Agenda SMS em 10 minutos
- ❌ **Outros casos** = Apenas registra

**Resposta**:
```json
{"status": "ok"}
```

---

### 2.2. 📞 Webhook GhostPay 
```http
POST /ghostpay/
Content-Type: application/json
```

**Payload Esperado**:
```json
{
  "paymentId": "txn_123456789",
  "status": "PENDING",
  "paymentMethod": "PIX",
  "totalValue": 5000,
  "customer": {
    "name": "João Silva",
    "phone": "+5517992666990"
  }
}
```

**Comportamento**:
- ✅ **PIX + PENDING** = Agenda SMS em 10 minutos
- ❌ **Outros casos** = Apenas registra

**Resposta**:
```json
{"status": "ok"}
```

---

### 3. 📊 Monitoramento

#### Listar Webhooks
```http
GET /events/
GET /events/?payment_method=pix
GET /events/?payment_status=waiting
```

#### Listar SMS Enviados
```http
GET /sms-logs/
GET /sms-logs/?status=sent
```

#### Status do Banco
```http
GET /debug/
```

---

### 4. 🧪 Testes

#### Teste de Formato (sem salvar)
```http
POST /tribopay-test/
Content-Type: application/json

{
  "status": "waiting",
  "method": "pix",
  "customer": {"name": "Teste", "phone_number": "11999999999"},
  "transaction": {"id": "test_001", "amount": 5000}
}
```

#### Teste de Formato GhostPay (sem salvar)
```http
POST /ghostpay-test/
Content-Type: application/json

{
  "paymentId": "txn_test_001",
  "status": "PENDING",
  "paymentMethod": "PIX",
  "totalValue": 5000,
  "customer": {"name": "Teste", "phone": "+5511999999999"}
}
```

#### Teste de SMS Manual
```http
POST /test-sms/
Content-Type: application/json

{
  "phone_number": "17992666990",
  "message": "Teste de SMS"
}
```

#### Teste de Formatação de Telefone
```http
POST /test-phone-formatting/
Content-Type: application/json

{
  "phone_number": "17992666990"
}
```

**Resposta**:
```json
{
  "original_phone": "17992666990",
  "formatted_phone": "+5517992666990",
  "is_valid": true,
  "formatting_applied": true
}
```

---

### 5. 🔧 Administração

#### Forçar Migração
```http
POST /force-migrate/
```

#### Status do Scheduler
```http
GET /sms-scheduler-status/
```

---

## 📱 Formatação de Telefone

O sistema formata automaticamente números brasileiros:

| Entrada | Saída | Descrição |
|---------|-------|-----------|
| `17992666990` | `+5517992666990` | 11 dígitos → +55 |
| `1199887766` | `+5511999887766` | 10 dígitos → +55 + 9 |
| `+5511987654321` | `+5511987654321` | Já formatado → sem alteração |

---

## 🎮 Exemplos de Uso

### Webhook PIX Pendente (Agenda SMS)
```bash
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/tribopay/ \
  -H "Content-Type: application/json" \
  -d '{
    "status": "waiting",
    "method": "pix",
    "customer": {
      "name": "João Silva",
      "phone_number": "17992666990"
    },
    "transaction": {
      "id": "pix_001",
      "amount": 5000
    }
  }'
```

### Cartão Pago (Apenas Registra)
```bash
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/tribopay/ \
  -H "Content-Type: application/json" \
  -d '{
    "status": "paid",
    "method": "credit_card",
    "customer": {
      "name": "Maria Santos",
      "phone_number": "11987654321"
    },
    "transaction": {
      "id": "cc_001",
      "amount": 10000
    }
  }'
```

### Verificar Eventos
```bash
curl https://sms-senderv2.onrender.com/api/webhooks/events/
```

### Testar Formatação
```bash
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/test-phone-formatting/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "17992666990"}'
```

---

## 📋 Respostas da API

### Sucesso Geral
```json
{"status": "ok"}
```

### Erro de Validação
```json
{
  "error": "Dados inválidos",
  "details": {
    "customer": ["Este campo é obrigatório"]
  }
}
```

### Erro do Twilio (SMS)
```json
{
  "status": "error",
  "error": "Erro Twilio: Authentication Error - invalid username",
  "phone_number": "17992666990"
}
```

---

## 🔐 Configuração Twilio (Produção)

Para enviar SMS reais, configure no painel da Render:

```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token  
TWILIO_PHONE_NUMBER=your_twilio_number
```

---

## 📊 Monitoramento

### URLs Úteis
- **Health Check**: https://sms-senderv2.onrender.com/api/webhooks/health/
- **Eventos**: https://sms-senderv2.onrender.com/api/webhooks/events/
- **SMS Logs**: https://sms-senderv2.onrender.com/api/webhooks/sms-logs/
- **Admin**: https://sms-senderv2.onrender.com/admin/ (requer login)

### Filtros Disponíveis
```http
GET /events/?payment_method=pix
GET /events/?payment_status=waiting
GET /events/?processed=true
GET /sms-logs/?status=sent
GET /sms-logs/?webhook_event=1
```

---

## 🏗️ Deploy e Configuração

### Deploy Automático
1. Fork do repositório
2. Conectar no Render
3. Usar o arquivo `render.yaml` (Blueprint)
4. Configurar variáveis Twilio

### Migração Manual
```bash
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/force-migrate/
```

---

## 🔍 Troubleshooting

### Problema: "no such table"
**Solução**: Execute migração via `/force-migrate/`

### Problema: SMS não envia (401 Twilio)
**Solução**: Configure credenciais Twilio no Render

### Problema: PIX não agenda SMS
**Solução**: Verifique se `status=waiting` e `method=pix`

### Problema: Número inválido
**Solução**: Use formato brasileiro (11 dígitos) ou internacional (+55...)

---

## 📈 Status do Sistema

**✅ Funcionando**: https://sms-senderv2.onrender.com/
- Database: Migrado e funcional
- Cache/Redis: Conectado
- Formatação de telefone: Implementada
- Webhook processing: Funcional
- SMS scheduling: Ativo (aguarda credenciais Twilio)

**🎯 Pronto para produção!** Basta configurar credenciais Twilio para envios reais.

---

*Documentação atualizada em: 25 de Maio de 2025*
