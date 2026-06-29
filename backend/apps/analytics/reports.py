"""
Report generation service for admin exports.
"""
import csv
from io import StringIO
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta

from apps.analytics.services import AnalyticsService
from apps.transactions.models import Transaction
from apps.users.models import User
from apps.lotteries.models import Lottery


class ReportService:
    """Service for generating reports."""
    
    @staticmethod
    def generate_financial_report(start_date, end_date, format='csv'):
        """
        Generate financial report.
        
        Args:
            start_date: Start date
            end_date: End date
            format: Report format ('csv' or 'json')
            
        Returns:
            HttpResponse or dict
        """
        metrics = AnalyticsService.get_financial_metrics(start_date, end_date)
        
        if format == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            
            writer.writerow(['Financial Report'])
            writer.writerow(['Period', f"{start_date.date()} to {end_date.date()}"])
            writer.writerow([])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Revenue', metrics['revenue']])
            writer.writerow(['Deposits', metrics['deposits']])
            writer.writerow(['Withdrawals', metrics['withdrawals']])
            writer.writerow(['Prizes Awarded', metrics['prizes_awarded']])
            writer.writerow(['Net Revenue', metrics['net_revenue']])
            
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="financial_report_{start_date.date()}.csv"'
            return response
        
        return metrics
    
    @staticmethod
    def generate_user_report(start_date, end_date, format='csv'):
        """
        Generate user acquisition report.
        
        Args:
            start_date: Start date
            end_date: End date
            format: Report format ('csv' or 'json')
            
        Returns:
            HttpResponse or dict
        """
        metrics = AnalyticsService.get_user_metrics(start_date, end_date)
        
        if format == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            
            writer.writerow(['User Report'])
            writer.writerow(['Period', f"{start_date.date()} to {end_date.date()}"])
            writer.writerow([])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Total Users', metrics['total_users']])
            writer.writerow(['Active Users (30 days)', metrics['active_users']])
            writer.writerow(['New Registrations', metrics['new_registrations']])
            writer.writerow(['Users with Tickets', metrics['users_with_tickets']])
            
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="user_report_{start_date.date()}.csv"'
            return response
        
        return metrics
    
    @staticmethod
    def export_transactions(start_date, end_date, filters=None):
        """
        Export transaction data.
        
        Args:
            start_date: Start date
            end_date: End date
            filters: Additional filters dict
            
        Returns:
            HttpResponse with CSV
        """
        queryset = Transaction.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).select_related('user', 'lottery')
        
        if filters:
            if filters.get('type'):
                queryset = queryset.filter(type=filters['type'])
            if filters.get('status'):
                queryset = queryset.filter(status=filters['status'])
        
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Transaction ID', 'User', 'Type', 'Amount', 'Status', 'Description', 'Date'])
        
        for trans in queryset:
            writer.writerow([
                str(trans.id),
                trans.user.username,
                trans.type,
                str(trans.amount),
                trans.status,
                trans.description,
                trans.created_at.isoformat(),
            ])
        
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="transactions_{start_date.date()}.csv"'
        return response

