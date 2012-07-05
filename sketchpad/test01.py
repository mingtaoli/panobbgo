#!/usr/bin/env python
# -*- coding: utf8 -*-

import sys
sys.path.append(".")
from panobbgo import *
import numpy as np


# define problem
class Rosenbrock(Problem):
  '''
  f(x) = sum_i^n-1 (100 (x_{i+1} - x_i^2)^2 + (1-x_i)^2)
  '''
  def __init__(self, dims, par1 = 100):
    box = [(-5,5)] * dims
    self._dims = dims
    self.par1 = par1
    Problem.__init__(self, box)

  def eval(self, x):
    return sum(self.par1 * (x[1:] - x[:-1]**2)**2 + (1-x[:-1])**2)
    


class Rastrigin(Problem):
  '''
  f(x) = 10*n + sum_i^n (x_i^2 - 10 cos(2 pi x_i) )
  '''
  def __init__(self, dims, par1 = 10, offset=0):
    box = [(-5,5)] * dims
    self.offset = offset
    self._dims = dims
    self.par1 = par1
    Problem.__init__(self, box)

  def eval(self, x):
    x -= self.offset
    return self.par1 * self.dim + \
           sum(x**2 - self.par1 * np.cos(2 * np.pi * x))
  
problem = Rosenbrock(3)
#problem = Rastrigin(3, offset=1.1)

results = Results()

rand_pts = RandomPoints(problem, results)
heur_pts = HeuristicPoints(problem, results)
calc_pts = CalculatedPoints(problem, results)

controller = Controller(problem, results, rand_pts,heur_pts,calc_pts)

# keep main thread alive until all created points are also consumed 
# and processed by the evaluator_thread
controller.join()

print results.best()
