# Copyright 2016: Venidera Research & Development.
# All Rights Reserved.
#
# Licensed under the GNU General Public License, Version 3.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      https://www.gnu.org/licenses/gpl-3.0.en.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import grequests as gr
import time
import itertools
from datetime import datetime
import socket

from json import dumps as tdumps, loads
from logging import info

def ping(host, port):
    try:
        socket.socket().connect((host, port))
        info('Ping in '+host+':'+str(port) + " OpenTSDB Server: Ok\n")
        return True
    except socket.error as err:
        print('ping fail')
        if err.errno == socket.errno.ECONNREFUSED:
            raise Exception('Can\'t connect to OpenTSDB Server')
        raise Exception('Fail to test OpenTSDB connection status')

class Connection(object):
    def __init__(self, server='localhost', port=4242):
        self.server = server
        self.port = port
        ping(server, port)
        self.url = 'http://%s:%d' % (server, port)
        self.headers = {'content-type': "application/json"}
        self.aggregators = self.aggregators()
        self.ids = {"filter": {}, "metric": {}}

    def get_endpoint(self, key=""):
        endpoint = '/api' + {
            'filters': '/config/filters',
            'query_exp': '/query/exp',
            'aggr': '/aggregators',
            'suggest': '/suggest',
            'version': '/version',
            'put': '/put?details',
            'query': '/query',
            'stats': '/stats',
        }.get(str(key))

        assert endpoint is not '/api', \
            "Please provide a valid endpoint."
        return endpoint

    def _get(self, endpoint="", params=dict()):
        r = gr.get(self.url + self.get_endpoint(endpoint),
                   params=params)
        gr.map([r])
        return r.response

    def _post(self, endpoint="", data=dict()):
        assert isinstance(data, dict), 'Field <data> must be a dict.'

        r = gr.post(self.url + self.get_endpoint(endpoint),
            data=self.dumps(data), headers=self.headers)
        gr.map([r])

        return r.response

    def process_response(self, response):
        status = response.status_code

        if not (200 <= status < 300):
            info("HTTP error code = %d" % status)
            return False

        data = loads(response.text)
        return data if data else None

    def filters(self):
        """ Lists the various filters loaded by the TSD """
        resp = self._get(endpoint="filters")
        return self.process_response(resp)

    def statistics(self):
        """Get info about what metrics are registered and with what stats."""
        resp = self._get(endpoint="stats")
        return self.process_response(resp)

    def aggregators(self):
        """Used to get the list of default aggregation functions. """
        resp = self._get(endpoint="aggr")
        return self.process_response(resp)

    def version(self):
        """Used to check OpenTSDB version. """
        resp = self._get(endpoint="version")
        return self.process_response(resp)

    def suggest(self, t='metrics', q='', m=9999):
        """ Matches the string in the query on the first chars of the stored data.

        Parameters
        ----------
        't' : string (default='metrics')
            The type of data. Must be one of the following: metrics, tagk or tagv.

        'q' : string, optional (default='')
            A string to match on for the given type.

        'm' : int, optional (default=9999)
            The maximum number of suggested results. Must be greater than 0.

        """
        params = {'type': t, 'q': q, 'max': m}
        resp = self._get(endpoint="suggest", params=params)
        return self.process_response(resp)

    def put(self, metric=None, timestamps=[], values=[], tags=dict(),
        details=True, verbose=True, ptcl=20, att=5):
        """ Put time serie points into OpenTSDB over HTTP.

        Parameters
        ----------
        'metric' : string, required (default=None)
            The name of the metric you are storing.

        'timestamps' : int, required (default=None) ** [generated over mktime]
            A Unix epoch style timestamp in seconds or milliseconds.

        'values' : array, required (default=[])
            The values to record.

        'tags' : map, required (default=dict())
            A map of tag name/tag value pairs.

        'details' : boolean, optional (default=True)
            Whether or not to return detailed information

        'verbose' : boolean, optional (default=False)
            Enable verbose output.

        'ptcl' : int, required (default=10)
            Number of points sent per http request

        'att' : int, required (default=5)
            Number of HTTP request attempts
        """
        assert isinstance(metric, str), 'Field <metric> must be a string.'
        assert isinstance(values, list), 'Field <values> must be a list.'
        assert isinstance(timestamps, list), 'Field <timestamps> must be a list.'

        if len(timestamps) > 0:
            assert len(timestamps) == len(values), \
                'Field <timestamps> dont fit field <values>.'
            assert all(isinstance(x, (int, datetime)) for x in timestamps), \
                'Field <timestamps> must be integer or datetime'

        pts = list()
        ptl = []
        ptc = 0

        for n, v in enumerate(values):
            v = float(v)

            if not timestamps:
                current_milli_time = lambda: int(round(time.time() * 1000))
                nts = current_milli_time()
            else:
                nts = timestamps[n]

                if isinstance(nts, datetime):
                    nts = int(time.mktime(nts.timetuple()))
                elif not isinstance(nts, int):
                    nts = int(nts)

            u = {'timestamp': nts, 'metric': metric, 'value': v, 'tags': tags}

            ptl.append(u)
            ptc += 1

            if ptc == ptcl:
                ptc = 0
                pts.append(gr.post(self.url + self.get_endpoint("put") +
                '?summary=true&details=true', data=self.dumps(ptl)))
                ptl = list()

        if ptl:
            pts.append(gr.post(self.url + self.get_endpoint("put") +
                '?summary=true&details=true', data=self.dumps(ptl)))

        attempts = 0
        fails = 1
        while attempts < att and fails > 0:
            gr.map(pts)

            if verbose:
                print('Attempt %d: Request submitted with HTTP status codes %s' \
                    % (attempts + 1, str([x.response.status_code for x in pts])))

            pts = [x for x in pts if not 200 <= x.response.status_code <= 300]
            attempts += 1
            fails = len([x for x in pts])

        if verbose:
            total = len(values)
            print("%d of %d (%.2f%%) requests were successfully sent" \
                % (total - fails, total, 100 * round(float((total - fails))/total, 2)))

        return {
            'points': len(values),
            'success': len(values) - fails,
            'failed': fails
        }

    def query(self, metric, aggr='sum', tags=dict(), start='1h-ago', end=None,
        show_summary=False, show_json=False, nots=False, tsd=True, union=False):
        """ Enables extracting data from the storage system

        Parameters
        ----------
        'metric' : string, required (default=None)
            The name of a metric stored in the system.

        'aggr' : string, required (default=sum)
            The name of an aggregation function to use.

        'tags' : map, required (default=dict())
            A map of tag name/tag value pairs.

        'start' : string, required (default=1h-ago)
            The start time for the query.

        'end' : string, optional (default=current time)
            An end time for the query.

        'show_summary' : boolean, optional (default=False)
            Whether or not to show a summary of timings surrounding the query.

        'show_json': boolean, optional (default=False)
            If true, returns the response in the JSON format

        'nots': boolean, optional (default=False)
            Hides timestamp results

        'tsd': boolean, optional (default=True)
            Set timestamp as datetime object instead of an integer

        'union': boolean, optional (default=False)
            Returns the points of the time series (i.e. metric + tags) in one list
        """
        assert isinstance(metric, str), 'Field <metric> must be a string.'
        assert aggr in self.aggregators, \
            'The aggregator is not valid. Check OTSDB docs for more details.'

        data = {"start": start, "queries" :
            [
                {
                    "aggregator": aggr,
                    "metric": metric,
                    "tags": tags,
                    'show_summary': show_summary
                }
            ]
        }

        if end:
            data['end'] = end
        resp = self._post(endpoint="query", data=data)

        if 200 <= resp.status_code <= 300:
            result = None
            if show_json:
                # Raw response
                result = resp.text
            else:
                data = loads(resp.text)
                if union:
                    dpss = dict()
                    for x in data:
                        if 'metric' in x.keys():
                            for k,v in x['dps'].iteritems():
                                dpss[k] = v
                    points = sorted(dpss.items())
                    if not nots:
                        result = {'results':{'timestamps':[],'values':[]}}
                        if tsd:
                            result['results']['timestamps'] = [datetime.fromtimestamp(float(x[0])) for x in points]
                        else:
                            result['results']['timestamps'] = [x[0] for x in points]
                    else:
                        result = {'results':{'values':[]}}
                    result['results']['values'] = [float(x[1]) for x in points]
                else:
                    result = {'results':[]}
                    for x in data:
                        if 'metric' in x.keys():
                            dps = x['dps']
                            points = sorted(dps.items())
                            resd = {'metric':x['metric'],'tags':x['tags'],'timestamps':[],'values':[float(y[1]) for y in points]}
                            if not nots:
                                if tsd:
                                    resd['timestamps'] = [datetime.fromtimestamp(float(x[0])) for x in points]
                                else:
                                    resd['timestamps'] = [x[0] for x in points]
                            else:
                                del resd['timestamps']
                            result['results'].append(resd)
                if show_summary:
                    result['summary'] = data[-1]['statsSummary']
            return result
        else:
            print('No results found')
            return []

    def gen_id(self, tid="", desc=""):
        assert tid in self.ids.keys(), "Field <tip> is not valid."
        assert desc, "Field <desc> is not valid."

        if desc not in self.ids[tid].keys():
            if len(self.ids[tid]) == 0:
                self.ids[tid][desc] = 1
            else:
                self.ids[tid][desc] = max(self.ids[tid].values()) + 1
        return "%s%d" % (tid[:1], self.ids[tid][desc])

    def build_policy(self, vpol=None):
        assert vpol != None, \
            'Field <vpol> must have a value.'

        if vpol == 0:
            return {'policy': 'zero'}
        elif any(isinstance(vpol, i) for i in [int, float]):
            return {'policy': 'scalar', 'value': vpol}
        elif vpol in ['nan', 'null']:
            return {'policy': vpol}
        else:
            assert False, 'Field <vpol> is not valid.'

    def build_downsampler(self, aggr='max', interval=None, vpol=None):
        assert interval != None, \
            'Field <interval> is not valid.'
        assert aggr in self.aggregators, \
            'The aggregator is not valid. Check OTSDB docs for more details.'

        ret = {'interval': interval, 'aggregator': aggr}
        if vpol:
            ret['fillPolicy'] = self.build_policy(vpol)
        return ret

    def build_filter(self, tags=[], group=False):
        assert len(tags) > 0 and isinstance(tags, list), \
            'Field <tags> is not valid.'

        obj = {"id" : self.gen_id("filter", self.dumps(tags)), "tags" : []}
        for t in tags:
            obj["tags"].append(
                {
                    "type": "wildcard",
                    "tagk": t,
                    "filter": "*",
                    "groupBy": group
                }
            )

        return obj

    def query_expressions(self, aggr='sum', start='1d-ago', end='now', vpol=0,
        metrics=[], exprs=[], dsampler=None):
        """ Allows for querying data using expressions.

        Parameters
        ----------
        'aggr' : string, required (default=sum)
            The name of an aggregation function to use.

        'start' : string, required (default=1h-ago)
            The start time for the query.

        'end' : string, optional (default=current time)
            An end time for the query.

        'vpol': [int, float, str], required (default=0)
            The value used to replace "missing" values, i.e. when a data point was
            expected but couldn't be found in storage.

        'metrics': array of tuples, required (default=[])
            Determines the pairs (metric, tags) in the expressions.

        'exprs': array of tuples, required (default=[])
            A list with one or more pairs (id, expr) of expressions.

        'dsampler': tuple of three elements, optional (default=None)
            Reduces the number of data points returned, given an interval
        """
        assert aggr in self.aggregators, \
            'The aggregator is not valid. Check OTSDB docs for more details.'

        assert any(isinstance(vpol, i) for i in [int, float]) or \
                (isinstance(vpol, str) and vpol in ['null', 'nan']), \
            'Field <vpol> is not valid.'

        assert isinstance(metrics, list), 'Field <metrics> must be a list.'
        assert len(metrics) > 0, 'Field <metrics> must have at least one metric'
        for m in metrics:
            assert len(m) == 2, \
                'Tuple must have the (metric, tags) format.'
            assert isinstance(m[0], str), \
                'Field <metric> must be a string.'
            assert isinstance(m[1], list), \
                'Field <tags> must be a list.'

        assert isinstance(exprs, list), 'Field <exprs> must be a list.'
        assert len(exprs) > 0, 'Field <exprs> must have at least one metric'
        for e in exprs:
            assert len(e) == 2, \
                'Tuple must have the (id, expr) format.'
            assert isinstance(e[0], str), \
                'Field <id> must be a string.'
            assert isinstance(e[1], str), \
                'Field <expr> must be a string.'

        if dsampler:
            assert 2 <= len(dsampler) <= 3, \
                'Field <dsampler> must be composed by (interval, aggr) ' \
                'or (interval, aggr, vpol).'
            assert isinstance(dsampler[0], str), \
                'Field <interval> must be a string.'
            assert dsampler[1] in self.aggregators, \
                'Field <aggr> is not a valid aggregator.'
        # Setting <time> definitions
        time = {
            'start': start,
            'aggregator': aggr,
            'end': end
        }
        if dsampler:
            time['downsampler'] = self.build_downsampler(
                interval=dsampler[0], aggr=dsampler[1],
                vpol=dsampler[2] if len(dsampler) == 3 else None)

        # Setting <filters> definitions
        filters = {i[0]: self.build_filter(tags=i[1]) for i in metrics}

        # Setting <metric> definitions
        q_metrics = []
        for m in metrics:
            obj = {
                'id': self.gen_id(tid="metric", desc=m[0]),
                'filter': filters[m[0]]['id'],
                'metric': m[0]
            }
            if vpol is not None:
                obj['fillPolicy'] = self.build_policy(vpol)
            q_metrics.append(obj)

        filters = filters.values()
        filters = [i for n, i in enumerate(filters) if i not in filters[n + 1:]]

        assert isinstance(filters, list) and len(filters) > 0, \
            'Object filter is not valid.'

        # Setting <expression> definitions
        q_exprs = []
        for e in exprs:
            m_id = e[1]
            for i, j in self.ids["metric"].iteritems():
                m_id = m_id.replace(i, "m%d" % j)

            obj = {
                'id': e[0],
                'expr': m_id
            }

            q_exprs.append(obj)

        outputs = [
            {
                'id': e[0],
                'alias': 'Expression %s' % e[0]
            } for e in exprs]

        # Building the data query
        data = {
           'time': time,
           'metrics': q_metrics,
           'filters': filters,
           'expressions': q_exprs,
           'outputs': outputs
        }

        # Sending request to OTSDB and capturing HTTP response
        resp = self._post(endpoint="query_exp", data=data)
        return self.process_response(resp)

    def query_summing(self, aggr='sum', start='1d-ago', end='now', vpol=0,
        metrics=[], dsampler=None):
        """ Sum all required metrics using query with expressions """
        assert isinstance(metrics, list), 'Field <metrics> must be a list.'
        assert len(metrics) > 0, 'Field <metrics> must have at least one metric'
        for m in metrics:
            assert len(m) == 2, \
                'Tuple must have the (metric, tags) format.'
            assert isinstance(m[0], str), \
                'Field <metric> must be a string.'
            assert isinstance(m[1], list), \
                'Field <tags> must be a list.'

        expr = ""
        for m in metrics:
            expr += "%s + " % m[0]
        expr = expr[:-3]

        expressions = [("sum", expr)]
        return self.query_expressions(aggr='sum', start=start, end=end, vpol=vpol,
            metrics=metrics, exprs=expressions, dsampler=dsampler)

    def dumps(self, x):
        return tdumps(x, default=str)
