from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('r/', include('requirements.urls')),
    path('admin/', admin.site.urls),
]
