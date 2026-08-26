from django import template
from django.template.context import RequestContext

register = template.Library()

# Template tag returning updated URL query string while preserving existing filter parameters
@register.simple_tag(takes_context=True)
def url_replace(context: RequestContext, **kwargs) -> str:
    request = context.get('request')
    if not request:
        query_dict = {}
    else:
        query_dict = request.GET.copy()

    # Update or remove specified URL parameters
    for key, value in kwargs.items():
        if value is None or value == '':
            query_dict.pop(key, None)
        else:
            query_dict[key] = str(value)

    # When changing a filter, reset pagination page to 1
    if any(k != 'page' for k in kwargs.keys()) and 'page' not in kwargs:
        query_dict.pop('page', None)

    encoded = query_dict.urlencode()
    return f"?{encoded}" if encoded else "?"
