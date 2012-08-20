# -*- coding: utf8 -*-

'''
This is the core part, currently only managing the global
DB of point evaluations. For more, look into the strategy.py file.
'''

from config import loggers
logger = loggers['core']
from panobbgo_problems import Result

class Results(object):
  '''
  List of results w/ notificaton for new results.
  Later on, this will be a cool database.
  '''
  def __init__(self, strategy):
    import numpy as np
    self._strategy = strategy
    self._results = []
    self._last_nb = 0 #for logging
    self.fx_delta_last = None
    self._best = Result(None, np.infty)

    # grid for storing points which are nearby.
    # maps from rounded coordinates tuple to point
    self._grid = dict()
    self._grid_div = 5.
    self._grid_lengths = self.problem.ranges / float(self._grid_div)

  def in_same_grid(self, point):
    key = tuple(self._grid_mapping(point.x))
    return self._grid.get(key, [])

  def _grid_mapping(self, x):
    from numpy import floor
    l = self._grid_lengths
    #m = self._problem.box[:,0]
    return tuple(floor(x / l) * l)

  def _grid_add(self, r):
    key = self._grid_mapping(r.x)
    bin = self._grid.get(key, [])
    bin.append(r)
    self._grid[key] = bin

  def add_results(self, new_results):
    '''
    add one single or a list of new @Result objects.
    * calc some statistics
    * send out new_results & new_result events
    '''
    import heapq
    if isinstance(new_results, Result):
      new_results = [ new_results ]
    # notification for all recieved results at once
    self.eventbus.publish("new_results", results = new_results)
    for r in new_results:
      assert isinstance(r, Result), "Got object of type %s != Result" % type(r)
      heapq.heappush(self._results, r)
      self._grid_add(r)
      self.eventbus.publish("new_result", result = r)
    if len(self._results) / 100 > self._last_nb / 100:
      #self.info()
      self._last_nb = len(self._results)

  def info(self):
    logger.info("%d results in DB" % len(self._results))

  def __iadd__(self, results):
    self.add_results(results)
    return self

  def __len__(self):
    return len(self._results)

  @property
  def best(self): return self._best

  @property
  def strategy(self): return self._strategy

  @property
  def eventbus(self): return self._strategy.eventbus

  @property
  def problem(self): return self._strategy.problem

  def n_best(self, n):
    import heapq
    return heapq.nsmallest(n, self._results)

class Event(object):
  '''
  This class holds the data for one single @EventBus event.
  '''
  def __init__(self, **kwargs):
    from IPython.utils.timing import time
    self._when   = time.time()
    self._kwargs = kwargs
    for k, v in kwargs.iteritems():
      setattr(self, k, v)

  def __repr__(self):
    return "Event[%s]" % self._kwargs

class EventBus(object):
  '''
  This event bus is used to publish and send events.
  E.g. it is used to send information like "new best point"
  to all subscribing heuristics.
  '''
  # pattern for a valid key
  import re
  _re_key = re.compile(r'^[a-z_]+$')

  def __init__(self):
    self._subs = {}

  @property
  def keys(self):
    return self._subs.keys()

  def register(self, target):
    '''
    registers a target for this event bus instance. it needs to have
    "on_<key>" methods.
    '''
    from heuristics import StopHeuristic
    from Queue import Empty, LifoQueue
    from threading import Thread

    # important: this decouples the dispatcher's thread from the actual target
    def run(key, target):
      isfirst = True
      while True:
        # draining the queue... otherwise it might get really huge
        # it's up to the heuristics to only work with the most important points
        events = []
        try:
          while True:
            events.append(target._eventbus_events[key].get(block=isfirst))
            isfirst = False
        except Empty:
          isfirst = True

        try:
          newpoints = getattr(target, 'on_%s' % key)(events)
          # heuristics might call self.emit and/or return a list
          if newpoints != None: target.emit(newpoints)
        except StopHeuristic:
          logger.info("'%s' for 'on_%s' stopped -> unsubscribing." % (target.name, key))
          self.unsubscribe(key, target)

    target._eventbus_events = {}
    # bind all 'on_<key>' methods to events in the eventbus
    import inspect
    for name, _ in inspect.getmembers(target, predicate=inspect.ismethod):
      if not name.startswith("on_"): continue
      key = name[3:]
      target._eventbus_events[key] = LifoQueue()
      t = Thread(target = run, args = (key, target,),
          name='EventBus: %s/%s'%(target.name, key))
      t.daemon = True
      t.start()
      # thread running, now subscribe to events
      self.subscribe(key, target)

  def _check_key(self, key):
    if not EventBus._re_key.match(key):
      raise Exception('EventBus: "%s" key not allowed' % key)

  def subscribe(self, key, target):
    self._check_key(key)
    if not key in self._subs:
      self._subs[key] = []

    assert target not in self._subs[key]
    self._subs[key].append(target)

  def unsubscribe(self, key, target):
    self._check_key(key)
    if not key in self._subs:
      logger.critical("cannot unsubscribe unknown key '%s'" % key)
      return
    if target in self._subs[key]:
      # TODO this might be called more than once ... fixable?
      self._subs[key].remove(target)

  def publish(self, key, **kwargs):
    if key not in self._subs:
      #logger.warning("EventBus: key '%s' unknown." % key)
      return

    for target in self._subs[key]:
      event = Event(**kwargs)
      #logger.info("EventBus: publishing %s -> %s" % (key, event))
      target._eventbus_events[key].put(event)
