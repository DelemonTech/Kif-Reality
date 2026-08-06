# main/utils.py
from django.http import JsonResponse as DjangoJsonResponse

def utf8_json_response(data, **kwargs):
    """Helper to return JsonResponse with proper UTF-8 encoding"""
    kwargs.setdefault('json_dumps_params', {})
    kwargs['json_dumps_params']['ensure_ascii'] = False
    return DjangoJsonResponse(data, **kwargs)