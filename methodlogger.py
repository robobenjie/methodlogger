""" Module related to logging method calls.

Example 1: Basic Usage

@log_method()
def double(a):
  return 2 * a

@log_method()
def add_two(a, b):
  return a + b

@log_method()
def sum_doubled(a, b):
  result = add_two(double(a=a), double(b))
  log("lol gotem!")
  return result

@log_method()
def math():
  log("lets do some math", )
  return add_two(double(4), b=sum_doubled(2,3))
  
Example Output:
 1679191663.43363|MainThread: <math()>
 1679191663.43549|MainThread: . "lets do some math"
 1679191663.43642|MainThread: . <double(4) -> 8 />
 1679191663.43724|MainThread: . <sum_doubled(2, 3)>
 1679191663.43726|MainThread: . . <double(a=2) -> 4 />
 1679191663.43882|MainThread: . . <double(3) -> 6 />
 1679191663.43946|MainThread: . . <add_two(4, 6) -> 10 />
 1679191663.43952|MainThread: . . "lol gotem!"
 1679191663.43955|MainThread: . </sum_doubled -> 10>
 1679191663.43960|MainThread: . <add_two(8, b=10) -> 18 />
 1679191663.43964|MainThread: </math -> 18>
 
Example 2: Alternate log method

import logger

def logger_log(msg, loglevel):
 "Need this to reverse arg order for logger.log"
 logger.log(loglevel, msg)

set_log_method(logger_log)

@log_method(logger.INFO)
def do_thing_one():
 for i in range(100):
   do_fast_thing(i)

@log_method(logger.DEBUG)
def do_fast_thing(i):
  pass
"""
  
import threading
import functools
import time

thread_local = threading.local()

logfn = print

def set_log_method(fn):
  """Call this to change the method used to log methods."""
  global logfn
  logfn = fn

def truncate_str(val):
  """Used in case an argument is like 10000 characters or whatever."""
  return str(val)[:50]

def _print_start_once():
  """Print the start of the previous layer.
  
  We need this because we want to have <selfClosedTags /> if there
  are no children so we have to delay printing the start tag until
  a child log statement wants to be added. Centralized here so that
  log and log_method can share it.
  """
  previous_start_str = getattr(thread_local, 'start_str', None)
  if previous_start_str:
    logfn(
        previous_start_str,
        *thread_local.logger_args,
        **thread_local.logger_kwargs)
  thread_local.start_str = None

def log(message, *logger_args, **logger_kwargs):
  """Log a string at the current indentation value"""
  indent = getattr(thread_local, 'depth', 0)
  thread_name = threading.current_thread().name
  _print_start_once()
  logfn(
      f"{time.time():.5f}|{thread_name}: {'. ' * indent}\"{message}\"",
      *logger_args,
      **logger_kwargs)


def log_method(*logger_args, **logger_kwargs):
  """Main method of the module. Used to decorate methods you want logged."""
  def log_method_inner(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
      indent = getattr(thread_local, 'depth', 0)
      thread_name = threading.current_thread().name
      arg_strs = [truncate_str(a) for a in args]

      # This is a gross hack to remove the 'self' from args
      if args and hasattr(args[0], func.__name__):
        arg_strs = arg_strs[1:]
      arg_strs.extend(f"{name}={truncate_str(val)}" for name, val in kwargs.items())
      start_str = f"{time.time():.5f}|{thread_name}: {'. ' * indent}<{func.__name__}({', '.join(arg_strs)})>"
      _print_start_once()
      thread_local.logger_args = logger_args
      thread_local.logger_kwargs = logger_kwargs
      thread_local.start_str = start_str

      try:
        thread_local.depth = indent + 1
        result = func(*args, **kwargs)
        
        if thread_local.start_str == start_str:
          # No children have been logged: log it as a <selfclose />
          logfn(
              start_str[:-1] + f" -> {truncate_str(result)} />",
              *logger_args,
              **logger_kwargs)
        else:
          logfn(
              f"{time.time():.5f}|{thread_name}: {'. ' * indent}</{func.__name__} -> {truncate_str(result)}>",
              *logger_args,
              **logger_kwargs)
        return result
      except Exception as e:
        if thread_local.start_str == start_str:
          logfn(
              start_str[:-1] + f" !! {e.__class__.__name__}: {e} />",
              *logger_args,
              **logger_kwargs)
        else:
          logfn(
              f"{time.time():.5f}|{thread_name}: {'. ' * indent}</{func.__name__} !! {e.__class__.__name__}: {e}>",
              *logger_args,
              **logger_kwargs)
        raise
      finally:
        thread_local.depth = indent
        thread_local.start_str = None
    return wrapped
  return log_method_inner
