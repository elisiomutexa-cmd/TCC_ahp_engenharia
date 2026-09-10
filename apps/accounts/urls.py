from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("entrar/", views.AppLoginView.as_view(), name="login"),
    path("sair/", views.AppLogoutView.as_view(), name="logout"),
    path("perfil/", views.ProfileView.as_view(), name="profile"),
    path("palavra-passe/", views.AppPasswordChangeView.as_view(), name="password_change"),
    path("recuperar/", views.AppPasswordResetView.as_view(), name="password_reset"),
    path("recuperar/enviado/", views.AppPasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "recuperar/<uidb64>/<token>/",
        views.AppPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "recuperar/concluido/",
        views.AppPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("utilizadores/", views.UserListView.as_view(), name="users"),
    path("utilizadores/novo/", views.UserCreateView.as_view(), name="user_create"),
    path("utilizadores/<int:pk>/editar/", views.UserUpdateView.as_view(), name="user_update"),
]
