from django.core.exceptions import RequestDataTooBig
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import GenerateSerializer, ModifySerializer
from .services import generate
from .services.validator import GeometryError
from .services.llm_client import ProviderError, ProviderTimeout

class GenerateView(APIView):
    serializer_class = GenerateSerializer

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            return Response(generate(serializer.validated_data))
        except RequestDataTooBig:
            return Response({'error':'Request body too large.'}, status=413)
        except ProviderTimeout as exc:
            return Response({'error':str(exc)}, status=504)
        except ProviderError as exc:
            return Response({'error':str(exc)}, status=502)
        except GeometryError as exc:
            return Response({'error':str(exc)}, status=422)

class ModifyView(GenerateView):
    serializer_class = ModifySerializer
