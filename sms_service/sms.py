import logging
from decimal import Decimal
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from django.conf import settings

logger = logging.getLogger(__name__)

# Importar utilitários de logging estruturado
try:
    from webhooks.logging_utils import sms_structured_logger
except ImportError:
    # Fallback se não conseguir importar
    sms_structured_logger = None


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
            # Formatar número para padrão internacional
            formatted_phone = self.format_phone_for_twilio(phone_number)
            
            # Log da formatação do telefone
            if sms_structured_logger:
                sms_structured_logger.log_phone_formatting(phone_number, formatted_phone, True)
            
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
                to=formatted_phone
            )
            
            # Log estruturado do sucesso
            if sms_structured_logger:
                sms_structured_logger.log_sms_attempt(
                    phone=phone_number,
                    message_type="recovery",
                    success=True,
                    sid=message_obj.sid,
                    formatted_phone=formatted_phone
                )
            
            logger.info(f"SMS enviado com sucesso para {formatted_phone} (original: {phone_number}). SID: {message_obj.sid}")
            return True, message_obj.sid, None
            
        except TwilioException as e:
            error_msg = f"Erro Twilio: {str(e)}"
            
            # Log estruturado do erro
            if sms_structured_logger:
                sms_structured_logger.log_sms_attempt(
                    phone=phone_number,
                    message_type="recovery",
                    success=False,
                    error=error_msg
                )
            
            logger.error(f"Falha ao enviar SMS para {phone_number}: {error_msg}")
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Erro geral: {str(e)}"
            
            # Log estruturado do erro
            if sms_structured_logger:
                sms_structured_logger.log_sms_attempt(
                    phone=phone_number,
                    message_type="recovery",
                    success=False,
                    error=error_msg
                )
            
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
            # Formatar número para padrão internacional
            formatted_phone = self.format_phone_for_twilio(phone_number)
            
            # Log da formatação do telefone
            if sms_structured_logger:
                sms_structured_logger.log_phone_formatting(phone_number, formatted_phone, True)
            
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_phone,
                to=formatted_phone
            )
            
            # Log estruturado do sucesso
            if sms_structured_logger:
                sms_structured_logger.log_sms_attempt(
                    phone=phone_number,
                    message_type="custom",
                    success=True,
                    sid=message_obj.sid,
                    formatted_phone=formatted_phone
                )
            
            logger.info(f"SMS personalizado enviado para {formatted_phone} (original: {phone_number}). SID: {message_obj.sid}")
            return True, message_obj.sid, None
            
        except TwilioException as e:
            error_msg = f"Erro Twilio: {str(e)}"
            
            # Log estruturado do erro
            if sms_structured_logger:
                sms_structured_logger.log_sms_attempt(
                    phone=phone_number,
                    message_type="custom",
                    success=False,
                    error=error_msg
                )
            
            logger.error(f"Falha ao enviar SMS personalizado para {phone_number}: {error_msg}")
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Erro geral: {str(e)}"
            
            # Log estruturado do erro
            if sms_structured_logger:
                sms_structured_logger.log_sms_attempt(
                    phone=phone_number,
                    message_type="custom",
                    success=False,
                    error=error_msg
                )
            
            logger.error(f"Falha inesperada ao enviar SMS personalizado para {phone_number}: {error_msg}")
            return False, None, error_msg
    
    def _create_recovery_message(self, customer_name, amount_formatted):
        """
        Cria mensagem de recuperação personalizada
        """
        return f"""ATENÇAO {customer_name} , voce esta prestes a perder sua INDENIZACAO, Pague o imposto e resgate AGORA! https://encurtador.com.br/hevVF"""
    
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
    
    def format_phone_for_twilio(self, phone_number):
        """
        Formata número de telefone para o padrão internacional do Twilio
        
        Args:
            phone_number (str): Número do telefone
            
        Returns:
            str: Número formatado no padrão internacional (+55DDNNNNNNNNN)
        """
        # Se já está no formato internacional, retorna como está
        if phone_number.startswith('+'):
            return phone_number
        
        # Remover caracteres especiais
        clean_number = ''.join(filter(str.isdigit, phone_number))
        
        # Se tem 11 dígitos (formato brasileiro), adicionar +55
        if len(clean_number) == 11:
            return f"+55{clean_number}"
        
        # Se tem 10 dígitos (formato brasileiro sem 9), adicionar +55 e o 9
        if len(clean_number) == 10:
            # Assumir que é celular e adicionar o 9
            ddd = clean_number[:2]
            numero = clean_number[2:]
            return f"+55{ddd}9{numero}"
        
        # Para outros formatos, retornar como está (pode ser internacional sem +)
        return phone_number
