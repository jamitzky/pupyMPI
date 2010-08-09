/*

 pupyprof
 Profiler/Tracefile generator for pupyMPI

*/

#include "Python.h"
#include "frameobject.h"
#include "_ytiming.c"

// Global variables
static PyObject *PupyprofError;
static int profrunning;
static time_t profstarttime;
static long long profstarttick;
static long long profstoptick;

char *
_get_current_thread_class_name(void)
{
    PyObject *mthr, *cthr, *tattr1, *tattr2;

    mthr = cthr = tattr1 = tattr2 = NULL;

    mthr = PyImport_ImportModule("threading");
    if (!mthr)
        goto err;
    cthr = PyObject_CallMethod(mthr, "currentThread", "");
    if (!cthr)
        goto err;
    tattr1 = PyObject_GetAttrString(cthr, "__class__");
    if (!tattr1)
        goto err;
    tattr2 = PyObject_GetAttrString(tattr1, "__name__");
    if (!tattr2)
        goto err;

    return PyString_AS_STRING(tattr2);

err:
    Py_XDECREF(mthr);
    Py_XDECREF(cthr);
    Py_XDECREF(tattr1);
    Py_XDECREF(tattr2);
    return NULL; //continue enumeration on err.
}

static int
_yapp_callback(PyObject *self, PyFrameObject *frame, int what,
               PyObject *arg)
{
	return 1;
}


static void
_profile_thread(PyThreadState *ts)
{
	return;
}

static void
_unprofile_thread(PyThreadState *ts)
{
    ts->use_tracing = 0;
    ts->c_profilefunc = NULL;
}

static void
_ensure_thread_profiled(PyThreadState *ts)
{
    PyThreadState *p = NULL;

    for (p=ts->interp->tstate_head ; p != NULL; p = p->next) {
        if (ts->c_profilefunc != _yapp_callback)
            _profile_thread(ts);
    }
}

static void
_enum_threads(void (*f) (PyThreadState *))
{
    PyThreadState *p = NULL;

    for (p=PyThreadState_GET()->interp->tstate_head ; p != NULL; p = p->next) {
        f(p);
    }
}

static int
_init_profiler(void)
{
    return 1;
}

static PyObject*
start(PyObject *self, PyObject *args)
{
    if (profrunning) {
        PyErr_SetString(PupyprofError, "profiler is already started. yappi is a per-interpreter resource.");
        return NULL;
    }

    if (!_init_profiler()) {
        PyErr_SetString(PupyprofError, "profiler cannot be initialized.");
        return NULL;
    }

    _enum_threads(&_profile_thread);

    profrunning = 1;
    time (&profstarttime);
    profstarttick = tickcount();

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
profile_event(PyObject *self, PyObject *args)
{
	char *ev;
	PyObject *arg;
	PyStringObject *event;
	PyFrameObject *frame;

	if(!PyArg_ParseTuple(args, "OOO", &frame, &event, &arg)) {
		return NULL;
	}

	_ensure_thread_profiled(PyThreadState_GET());
	return NULL;
}

static PyObject*
stop(PyObject *self, PyObject *args)
{
    if (!profrunning) {
        PyErr_SetString(PupyprofError, "profiler is not started yet.");
        return NULL;
    }

    _enum_threads(&_unprofile_thread);

    profrunning = 0;
    profstoptick = tickcount();

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef pupyprof_methods[] = {
    {"start", start, METH_VARARGS, NULL},
    {"stop", stop, METH_VARARGS, NULL},
    {"profile_event", profile_event, METH_VARARGS, NULL}, // for internal usage. do not call this.
    {NULL, NULL}      /* sentinel */
};


PyMODINIT_FUNC
init_pupyprof(void)
{
    PyObject *m, *d;

    m = Py_InitModule("_pupyprof",  pupyprof_methods);
    if (m == NULL)
        return;
    d = PyModule_GetDict(m);
    PupyprofError = PyErr_NewException("_pupyprof.error", NULL, NULL);
    PyDict_SetItemString(d, "error", PupyprofError);

    if (!_init_profiler()) {
        PyErr_SetString(PupyprofError, "profiler cannot be initialized.");
        return;
    }
}
