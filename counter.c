#include <stdint.h>

#include <Python.h>

#define MODULE_DOC \
"Provides bounded counters for python."

#define UINT64_DOC \
"Represents an unsigned 64 bit integer."

#define E_UINT64_ARGS \
"expected a positive integer"

typedef struct {
    PyObject_HEAD
    uint64_t cnt;
} counter_UInt64;

static void
UInt64_dealloc(counter_UInt64* self)
{
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject *
UInt64_new(PyTypeObject* type, PyObject* args, PyObject* kwds)
{
    return (PyObject*)((counter_UInt64*)type->tp_alloc(type, 0));
}

static int
UInt64_init(counter_UInt64* self)
{
    self->cnt = 0;
    return 0;
}

static PyObject*
UInt64_inc(counter_UInt64* self)
{
    return PyLong_FromUnsignedLong(++self->cnt);
}

static PyMethodDef UInt64_methods[] =
{
    {
        "inc",
        (PyCFunction)UInt64_inc,
        METH_NOARGS,
        NULL
    },
    {
        NULL
    }
};

static PyTypeObject counter_UInt64Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "counter.UInt64",                           /* tp_name */
    sizeof(counter_UInt64),                     /* tp_basicsize */
    0,                                          /* tp_itemsize */
    (destructor)UInt64_dealloc,                 /* tp_dealloc */
    0,                                          /* tp_print */
    0,                                          /* tp_getattr */
    0,                                          /* tp_setattr */
    0,                                          /* tp_reserved */
    0,                                          /* tp_repr */
    0,                                          /* tp_as_number */
    0,                                          /* tp_as_sequence */
    0,                                          /* tp_as_mapping */
    0,                                          /* tp_hash  */
    0,                                          /* tp_call */
    0,                                          /* tp_str */
    0,                                          /* tp_getattro */
    0,                                          /* tp_setattro */
    0,                                          /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,   /* tp_flags */
    UINT64_DOC,                                 /* tp_doc */
    0,                                          /* tp_traverse */
    0,                                          /* tp_clear */
    0,                                          /* tp_richcompare */
    0,                                          /* tp_weaklistoffset */
    0,                                          /* tp_iter */
    0,                                          /* tp_iternext */
    UInt64_methods,                             /* tp_methods */
    0,                                          /* tp_members */
    0,                                          /* tp_getset */
    0,                                          /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    (initproc)UInt64_init,                      /* tp_init */
    0,                                          /* tp_alloc */
    UInt64_new,                                 /* tp_new */
};


static PyModuleDef countermodule = {
    PyModuleDef_HEAD_INIT,
    "counter",
    MODULE_DOC,
    -1,
    NULL, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit_counter(void)
{
    PyObject* module = NULL;
    counter_UInt64Type.tp_new = PyType_GenericNew;

    if (PyType_Ready(&counter_UInt64Type) < 0)
    {
        return NULL;
    }

    module = PyModule_Create(&countermodule);

    if (module == NULL)
    {
        return NULL;
    }

    Py_INCREF(&counter_UInt64Type);
    PyModule_AddObject(module, "UInt64", (PyObject*)&counter_UInt64Type);

    return module;
}
