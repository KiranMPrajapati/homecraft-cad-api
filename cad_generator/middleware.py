from django.http import JsonResponse
from django.conf import settings
from django.core.exceptions import RequestDataTooBig

class BodyLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):
            try:
                if len(request.body) > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
                    raise RequestDataTooBig
            except RequestDataTooBig:
                return JsonResponse({'error':'Request body too large.'}, status=413)
        return self.get_response(request)
