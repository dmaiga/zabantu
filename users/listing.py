from django.core.paginator import Paginator


def paginate(request, queryset, per_page=20):
    """Pagine `queryset` selon ?page=. Renvoie (page, querystring sans « page ») pour garder les filtres dans les liens."""
    page_obj = Paginator(queryset, per_page).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return page_obj, params.urlencode()
