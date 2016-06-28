# Copyright 2016: Venidera Research & Development.
# All Rights Reserved.
#
# Licensed under the GNU General Public License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      https://www.gnu.org/licenses/gpl-2.0.en.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
import random
import numpy as np
from rest.client import Client

class Connection(object):
    def __init__(self,server='localhost',port=4242):
        self.client = Client(server=server, port=port)

    def test_get_statistics(self):
        print self.client.statistics()

    def test_get_aggregators(self):
        print self.client.aggregators()

    def test_get_filters(self):
        print self.client.filters()

    def test_get_version(self):
        print self.client.version()

    def test_put_metric(self, metric='test.m'):
        print "#1 Put metric"
        values = random.sample(range(30), 25)
        self.client.put(verbose=True, metric=metric, values=values,
            tags=dict({'mean': np.mean(values), 'std': np.std(values)}))
        print "#2 Put metric"
        values = random.sample(range(10), 10)
        ts = random.sample(range(10000,11000), 10)
        self.client.put(verbose=True, metric=metric, timestamp=ts, values=values,
            tags=dict({'mean': np.mean(values), 'std': np.std(values)}))
        print "#3 Put metric"
        values = random.sample(range(500), 500)
        self.client.put(verbose=True, metric=metric, values=values, ptcl=30,
            tags=dict({'mean': np.mean(values), 'std': np.std(values)}))

    def test_suggest(self):
        print "#1 Suggest"
        print self.client.suggest()
        print "#2 Suggest"
        print self.client.suggest(m=2)
        print "#3 Suggest"
        print self.client.suggest(q='test.')

    def test_query_metric(self, metric='test.m'):
        print "#1 Query metric"
        print self.client.query(metric=metric)
        print "#2 Query metric"
        print self.client.query(metric=metric, show_summary=True, show_json=True,nots=True, tsd=False, union=True)

    def test_query_expr_metric(self):
        metrics = [
            {'id': 'a', 'name': 'test.a'},
            {'id': 'b', 'name': 'test.b'}
        ]
        expr = [
            {'id': 'ex1', 'expr': 'a + b'},
            {'id': 'ex2', 'expr': '4*a + 3*b'}
        ]
        print self.client.query_exp(metrics=metrics, expr=expr)
