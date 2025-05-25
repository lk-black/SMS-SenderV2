# 📚 Documentação Completa da API SMS-Sender

## 🌐 Base URL
```
https://sms-senderv2.onrender.com/api/webhooks/
```

---

## 📋 Índice

- [🔍 Status e Monitoramento](#-status-e-monitoramento)
- [📨 Webhooks de Pagamento](#-webhooks-de-pagamento)
- [💬 SMS e Mensagens](#-sms-e-mensagens)
- [🔧 Administração e Debug](#-administração-e-debug)
- [📊 Relatórios e Auditoria](#-relatórios-e-auditoria)
- [🧪 Testes e Desenvolvimento](#-testes-e-desenvolvimento)

---

## 🔍 Status e Monitoramento

### GET `/health/`
**Status de saúde do sistema**

Verifica se todos os serviços estão funcionando.

```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/health/"
```

**Resposta:**
```json
{
  "status": "healthy",
  "timestamp": "2025-05-25T19:11:23.340982+00:00",
  "database": "connected",
  "cache": "connected",
  "sms_scheduler": {
    "redis_available": true,
    "celery_available": true
  },
  "processing_time_ms": 15.08
}
```

### GET `/sms-scheduler-status/`
**Status do agendador de SMS**

Verifica o status específico do sistema de agendamento.

```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/sms-scheduler-status/"
```

### GET `/twilio-config-check/`
**Verificação das configurações Twilio**

Verifica se as credenciais do Twilio estão configuradas.

```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/twilio-config-check/"
```

---

## 📨 Webhooks de Pagamento

### POST `/ghostpay/`
**Webhook principal da GhostPay** ⭐

Endpoint para receber notificações de pagamento da GhostPay.

```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/ghostpay/" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "1234567890",
    "status": "PENDING",
    "payment_method": "PIX",
    "amount": 50.00,
    "customer": {
      "name": "João Silva",
      "phone": "+5511999999999"
    }
  }'
```

### POST `/tribopay/`
**Webhook principal da TriboPay**

Endpoint para receber notificações de pagamento da TriboPay.

```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/tribopay/" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "id": "1234567890",
      "status": "waiting_payment",
      "payment_method": "pix",
      "amount": 50.00
    },
    "customer": {
      "name": "João Silva",
      "phone": "+5511999999999"
    }
  }'
```

---

## 💬 SMS e Mensagens

### POST `/test-sms/`
**Teste de envio de SMS**

Envia um SMS de teste para verificar a funcionalidade.

```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/test-sms/" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+5511999999999",
    "customer_name": "João Silva",
    "amount": 50.00
  }'
```

### POST `/test-immediate-sms/`
**Teste de SMS agendado** ⭐

Cria um webhook de teste e agenda um SMS para 1 minuto.

```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/test-immediate-sms/" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Resposta:**
```json
{
  "status": "success",
  "message": "SMS agendado para 1 minuto (teste imediato)",
  "webhook_id": 1,
  "payment_id": "immediate_test_1748200148",
  "task_id": "4051b6ac-40e1-4b42-b076-253ed3aec6ca",
  "countdown_seconds": 60
}
```

### POST `/force-process-pending-sms/`
**Processamento manual de SMS** ⭐

Força o envio imediato de todos os SMS pendentes.

```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/force-process-pending-sms/" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Resposta:**
```json
{
  "status": "success",
  "message": "Processamento forçado concluído",
  "processed_webhooks": 1,
  "sms_sent": 1,
  "sms_blocked": 0
}
```

### GET `/pending-sms/`
**Lista de SMS pendentes**

Lista todos os SMS que estão agendados para envio.

```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/pending-sms/"
```

---

## 🔧 Administração e Debug

### POST `/force-migrate/`
**Migração forçada do banco** ⭐

Executa as migrações do banco de dados.

```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/force-migrate/" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### GET `/debug/`
**Debug do banco de dados**

Verifica o status das tabelas e conexão com o banco.

```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/debug/"
```

### POST `/test-celery-task/`
**Teste de conectividade Celery** ⭐

Testa se os workers Celery estão funcionando.

```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/test-celery-task/" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Resposta:**
```json
{
  "status": "success",
  "message": "Task Celery enviada para execução",
  "task_id": "d1120e0d-7c10-4b3d-9d26-e52c71deffef",
  "task_state": "PENDING",
  "info": "Verificar logs do worker para confirmação"
}
```

---

## 📊 Relatórios e Auditoria

### GET `/events/`
**Lista de eventos de webhook**

Lista todos os webhooks recebidos.

```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/events/"
```

**Filtros disponíveis:**
- `?payment_method=pix` - Filtrar por método de pagamento
- `?payment_status=waiting_payment` - Filtrar por status
- `?processed=true` - Filtrar por processados

### GET `/events/{id}/`
**Detalhes de um evento específico**

Obtém detalhes de um webhook específico.

```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/events/1/"
```

### GET `/sms-logs/`
**Lista de logs de SMS**

Lista todos os SMS enviados com seus status.

```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/sms-logs/"
```

**Filtros disponíveis:**
- `?status=sent` - Filtrar por status (sent/failed)
- `?webhook_event=1` - Filtrar por evento específico

### GET `/sms-logs/{id}/`
**Detalhes de um log específico**

Obtém detalhes de um SMS específico.

```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/sms-logs/1/"
```

---

## 🧪 Testes e Desenvolvimento

### POST `/ghostpay-test/`
**Teste de formato GhostPay**

Testa o formato de webhook sem salvar no banco.

```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/ghostpay-test/" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test123",
    "status": "PENDING",
    "payment_method": "PIX"
  }'
```

### POST `/ghostpay-debug/`
**Debug de webhook GhostPay**

Captura dados brutos do webhook para análise.

```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/ghostpay-debug/" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### POST `/tribopay-test/`
**Teste de formato TriboPay**

Testa o formato de webhook da TriboPay.

```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/tribopay-test/" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### POST `/test-phone-formatting/`
**Teste de formatação de telefone**

Testa a formatação de números de telefone.

```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/test-phone-formatting/" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "11999999999"
  }'
```

---

## 🚀 Fluxo Completo do Sistema

### 1. **Recebimento de Webhook**
```
Payment Gateway → /ghostpay/ ou /tribopay/ → Webhook processado
```

### 2. **Agendamento de SMS**
```
Webhook PIX/PENDING → SMS agendado para 10 minutos → Celery Task
```

### 3. **Envio de SMS**
```
Celery Worker → Twilio API → SMS enviado → Log gravado
```

### 4. **Monitoramento**
```
/health/ → Status geral
/sms-logs/ → Histórico de envios
/events/ → Histórico de webhooks
```

---

## 🔐 Autenticação

**Todos os endpoints são públicos** para facilitar a integração com gateways de pagamento. Em produção, considere implementar:

- Verificação de IP de origem
- Assinatura de webhook
- Rate limiting

---

## 📱 Exemplo de Uso Completo

### 1. Verificar saúde do sistema
```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/health/"
```

### 2. Simular webhook de pagamento
```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/ghostpay/" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "pay_123456",
    "status": "PENDING",
    "payment_method": "PIX",
    "amount": 100.00,
    "customer": {
      "name": "João Silva",
      "phone": "+5511999999999"
    }
  }'
```

### 3. Verificar eventos criados
```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/events/"
```

### 4. Forçar processamento de SMS (se necessário)
```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/force-process-pending-sms/"
```

### 5. Verificar logs de SMS
```bash
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/sms-logs/"
```

---

## 💡 Dicas Importantes

1. **⭐ Endpoints principais** estão marcados com estrela
2. **Webhooks PIX** acionam SMS automático em 10 minutos
3. **Force migrate** deve ser executado após deploy
4. **Health check** deve ser usado para monitoramento
5. **Test endpoints** são seguros para desenvolvimento

---

## 🆘 Solução de Problemas

### SMS não enviados?
1. Verificar `/health/` - sistema saudável?
2. Verificar `/twilio-config-check/` - credenciais OK?
3. Executar `/force-process-pending-sms/` - processamento manual
4. Verificar `/sms-logs/` - logs de erro

### Webhooks não funcionando?
1. Testar com `/ghostpay-test/` ou `/tribopay-test/`
2. Verificar `/debug/` - banco funcionando?
3. Executar `/force-migrate/` se necessário

### Workers Celery não funcionando?
1. Testar `/test-celery-task/`
2. Usar `/force-process-pending-sms/` como alternativa
3. Verificar logs no dashboard do Render.com

---

**📧 Sistema SMS-Sender v2.0 - Desenvolvido para recuperação automática de pagamentos PIX**
