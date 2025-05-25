import json
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from .models import WebhookEvent, SMSLog
from .tasks import schedule_sms_recovery


class WebhookTestCase(TestCase):
    """Testes para o sistema de webhooks"""

    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse('webhooks:tribopay-webhook')
        
        self.sample_webhook_data = {
            "id": "payment_123",
            "payment_method": "pix",
            "payment_status": "waiting_payment",
            "amount": 5000,  # R$ 50,00 em centavos
            "created_at": "2025-05-24T10:00:00Z",
            "updated_at": "2025-05-24T10:00:00Z",
            "customer": {
                "phone_number": "+5511999999999",
                "name": "João Silva",
                "email": "joao@email.com"
            }
        }

    def test_receive_valid_webhook(self):
        """Testa recebimento de webhook válido"""
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(self.sample_webhook_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
        
        # Verifica se o webhook foi salvo
        webhook_event = WebhookEvent.objects.get(payment_id="payment_123")
        self.assertEqual(webhook_event.payment_method, "pix")
        self.assertEqual(webhook_event.payment_status, "waiting_payment")
        self.assertEqual(webhook_event.amount, 5000)
        self.assertEqual(webhook_event.customer_phone, "+5511999999999")

    def test_duplicate_webhook_ignored(self):
        """Testa se webhooks duplicados são ignorados"""
        # Primeiro webhook
        self.client.post(
            self.webhook_url,
            data=json.dumps(self.sample_webhook_data),
            content_type='application/json'
        )
        
        # Segundo webhook idêntico
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(self.sample_webhook_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        # Deve haver apenas um registro
        self.assertEqual(WebhookEvent.objects.count(), 1)

    def test_invalid_webhook_data(self):
        """Testa webhook com dados inválidos"""
        invalid_data = {
            "payment_method": "pix",
            # Faltando campos obrigatórios
        }
        
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('webhooks.tasks.schedule_sms_recovery.apply_async')
    def test_pix_schedules_sms(self, mock_task):
        """Testa se PIX aguardando pagamento agenda SMS"""
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(self.sample_webhook_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verifica se a task foi agendada
        mock_task.assert_called_once()
        args, kwargs = mock_task.call_args
        self.assertEqual(kwargs['countdown'], 600)  # 10 minutos

    @patch('sms_service.sms.TwilioSMSService.send_recovery_sms')
    def test_sms_recovery_task(self, mock_send_sms):
        """Testa a task de envio de SMS de recuperação"""
        # Mock do retorno do Twilio
        mock_send_sms.return_value = (True, "SM123456", None)
        
        # Criar webhook event
        webhook_event = WebhookEvent.objects.create(
            payment_id="payment_123",
            payment_method="pix",
            payment_status="waiting_payment",
            amount=5000,
            customer_phone="+5511999999999",
            customer_name="João Silva",
            raw_data=self.sample_webhook_data
        )
        
        # Executar task
        schedule_sms_recovery(webhook_event.id)
        
        # Verificar se SMS foi "enviado"
        mock_send_sms.assert_called_once_with(
            phone_number="+5511999999999",
            customer_name="João Silva",
            amount=5000
        )
        
        # Verificar se log foi criado
        sms_log = SMSLog.objects.get(webhook_event=webhook_event)
        self.assertEqual(sms_log.status, 'sent')
        self.assertEqual(sms_log.twilio_sid, "SM123456")


class SMSServiceTestCase(TestCase):
    """Testes para o serviço de SMS"""

    @patch('twilio.rest.Client')
    def test_send_recovery_sms_success(self, mock_client_class):
        """Testa envio bem-sucedido de SMS de recuperação"""
        # Mock do cliente Twilio
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value = mock_client
        
        from sms_service.sms import TwilioSMSService
        
        service = TwilioSMSService()
        success, message_sid, error = service.send_recovery_sms(
            phone_number="+5511999999999",
            customer_name="João Silva",
            amount=5000
        )
        
        self.assertTrue(success)
        self.assertEqual(message_sid, "SM123456")
        self.assertIsNone(error)

    def test_phone_number_validation(self):
        """Testa validação de números de telefone"""
        from sms_service.sms import TwilioSMSService
        
        service = TwilioSMSService()
        
        # Números válidos
        self.assertTrue(service.validate_phone_number("+5511999999999"))
        self.assertTrue(service.validate_phone_number("11999999999"))
        
        # Números inválidos
        self.assertFalse(service.validate_phone_number("123"))
        self.assertFalse(service.validate_phone_number("abc"))
        self.assertFalse(service.validate_phone_number(""))


class APITestCase(TestCase):
    """Testes para os endpoints da API"""

    def setUp(self):
        self.client = Client()
        
        # Criar dados de teste
        self.webhook_event = WebhookEvent.objects.create(
            payment_id="payment_test",
            payment_method="pix",
            payment_status="waiting_payment",
            amount=10000,
            customer_phone="+5511888888888",
            customer_name="Maria Santos",
            raw_data={"test": "data"}
        )
        
        self.sms_log = SMSLog.objects.create(
            webhook_event=self.webhook_event,
            phone_number="+5511888888888",
            message="SMS de teste",
            status="sent",
            twilio_sid="SM789012"
        )

    def test_webhook_events_list(self):
        """Testa listagem de eventos de webhook"""
        url = reverse('webhooks:webhook-events')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['payment_id'], "payment_test")

    def test_webhook_event_detail(self):
        """Testa detalhes de um evento específico"""
        url = reverse('webhooks:webhook-event-detail', args=[self.webhook_event.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['payment_id'], "payment_test")
        self.assertEqual(data['amount_in_real'], 100.0)

    def test_sms_logs_list(self):
        """Testa listagem de logs de SMS"""
        url = reverse('webhooks:sms-logs')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['twilio_sid'], "SM789012")

    @patch('sms_service.sms.TwilioSMSService.send_custom_sms')
    def test_test_sms_endpoint(self, mock_send_sms):
        """Testa endpoint de teste de SMS"""
        mock_send_sms.return_value = (True, "SM999999", None)
        
        url = reverse('webhooks:test-sms')
        data = {
            "phone_number": "+5511777777777",
            "message": "Mensagem de teste"
        }
        
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['message_sid'], "SM999999")
