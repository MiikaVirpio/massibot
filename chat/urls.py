from django.urls import path

from . import views

app_name = "chat"
urlpatterns = [
    path("", views.index, name="index"),
    path("send_message", views.send_message, name="send-message"),
    path("reset_thread", views.reset_thread, name="reset-thread"),
    path("get_summary", views.get_summary, name="get-summary"),
    path("get_memories", views.get_memories, name="get-memories"),
]