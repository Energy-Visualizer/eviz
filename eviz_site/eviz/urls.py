from django.urls import path, re_path

from . import views

urlpatterns = [
    # main pages
    path('', views.index, name='home'),
    path("visualizer", views.visualizer, name="visualizer"),

    # auth related pages
    path('login/', views.user_login, name='login'),
    path('signup/', views.user_signup, name='signup'),
    path('logout/', views.user_logout, name='logout'),
    path('render_history/', views.render_history, name='render_history'),
    # misc pages
    path('about/', views.about, name='about'),
    path('data-info/', views.data_info, name="data-info"),
    re_path(r"static/css/([^(\.css)]*\.css)", views.handle_css_static),

    # service hooks
    path("plot", views.get_plot),
    path("data", views.get_data)
]