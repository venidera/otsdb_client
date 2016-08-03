# otsdb_client

[![GitHub Release](https://img.shields.io/badge/release-v0.0.3-blue.svg)](https://github.com/venidera/otsdb_client/releases)
[![Build Status](https://img.shields.io/badge/build-passing-green.svg)](https://github.com/venidera/otsdb_client)
[![GitHub license](https://img.shields.io/badge/license-GPLv3-yellow.svg)](https://raw.githubusercontent.com/venidera/otsdb_client/master/LICENSE)

A simple Python Client to async consume of OpenTSDB HTTP API
The writing method (put) was initially done using a simple socket and the reading http request made trough the urllib3.
We refactory everything to use only HTTP with grequests.

This package was made and tested with Python 2.7 and 3.5.

## Table of contents

* [Requirements](#requirements)
* [Installation](#installation)
* [To-do list](#todolist)
* [How to use](#howtouse)
* [Maintainers](#maintainers)
* [License](#license)

## Requirements:

* grequests==0.3.0

## Installation

Clone the repo for development purposes:

```
$ git clone https://github.com/venidera/otsdb_client.git
$ cd otsdb_client
$ virtualenv --python=python3.5 --prompt=" OTSDB Client " venv-3.5
$ source venv-3.5/bin/activate ; pip install pip setuptools --upgrade
$ python setup.py install
```

Install using pip:

```
$ pip install git+https://github.com/venidera/otsdb_client.git
```

## To-do list

* Check for limits and blocking impacts: Done - Solution: use grequests to make async http calls;
* Implement worker or multithread: pending (inpired by [potsdb](https://github.com/orionvm/potsdb));
* Implement the reading with chunks: pending.

## How to use

```python
>>> from otsdb_client import Connection
>>> c = Connection(server='localhost', port=4242)
>>> c.put(metric='test_put',timestamps=[int(mktime(datetime.now().timetuple()))],values=[2000.00],tags={'tagk':'tagv'})

>>> c.query(metric='test_put',aggr='sum',tags={'test':'*'},start='1h-ago')
{'results': [{'metric': u'test_put', 'values': [2000.0], 'ts': [datetime.datetime(2016, 2, 4, 0, 28, 19)], 'tags': {u'test': u'client', u'type': u'telnet'}}]}
>>> c.query(metric='test_put',aggr='sum',tags={'test':'*'},start='1h-ago',union=True)
{'results': {'values': [2000.0], 'ts': [datetime.datetime(2016, 2, 4, 0, 28, 19)]}}
```

### Methods

The following OpenTSDB related methods are currently implemented at `otsdb_client/rest/client.py`:

* `version()` from **[/api/version](http://opentsdb.net/docs/build/html/api_http/version.html)**
* `filters()` from **[/api/config/filters](http://opentsdb.net/docs/build/html/api_http/config/filters.html)**
* `statistics()` from **[/api/stats](http://opentsdb.net/docs/build/html/api_http/stats.html)**
* `aggregators()` from **[/api/aggregators](http://opentsdb.net/docs/build/html/api_http/aggregators.html)**
* `put()` from **[/api/put](http://opentsdb.net/docs/build/html/api_http/put.html)**
* `suggest()` from **[/api/suggest](http://opentsdb.net/docs/build/html/api_http/suggest.html)**
* `query()` from **[/api/query](http://opentsdb.net/docs/build/html/api_http/query.html)**
* `query_exp()` from **[/api/query/exp](http://opentsdb.net/docs/build/html/api_http/query/exp.html)**

#### Class instantiation (`__init__`):

Create objects of otsdb_client to execute read/write operations with OpenTSDB:

```python
class Connection(object):
    def __init__(self,server='localhost', port=4242):
        ...
```
Arguments:

* server (str): the IP address or URI of the server that will be accessed;
* port (int): the port that TSD is running.

 Example:

```python
>>> from otsdb_client import Connection
>>> c = Connection()
```
### Write data to OpenTSDB (`put`):

Insert a point (timestamp+value) into a Time Serie (Metric + Tags). At this moment, only one point can be added per call.

```python
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

```python
c.put(metric='sys.mem.used',value=4321,tags={'host':'server1'})
```

Now insert a point (ts/value) for a metric in `2012-01-10 13:00`:

```python
from datetime import datetime
from time import mktime
ts = int(mktime(datatime(2012,01,10,13,00).timetuple()))
c.put(metric='metric.name',ts=ts,value=321.20,tags={'tagname':'tagvalue'})
```

### Read data to OpenTSDB (`query`):

Read points (aggregated  or not) of a time serie. At this moment, only simple use of the `/api/query` endpoint was implemented. The aggregator defined will be validated with the `/api/aggregators` endpoint results.

```python
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

```python
results = c.query(metric='metric_name',aggr='sum',tags={'tagn':'*'},start='1d-ago')
```

### Tests

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

## Maintainers

**Andre E. Toscano** and **Rafael G. Vieira** from [Venidera Research and Development](http://portal.venidera.com).

## License

This package is released and distributed under the license [GNU GPL Version 3, 29 June 2007](https://www.gnu.org/licenses/gpl-3.0.html).
