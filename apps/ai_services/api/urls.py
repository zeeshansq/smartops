from django.urls import path

from .views import AIGenerateView, AIStatusView

urlpatterns = [
    path('generate/', AIGenerateView.as_view(), name='ai-generate'),
    path('status/<str:task_id>/', AIStatusView.as_view(), name='ai-status'),
]
