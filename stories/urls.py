from django.urls import path
from . import views

app_name = "stories"

urlpatterns = [
    path("s/<slug:code>/", views.play, name="play"),
    path("s/<slug:code>/restart/", views.restart, name="restart"),  # ✅ 新增
    path("choose/<int:choice_id>/", views.choose, name="choose"),
]

