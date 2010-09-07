/*

 pupyprof
 Profiler/Tracefile generator for pupyMPI

*/

#include "Python.h"
#include "frameobject.h"
#include "_ytiming.c"
#include "_ymem.c"
#include "_yhashtab.c"

#define EVENTMAP_SIZE 10

// Global variables
static PyObject *PupyprofError;
static int profrunning;
static time_t profstarttime;
static long long profstarttick;
static long long profstoptick;
int state_depth = 1;
static _htab *eventmap;
uintptr_t main_threadstate = NULL;

// States
enum states { STATE_RUNNING, STATE_MPI_COMM, STATE_MPI_COLLECTIVE, 
			  STATE_MPI_WAIT, STATE_FINALIZED, MAX_STATES 
			} current_state;
enum events { EV_COLLECTIVE_ENTER, EV_COLLECTIVE_LEAVE, EV_COMM_ENTER, 
			  EV_COMM_LEAVE, EV_WAIT_ENTER, EV_WAIT_LEAVE, EV_FINALIZE, 
			  EV_UNKNOWN, MAX_EVENTS 
			} new_event;

// stat related definitions
typedef struct {
	struct timeval tv;
	enum states state;
} _statitem; //statitem created while getting stats

// Linked list for storing traces
struct _stat_node_t {
	_statitem *it;
	struct _stat_node_t *next;
};
typedef struct _stat_node_t _statnode; // linked list used for appending stats

static _statnode *statshead;
static _statnode *statstail;

// State names for printing 
char *state_names[] = {"RUNNING", "MPI_COMM", "MPI_COLLECTIVE", "MPI_WAIT", "FINALIZED"};
char *event_names[] = {"COLLECTIVE_ENTER", "COLLECTIVE_LEAVE", "COMM_ENTER", "COMM_LEAVE", 
					   "WAIT_ENTER", "WAIT_LEAVE", "FINALIZE", "UNKNOWN"};

// State transition table and change functions {{{
void _state_change(enum states);
inline void _ev_nothing(void) {
	/* Do nothing */
}

void _ev_collective_enter(void) {
	_state_change(STATE_MPI_COLLECTIVE);
}

void _ev_collective_leave(void) {
	_state_change(STATE_RUNNING);
}

void _ev_comm_enter(void) {
	_state_change(STATE_MPI_COMM);
}

void _ev_comm_leave(void) {
	_state_change(STATE_RUNNING);
}

void _ev_wait_enter(void) {
	_state_change(STATE_MPI_WAIT);
}

void _ev_wait_leave(void) {
	_state_change(STATE_RUNNING);
}

void _ev_finalize(void) {
	_state_change(STATE_FINALIZED);
}

void _inc_state_depth(void) {
	state_depth++;
}

void (*const state_table [MAX_STATES][MAX_EVENTS]) (void) = {
	{ _ev_collective_enter, _ev_nothing, _ev_comm_enter, _ev_nothing, _ev_wait_enter, _ev_nothing, _ev_finalize, _ev_nothing }, // STATE_RUNNING
	{ _ev_nothing, _ev_nothing, _inc_state_depth, _ev_comm_leave, _ev_nothing, _ev_nothing, _ev_nothing, _ev_nothing }, // STATE_MPI_COMM
	{ _inc_state_depth, _ev_collective_leave, _ev_nothing, _ev_nothing, _ev_nothing, _ev_nothing, _ev_nothing, _ev_nothing }, // STATE_MPI_COLLECTIVE
	{ _ev_nothing, _ev_nothing, _ev_nothing, _ev_nothing, _inc_state_depth, _ev_wait_leave, _ev_nothing, _ev_nothing }, // STATE_MPI_WAIT
	{ _ev_nothing, _ev_nothing, _ev_nothing, _ev_nothing, _ev_nothing, _ev_nothing, _ev_nothing, _ev_nothing }  // STATE_FINALIZED
};
/* End state change functions }}} */

_statitem *
_create_statitem(enum states state)
{
    _statitem *si;

	// Allocate memory for this statitem
    si = (_statitem *)ymalloc(sizeof(_statitem));
    if (!si)
        return NULL;

	// Fill in the given state and current time
	gettimeofday(&si->tv, NULL);
	si->state = state;

	return si;
}

void _state_change(enum states new_state) {
	_statitem *si;
	_statnode *p, *sni;

	// State depth ensures we only count the outermost state changes, ie. those
	// the user initiates
	state_depth--;
	
	if(0 == state_depth) {
		current_state = new_state;
		state_depth++;

		// Create stats item and insert at end of stat list
		si = _create_statitem(new_state);
		sni = (_statnode *)ymalloc(sizeof(_statnode));
		sni->it = si;
		sni->next = NULL;

		if(NULL == statshead) {
			// Empty stats list, just make it the new element
			statstail = statshead = sni;
		} else {
			// Append to tail of stats list
			p = statstail;
			p->next = sni;
			statstail = sni;
		}
	}

	return;
}

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

/*
 * Translate Python code objects into events by looking at the file names and method names.
 *
 * entering indicates whether the interpreter is entering (calling) or leaving
 * (returning from) a method.
 */
enum events _event_from_code(PyCodeObject *co, int entering) {
	char *filename, *name;
	_hitem *it;
	enum events ev;

	// Employ a hash map to make code object lookups faster, as the address of
	// the code object does not change.
	it = hfind(eventmap, (uintptr_t)co);
	if(it) {
		// If in a leaving context return the corresponding LEAVE event
		if(!entering) {
			switch((enum events) it->val) {
				case EV_COLLECTIVE_ENTER:
					return EV_COLLECTIVE_LEAVE;
					break;
				case EV_WAIT_ENTER:
					return EV_WAIT_LEAVE;
					break;
				case EV_COMM_ENTER:
					return EV_COMM_LEAVE;
					break;
				default:
					break;
			}
		}
		return (enum events) it->val;
	}

	filename = PyString_AS_STRING(co->co_filename);
	name = PyString_AS_STRING(co->co_name);

	// Simple strstr lookups - this is horribly slow, hence the hash map above
	if(NULL != strstr(filename, "pupympi/mpi/communicator.py")) {
		// Collective operations
		if(0 == strcmp(name, "allgather") || 0 == strcmp(name, "allreduce") || 0 == strcmp(name, "alltoall") || 
		   0 == strcmp(name, "barrier") || 0 == strcmp(name, "bcast") || 0 == strcmp(name, "gather") ||
		   0 == strcmp(name, "reduce") || 0 == strcmp(name, "scan") || 0 == strcmp(name, "scatter")) {
			// Return collective event enter or leave
			if(entering)
				ev = EV_COLLECTIVE_ENTER;
			else
				ev = EV_COLLECTIVE_LEAVE;
			goto out;
		}
		// Point-to-point communication
		if(0 == strcmp(name, "send") || 0 == strcmp(name, "isend") || 0 == strcmp(name, "recv") || 0 == strcmp(name, "irecv")) {
			ev = entering ? EV_COMM_ENTER : EV_COMM_LEAVE;
			goto out;
		}
		// Waiting
		if(0 == strcmp(name, "waitsome") || 0 == strcmp(name, "waitany") || 0 == strcmp(name, "waitall")) {
			if(entering)
				ev = EV_WAIT_ENTER;
			else
				ev = EV_WAIT_LEAVE;
			goto out;
		}
	}
	// Single request waiting
	if(NULL != strstr(filename, "pupympi/mpi/request.py") && 0 == strcmp(name, "wait")) {
		if(entering)
			ev = EV_WAIT_ENTER;
		else
			ev = EV_WAIT_LEAVE;
		goto out;
	}
	// Finalize
	if(NULL != strstr(filename, "pupympi/mpi/__init__.py") && 0 == strcmp(name, "finalize")) {
		ev = EV_FINALIZE;
		goto out;
	}

	ev = EV_UNKNOWN;
out:
	hadd(eventmap, (uintptr_t)co, ev);
	return ev;
}

static void
_call_enter(PyObject *self, PyFrameObject *frame, PyObject *arg, int ccall)
{
	// A method was entered. Look up the code object, get the corresponding
	// event and run the state change function.
	new_event = _event_from_code(frame->f_code, 1);

	state_table[current_state][new_event]();
	
}

static void
_call_leave(PyObject *self, PyFrameObject *frame, PyObject *arg)
{
	// A method was left. Look up the code object, get the corresponding event
	// and run the state change function.
	new_event = _event_from_code(frame->f_code, 0);
	
	state_table[current_state][new_event]();
}

static int
_prof_callback(PyObject *self, PyFrameObject *frame, int what,
               PyObject *arg)
{
	// We're only concerned about what the main thread is doing
	// (hopefully nobody renamed it...)
	// As with the code object to event translations, caching the address of
	// the main thread is much faster than running string comparisons all the
	// time.
	if(!main_threadstate) {
		if(0 == strcmp("_MainThread", _get_current_thread_class_name())) {
			main_threadstate = (uintptr_t)frame->f_tstate;
		} else {
			return 0;
		}
	} 
	if(main_threadstate != (uintptr_t)frame->f_tstate) {
		return 0;
	}
	
	switch (what) {
    case PyTrace_CALL:
        _call_enter(self, frame, arg, 0);
        break;
    case PyTrace_RETURN: // either normally or with an exception
        _call_leave(self, frame, arg);
        break;

    default:
        break;
    }

	return 0;
}


static void
_profile_thread(PyThreadState *ts)
{
	ts->use_tracing = 1;
	ts->c_profilefunc = _prof_callback;
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
        if (ts->c_profilefunc != _prof_callback)
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
	statshead = statstail = NULL;
	eventmap = htcreate(EVENTMAP_SIZE);
	if(!eventmap)
		return 0;
    return 1;
}

static PyObject*
start(PyObject *self, PyObject *args)
{
    if (profrunning) {
        PyErr_SetString(PupyprofError, "profiler is already started. pupyprof is a per-interpreter resource.");
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
	_state_change(STATE_RUNNING);

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
    
	ev = PyString_AS_STRING(event);

    if (strcmp("call", ev)==0)
        _prof_callback(self, frame, PyTrace_CALL, arg);
    else if (strcmp("return", ev)==0)
        _prof_callback(self, frame, PyTrace_RETURN, arg);
    else if (strcmp("c_call", ev)==0)
        _prof_callback(self, frame, PyTrace_C_CALL, arg);
    else if (strcmp("c_return", ev)==0)
        _prof_callback(self, frame, PyTrace_C_RETURN, arg);
    else if (strcmp("c_exception", ev)==0)
        _prof_callback(self, frame, PyTrace_C_EXCEPTION, arg);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
get_stats(PyObject *self, PyObject *args)
{

    _statnode *p;
    PyObject *buf,*li;
    int fcnt;
	char temp[128];

    li = buf = NULL;

    li = PyList_New(0);
    if (!li)
        goto err;
    if (PyList_Append(li, PyString_FromString("# Timestamp    State")) < 0)
        goto err;

    fcnt = 0;
    p = statshead;
    while(p) {
		snprintf(temp, 127, "%.3f %s", (p->it->tv.tv_sec + (p->it->tv.tv_usec / 1000000.0)), state_names[p->it->state]);
        buf = PyString_FromString(temp);
        if (!buf)
            goto err;
        if (PyList_Append(li, buf) < 0)
            goto err;

        Py_DECREF(buf);
        fcnt++;
        p = p->next;
    }

    return li;
err:
    Py_XDECREF(li);
    Py_XDECREF(buf);
    return NULL;
}

void
clear_stats(PyObject *self, PyObject *args)
{
	_statnode *p;

	p = statshead;

	statshead = statstail = NULL;

	while(NULL != p) {
		p = p->next;
		yfree(p->it);
		yfree(p);
	}
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
    {"get_stats", get_stats, METH_VARARGS, NULL},
    {"clear_stats", clear_stats, METH_VARARGS, NULL},
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
