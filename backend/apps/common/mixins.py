"""
Reusable mixins for Django REST Framework viewsets.
"""
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator
from django.db.models import Q


class PaginationMixin:
    """Mixin for custom pagination."""
    
    def paginate_queryset(self, queryset, page_size=20):
        """
        Paginate queryset.
        
        Args:
            queryset: queryset to paginate
            page_size: number of items per page
        
        Returns:
            paginated queryset
        """
        page = self.request.query_params.get('page', 1)
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        return {
            'results': page_obj.object_list,
            'count': paginator.count,
            'page': page,
            'pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }


class FilterMixin:
    """Mixin for filtering querysets."""
    
    def get_filtered_queryset(self, queryset, filters=None):
        """
        Apply filters to queryset.
        
        Args:
            queryset: queryset to filter
            filters: dict of filters to apply
        
        Returns:
            filtered queryset
        """
        if filters is None:
            filters = {}
        
        for key, value in filters.items():
            if value is not None and value != '':
                if '__' in key:
                    # Support for related field lookups
                    queryset = queryset.filter(**{key: value})
                else:
                    queryset = queryset.filter(**{key: value})
        
        return queryset


class SearchMixin:
    """Mixin for search functionality."""
    
    search_fields = []
    
    def get_search_queryset(self, queryset, search_term=None):
        """
        Apply search to queryset.
        
        Args:
            queryset: queryset to search
            search_term: search term
        
        Returns:
            searched queryset
        """
        if not search_term or not self.search_fields:
            return queryset
        
        search_query = Q()
        for field in self.search_fields:
            search_query |= Q(**{f"{field}__icontains": search_term})
        
        return queryset.filter(search_query)


class OrderingMixin:
    """Mixin for ordering querysets."""
    
    ordering_fields = []
    default_ordering = ['-created_at']
    
    def get_ordered_queryset(self, queryset):
        """
        Apply ordering to queryset.
        
        Args:
            queryset: queryset to order
        
        Returns:
            ordered queryset
        """
        ordering = self.request.query_params.get('ordering', None)
        
        if ordering:
            # Validate ordering field
            ordering_fields = ordering.lstrip('-').split(',')
            valid_ordering = []
            for field in ordering_fields:
                field = field.strip()
                if field in self.ordering_fields or f"-{field}" in self.ordering_fields:
                    valid_ordering.append(ordering if ',' not in ordering else field)
            
            if valid_ordering:
                return queryset.order_by(*valid_ordering)
        
        return queryset.order_by(*self.default_ordering)


class StandardResponseMixin:
    """Mixin for standardizing API responses."""
    
    def success_response(self, data=None, message='Success', status_code=status.HTTP_200_OK):
        """
        Return success response.
        
        Args:
            data: response data
            message: success message
            status_code: HTTP status code
        
        Returns:
            Response object
        """
        response_data = {
            'success': True,
            'message': message,
        }
        if data is not None:
            response_data['data'] = data
        
        return Response(response_data, status=status_code)
    
    def error_response(self, message='Error', errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        """
        Return error response.
        
        Args:
            message: error message
            errors: error details
            status_code: HTTP status code
        
        Returns:
            Response object
        """
        response_data = {
            'success': False,
            'message': message,
        }
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data, status=status_code)

