from django.urls import path
from spotify import views

urlpatterns = [
    path("", views.login, name='login'),
    path("home", views.home, name='home'),
    path("login_validate", views.login_validate, name="login_validate"),
    path("sign_up", views.sign_up, name="sign_up"),
    path("sign_up_email", views.sign_up_email, name="sign_up_email"),
    path("sign_up_form", views.sign_up_form, name="sign_up_form"),
    path("save_sign_up", views.save_sign_up, name="save_sign_up"),
    path("reset_password", views.reset_password, name="reset_password"),
    path("reset_password_submission", views.reset_password_submission, name="reset_password_submission"),
    path("dashboard", views.dashboard, name="dashboard"),
    path("chatbot", views.chatbot, name="chatbot"),
    path("get_openai_answer", views.get_openai_answer, name="get_openai_answer"),
    path("download_app", views.download_app, name="download_app"),
    path("notification", views.notification, name="notification"),
    path("like_song", views.like_song, name="like_song"),
    path("your_library", views.your_library, name="your_library"),
    path("logout", views.logout, name="logout"),
]