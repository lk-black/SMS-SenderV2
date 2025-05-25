import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from webhooks.models import WebhookEvent
from sms_service.sms import TwilioSMSService


class Command(BaseCommand):
    """
    Command para testar o sistema de SMS de recuperação
    """
    help = 'Testa o sistema de envio de SMS de recuperação'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            help='Número de telefone para teste (ex: +5511999999999)',
            required=True
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Nome do cliente para teste',
            default='Cliente Teste'
        )
        parser.add_argument(
            '--amount',
            type=int,
            help='Valor em centavos para teste',
            default=5000
        )
        parser.add_argument(
            '--create-webhook',
            action='store_true',
            help='Criar webhook de teste no banco'
        )

    def handle(self, *args, **options):
        phone = options['phone']
        name = options['name']
        amount = options['amount']
        create_webhook = options['create_webhook']

        self.stdout.write(self.style.SUCCESS('=== TESTE DO SISTEMA SMS RECOVERY ==='))
        
        # Testar serviço SMS
        self.stdout.write('\n1. Testando serviço SMS...')
        sms_service = TwilioSMSService()
        
        # Validar número
        if not sms_service.validate_phone_number(phone):
            self.stdout.write(
                self.style.ERROR(f'❌ Número de telefone inválido: {phone}')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Número válido: {phone}')
        )
        
        # Enviar SMS de teste
        self.stdout.write('\n2. Enviando SMS de recuperação...')
        try:
            success, message_sid, error = sms_service.send_recovery_sms(
                phone_number=phone,
                customer_name=name,
                amount=amount
            )
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ SMS enviado com sucesso!')
                )
                self.stdout.write(f'   SID: {message_sid}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Falha ao enviar SMS: {error}')
                )
                return
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro ao testar SMS: {str(e)}')
            )
            self.stdout.write(
                self.style.WARNING('💡 Verifique se as credenciais do Twilio estão configuradas no .env')
            )
            return
        
        # Criar webhook de teste se solicitado
        if create_webhook:
            self.stdout.write('\n3. Criando webhook de teste...')
            
            webhook_data = {
                "id": f"test_payment_{int(timezone.now().timestamp())}",
                "payment_method": "pix",
                "payment_status": "waiting_payment",
                "amount": amount,
                "created_at": timezone.now().isoformat(),
                "updated_at": timezone.now().isoformat(),
                "customer": {
                    "phone_number": phone,
                    "name": name,
                    "email": "teste@email.com"
                }
            }
            
            webhook_event = WebhookEvent.objects.create(
                payment_id=webhook_data["id"],
                payment_method=webhook_data["payment_method"],
                payment_status=webhook_data["payment_status"],
                amount=webhook_data["amount"],
                customer_phone=phone,
                customer_name=name,
                customer_email="teste@email.com",
                payment_created_at=timezone.now(),
                payment_updated_at=timezone.now(),
                raw_data=webhook_data
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Webhook criado: {webhook_event.id}')
            )
            self.stdout.write(f'   Hash: {webhook_event.webhook_hash[:8]}')
        
        # Resumo
        self.stdout.write('\n=== RESUMO DO TESTE ===')
        self.stdout.write(f'📱 Telefone: {phone}')
        self.stdout.write(f'👤 Nome: {name}')
        self.stdout.write(f'💰 Valor: R$ {amount/100:.2f}')
        if 'success' in locals() and success:
            self.stdout.write(f'📨 Status SMS: ✅ Enviado (SID: {message_sid})')
        else:
            self.stdout.write(f'📨 Status SMS: ❌ Falhou')
        
        self.stdout.write('\n✅ Teste concluído!')
