from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Returns the current URL query string with updated parameters.
    If a parameter is passed as empty string or None, it is removed from query string.
    Example:
      {% url_replace category=cat.slug %}
      {% url_replace page=2 %}
      {% url_replace brand='' %}
    """
    request = context.get('request')
    if not request:
        query_dict = {}
    else:
        query_dict = request.GET.copy()

    for key, value in kwargs.items():
        if value is None or value == '':
            query_dict.pop(key, None)
        else:
            query_dict[key] = str(value)

    # When changing a filter (not page), reset page to 1 if present
    if any(k != 'page' for k in kwargs.keys()) and 'page' not in kwargs:
        query_dict.pop('page', None)

    encoded = query_dict.urlencode()
    return f"?{encoded}" if encoded else "?"
