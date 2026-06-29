"""
Analytics views for admin dashboard.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.core.cache import cache
from apps.common.cache import CacheKeys
from datetime import timedelta, datetime

from apps.analytics.services import AnalyticsService
from apps.users.permissions import IsAdminUser


class AnalyticsViewSet(viewsets.ViewSet):
    """Analytics endpoints for admin dashboard"""
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard overview metrics"""
        # Get date range from query params
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        end_date = timezone.now()
        
        # Try to get from cache
        cache_key = CacheKeys.analytics_summary({'days': days})
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return Response(cached_result)
        
        financial = AnalyticsService.get_financial_metrics(start_date, end_date)
        users = AnalyticsService.get_user_metrics(start_date, end_date)
        lotteries = AnalyticsService.get_lottery_metrics(start_date, end_date)
        
        result = {
            'financial': financial,
            'users': users,
            'lotteries': lotteries,
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, result, 300)
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def financial(self, request):
        """Get financial metrics"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
            except:
                start_date = None
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
            except:
                end_date = None
        
        metrics = AnalyticsService.get_financial_metrics(start_date, end_date)
        return Response(metrics)
    
    @action(detail=False, methods=['get'])
    def users(self, request):
        """Get user metrics"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
            except:
                start_date = None
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
            except:
                end_date = None
        
        metrics = AnalyticsService.get_user_metrics(start_date, end_date)
        return Response(metrics)
    
    @action(detail=False, methods=['get'])
    def lotteries(self, request):
        """Get lottery metrics"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
            except:
                start_date = None
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
            except:
                end_date = None
        
        metrics = AnalyticsService.get_lottery_metrics(start_date, end_date)
        return Response(metrics)
    
    @action(detail=False, methods=['get'])
    def charts(self, request):
        """Get chart data"""
        metric_type = request.query_params.get('type', 'revenue')
        period = request.query_params.get('period', 'days')
        days = int(request.query_params.get('days', 30))
        
        chart_data = AnalyticsService.get_chart_data(metric_type, period, days)
        return Response({
            'type': metric_type,
            'data': chart_data
        })
    
    @action(detail=False, methods=['get'])
    def reports_financial(self, request):
        """Download financial report"""
        from apps.analytics.reports import ReportService
        from datetime import datetime
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        format_type = request.query_params.get('format', 'csv')
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        else:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
            except:
                start_date = timezone.now() - timedelta(days=30)
        
        if not end_date:
            end_date = timezone.now()
        else:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
            except:
                end_date = timezone.now()
        
        return ReportService.generate_financial_report(start_date, end_date, format_type)
    
    @action(detail=False, methods=['get'])
    def reports_users(self, request):
        """Download user report"""
        from apps.analytics.reports import ReportService
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        format_type = request.query_params.get('format', 'csv')
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        else:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
            except:
                start_date = timezone.now() - timedelta(days=30)
        
        if not end_date:
            end_date = timezone.now()
        else:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
            except:
                end_date = timezone.now()
        
        return ReportService.generate_user_report(start_date, end_date, format_type)
    
    @action(detail=False, methods=['get'])
    def reports_transactions(self, request):
        """Export transactions"""
        from apps.analytics.reports import ReportService
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        else:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
            except:
                start_date = timezone.now() - timedelta(days=30)
        
        if not end_date:
            end_date = timezone.now()
        else:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
            except:
                end_date = timezone.now()
        
        filters = {
            'type': request.query_params.get('type'),
            'status': request.query_params.get('status'),
        }
        
        return ReportService.export_transactions(start_date, end_date, filters)

