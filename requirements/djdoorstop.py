import os
import hashlib
from typing import Any, Dict, Optional

from doorstop import DoorstopError, Item
from doorstop.core.base import auto_load, auto_save
from doorstop.core.document import Document
from doorstop.core.types import to_bool
from doorstop import common, settings

log = common.logger(__name__)


class DjReference(object):
    def __init__(self, _path, _type, _item):
        #  type: (str, str, DjItem) -> None
        self._path = _path
        self._type = _type
        self._item = _item  # type: DjItem

    @property
    def path(self):
        return self._path

    @property
    def basename(self):
        return os.path.basename(self.path)

    @property
    def full_path(self):
        return os.path.join(self._item.document.path, self.path)
    
    @property
    def md5(self):
        return hashlib.md5(open(self.full_path, 'rb').read()).hexdigest().upper()

    @property
    def type(self):
        return self._type


class DjForeignField(object):
    def __init__(self, name, data=None):
        #  type: (str, Optional[Dict]) -> None
        self._item = None
        self._name = name
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

    @property
    def name(self):
        return self._name

    @property
    def data(self):
        return None if self._item is None else self.value(self._item)

    def value(self, item, sep=','):
        # type: (DjItem, str) -> str
        if self._type == 'string':
            return item.get(self._name)
        elif self._type == 'single':
            return item.get(self._name)


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

    @property
    def references_list(self):
        references = []
        if self.references is not None:
            for r in self.references:
                references.append(DjReference(r['path'], r['type'], self))
        return references


class DjDocument(Document):
    def __init__(self, path, root=os.getcwd(), **kwargs):
        #  type: (str, str, Any) -> None
        super().__init__(path, root, **kwargs)
        self._foreign_fields2 = {}  # type: Dict[DjForeignField]

    def _iter(self, reload=False):
        """Yield the document's items."""
        if self._itered and not reload:
            msg = "iterating document {}'s loaded items...".format(self)
            log.debug(msg)
            yield from list(self._items)
            return
        log.info("loading document {}'s items...".format(self))
        # Reload the document's item
        self._items = []
        filenames = []
        for filename in os.listdir(self.path):
            if os.path.isfile(os.path.join(self.path, filename)) and filename[-4:] == '.yml':
                filenames.append(filename)
        for filename in filenames:
            path = os.path.join(self.path, filename)
            try:
                item = Item.factory(self, path, root=self.root, tree=self.tree)
            except DoorstopError:
                pass  # skip non-item files
            else:
                self._items.append(item)
                if reload:
                    try:
                        item.load(reload=reload)
                    except Exception:
                        log.error("Unable to load: %s", item)
                        raise
                if settings.CACHE_ITEMS and self.tree:
                    self.tree._item_cache[item.uid] = item  # pylint: disable=protected-access
                    log.trace("cached item: {}".format(item))
        # Set meta attributes
        self._itered = True
        # Yield items
        yield from list(self._items)

    def load(self, reload=False):
        loaded = self._loaded
        super().load(reload)
        if loaded and not reload:
            return
        data = self._load_with_include(self.config)
        attributes = data.get('attributes', {})
        foreign_fields = attributes.get('foreign-fields', {})
        for key, value in foreign_fields.items():
            self._foreign_fields2[key] = DjForeignField(key, value)

    def save(self):
        super().save()

    @property
    def foreign_fields2(self):
        #  type: () -> Dict[DjForeignField]
        return self._foreign_fields2
