##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
"""ZCatalog Findable class
"""

import warnings

from Acquisition import aq_base
from App.special_dtml import DTMLFile


class CatalogAware:
    """ This is a Mix-In class to make objects automaticly catalog and
    uncatalog themselves in Zope, and to provide some other basic
    attributes that are useful to catalog.  Note that if your class
    subclasses CatalogAware, it will only catalog itself when
    it is added or copied in Zope.  If you make changes to your own
    object, you are responsible for calling your object's index_object
    method. """

    meta_type='CatalogAware'
    default_catalog='Catalog'

    manage_editCatalogerForm=DTMLFile('dtml/editCatalogerForm', globals())

    def _warn_deprecated(self):
        warnings.warn('The Products.ZCatalog.CatalogPathAwareness module is '
                      'deprecated and will be removed in Zope 4. Please '
                      'use event subscribers for zope.lifecycle events to '
                      'automatically index and unindex your objects.',
                      DeprecationWarning, stacklevel=3)

    def manage_editCataloger(self, default, REQUEST=None):
        """ """
        self.default_catalog=default
        message = "Your changes have been saved"
        if REQUEST is not None:
            return self.manage_main(self, REQUEST, manage_tabs_message=message)

    def manage_afterAdd(self, item, container):
        self.index_object()
        for object in self.objectValues():
            try:
                s = object._p_changed
            except Exception:
                s = 0
            object.manage_afterAdd(item, container)
            if s is None:
                object._p_deactivate()

    def manage_afterClone(self, item):
        self.index_object()
        for object in self.objectValues():
            try:
                s = object._p_changed
            except Exception:
                s = 0
            object.manage_afterClone(item)
            if s is None:
                object._p_deactivate()

    def manage_beforeDelete(self, item, container):
        self.unindex_object()
        for object in self.objectValues():
            try:
                s = object._p_changed
            except Exception:
                s = 0
            object.manage_beforeDelete(item, container)
            if s is None:
                object._p_deactivate()

    def creator(self):
        """Return a sequence of user names who have the local
            Owner role on an object. The name creator is used
            for this method to conform to Dublin Core."""
        users=[]
        for user, roles in self.get_local_roles():
            if 'Owner' in roles:
                users.append(user)
        return ', '.join(users)

    def onDeleteObject(self):
        """Object delete handler. I think this is obsoleted by
        manage_beforeDelete """
        self.unindex_object()

    def getPath(self):
        """Return the physical path for an object."""
        return '/'.join(self.getPhysicalPath())

    def summary(self, num=200):
        """Return a summary of the text content of the object."""
        if not hasattr(self, 'text_content'):
            return ''
        attr=getattr(self, 'text_content')
        if callable(attr):
            text=attr()
        else:
            text=attr
        n = min(num, len(text))
        return text[:n]

    def index_object(self):
        """A common method to allow Findables to index themselves."""
        self._warn_deprecated()
        if hasattr(self, self.default_catalog):
            getattr(self,
                    self.default_catalog).catalog_object(self, self.getPath())

    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        self._warn_deprecated()
        if hasattr(self, self.default_catalog):
            getattr(self,
                    self.default_catalog).uncatalog_object(self.getPath())

    def reindex_object(self):
        """ Suprisingly useful """
        self.unindex_object()
        self.index_object()

    def reindex_all(self, obj=None):
        """ """
        if obj is None:
            obj = self
        if hasattr(aq_base(obj), 'index_object'):
            obj.index_object()
        if hasattr(aq_base(obj), 'objectValues'):
            for item in obj.objectValues():
                self.reindex_all(item)
        return 'done!'
