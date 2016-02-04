from socket import socket,AF_INET,SOCK_STREAM
from datetime import datetime
from time import mktime
from urllib3 import PoolManager
from json import loads

class Connection(object):
    def __init__(self,server='localhost', port=4242):
        self.server = server
        self.port = int(port)
        self.conn = None
        self.http = None
        self.aggregators = None
        self._connect()

    def _connect(self):
        # Create connection with a socket to PUT values into OpenTSDB
        conn = socket(AF_INET,SOCK_STREAM)
        conn.settimeout(2)
        try :
            conn.connect((self.server, self.port))
        except :
            print 'Unable to connect at server %s and port %d' % (self.server,self.port)
            return
        if conn:
            print 'Connected to OpenTSDB'
            self.conn = conn
        else:
            print 'Fail to connect to OpenTSDB'
            self.conn = None
        # Create the PoolManager for http connections
        #self.http = PoolManager(10,retries=3,timeout=10.0)
        self.http = PoolManager(10,timeout=10.0)
        self.aggregators = self._get_aggr()

    def _isconnected(self):
        if not self.conn or not self.http:
            self._connect()
        if self.conn and self.http:
            return True
        else:
            return False

    def put(self,metric,ts=None,value=0.0,tags=dict()):
        if not self._isconnected():
            print 'connection was lost'
            return
        elif not isinstance(metric,str):
            print 'metric must be a string'
            return
        elif not isinstance(value,float):
            print 'value must be a float'
            return
        if not ts:
            ts = int(mktime(datetime.now().timetuple()))
        try:
            tags_str = ''
            for k,v in tags.iteritems():
                tags_str += str(k) + '=' + str(v) + ' '
            cmd = 'put %s %d %4.2f %s\n' % (metric,ts,float(value),tags_str)
            print 'cmd: '+cmd[:-1]
            self.conn.send(cmd)
            print 'point written successfully'
            return True
        except:
            print 'fail to put the point'
            return False

    def _disconnect(self):
        self.conn.close()
        self.http = None

    def __del__(self):
        self._disconnect()

    def url(self):
        return 'http://'+self.server+':'+str(self.port)

    def _get_aggr(self):
        if not self._isconnected():
            print 'connection was lost'
            return
        query = '/api/aggregators'
        response = self.http.request('GET',self.url()+query)
        status = int(response.status)
        if status >= 200 and status < 300:
            return loads(response.data)
        else:
            print 'No aggregators found'
            return []

    def query(self, metric, aggr, tags=dict(), start='', end=None, nots=False,\
        tsd=True, json=False,show_summary=False,union=False,chunked=False):
        # Support only one metric per query
        # chunked: will be implemented in future, to stream over urllib3
        # Example: /api/query?m=sum:test_post{test=*}&start=1d-ago
        # other options in query: &no_annotations=true&global_annotations=false&show_summary=true
        # More available: http://opentsdb.net/docs/build/html/api_http/query/index.html
        if not self._isconnected():
            print 'connection was lost'
            return
        elif aggr not in self.aggregators:
            print 'must use some valid aggregator like: ',self.aggregators
            return
        query = '/api/query?m='+aggr+':'+metric
        tags_str = ''
        ntags = len(tags)
        ctags = 0
        for k,v in tags.iteritems():
            ctags += 1
            tags_str += k+'='+v
            if ctags < ntags:
                tags_str += ','
        if ntags > 0:
            query += '{'+tags_str+'}'
        query += '&start='+start
        if end:
            query += '&end='+end
        if show_summary:
            query += '&show_summary=true'
        response = self.http.request('GET',self.url()+query)
        status = int(response.status)
        if status >= 200 and status < 300:
            result = None
            if json:
                # Raw response
                result = response.data
            else:
                data = loads(response.data)
                if union:
                    dpss = dict()
                    for x in data:
                        if 'metric' in x.keys():
                            for k,v in x['dps'].iteritems():
                                dpss[k] = v
                    points = sorted(dpss.items())
                    if not nots:
                        result = {'results':{'ts':[],'values':[]}}
                        if tsd:
                            result['results']['ts'] = [datetime.fromtimestamp(float(x[0])) for x in points]
                        else:
                            result['results']['ts'] = [x[0] for x in points]
                    else:
                        result = {'results':{'values':[]}}
                    result['results']['values'] = [x[1] for x in points]
                else:
                    result = {'results':[]}
                    for x in data:
                        if 'metric' in x.keys():
                            dps = x['dps']
                            points = sorted(dps.items())
                            resd = {'metric':x['metric'],'tags':x['tags'],'ts':[],'values':[y[1] for y in points]}
                            if not nots:
                                if tsd:
                                    resd['ts'] = [datetime.fromtimestamp(float(x[0])) for x in points]
                                else:
                                    resd['ts'] = [x[0] for x in points]
                            else:
                                del resd['ts']
                            result['results'].append(resd)
                if show_summary:
                    result['summary'] = data[-1]['statsSummary']
            return result
        else:
            print 'No results found'
            return []
