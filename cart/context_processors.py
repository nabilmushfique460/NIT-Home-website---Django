from .cart import Cart

def cart(request):
    """Provides the Cart object to all templates."""
    return {'cart': Cart(request)}
