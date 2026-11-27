from django.urls import path

from . import views

urlpatterns = [
    path('chatbot', views.chatbot, name='chatbot'),
    path('get_openai_answer', views.get_openai_answer, name='get_openai_answer'),
]
