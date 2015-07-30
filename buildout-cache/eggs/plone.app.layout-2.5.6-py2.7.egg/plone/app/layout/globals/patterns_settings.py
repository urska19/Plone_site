# This module contains the global patterns settings

from zope.interface import implements
from zope.component import getAdapters
from zope.publisher.browser import BrowserView
from .interfaces import IPatternsSettingsRenderer
from Products.CMFPlone.interfaces import IPatternsSettings
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.component import getMultiAdapter


class PatternsSettings(BrowserView):
    """
    Default patterns settings
    """
    implements(IPatternsSettingsRenderer)

    def __call__(self):
        portal_state = getMultiAdapter(
            (self.context, self.request), name=u'plone_portal_state')
        # do not use getSite because it's possible it could be different
        # than the actual portal url
        base_url = portal_state.portal_url()
        result = {
            'data-base-url': self.context.absolute_url(),
            'data-portal-url': base_url,
            'data-i18ncatalogurl': base_url + '/plonejsi18n'
        }

        # first, check for any adapters that need pattern data defined
        adapters = getAdapters((self.context, self.request, None), IPatternsSettings)
        [result.update(x[1]()) for x in adapters]

        # Resources Registered UI patterns can override adapters
        registry = getUtility(IRegistry)
        try:
            pattern_options = registry['plone.patternoptions']
        except (AttributeError, KeyError):
            pattern_options = {}
        for key, value in pattern_options.items():
            result['data-pat-' + key] = value

        return result
