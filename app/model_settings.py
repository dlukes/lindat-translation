import json
import logging
import os
from flask import current_app
import tensorflow as tf
from tensor2tensor.utils import registry, usr_dir
from iso639 import to_name
import networkx as nx

from . import settings

log = logging.getLogger(__name__)

usr_dir.import_usr_dir('t2t_usr_dir')
hparams = tf.contrib.training.HParams(data_dir=os.path.expanduser('t2t_data_dir'))


#TODO handle prefix_with
#TODO src/tgt as array
class Models(object):

    def __init__(self, models_cfg):
        self._models = {}
        self._default_model_name = models_cfg[0]['model']
        self._G = nx.DiGraph()
        for cfg in models_cfg:
            model = Model(cfg)
            if model.model in self._models:
                log.error("Model names should be unique")
                import sys
                sys.exit(1)
            self._models[model.model] = model
            if cfg.get('default'):
                _default_model_name = cfg['model']
            # This will keep only the last model
            self._G.add_edge(cfg['source'], cfg['target'], cfg=model)

        # There may be more than one shortest path between sa source and target; this returns only one
        self._shortest_path = nx.shortest_path(self._G)
        _directions = []
        for item in self._shortest_path.items():
            u = item[0]
            for v in item[1].keys():
                if u != v:
                    display = '{}->{}'.format(to_name(u), to_name(v))
                    _directions.append((u, v, display))
        self._directions = sorted(_directions, key=lambda x: x[2])

    def get_possible_directions(self):
        return self._directions

    def get_model_list(self, source, target):
        """
        Returns a list of models that need to be used to translate from source to target
        :param source:
        :param target:
        :return:
        """
        try:
            path = self._shortest_path[source][target]
            if len(path) > 1:
                # TODO cfg is now a model class
                return [self._G[pair[0]][pair[1]]['cfg'] for pair in zip(path[0:-1], path[1:])]
            else:
                return []
        except KeyError as e:
            return []

    def get_default_model_name(self):
        return self._default_model_name

    def get_model_names(self):
        return list(self._models.keys())

    def get_models(self):
        # TODO this used to return the json cfg not model classes
        return list(self._models.values())

    def get_model(self, model_name):
        return self._models.get(model_name, self._models.get(self.get_default_model_name()))


class Model(object):

    def __init__(self, cfg):
        for key in cfg:
            if key != 'server':
                setattr(self, key, cfg[key])
            else:
                setattr(self, '_server', cfg[key])
        self.problem = registry.problem(cfg['problem'])
        self.problem.get_hparams(hparams)
        domain = cfg.get('domain', '')
        if domain:
            ' ({})'.format(domain)
        self.title = '{} ({}{})'.format(cfg['model'], cfg.get('display', '{}->{}'
                                                              .format(to_name(cfg['source']),
                                                                      to_name(cfg['target']))),
                                        domain)

    @property
    def server(self):
        """
        This method needs a valid app context
        :return:
        """
        if hasattr(self, '_server'):
            return self._server.format(**current_app.config)
        else:
            return current_app.config['DEFAULT_SERVER']

    def __iter__(self):
        yield 'model', self.model
        yield 'source', self.source
        yield 'target', self.target
        yield 'title', self.title
        if hasattr(self, 'default'):
            yield 'default', self.default
        if hasattr(self, 'domain'):
            yield 'domain', self.domain


with open(os.path.join(os.path.dirname(__file__), 'models.json')) as models_json:
    models_cfg = json.load(models_json)

models = Models(models_cfg)



