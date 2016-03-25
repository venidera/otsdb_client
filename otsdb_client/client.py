from socket import socket,AF_INET,SOCK_STREAM
from datetime import datetime
from time import mktime,sleep
from urllib3 import PoolManager,Retry,Timeout
from json import loads,dumps

class Connection(object):
    def __init__(self,server='localhost', port=4242):
        self.server = server
        self.port = int(port)
        self.conn = None
        self.http = None
        self.aggregators = None
        self._connect()

    def _connect(self,wctype='http'):
        # Create connection with a socket to PUT values into OpenTSDB
        if wctype not in ['telnet','http']:
            print 'Invalid connection type for writing'
            return False
        if wctype == 'telnet':
            conn = socket(AF_INET,SOCK_STREAM)
            conn.settimeout(2)
            try :
                conn.connect((self.server, self.port))
            except :
                print 'Unable to connect at server %s and port %d' % (self.server,self.port)
                return
            if conn:
                print 'Connected to OpenTSDB over telnet'
                self.conn = conn
                self.wctype = 'telnet'
            else:
                print 'Fail to connect to OpenTSDB'
                self.conn = None
        else:
            self.wctype = 'http'
            # Create the PoolManager for http connections
            self.http = PoolManager(10,retries=Retry(total=20),timeout=Timeout(total=30.0))
            if self.http:
                print 'HTTP client ready to access OpenTSDB server'
            self.aggregators = self._get_aggr()

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

    def _isconnected(self):
        # If no connection, connect
        if self.wctype == 'telnet':
            if not self.conn:
                self._connect()
            try:
                self.conn.getpeername()
                return True
            except:
                return False
        elif self.wctype == 'http':
            if not self.http:
                self._connect()
            if self.http:
                return True
            else:
                return False

    def put(self,metric,ts=None,values=[],tags=dict(),details=True,verbose=False,ptcl=10,twait=0.3):
        rs = {'points':0,'success':0,'failed':0}
        if details:
            ldetails = list()
        #{ 'ts' : ts, 'values': values, 'input-results': list(), 'input-type':''}
        if not self._isconnected():
            print 'connection was lost'
            return
        elif not isinstance(metric,str):
            print 'metric must be a string'
            return
        elif not isinstance(values,list):
            print 'values must be a list of values'
            return
        if ts:
            # check 1
            if not isinstance(ts,list):
                print 'timestamps must be passed as a list'
                return
            elif len(ts) != len(values):
                print 'if timestamps are passed they must be in the same number of values'
                return
            else:
                for i in ts:
                    if not isinstance(i,datetime) and not isinstance(i,int):
                        print 'timestamps must be passed as integer or datetime'
                        return
        if self.wctype == 'http':
            url = self.url() + '/api/put?summary=true&details=true'
            if verbose:
                print 'Putting data over http to url: %s' % (url)
            # separate to send 50 points per request
            pts = list()
            ptl = list()
            ptc = 0
            for n,v in enumerate(values):
                if not ts:
                    nts = int(mktime(datetime.now().timetuple()))
                else:
                    nts = ts[n]
                    if isinstance(nts,datetime):
                        nts = int(mktime(nts.timetuple()))
                    else:
                        if not isinstance(nts,int):
                            nts = int(nts)
                ptl.append({'timestamp':nts,'metric':metric,'value':float(v),'tags':tags})
                ptc += 1
                if ptc == ptcl:
                    ptc = 0
                    pts.append(list(ptl))
                    ptl = list()
            if ptl:
                pts.append(list(ptl))
            for n,ptset in enumerate(pts):
                if details:
                    dt = {'points':ptset,'type':'http'}
                rs['points'] += len(ptset)
                reqrs = self.http.request('POST',url,body=dumps(ptset),headers={'Content-Type': 'application/json'})
                if reqrs.status in [200,204]:
                    rspts = loads(reqrs.data)
                    rs['success'] += rspts['success']
                    rs['failed'] += rspts['failed']
                    if details:
                        dt['result'] = 'OK'
                else:
                    rs['failed'] += len(ptset)
                    if details:
                        dt['result'] = 'FAIL'
                if verbose:
                    print 'Request %d submitted with http response code %d and results %s' % (n+1,reqrs.status,reqrs.data)
                if details:
                    ldetails.append(dt)
                sleep(twait)
        else:
            tags_str = ''
            for k,v in tags.iteritems():
                tags_str += str(k) + '=' + str(v) + ' '
            for n,v in enumerate(values):
                if not ts:
                    nts = int(mktime(datetime.now().timetuple()))
                else:
                    nts = ts[n]
                    if isinstance(nts,datetime):
                        nts = int(mktime(nts.timetuple()))
                    else:
                        if not isinstance(nts,int):
                            nts = int(nts)
                cmd = 'put %s %d %4.2f %s\n' % (metric,nts,float(v),tags_str)
                if details:
                    dt = {'command':cmd,'type':'telnet'}
                try:
                    rs['points'] += 1
                    self.conn.send(cmd)
                    rs['success'] += 1
                    if details:
                        dt['result'] = 'OK'
                except:
                    rs['failed'] += 1
                    if details:
                        dt['result'] = 'FAIL'
                if details:
                    ldetails.append(dt)
        if details:
            rs['details'] = ldetails
        return rs

    def _disconnect(self):
        if self.wctype == 'telnet':
            self.conn.close()
        elif self.wctype == 'http':
            self.http = None
        self.aggregators = None

    def __del__(self):
        self._disconnect()

    def url(self):
        return 'http://'+self.server+':'+str(self.port)

    def query(self, metric, aggr='sum', tags=dict(), start='1h-ago', end=None, nots=False,\
        tsd=True, json=False,show_summary=False,union=False,chunked=False):
        # Support only one metric per query
        # Arguments description:
        # metric = the metric Name
        # aggr = an aggregator
        # tags = tags to the points that defined a timeserie
        # start = the initial value for the time interval
        # end = (Optional) the final value for the interval (default = now)
        # nots = return only values and no timestamps
        # tsd = return timestamps as datetime objects / other option will be a integer
        # json = if True will return the exact response of the http request
        # show_summary = Add information summary of the query
        # union = return the points of the time series (Metric+Tags) in one list
        # chunked: will be implemented in future, to stream over urllib3
        # Example: /api/query?m=sum:test_post{test=*}&start=1d-ago
        # other options in query: &no_annotations=true&global_annotations=false&show_summary=true
        # More available: http://opentsdb.net/docs/build/html/api_http/query/index.html
        restore_conn = False
        if self.wctype != 'http':
            restore_conn = True
            self._connect('http')
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
            if restore_conn:
                self._connect('telnet')
            return result
        else:
            print 'No results found'
            if restore_conn:
                self._connect('telnet')
            return []
