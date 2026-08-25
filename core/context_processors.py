from products.models import Category

def site_context(request):
    categories = Category.objects.all().order_by('name')
    return {'site_name': 'N-IT Home', 'site_tagline': 'Premium PC Hardware & Components', 'currency_symbol': '$', 'nav_categories': categories}
