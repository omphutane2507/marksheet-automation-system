from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from marks import views as marks_views

urlpatterns = [
    # path('admin/', admin.site.urls),  # Disabled — use your app's own admin panel instead
    path('login/',    auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/',   auth_views.LogoutView.as_view(), name='logout'),
    path('register/', marks_views.register_view, name='register'),
    path('', include('marks.urls')),
]
