from typing import Any
from django.http import HttpRequest
from .cart import Cart

# Context processor exposing current shopping cart instance to all templates
def cart(request: HttpRequest) -> dict[str, Any]:
    return {'cart': Cart(request)}
