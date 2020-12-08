import os
from typing import Any, Dict, Optional

from doorstop import DoorstopError, Item
from doorstop.core.base import auto_load, auto_save
from doorstop.core.document import Document
from doorstop.core.types import to_bool


class DjForeignField(object):
    def __init__(self, data=None):
        #  type: (Optional[Dict]) -> None
        self._type = 'string'
        self._description = ''
        self._choices = {}

        if data is not None:
            for key, value in data.items():
                if key == 'type':
                    self._type = value
                elif key == 'description':
                    self._description = value
                elif key == 'choices':
                    self._choices = value
                else:
                    raise DoorstopError("unexpected attributes configuration '{}' in: {}".format(key, data))


class DjItem(Item):
    DEFAULT_DELETED = False
    DEFAULT_PENDING = False

    def __init__(self, document, path, root=os.getcwd(), **kwargs):
        #  type: (Document, str, str, Any) -> None
        super().__init__(document, path, root, **kwargs)
        self._data['deleted'] = DjItem.DEFAULT_DELETED
        self._data['pending'] = DjItem.DEFAULT_PENDING

    def _set_attributes(self, attributes):
        removed_keys = []
        for key, value in attributes.items():
            if key == 'deleted':
                self._data[key] = to_bool(value)
            elif key == 'pending':
                self._data[key] = to_bool(value)
            else:
                value = None
            if value is not None:
                removed_keys.append(key)
        for key in removed_keys:
            del attributes[key]
        super()._set_attributes(attributes)

    @property  # type: ignore
    @auto_load
    def deleted(self):
        """Get the item's deleted status.

        A deleted item will not be exported in documents. Delted items are
        intended to be used for:

        - temporarily disabled requirements or removed requirements

        """
        return self._data['deleted']

    @deleted.setter  # type: ignore
    @auto_save
    def deleted(self, value):
        """Set the item's active status."""
        self._data['deleted'] = to_bool(value)

    @property  # type: ignore
    @auto_load
    def pending(self):
        """Get the item's pending status.

        A pending item is a wokr in progress item
        intended to be used for:

        - hilights if requisute is need more works and reviews

        """
        return self._data['pending']

    @pending.setter  # type: ignore
    @auto_save
    def pending(self, value):
        """Set the item's active status."""
        self._data['pending'] = to_bool(value)


class DjDocument(Document):
    def __init__(self, path, root=os.getcwd(), **kwargs):
        #  type: (str, str, Any) -> None
        super().__init__(path, root, **kwargs)
        self._foreign_fields = {}  # type: Dict[DjForeignField]

    def load(self, reload=False):
        loaded = self._loaded
        super().load(reload)
        if loaded and not reload:
            return
        data = self._load_with_include(self.config)
        foreign_fields = data.get('foreign_fields', {})
        for key, value in foreign_fields.items():
            self._foreign_fields[key] = DjForeignField(value)

    def save(self):
        super().save()

    @property
    def foreign_fields(self):
        #  type: () -> Dict[DjForeignField]
        return self._foreign_fields
