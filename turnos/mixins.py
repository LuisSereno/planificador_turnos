"""
Custom mixins for views
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse


class SuperuserRequiredMixin(UserPassesTestMixin):
    """Mixin que requiere que el usuario sea superusuario"""

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(self.request, 'No tienes permisos para acceder a esta página.')
        return redirect('turnos:dashboard')


class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin que requiere que el usuario sea staff"""

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, 'No tienes permisos para acceder a esta página.')
        return redirect('turnos:dashboard')


class OwnerRequiredMixin(UserPassesTestMixin):
    """Mixin que verifica que el usuario sea el propietario del objeto"""

    owner_field = 'creado_por'

    def test_func(self):
        obj = self.get_object()
        return (
                self.request.user.is_superuser or
                getattr(obj, self.owner_field, None) == self.request.user
        )

    def handle_no_permission(self):
        messages.error(self.request, 'No tienes permisos para modificar este objeto.')
        return redirect('turnos:dashboard')


class AjaxRequiredMixin:
    """Mixin que requiere que la petición sea AJAX"""

    def dispatch(self, request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Esta vista solo acepta peticiones AJAX'}, status=400)
        return super().dispatch(request, *args, **kwargs)


class JSONResponseMixin:
    """Mixin para retornar respuestas JSON"""

    def render_to_json_response(self, context, **response_kwargs):
        """Renderiza el contexto como JSON"""
        return JsonResponse(self.get_data(context), **response_kwargs)

    def get_data(self, context):
        """Convierte el contexto a un dict serializable"""
        return context


class FormMessageMixin:
    """Mixin para añadir mensajes automáticos en formularios"""

    success_message = 'Operación realizada con éxito.'
    error_message = 'Ha ocurrido un error. Por favor, revisa los campos.'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        messages.error(self.request, self.error_message)
        return response


class PaginationMixin:
    """Mixin para paginación personalizada"""

    paginate_by = 20
    paginate_orphans = 3

    def get_paginate_by(self, queryset):
        """Permite personalizar el número de elementos por página desde GET"""
        per_page = self.request.GET.get('per_page')
        if per_page and per_page.isdigit():
            return min(int(per_page), 100)  # Máximo 100
        return self.paginate_by


class SearchMixin:
    """Mixin para añadir funcionalidad de búsqueda"""

    search_fields = []
    search_param = 'q'

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get(self.search_param)

        if search_query and self.search_fields:
            from django.db.models import Q

            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f'{field}__icontains': search_query})

            queryset = queryset.filter(q_objects)

        return queryset


class FilterMixin:
    """Mixin para añadir funcionalidad de filtrado"""

    filter_fields = {}

    def get_queryset(self):
        queryset = super().get_queryset()

        for param, field in self.filter_fields.items():
            value = self.request.GET.get(param)
            if value:
                queryset = queryset.filter(**{field: value})

        return queryset


class ExportMixin:
    """Mixin para exportar datos"""

    def export_to_csv(self, queryset, filename='export.csv'):
        """Exporta el queryset a CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # Escribir headers
        if queryset.exists():
            fields = [f.name for f in queryset.model._meta.fields]
            writer.writerow(fields)

            # Escribir datos
            for obj in queryset:
                writer.writerow([getattr(obj, f) for f in fields])

        return response

    def export_to_excel(self, queryset, filename='export.xlsx'):
        """Exporta el queryset a Excel"""
        from openpyxl import Workbook
        from django.http import HttpResponse

        wb = Workbook()
        ws = wb.active

        # Escribir headers
        if queryset.exists():
            fields = [f.name for f in queryset.model._meta.fields]
            ws.append(fields)

            # Escribir datos
            for obj in queryset:
                ws.append([getattr(obj, f) for f in fields])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)

        return response


class BreadcrumbMixin:
    """Mixin para añadir breadcrumbs al contexto"""

    breadcrumbs = []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = self.get_breadcrumbs()
        return context

    def get_breadcrumbs(self):
        """Retorna la lista de breadcrumbs"""
        return self.breadcrumbs


class TitleMixin:
    """Mixin para añadir título a la página"""

    title = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.get_title()
        return context

    def get_title(self):
        """Retorna el título de la página"""
        return self.title or ''


class ActiveMenuMixin:
    """Mixin para marcar el menú activo"""

    active_menu = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_menu'] = self.active_menu
        return context
