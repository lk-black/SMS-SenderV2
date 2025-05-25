# 📚 SMS-Sender - Índice da Documentação

## 🎯 Sistema de Recuperação de Pagamentos PIX via SMS

Bem-vindo à documentação completa do SMS-Sender! Este sistema automatiza o envio de SMS de recuperação para pagamentos PIX pendentes.

---

## 📖 Guias Disponíveis

### 🚀 **Para Começar Rapidamente**
| Documento | Descrição | Quando Usar |
|-----------|-----------|-------------|
| [🚀 Guia Rápido](./API_QUICK_REFERENCE.md) | Comandos essenciais e endpoints principais | Desenvolvimento e testes rápidos |
| [📋 Documentação Completa](./API_COMPLETE_DOCUMENTATION.md) | Todos os endpoints detalhados com exemplos | Referência completa da API |

### 💻 **Para Desenvolvimento**
| Documento | Descrição | Quando Usar |
|-----------|-----------|-------------|
| [🛠️ Exemplos Práticos](./API_PRACTICAL_EXAMPLES.md) | Códigos em Python, JavaScript, cURL, etc. | Integração e automação |
| [📋 API Documentation](./API_DOCUMENTATION.md) | Documentação técnica original | Referência técnica detalhada |

### 🚀 **Para Deploy e Produção**
| Documento | Descrição | Quando Usar |
|-----------|-----------|-------------|
| [📋 Deploy Guide](./DEPLOY_GUIDE.md) | Guia completo de deploy | Deploy inicial |
| [📋 Deploy Summary](./DEPLOY_SUMMARY.md) | Resumo do deploy | Verificação rápida |
| [📋 Auto Migration Guide](./AUTO_MIGRATION_GUIDE.md) | Sistema de migração automática | Troubleshooting DB |

### ⚙️ **Para Configuração**
| Documento | Descrição | Quando Usar |
|-----------|-----------|-------------|
| [📋 Redis Configuration](./REDIS_CONFIGURATION_GUIDE.md) | Configuração do Redis | Setup do cache |
| [📋 Render Redis Setup](./RENDER_REDIS_SETUP.md) | Redis específico do Render | Deploy no Render |

---

## 🎯 **Por Onde Começar?**

### 👤 **Sou Desenvolvedor**
1. 🚀 **[Guia Rápido](./API_QUICK_REFERENCE.md)** - Para testar em 30 segundos
2. 🛠️ **[Exemplos Práticos](./API_PRACTICAL_EXAMPLES.md)** - Para integrar no seu código

### 🏢 **Sou Gestor/Product Owner**
1. 📋 **[Documentação Completa](./API_COMPLETE_DOCUMENTATION.md)** - Para entender todas as funcionalidades
2. 📋 **[Deploy Summary](./DEPLOY_SUMMARY.md)** - Para entender o status atual

### 🔧 **Sou DevOps/SysAdmin**
1. 📋 **[Deploy Guide](./DEPLOY_GUIDE.md)** - Para fazer deploy
2. 📋 **[Redis Configuration](./REDIS_CONFIGURATION_GUIDE.md)** - Para configurar infraestrutura

---

## 🌟 **Funcionalidades Principais**

### 📨 **Recebimento de Webhooks**
- ✅ **GhostPay** - Gateway principal
- ✅ **TriboPay** - Gateway secundário
- ✅ **Validação automática** de formato
- ✅ **Prevenção de duplicatas**

### 💬 **SMS Automático**
- ✅ **Agendamento inteligente** (10 minutos para PIX)
- ✅ **Twilio Integration** para envio
- ✅ **Anti-duplicata** avançado
- ✅ **Logs completos** de entrega

### 🔍 **Monitoramento**
- ✅ **Health checks** em tempo real
- ✅ **Dashboard de status**
- ✅ **Logs detalhados**
- ✅ **Relatórios de envio**

### 🛠️ **Administração**
- ✅ **Processamento manual** de SMS
- ✅ **Migração automática** do banco
- ✅ **Testes integrados**
- ✅ **Debug tools**

---

## ⚡ **Quick Start (30 segundos)**

### 1️⃣ **Teste o Sistema**
```bash
curl https://sms-senderv2.onrender.com/api/webhooks/health/
```

### 2️⃣ **Envie um SMS de Teste**
```bash
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/test-immediate-sms/ \
  -H "Content-Type: application/json" -d '{}'
```

### 3️⃣ **Processe SMS Pendentes**
```bash
sleep 70 && curl -X POST https://sms-senderv2.onrender.com/api/webhooks/force-process-pending-sms/ \
  -H "Content-Type: application/json" -d '{}'
```

**🎉 Se retornar `"sms_sent": 1`, está funcionando perfeitamente!**

---

## 🔗 **Links Úteis**

### 🌐 **Produção**
- **API Base:** https://sms-senderv2.onrender.com/api/webhooks/
- **Health Check:** https://sms-senderv2.onrender.com/api/webhooks/health/
- **Dashboard:** https://dashboard.render.com/web/srv-csp8l0i3esus73d8l7e0

### 📱 **Integração**
- **Webhook GhostPay:** `POST /ghostpay/`
- **Webhook TriboPay:** `POST /tribopay/`
- **Teste de SMS:** `POST /test-immediate-sms/`
- **Processamento Manual:** `POST /force-process-pending-sms/`

### 📊 **Monitoramento**
- **Status Geral:** `GET /health/`
- **SMS Logs:** `GET /sms-logs/`
- **Eventos:** `GET /events/`
- **SMS Pendentes:** `GET /pending-sms/`

---

## 🆘 **Precisa de Ajuda?**

### 🔍 **Problemas Comuns**
1. **SMS não enviado?** → [Guia Rápido - Troubleshooting](./API_QUICK_REFERENCE.md#-troubleshooting-rápido)
2. **Webhook não funciona?** → [Exemplos Práticos](./API_PRACTICAL_EXAMPLES.md)
3. **Deploy com erro?** → [Deploy Guide](./DEPLOY_GUIDE.md)
4. **Redis não conecta?** → [Redis Configuration](./REDIS_CONFIGURATION_GUIDE.md)

### 📧 **Contato**
Para suporte técnico, consulte os logs detalhados em cada guia ou verifique o dashboard do Render.com.

---

**🚀 Sistema SMS-Sender v2.0 - Recuperação automática de pagamentos PIX**

*Documentação atualizada em: Maio 2025*
