from django.apps import AppConfig
from requirements import djdoorstop


class DoorstopConfig(AppConfig):
    name = 'requirements'

    def ready(self):
        from doorstop import core
        core.document.DOCUMENT_CLASS = djdoorstop.DjDocument
        core.item.ITEM_CLASS = djdoorstop.DjItem
