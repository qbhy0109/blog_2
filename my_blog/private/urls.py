from django.urls import path
from . import views


# 正在部署应用名称
app_name = 'private'

urlpatterns = [
    path('article-list/', views.article_list, name='article_list'),
]