"""

  wxAnyThread:  allow methods on wxPython objects to be called from any thread

In wxPython, methods that alter the state of the GUI are only safe to call from
the thread running the main event loop.  Other threads must typically post
events to the GUI thread instead of invoking methods directly.

While there are builtin shortcuts for this (e.g. wx.CallAfter) they do not
capture the full semantics of a function call.  This module provides an easy
way to invoke methods from any thread *transparently*, propagating return
values and exceptions back to the calling thread.

The main interface is a decorator named "anythread", which can be applied
to methods to make them safe to call from any thread, like so:

from .wxAnyThread import anythread # For correct use of the threads with the GUI in wxPython.

  class MyFrame(wx.Frame):

     @anythread
     def GetSomeData():
         dlg = MyQueryDialog(self,"Enter some data")
         if dlg.ShowModal() == wx.ID_OK:
             resp = dlg.GetResponse()
             return int(resp)
         else:
             raise NoDataEnteredError()

The GetSomeData method can now be directly invoked from any thread.
The calling thread will block while the main GUI thread shows the dialog,
and will then receive a return value or exception as appropriate.

"""

__ver_major__ = 0
__ver_minor__ = 2
__ver_patch__ = 2
__ver_sub__ = ""
__version__ = "%d.%d.%d%s" % (__ver_major__,__ver_minor__,
                              __ver_patch__,__ver_sub__)

import wx
import sys
import threading

__all__ = ['anythread']

_EVT_INVOKE_METHOD = wx.NewId()

class MethodInvocationEvent(wx.PyEvent):
    """Event fired to the GUI thread indicating a method invocation."""

    def __init__(self,func,args,kwds):
        wx.PyEvent.__init__(self)
        self.SetEventType(_EVT_INVOKE_METHOD)
        self.func = func
        self.args = args
        self.kwds = kwds
        self.event = threading.Event()

    def invoke(self):
        """Invoke the method, blocking until the main thread handles it."""
        wx.PostEvent(self.args[0],self)
        self.event.wait()
        try:
            return self.result
        except AttributeError:
            tb = self.traceback
            del self.traceback
            raise (type(self.exception), self.exception, tb)

    def process(self):
        """Execute the method and signal that it is ready."""
        try:
            self.result = self.func(*self.args,**self.kwds)
        except Exception as e:
            _,self.exception,self.traceback = sys.exc_info()
        self.event.set()


def handler(evt):
    """Simple event handler to register for invocation events."""
    evt.process()


def anythread(func):
    """Method decorator allowing call from any thread.

    The method is replaced by one that posts a MethodInvocationEvent to the
    object, then blocks waiting for it to be completed.  The target object
    is automatically connected to the _EVT_INVOKE_METHOD event if it wasn't
    alread connected.

    When invoked from the main thread, the function is executed immediately.
    """
    def invoker(*args,**kwds):
        #if wx.Thread_IsMain():
        if wx.IsMainThread():
            return func(*args,**kwds)
        else:
            self = args[0]
            if not hasattr(self,"_AnyThread__connected"):
                self.Connect(-1,-1,_EVT_INVOKE_METHOD,handler)
                self._AnyThread__connected = True
            evt = MethodInvocationEvent(func,args,kwds)
            return evt.invoke()
    invoker.__name__ = func.__name__
    invoker.__doc__ = func.__doc__
    return invoker


