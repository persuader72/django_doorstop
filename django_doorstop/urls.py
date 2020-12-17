from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('a/', admin.site.urls),
    path('r/', include('requirements.urls')),
    path('d/', include('documents.urls')),
    path('l/', include('stracklic.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', RedirectView.as_view(url='/r'), name='index')
]
