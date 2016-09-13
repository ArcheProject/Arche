from pyramid.httpexceptions import HTTPFound
import deform

from arche import _
from arche.views.base import BaseForm


button_finish = deform.Button('finish', title = _("Finish"), css_class="btn-primary btn pull-right")
button_next = deform.Button('next', title = _("Next"), css_class = 'btn btn-primary pull-right')
button_previous = deform.Button('previous', title = _("Previous"), css_class = 'btn btn-default')


class BaseWizardForm(BaseForm):
    """ Emulates much of the behaviour from the BaseForm,
        but uses states to request different kind of data.
        
        Each state can set corresponding title, appstruct and schema.

        With the same name as state, optionally add:
        <state>_schema
        <state>_title
        <state>_appstruct
    """
    states = ()
    
    @property
    def wizard_name(self):
        return self.__class__.__name__

    @property
    def data(self):
        return self.request.session.setdefault('wizard_data:%s' % self.wizard_name, {})

    @property
    def current_state(self):
        state = self.request.GET.get('_ws', None)
        if state and state in self.states:
            return state
        return self.states[0]

    @property
    def buttons(self):
        """ The first submit button is always the default action when pressing enter.
            No point in fighting this - better to simply change the order and positioning of the buttons.
        """
        buttons = []
        if self.states[-1] == self.current_state:
            buttons.append(button_finish)
        else:
            buttons.append(button_next)
        if self.states.index(self.current_state) != 0:
            buttons.append(button_previous)
        buttons.append(self.button_cancel)
        return buttons

    @property
    def title(self):
        return getattr(self, '%s_title' % self.current_state, '')

    def get_schema(self):
        return getattr(self, '%s_schema' % self.current_state, None)

    def appstruct(self):
        state_appstruct_name = '%s_appstruct' % self.current_state
        if hasattr(self, state_appstruct_name):
            state_appstruct = getattr(self, state_appstruct_name, None)
            if state_appstruct != None:
                return state_appstruct()
        return self.data.get(self.current_state, {})

    def _inject_state(self, state):
        self.request.GET['_ws'] = state

    def next_success(self, appstruct):
        self.data[self.current_state] = appstruct
        state = self.states[self.states.index(self.current_state) + 1]
        self._inject_state(state)
        return HTTPFound(location = self.request.url)

    def previous_success(self, appstruct):
        self.data[self.current_state] = appstruct
        state = self.states[self.states.index(self.current_state) - 1]
        self._inject_state(state)
        return HTTPFound(location = self.request.url)

    def previous_failure(self, *args):
        state = self.states[self.states.index(self.current_state) - 1]
        self._inject_state(state)
        return HTTPFound(location = self.request.url)

    def finish_success(self, appstruct):
        self.data[self.current_state] = appstruct
        final_appstruct = {}
        for state in self.states:
            final_appstruct[state] = self.data[state]
        return self.final_success(final_appstruct)

    def final_success(self, final_appstruct):
        """ A combined appstruct of all the data used.
            Clear it, save it or something else.
            You need to override this method to make the form actually do something.
        """
        self.data.clear()
        self.flash_messages.add("Captured data was: %r" % final_appstruct, type = 'success')
        return HTTPFound(location = self.request.resource_url(self.context))

    def cancel(self, *args):
        self.data.clear()
        return self.relocate_response(self.request.resource_url(self.context), msg = self.default_cancel)
    cancel_success = cancel_failure = cancel
