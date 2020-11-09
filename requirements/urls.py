from django.urls import path
from .views import IndexView, ItemDetailView, ItemUpdateView, DocumentUpdateView, ItemActionView, ItemRawFileView, DocumentExportView, \
    VersionControlView, FullGraphView, GrpahDataView, DocumentActionView, DocumentSourceView, FileDownloadView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('<slug:doc>', IndexView.as_view(), name='index-doc'),
    path('<slug:doc>/media/<path:file>', FileDownloadView.as_view(), name='index-media'),
    path('graph/<slug:doc>', FullGraphView.as_view(), name='graph'),
    path('graph/data/<slug:doc>', GrpahDataView.as_view(), name='graph-data'),
    path('item/details/<slug:doc>/<slug:item>', ItemDetailView.as_view(), name='item-details'),
    path('item/details/<slug:doc>/media/<path:file>', FileDownloadView.as_view(), name='doc-media'),
    path('item/update/<slug:doc>/<slug:item>', ItemUpdateView.as_view(), name='item-update'),
    path('item/update/<slug:doc>/<slug:item>/<slug:from>', ItemUpdateView.as_view(), name='item-update-from'),
    path('item/rawfile/<slug:doc>/<slug:item>', ItemRawFileView.as_view(), name='item-rawfile'),
    path('item/delete/<slug:doc>/<slug:item>', ItemDetailView.as_view(), name='item-delete'),
    path('item/review/<slug:doc>/<slug:item>/<slug:action>', ItemActionView.as_view(), name='item-action'),
    path('item/action/<slug:doc>/<slug:item>/<slug:action>/<slug:where>', ItemActionView.as_view(), name='item-action-return'),
    path('item/review/<slug:doc>/<slug:item>/<slug:action>/<slug:target>', ItemActionView.as_view(), name='item-action-target'),
    path('item/closecomm/<slug:doc>/<slug:item>/<slug:action>/<int:index>', ItemActionView.as_view(), name='item-close-comment'),
    path('item/update/<slug:doc>', DocumentUpdateView.as_view(), name='document-update'),
    path('item/export/<slug:doc>', DocumentExportView.as_view(), name='document-export'),
    path('doc/action/<slug:doc>/<slug:action>', DocumentActionView.as_view(), name='document-action'),
    path('doc/source/<slug:doc>', DocumentSourceView.as_view(), name='document-source'),
    path('vcs/', VersionControlView.as_view(), name='version_control'),
    path('vcs/action/<slug:action>', VersionControlView.as_view(), name='vcs-action'),
]
