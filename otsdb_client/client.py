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

import json
import time
import itertools
import grequests as gr
from datetime import datetime
import socket
from logging import info

def ping(host, port):
    try:
        socket.socket().connect((host, port))
        info('Ping in '+host+':'+str(port) + " OpenTSDB Server: Ok\n")
        return True
    except socket.error as err:
        if err.errno == socket.errno.ECONNREFUSED:
            info('Can\'t connect to OpenTSDB Server')
            return False
        raise Exception('Fail to test OpenTSDB connection status')

class OpenTSDBError(Exception):
    def __init__(self, msg=None):
        if msg is None:
            msg = 'Unknown OpenTSDB error occurred. \n %s \n %s'
        self.msg = msg
        super(OpenTSDBError, self).__init__(msg)

class Connection(object):
    def __init__(self, server='localhost', port=4242):
        self.server = server
        self.port = port
        ping(server,port)

    def get_endpoint(self, key):
        """ Selects the OTSDB required enpoint. """
        return {
            'filters': '/api/config/filters',
            'query_exp': '/api/query/exp',
            'aggr': '/api/aggregators',
            'suggest': '/api/suggest',
            'version': '/api/version',
            'put': '/api/put?details',
            'query': '/api/query',
            'stats': '/api/stats',
        }.get(key)

    def get_url(self):
        """ Returns the domain of the OTSDB requested URL. """
        return 'http://' + self.server + ':' + str(self.port)

    def _make_request(self, endpoint, query=None, process=True):
        """ Performs HTTP GET requests """
        print('URL: '+self.get_url() + self.get_endpoint(endpoint))
        print('params: '+str(query))
        req = gr.get(self.get_url() + self.get_endpoint(endpoint), params=query)
        gr.map([req])
        return self.process_response(req.response) if process else req.response

    def filters(self):
        """ Lists the various filters loaded by the TSD """
        return self._make_request("filters")

    def statistics(self):
        """Get info about what metrics are registered and with what stats."""
        return self._make_request("stats")

    def aggregators(self):
        """Used to get the list of default aggregation functions. """
        return self._make_request("aggr")

    def version(self):
        """Used to check OpenTSDB version. """
        return self._make_request("version")

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
        query = {'type': t, 'q': q, 'max': m}
        return self._make_request("suggest", query)

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
                pts.append(gr.post(self.get_url() + self.get_endpoint("put") +
                '?summary=true&details=true', data=json.dumps(ptl)))
                ptl = list()

        if ptl:
            pts.append(gr.post(self.get_url() + self.get_endpoint("put") +
                '?summary=true&details=true', data=json.dumps(ptl)))

        attempts = 0
        fails = 1
        while attempts < att and fails > 0:
            gr.map(pts)

            if verbose:
                print('Attempt %d: Request submitted with HTTP status codes %s' \
                    % (attempts + 1, str([x.response.status_code for x in pts])))

            pts = [x for x in pts if not 200 <= x.response.status_code <= 300]
            attempts += 1
            fails = sum(len(x) for x in pts)

        if verbose:
            total = len(values)
            print("%d of %d (%.2f%%) requests were successfully sent" \
                % (total - fails, total, 100 * round((total - fails)/total, 2)))

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
        assert aggr in self.aggregators(), \
            'The aggregator is not valid. Check OTSDB docs for more details.'

        query = {'m': '%s:%s' % (aggr, metric), 'start': start, \
                 'show_summary': show_summary, 'tags': tags}
        if end:
            query['end'] = end

        response = self._make_request("query", query, False)
        if 200 <= response.status_code <= 300:
            result = None
            if show_json:
                # Raw response
                result = response.text
            else:
                data = json.loads(response.text)
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

    def hquery_exp(self, aggr='sum', start='1d-ago', end=None, vpol=0, metrics=[],
        expr={}):
        """ Allows for querying data using expressions.

        Parameters
        ----------
        'aggr' : string, required (default=sum)
            The global aggregation function to use for all metrics. It may be
            overridden on a per metric basis.

        'start' : string, required (default=1h-ago)
            The start time for the query. This may be relative, absolute human
            readable or absolute Unix Epoch.

        'end' : string, optional (default=current time)
            The end time for the query. If left out, the end is now

        'vpol': (int, long, float), required (default=0)
            The value used to replace "missing" values, i.e. when a data point was
            expected but couldn't be found in storage.

        'metrics': array of dict, required (default=[])
            Determines which metrics are included in the expression.

        'expr': dict, required (default=[])
            A dictionary with one or more expressions over the metrics.
        """

        # Checking for data consistency
        assert isinstance(metrics, list), 'Field <metrics> must be a list.'
        assert len(metrics) >= 1, 'Field <metrics> must have at least one element'
        for m in metrics:
            assert not ['id', 'name', 'tags'] in m.keys(), \
                'The metric object must have the fields <id>, <name> and <tags>'
            assert len(m['tags']) >= 1, \
                'The field <metric.tags> must have at least one element'

        assert aggr in self.aggregators(), \
            'The aggregator is not valid. Check OTSDB docs for more details.'

        assert isinstance(expr, dict), 'Field <expr> must be a dictionary.'
        assert len(expr) >= 1, 'The field <expr> must have at least one element'

        res = []
        for a, b in itertools.combinations(reversed(sorted(expr.iteritems())), 2):
            expr[a[0]] = expr[a[0]].replace(b[0], "(%s)" % b[1])

        for n, metric in enumerate(metrics):

            for key in expr:
                expr[key] = expr[key].replace(metric['id'], 'res[%d]' % n)

            # Requesting from query endpoint
            response = self.query(metric=metric['name'], aggr=aggr,
                tags=metric['tags'], start=start, end=end, nots=True, union=True)

            res.append(response['results']['values'])

        m = max(len(x) for x in res)
        res = [ x + ([vpol] * (m - len(x))) for x in res]

        return dict([(key, eval(expr[key]).tolist()) for key in sorted(expr)])

    def query_exp(self, aggr='sum', start='1d-ago', end=None, vpol=0, metrics=[],
        expr=[], show_json=True):
        """ Enables extracting data from the storage system

        Parameters
        ----------
        'aggr' : string, required (default=sum)
            The name of an aggregation function to use.

        'start' : string, required (default=1h-ago)
            The start time for the query.

        'end' : string, optional (default=current time)
            An end time for the query.

        'metrics': array of dict, required (default=[])
            Determines which metrics are included in the expression.

        'vpol': int, required (default=0)
            The value used to replace "missing" values, i.e. when a data point was
            expected but couldn't be found in storage.

        'expr': array of dict, required (default=[])
            A list of one or more expressions over the metrics.

        'show_json': boolean, optional (default=True)
            If true, returns the response in the JSON format
        """

        # Checking data consistence
        assert isinstance(metrics, list), 'Field <metrics> must be a list.'
        assert len(metrics) >= 1, 'Field <metrics> must have at least one metric'
        for m in metrics:
            assert not ['id', 'name'] in m.keys(), \
                'The metric object must have the fields <id> and <name>'
        assert aggr in self.aggregators(), \
            'The aggregator is not valid. Check OTSDB docs for more details.'
        assert isinstance(expr, list), 'Field <expr> must be a list.'
        assert len(expr) >= 1, 'Field <expr> must have at least one expression'
        for e in expr:
            assert not ['id', 'expr'] in e.keys(), \
                'The expression object must have the fields <id> and <expr>'
        # Setting <time> definitions
        time = {
            'start': start,
            'end': end,
            'aggregator': aggr
        }
        # Setting <metric> and <policy> definitions
        metrics = [{
            'id': x['id'],
            'metric': x['name'],
            'fillPolicy': {
                'policy': 'scalar',
                'value': vpol
            }
        } for x in metrics]
        # Setting <expression> definitions
        expressions = [{
            'id': x['id'],
            'expr': x['expr']
        } for x in expr]
        # Building the data query
        query = {
           'time': time,
           'metrics': metrics,
           'expressions': expressions
        }
        # Sending request to OTSDB and capturing HTTP response
        response = self._make_request("query_exp", query, False)
        if 200 <= response.status_code <= 300:
            print(json.loads(response.text) if show_json else response.text)
        else:
            # Esta dando erro 500 aqui
            print(response.text)
            print('No results found')
            return []

    @staticmethod
    def process_response(resp):
        try:
            res = json.loads(resp.text)
        except Exception:
            raise OpenTSDBError(resp.text)
        if 'error' in res:
            raise OpenTSDBError(res['error'])
        return res
