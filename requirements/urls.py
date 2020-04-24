from django.urls import path
from .views import IndexView, ItemDetailView, ItemUpdateView, DocumentUpdateView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('<slug:doc>', IndexView.as_view(), name='index-doc'),
    path('item/details/<slug:doc>/<slug:item>', ItemDetailView.as_view(), name='item-details'),
    path('item/update/<slug:doc>/<slug:item>', ItemUpdateView.as_view(), name='item-update'),
    path('item/delete/<slug:doc>/<slug:item>', ItemDetailView.as_view(), name='item-delete'),
    path('item/review/<slug:doc>/<slug:item>', ItemDetailView.as_view(), name='item-review'),
    path('item/update/<slug:doc>', DocumentUpdateView.as_view(), name='document-update'),
]
