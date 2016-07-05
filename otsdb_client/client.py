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

class Connection(Client):
    #def __init__(self,server='localhost',port=4242):
    #    self.client = Client(server=server, port=port)

    def test_get_statistics(self):
        print self.statistics()

    def test_get_aggregators(self):
        print self.aggregators()

    def test_get_filters(self):
        print self.filters()

    def test_get_version(self):
        print self.version()

    def test_put_metric(self, metric='test.m'):
        print "#1 Put metric"
        values = random.sample(range(30), 25)
        self.put(verbose=True, metric=metric, values=values,
            tags=dict({'mean': np.mean(values), 'std': np.std(values)}))
        print "#2 Put metric"
        values = random.sample(range(10), 10)
        ts = random.sample(range(10000,11000), 10)
        self.put(verbose=True, metric=metric, timestamp=ts, values=values,
            tags=dict({'mean': np.mean(values), 'std': np.std(values)}))
        print "#3 Put metric"
        values = random.sample(range(500), 500)
        self.put(verbose=True, metric=metric, values=values, ptcl=30,
            tags=dict({'mean': np.mean(values), 'std': np.std(values)}))

    def test_suggest(self):
        print "#1 Suggest"
        print self.suggest()
        print "#2 Suggest"
        print self.suggest(m=2)
        print "#3 Suggest"
        print self.suggest(q='test.')

    def test_query_metric(self, metric='test.m'):
        print "#1 Query metric"
        print self.query(metric=metric)
        print "#2 Query metric"
        print self.query(metric=metric, show_summary=True, show_json=True,nots=True, tsd=False, union=True)

    def test_query_expr_metric(self):
        metrics = [
            {"id": "f1", "name": "test.f1", "tags": {'type': 'ts'}},
            {"id": "f2", "name": "test.f2", "tags": {'type': 'ts'}}
        ]

        expr = {
            "ex1": "f1 + f2",
            "ex2": "ex1 * 2",
            "ex3": "2 * ex2",
            "ex4": "4*ex1 + 3*ex2",
            "ex5": "ex4*f1 + f2",
            "ex6": "ex5 - ex4 + ex3 + ex2 - ex1",
        }

        print self.hquery_exp(metrics=metrics, expr=expr)
