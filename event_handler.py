
class EventHandler:

    def __init__(self):
        self.model_views = []

    def register_view(self, model, event_id, f):
        self.model_views.append((model, event_id, f))

    def unregister_view(self, model, event_id, f):
        [self.model_views.remove(el) for el in self.model_views if el == (model,event_id,f)]

    def unregister_views(self, model):
        [self.model_views.remove(el) for el in self.model_views if el[0] == model]

    def _get_fs(self, query_model, event_id):
        return [f for (model, id, f) in self.model_views if model == query_model and id == event_id]

    def event(self, model, id, **kwargs):
        [f(**kwargs) for f in self._get_fs(model, id)]
