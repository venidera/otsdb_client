otsdb_client
============

A simple Python client to OpenTSDB.
The writing method (put) uses a simple socket and the reading a http request made trough the urllib3.

The current implementation will not use a worker (like the good [potsdb](https://github.com/orionvm/potsdb) package]), fancy multithread control or stream for chunked results. It's a start point to a good (hope) OpenTSDB client.

This package was made and tested only with Python 2.7.

# ToDo:

* Check for limits and blocking impacts;
* Implement worker or multithread;
* Implement the reading with chunks.

# Requirements:

* urllib3>=1.14
* grequests==0.3.0
* numpy==1.11.0

Installation
===
Clone this repo, then
```
$ cd otsdb_client
$ python setup.py install
```
or
```
$ pip install git+https://github.com/venidera/otsdb_client.git
```

Usage (Deprecated - will be updated soon ;) )
===
Complete example of connect, put and read points from OpenTSDB:

```
>>> from otsdb_client import Connection
>>> c = Connection('localhost',4242)
Connected to OpenTSDB
>>> c.put(metric='test_put',value=2000.00,tags={'test':'client','type':'telnet'})
cmd: put test_put 1454552899 2000.00 test=client type=telnet
point written successfully
True
>>> c.query(metric='test_put',aggr='sum',tags={'test':'*'},start='1h-ago')
{'results': [{'metric': u'test_put', 'values': [2000.0], 'ts': [datetime.datetime(2016, 2, 4, 0, 28, 19)], 'tags': {u'test': u'client', u'type': u'telnet'}}]}
>>> c.query(metric='test_put',aggr='sum',tags={'test':'*'},start='1h-ago',union=True)
{'results': {'values': [2000.0], 'ts': [datetime.datetime(2016, 2, 4, 0, 28, 19)]}}
```

## Methods

### Class instantiation (`__init__`):

Create objects of otsdb_client to execute read/write operations with OpenTSDB:

```
class Connection(object):
    def __init__(self,server='localhost', port=4242):
        ...
```

#### Arguments:

* server (str): the IP address or URI of the server that will be accessed;
* port (int): the port that TSD is running.

#### Example:

```
>>> from otsdb_client import Connection
>>> c = Connection()
```

same of

```
>>> c = Connection('localhost',4242)
```

### Write data to OpenTSDB (`put`):

Insert a point (timestamp+value) into a Time Serie (Metric + Tags). At this moment, only one point can be added per call.

```
def put(self,metric,ts=None,value=0.0,tags=dict()):
    ...
```

Better take a look at [OpenTSDB data model and naming schema.](http://opentsdb.net/docs/build/html/user_guide/writing.html)

#### Arguments:

* metric (str): the name of the metric;
* ts (int - Optional): point's integer timestamp (Epoch/Unix timestamp), if it is not passed will assume `ts = int(mktime(datetime.now().timetuple()))`;
* value (float): the value of the point;
* tags (dict()): a dictionary with tagn (tag name) equals tagv (tag value). Example: `tags={'tag1':'valtag1','tag2':'valtag2'}`.

#### Example:

Storing memory used for a server at this moment. So, metric `sys.mem.used` and tag `host`:

```
c.put(metric='sys.mem.used',value=4321,tags={'host':'server1'})
```

Now insert a point (ts/value) for a metric in `2012-01-10 13:00`:

```
from datetime import datetime
from time import mktime
ts = int(mktime(datatime(2012,01,10,13,00).timetuple()))
c.put(metric='metric.name',ts=ts,value=321.20,tags={'tagname':'tagvalue'})
```

### Read data to OpenTSDB (`query`):

Read points (aggregated  or not) of a time serie. At this moment, only simple use of the `/api/query` endpoint was implemented. The aggregator defined will be validated with the `/api/aggregators` endpoint results.

```
def query(self, metric, aggr='sum', tags=dict(), start='1h-ago', end=None, nots=False,\
      tsd=True, json=False,show_summary=False,union=False,chunked=False):
    ...
```

Supports only one metric.

#### Arguments:
* metric (str) : the metric name;
* aggr (str) : an aggregator (example: `sum`, [take a look here](http://opentsdb.net/docs/build/html/api_http/aggregators.html));
* tags (dict) : tags to the points that defined a timeserie ([Naming schema](http://opentsdb.net/docs/build/html/user_guide/writing.html));
* start (str) : starting time for the query ([look here](http://opentsdb.net/docs/build/html/user_guide/query/index.html));
* end (str - Optional): a end time for the query (default = now);
* nots (bool): it's NoTimeStamps in results, if is defined as `True`;
* tsd (bool): return timestamps as datetime objects for `True`, and integer timestamps for `False`;
* json (bool): if True will return the exact response of the http request;
* show_summary (bool): will add information summary of the query when defined `True`;
* union (bool) : return the points of the time series (Metric+Tags) in one list, union for different tags (Be careful here);
* chunked: will be implemented in future, to stream over urllib3.

#### Example:

Query a metric for values of all its tags since 1 day ago:

```
results = c.query(metric='metric_name',aggr='sum',tags={'tagn':'*'},start='1d-ago')
```

License
=======
This package is released and distributed under the license GNU GPL Version 2, June 1991.


# New Doc

# OTSDBclient - A Simple Python Client to OpenTSDB

[![GitHub Release](https://img.shields.io/badge/release-v0.0.2-blue.svg)](https://github.com/venidera/otsdbclient/releases)
[![Build Status](https://img.shields.io/badge/build-passing-green.svg)](https://github.com/venidera/otsdbclient)
[![GitHub license](https://img.shields.io/badge/license-GPLv2-yellow.svg)](https://raw.githubusercontent.com/venidera/otsdbclient/master/LICENSE)

## Table of contents

* [Getting started](#getting-started)
* [Documentation](#documentation)
* [To-do list](#todolist)
* [Contributing](#contributing)
* [Maintainers](#maintainers)
* [License](#license)


## Getting started

Clone the repo with `git clone https://github.com/venidera/otsdbclient.git`, then

```
$ cd otsdbclient
$ python setup.py install
```
or just type
```
$ pip install git+https://github.com/venidera/otsdbclient.git
```

## Documentation

The current implementation will not use a worker (like the good [potsdb](https://github.com/orionvm/potsdb) package]), fancy multithread control or stream for chunked results. It's a start point to a good (hope) OpenTSDB client.

This package was made and tested only with Python 2.7.

Complete example of connect, put and read points from OpenTSDB:

```
>>> from otsdbclient import Client
>>> c = Client(server='localhost', port=4242)
Connected to OpenTSDB
>>> c.put(metric='test_put',value=2000.00,tags={'test':'client','type':'telnet'})
cmd: put test_put 1454552899 2000.00 test=client type=telnet
point written successfully
True
>>> c.query(metric='test_put',aggr='sum',tags={'test':'*'},start='1h-ago')
{'results': [{'metric': u'test_put', 'values': [2000.0], 'ts': [datetime.datetime(2016, 2, 4, 0, 28, 19)], 'tags': {u'test': u'client', u'type': u'telnet'}}]}
>>> c.query(metric='test_put',aggr='sum',tags={'test':'*'},start='1h-ago',union=True)
{'results': {'values': [2000.0], 'ts': [datetime.datetime(2016, 2, 4, 0, 28, 19)]}}
```

## Methods

The following OpenTSDB related methods are currently implemented at `otsdbclient/rest/client.py`:

* `version()` from **[/api/version](http://opentsdb.net/docs/build/html/api_http/version.html)**
* `filters()` from **[/api/config/filters](http://opentsdb.net/docs/build/html/api_http/config/filters.html)**
* `statistics()` from **[/api/stats](http://opentsdb.net/docs/build/html/api_http/stats.html)**
* `aggregators()` from **[/api/aggregators](http://opentsdb.net/docs/build/html/api_http/aggregators.html)**
* `put()` from **[/api/put](http://opentsdb.net/docs/build/html/api_http/put.html)**
* `suggest()` from **[/api/suggest](http://opentsdb.net/docs/build/html/api_http/suggest.html)**
* `query()` from **[/api/query](http://opentsdb.net/docs/build/html/api_http/query.html)**
* `query_exp()` from **[/api/query/exp](http://opentsdb.net/docs/build/html/api_http/query/exp.html)**

### Class instantiation (`__init__`):

Create objects of otsdbclient to execute read/write operations with OpenTSDB:

```
class Connection(object):
    def __init__(self,server='localhost', port=4242):
        ...
```

#### Arguments:

* server (str): the IP address or URI of the server that will be accessed;
* port (int): the port that TSD is running.

#### Example:

```
>>> from otsdbclient import Connection
>>> c = Connection()
```

same of

```
>>> c = Connection('localhost',4242)
```

### Write data to OpenTSDB (`put`):

Insert a point (timestamp+value) into a Time Serie (Metric + Tags). At this moment, only one point can be added per call.

```
def put(self,metric,ts=None,value=0.0,tags=dict()):
    ...
```

Better take a look at [OpenTSDB data model and naming schema.](http://opentsdb.net/docs/build/html/user_guide/writing.html)

#### Arguments:

* metric (str): the name of the metric;
* ts (int - Optional): point's integer timestamp (Epoch/Unix timestamp), if it is not passed will assume `ts = int(mktime(datetime.now().timetuple()))`;
* value (float): the value of the point;
* tags (dict()): a dictionary with tagn (tag name) equals tagv (tag value). Example: `tags={'tag1':'valtag1','tag2':'valtag2'}`.

#### Example:

Storing memory used for a server at this moment. So, metric `sys.mem.used` and tag `host`:

```
c.put(metric='sys.mem.used',value=4321,tags={'host':'server1'})
```

Now insert a point (ts/value) for a metric in `2012-01-10 13:00`:

```
from datetime import datetime
from time import mktime
ts = int(mktime(datatime(2012,01,10,13,00).timetuple()))
c.put(metric='metric.name',ts=ts,value=321.20,tags={'tagname':'tagvalue'})
```

### Read data to OpenTSDB (`query`):

Read points (aggregated  or not) of a time serie. At this moment, only simple use of the `/api/query` endpoint was implemented. The aggregator defined will be validated with the `/api/aggregators` endpoint results.

```
def query(self, metric, aggr='sum', tags=dict(), start='1h-ago', end=None, nots=False,\
      tsd=True, json=False,show_summary=False,union=False,chunked=False):
    ...
```

Supports only one metric.

#### Arguments:
* metric (str) : the metric name;
* aggr (str) : an aggregator (example: `sum`, [take a look here](http://opentsdb.net/docs/build/html/api_http/aggregators.html));
* tags (dict) : tags to the points that defined a timeserie ([Naming schema](http://opentsdb.net/docs/build/html/user_guide/writing.html));
* start (str) : starting time for the query ([look here](http://opentsdb.net/docs/build/html/user_guide/query/index.html));
* end (str - Optional): a end time for the query (default = now);
* nots (bool): it's NoTimeStamps in results, if is defined as `True`;
* tsd (bool): return timestamps as datetime objects for `True`, and integer timestamps for `False`;
* json (bool): if True will return the exact response of the http request;
* show_summary (bool): will add information summary of the query when defined `True`;
* union (bool) : return the points of the time series (Metric+Tags) in one list, union for different tags (Be careful here);
* chunked: will be implemented in future, to stream over urllib3.

#### Example:

Query a metric for values of all its tags since 1 day ago:

```
results = c.query(metric='metric_name',aggr='sum',tags={'tagn':'*'},start='1d-ago')
```

## To-do list

A small list of future improvements is provided below for developers starting to work with otsdbclient.

* Check for limits and blocking impacts;
* Implement the reading with chunks.


## Contributing

Please file a GitHub issue to [report a bug](https://github.com/venidera/otsdbclient/issues).


## Maintainers

**Andre E. Toscano** and **Rafael G. Vieira** from [Venidera Research and Development](http://portal.venidera.com).


## License

This package is released and distributed under the license [GNU GPL Version 2, June 1991](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html).


# Tests

```
# Begining the tests
client = RESTClientTest()

client.test_get_version()
client.test_get_filters()
client.test_get_statistics()
client.test_get_aggregators()
#client.test_put_metric()
client.test_suggest()
client.test_query_metric()
client.test_query_expr_metric()
```

