from products.models import Category
from accounts.models import Notification

def site_context(request):
    categories = Category.objects.all().order_by('name')
    unread_count = 0
    recent_notifications = []
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        recent_notifications = Notification.objects.filter(user=request.user)[:5]
    return {
        'site_name': 'N-IT HOME',
        'site_tagline': 'Premium PC Hardware & Components',
        'currency_symbol': '$',
        'nav_categories': categories,
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
    }
