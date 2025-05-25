import logging
from decimal import Decimal
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from django.conf import settings

logger = logging.getLogger(__name__)


class TwilioSMSService:
    """
    Serviço para envio de SMS via Twilio
    """
    
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_phone = settings.TWILIO_PHONE_NUMBER
    
    def send_recovery_sms(self, phone_number, customer_name="Cliente", amount=None):
        """
        Envia SMS de recuperação de venda
        
        Args:
            phone_number (str): Número do telefone do cliente
            customer_name (str): Nome do cliente
            amount (int): Valor em centavos
            
        Returns:
            tuple: (success: bool, message_sid: str, error: str)
        """
        try:
            # Formatar valor se fornecido
            amount_formatted = ""
            if amount:
                amount_decimal = Decimal(amount) / 100
                amount_formatted = f"de R$ {amount_decimal:.2f} "
            
            # Criar mensagem personalizada
            message = self._create_recovery_message(customer_name, amount_formatted)
            
            # Enviar SMS
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_phone,
                to=phone_number
            )
            
            logger.info(f"SMS enviado com sucesso para {phone_number}. SID: {message_obj.sid}")
            return True, message_obj.sid, None
            
        except TwilioException as e:
            error_msg = f"Erro Twilio: {str(e)}"
            logger.error(f"Falha ao enviar SMS para {phone_number}: {error_msg}")
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Erro geral: {str(e)}"
            logger.error(f"Falha inesperada ao enviar SMS para {phone_number}: {error_msg}")
            return False, None, error_msg
    
    def send_custom_sms(self, phone_number, message):
        """
        Envia SMS personalizado
        
        Args:
            phone_number (str): Número do telefone
            message (str): Mensagem a ser enviada
            
        Returns:
            tuple: (success: bool, message_sid: str, error: str)
        """
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_phone,
                to=phone_number
            )
            
            logger.info(f"SMS personalizado enviado para {phone_number}. SID: {message_obj.sid}")
            return True, message_obj.sid, None
            
        except TwilioException as e:
            error_msg = f"Erro Twilio: {str(e)}"
            logger.error(f"Falha ao enviar SMS personalizado para {phone_number}: {error_msg}")
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Erro geral: {str(e)}"
            logger.error(f"Falha inesperada ao enviar SMS personalizado para {phone_number}: {error_msg}")
            return False, None, error_msg
    
    def _create_recovery_message(self, customer_name, amount_formatted):
        """
        Cria mensagem de recuperação personalizada
        """
        return f"""Olá {customer_name}! 

Seu pagamento {amount_formatted}ainda está pendente. 

Para não perder sua compra, finalize o pagamento via PIX agora mesmo!

Se já pagou, ignore esta mensagem.

Dúvidas? Entre em contato conosco."""
    
    def validate_phone_number(self, phone_number):
        """
        Valida formato do número de telefone
        
        Args:
            phone_number (str): Número a ser validado
            
        Returns:
            bool: True se válido
        """
        # Remover caracteres especiais
        clean_number = ''.join(filter(str.isdigit, phone_number))
        
        # Verificar se tem formato brasileiro válido
        if len(clean_number) == 11 and clean_number.startswith(('11', '12', '13', '14', '15', '16', '17', '18', '19', '21', '22', '24', '27', '28', '31', '32', '33', '34', '35', '37', '38', '41', '42', '43', '44', '45', '46', '47', '48', '49', '51', '53', '54', '55', '61', '62', '63', '64', '65', '66', '67', '68', '69', '71', '73', '74', '75', '77', '79', '81', '82', '83', '84', '85', '86', '87', '88', '89', '91', '92', '93', '94', '95', '96', '97', '98', '99')):
            return True
        
        # Verificar se tem formato internacional válido (começando com +)
        if phone_number.startswith('+') and len(clean_number) >= 10:
            return True
            
        return False
