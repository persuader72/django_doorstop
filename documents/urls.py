from django.urls import path
from .views import IndexView

urlpatterns = [
    path('', IndexView.as_view(), name='docgen-index'),
    path('reqblock/<slug:md5>', IndexView.as_view(), name='docgen-blockid'),
]