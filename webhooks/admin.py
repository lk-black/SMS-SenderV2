from django.contrib import admin
from .models import WebhookEvent, SMSLog


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    """Admin interface para WebhookEvent"""
    
    list_display = [
        'webhook_hash_short', 'payment_method', 'payment_status', 
        'amount_in_real', 'customer_phone', 'customer_name',
        'processed', 'sms_scheduled', 'webhook_received_at'
    ]
    
    list_filter = [
        'payment_method', 'payment_status', 'processed', 
        'sms_scheduled', 'webhook_received_at'
    ]
    
    search_fields = [
        'payment_id', 'customer_phone', 'customer_name', 
        'customer_email', 'webhook_hash'
    ]
    
    readonly_fields = [
        'webhook_hash', 'webhook_received_at', 'amount_in_real',
        'payment_created_at', 'payment_updated_at'
    ]
    
    fieldsets = (
        ('Identificação', {
            'fields': ('webhook_hash', 'payment_id')
        }),
        ('Dados do Pagamento', {
            'fields': ('payment_method', 'payment_status', 'amount', 'amount_in_real',
                      'payment_created_at', 'payment_updated_at')
        }),
        ('Dados do Cliente', {
            'fields': ('customer_phone', 'customer_name', 'customer_email')
        }),
        ('Status de Processamento', {
            'fields': ('processed', 'sms_scheduled', 'webhook_received_at')
        }),
        ('Dados Brutos', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        })
    )
    
    ordering = ['-webhook_received_at']
    
    actions = ['mark_as_processed', 'resend_recovery_sms']
    
    def webhook_hash_short(self, obj):
        """Exibe hash abreviado"""
        return obj.webhook_hash[:8] + '...'
    webhook_hash_short.short_description = 'Hash'
    
    def mark_as_processed(self, request, queryset):
        """Marcar webhooks como processados"""
        updated = queryset.update(processed=True)
        self.message_user(request, f'{updated} webhook(s) marcado(s) como processado(s).')
    mark_as_processed.short_description = 'Marcar como processado'
    
    def resend_recovery_sms(self, request, queryset):
        """Reenviar SMS de recuperação"""
        from .tasks import schedule_sms_recovery
        
        count = 0
        for webhook in queryset.filter(payment_method='pix', payment_status='waiting_payment'):
            schedule_sms_recovery.delay(webhook.id)
            count += 1
        
        self.message_user(request, f'{count} SMS(s) de recuperação agendado(s).')
    resend_recovery_sms.short_description = 'Reenviar SMS de recuperação'


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    """Admin interface para SMSLog"""
    
    list_display = [
        'id', 'webhook_event_id', 'phone_number', 'status',
        'twilio_sid_short', 'sent_at', 'price'
    ]
    
    list_filter = ['status', 'sent_at', 'delivered_at']
    
    search_fields = [
        'phone_number', 'twilio_sid', 'webhook_event__payment_id',
        'webhook_event__customer_name'
    ]
    
    readonly_fields = ['sent_at', 'delivered_at']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('webhook_event', 'phone_number', 'message')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Twilio', {
            'fields': ('twilio_sid', 'price', 'price_unit')
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'delivered_at')
        })
    )
    
    ordering = ['-sent_at']
    
    def twilio_sid_short(self, obj):
        """Exibe SID abreviado"""
        if obj.twilio_sid:
            return obj.twilio_sid[:10] + '...'
        return '-'
    twilio_sid_short.short_description = 'Twilio SID'
    
    def webhook_event_id(self, obj):
        """ID do webhook relacionado"""
        return obj.webhook_event.id
    webhook_event_id.short_description = 'Webhook ID'
