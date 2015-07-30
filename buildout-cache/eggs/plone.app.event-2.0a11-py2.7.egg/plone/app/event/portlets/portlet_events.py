from Acquisition import aq_inner
from ComputedAttribute import ComputedAttribute
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.app.contenttypes.behaviors.collection import ISyndicatableCollection
from plone.app.contenttypes.interfaces import IFolder
from plone.app.event.base import expand_events
from plone.app.event.base import _prepare_range
from plone.app.event.base import start_end_query

from plone.app.event.base import RET_MODE_ACCESSORS
from plone.app.event.base import get_events
from plone.app.event.base import localized_now
from plone.app.event.portlets import get_calendar_url
from plone.app.portlets import PloneMessageFactory as _
from plone.app.portlets.portlets import base
from plone.app.uuid.utils import uuidToObject
from plone.app.vocabularies.catalog import CatalogSource
from plone.memoize.compress import xhtml_compress
from plone.memoize.instance import memoize
from plone.portlets.interfaces import IPortletDataProvider
from zExceptions import NotFound
from zope import schema
from zope.component import getMultiAdapter
from zope.contentprovider.interfaces import IContentProvider
from zope.interface import implementer
from plone.app.querystring import queryparser

try:
    from plone.app.contenttypes.behaviors.collection import ISyndicatableCollection as ICollection  # noqa
except ImportError:
    ICollection = None


class IEventsPortlet(IPortletDataProvider):

    count = schema.Int(
        title=_(u'Number of items to display'),
        description=_(u'How many items to list.'),
        required=True,
        default=5
    )

    state = schema.Tuple(
        title=_(u"Workflow state"),
        description=_(u"Items in which workflow state to show."),
        default=None,
        required=False,
        value_type=schema.Choice(
            vocabulary="plone.app.vocabularies.WorkflowStates"
        )
    )

    search_base_uid = schema.Choice(
        title=_(u'portlet_label_search_base', default=u'Search base'),
        description=_(
            u'portlet_help_search_base',
            default=u'Select search base Folder or Collection to search for '
                    u'events. The URL to to this item will also be used to '
                    u'link to in calendar searches. If empty, the whole site '
                    u'will be searched and the event listing view will be '
                    u'called on the site root.'
        ),
        required=False,
        source=CatalogSource(object_provides={
            'query': [
                ISyndicatableCollection.__identifier__,
                IFolder.__identifier__
            ],
            'operator': 'or'
        }),
    )


@implementer(IEventsPortlet)
class Assignment(base.Assignment):

    # reduce upgrade pain
    search_base = None

    def __init__(self, count=5, state=None, search_base_uid=None):
        self.count = count
        self.state = state
        self.search_base_uid = search_base_uid

    @property
    def title(self):
        return _(u"Events")

    def _uid(self):
        # This is only called if the instance doesn't have a search_base_uid
        # attribute, which is probably because it has an old
        # 'search_base' attribute that needs to be converted.
        path = self.search_base
        portal = getToolByName(self, 'portal_url').getPortalObject()
        try:
            search_base = portal.unrestrictedTraverse(path.lstrip('/'))
        except (AttributeError, KeyError, TypeError, NotFound):
            return
        return search_base.UID()
    search_base_uid = ComputedAttribute(_uid, 1)


class Renderer(base.Renderer):

    _template = ViewPageTemplateFile('portlet_events.pt')

    _search_base = None

    @property
    def search_base(self):
        if not self._search_base:
            self._search_base = uuidToObject(self.data.search_base_uid)
        return self._search_base

    @property
    def search_base_path(self):
        search_base = self.search_base
        if search_base is not None:
            search_base = '/'.join(search_base.getPhysicalPath())
        return search_base

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)

        context = aq_inner(self.context)

        calendar_url = get_calendar_url(context, self.search_base_path)

        self.next_url = '%s?mode=future' % calendar_url
        self.prev_url = '%s?mode=past' % calendar_url

        portal_state = getMultiAdapter(
            (self.context, self.request),
            name='plone_portal_state'
        )
        self.portal = portal_state.portal()

    def render(self):
        return xhtml_compress(self._template())

    @property
    def available(self):
        return self.data.count > 0 and len(self.events)

    @property
    @memoize
    def events(self):
        context = aq_inner(self.context)
        data = self.data

        query = {}
        if data.state:
            query['review_state'] = data.state

        events = []
        query.update(self.request.get('contentFilter', {}))
        search_base = self.search_base
        if ICollection.providedBy(search_base):
            # Whatever sorting is defined, we're overriding it.
            query = queryparser.parseFormquery(
                search_base, search_base.query,
                sort_on='start', sort_order=None
            )

            start = None
            if 'start' in query:
                start = query['start']
            else:
                start = localized_now(context)

            end = None
            if 'end' in query:
                end = query['end']

            start, end = _prepare_range(search_base, start, end)
            query.update(start_end_query(start, end))
            events = search_base.results(
                batch=False, brains=True, custom_query=query,
                limit=data.count
            )
            events = expand_events(
                events, ret_mode=RET_MODE_ACCESSORS,
                start=start, end=end,
                sort='start', sort_reverse=False
            )
            events = events[:data.count]  # limit expanded
        else:
            search_base_path = self.search_base_path
            if search_base_path:
                query['path'] = {'query': search_base_path}
            events = get_events(
                context, start=localized_now(context),
                ret_mode=RET_MODE_ACCESSORS,
                expand=True, limit=data.count, **query
            )
        return events

    def formatted_date(self, event):
        provider = getMultiAdapter(
            (self.context, self.request, self),
            IContentProvider, name='formatted_date'
        )
        return provider(event)


class AddForm(base.AddForm):
    schema = IEventsPortlet
    label = _(u"Add Events Portlet")
    description = _(u"This portlet lists upcoming Events.")

    def create(self, data):
        return Assignment(count=data.get('count', 5),
                          state=data.get('state', None),
                          search_base_uid=data.get('search_base_uid', 5))


class EditForm(base.EditForm):
    schema = IEventsPortlet
    label = _(u"Edit Events Portlet")
    description = _(u"This portlet lists upcoming Events.")
