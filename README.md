otsdb_client
============

A simple Python client to OpenTSDB.
The writing method (put) uses a simple socket and the reading a http request made trough the urllib3.

The current implementation will not use a worker, fancy multithread control or stream for chunked results. It's a start point to a good (hope) OpenTSDB client.

This package as made and tested only with Python 2.7.

# ToDo:

* Check for limits and blocking impacts;
* Implement worker or multithread;
* Implement the reading with chunks.

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

Usage
===
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

License
=======
This packaged is released and distributed under the license GNU GPL Version 2, June 1991.
