from django.urls import include, path

urlpatterns = [path('api/', include('cad_generator.urls'))]
