from django.urls import path, include, re_path
from django.contrib import admin
from . import views
from django.contrib.auth import views as auth_views
from webserver.views import CustomLoginView, profile, check_username_status
from webserver.forms import LoginForm

app_name = 'webserver'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'), 
    path('plants', views.show_plants, name='plant_server'),
    path('weather', views.weather_conditions),
    path('price', views.price_graph, name='price'),
    path('newplant', views.create_plant_form),
    path('auth/ticket/<int:plant_id>/', views.get_ticket),
    path('admin/action/del/user/<int:user_id>/', views.admin_delete_user),
    path('admin/action/del/plant/<int:plant_id>/', views.admin_delete_plant), 
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(redirect_authenticated_user=True, template_name='webserver/login.html',
                                           authentication_form=LoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        template_name='webserver/logout.html'), name='logout'),
    re_path(r'^oauth/', include('social_django.urls', namespace='social')),
    path('profile/', profile, name='profile'),
    path('users/', views.check_username_status, name = 'users'),
]
