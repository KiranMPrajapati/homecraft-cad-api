from django.urls import path
from cad_generator.views import GenerateView, ModifyView

app_name = 'cad_generator'
urlpatterns = [
    path('generate-floorplan/', GenerateView.as_view(), name='generate-floorplan'),
    path('modify-floorplan/', ModifyView.as_view(), name='modify-floorplan'),
]
