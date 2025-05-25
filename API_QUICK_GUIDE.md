# 🚀 API SMS Recovery - Guia Rápido

**URL Base**: `https://sms-senderv2.onrender.com/api/webhooks/`

## 📋 Endpoints Principais

### 🔍 Health Check
```bash
GET /health/
# Verifica se o serviço está funcionando
```

### 📞 Webhook TriboPay (Principal)
```bash
POST /tribopay/
Content-Type: application/json

# Payload esperado:
{
  "status": "waiting",           # waiting, paid, cancelled
  "method": "pix",              # pix, credit_card, boleto
  "customer": {
    "name": "João Silva",
    "phone_number": "+5511999999999"
  },
  "transaction": {
    "id": "trx_123",
    "amount": 5000              # valor em centavos (R$ 50,00)
  }
}

# ✅ PIX + waiting = Agenda SMS em 10min
# ❌ Outros casos = Apenas registra
```

### 🧪 Teste de Formato
```bash
POST /tribopay-test/
# Valida formato sem salvar no banco
# Retorna se agendaria SMS ou não
```

### 📊 Monitoramento
```bash
GET /events/                    # Lista webhooks processados
GET /events/?payment_method=pix # Filtrar só PIX
GET /sms-logs/                  # Lista SMS enviados
GET /debug/                     # Status do banco de dados
```

### 📱 Teste SMS
```bash
POST /test-sms/
{
  "phone_number": "+5511999999999",
  "message": "Teste SMS"
}
```

## 🎯 Lógica do Sistema

```
Webhook TriboPay → Validação → PIX + Waiting?
                                    ↓ SIM
                              Agenda SMS (10min)
                                    ↓
                              Celery + Twilio
                                    ↓
                              SMS Enviado + Log
```

## ⚙️ Configuração TriboPay

Configure o webhook na TriboPay para:
```
https://sms-senderv2.onrender.com/api/webhooks/tribopay/
```

## 🔧 Variáveis de Ambiente (Twilio)

```bash
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token  
TWILIO_PHONE_NUMBER=your_number
```

## 📝 Exemplo Prático

```bash
# Testar PIX aguardando (deve retornar would_schedule_sms: true)
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/tribopay-test/ \
  -H "Content-Type: application/json" \
  -d '{
    "status": "waiting",
    "method": "pix", 
    "customer": {"name": "Teste", "phone_number": "+5511999999999"},
    "transaction": {"id": "test", "amount": 5000}
  }'

# Resultado esperado:
# "is_pix_waiting": true
# "would_schedule_sms": true
```

## 🎖️ Status da API

✅ **Serviço Online**: https://sms-senderv2.onrender.com/  
✅ **Formato TriboPay**: Validado e funcionando  
✅ **Detecção PIX**: Funcionando corretamente  
✅ **Banco de Dados**: Configurado e migrações aplicadas  
⚙️ **SMS**: Requer configuração Twilio para produção  

---
*Sistema pronto para produção - configure apenas as credenciais Twilio*
