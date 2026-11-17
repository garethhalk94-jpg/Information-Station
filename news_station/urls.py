"""
URL routes for news_station.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("articles/<int:pk>/", views.article_detail, name="article_detail"),
    path("articles/new/", views.create_article, name="create_article"),
    path("articles/<int:pk>/edit/", views.edit_article, name="edit_article"),
    path(
        "articles/<int:pk>/delete/",
        views.delete_article,
        name="delete_article"
    ),
    path("my_articles/", views.my_articles, name="my_articles"),
]
