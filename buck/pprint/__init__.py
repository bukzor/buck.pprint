###
#  Author:      Buck Evan
#               buck.2019@gmail.com
#  Changes:
#       all methods return their "allowance"
#       indent is now incremented by _indent_per_level
#
####
#  Author:      Fred L. Drake, Jr.
#               fdrake@acm.org
#
#  This is a simple little module I wrote to make life easier.  I didn't
#  see anything quite like it in the library, though I may have overlooked
#  something.  I wrote this when I was trying to read some heavily nested
#  tuples with fairly non-descriptive content.  This is modeled very much
#  after Lisp/Scheme - style pretty-printing of lists.  If you find it
#  useful, thank small children who sleep at night.

"""Support to pretty-print lists, tuples, & dictionaries recursively.

Very simple, but useful, especially in debugging data structures.

Classes
-------

PrettyPrinter()
    Handle pretty-printing operations onto a stream using a configured
    set of formatting parameters.

Functions
---------

pformat()
    Format a Python object into a pretty-printed representation.

pprint()
    Pretty-print a Python object to a stream [default is sys.stdout].

saferepr()
    Generate a 'standard' repr()-like value, but protect against recursive
    data structures.

"""

import collections as _collections
import re
import sys as _sys
import types as _types
from io import StringIO as _StringIO

__all__ = ["pprint","pformat","isreadable","isrecursive","saferepr",
           "PrettyPrinter"]


def pprint(object, stream=None, indent=4, width=80, depth=None, *,
           compact=False):
    """Pretty-print a Python object to a stream [default is sys.stdout]."""
    printer = PrettyPrinter(
        stream=stream, indent=indent, width=width, depth=depth,
        compact=compact)
    printer.pprint(object)

def pformat(object, indent=4, width=80, depth=None, *, compact=False):
    """Format a Python object into a pretty-printed representation."""
    return PrettyPrinter(indent=indent, width=width, depth=depth,
                         compact=compact).pformat(object)

def saferepr(object):
    """Version of repr() which can handle recursive data structures."""
    return _safe_repr(object, {}, None, 0)[0]

def isreadable(object):
    """Determine if saferepr(object) is readable by eval()."""
    return _safe_repr(object, {}, None, 0)[1]

def isrecursive(object):
    """Determine if object requires a recursive representation."""
    return _safe_repr(object, {}, None, 0)[2]

class _safe_key:
    """Helper function for key functions when sorting unorderable objects.

    The wrapped-object will fallback to a Py2.x style comparison for
    unorderable types (sorting first comparing the type name and then by
    the obj ids).  Does not work recursively, so dict.items() must have
    _safe_key applied to both the key and the value.

    """

    __slots__ = ['obj']

    def __init__(self, obj):
        self.obj = obj

    def __lt__(self, other):
        obj1 = self.safe_key()
        obj2 = other.safe_key()
        try:
            return obj1 < obj2
        except TypeError:
            return ((str(type(self.obj)), id(self.obj)) < \
                    (str(type(other.obj)), id(other.obj)))

    def safe_key(self):
        if isinstance(self.obj, (set, frozenset)):
            return (len(self.obj), sorted(_safe_key(x).safe_key() for x in self.obj))
        else:
            return self.obj

    def __repr__(self):
        return '_safe_key(%r)' % self.obj


def _safe_tuple(t):
    "Helper function for comparing 2-tuples"
    return _safe_key(t[0]), _safe_key(t[1])


def clsname(obj):
    cls = type(obj)
    module = cls.__module__
    name = cls.__qualname__
    if module in ('__main__', 'builtins', 'collections'):
        return name
    else:
        return module + '.' + name


class PrettyPrinter:
    def __init__(self, indent=4, width=80, depth=None, stream=None, *,
                 compact=False):
        """Handle pretty printing operations onto a stream using a set of
        configured parameters.

        indent
            Number of spaces to indent for each level of nesting.

        width
            Attempted maximum number of columns in the output.

        depth
            The maximum depth to print out nested structures.

        stream
            The desired output stream.  If omitted (or false), the standard
            output stream available at construction will be used.

        compact
            If true, several items will be combined in one line.

        """
        indent = int(indent)
        width = int(width)
        if indent < 0:
            raise ValueError('indent must be >= 0')
        if depth is not None and depth <= 0:
            raise ValueError('depth must be > 0')
        if not width:
            raise ValueError('width must be != 0')
        self._depth = depth
        self._indent_per_level = indent
        self._width = width
        if stream is not None:
            self._stream = stream
        else:
            self._stream = _sys.stdout
        self._compact = bool(compact)

    def pprint(self, object):
        self._format(object, self._stream, 0, 0, {}, 0)
        self._stream.write("\n")

    def pformat(self, object):
        sio = _StringIO()
        self._format(object, sio, 0, 0, {}, 0)
        return sio.getvalue()

    def isrecursive(self, object):
        return self.format(object, {}, 0, 0)[2]

    def isreadable(self, object):
        s, readable, recursive = self.format(object, {}, 0, 0)
        return readable and not recursive

    def _format(self, object, stream, indent, allowance, context, level):
        """The core pretty-printing function.

        Input:
            object -- The value to be pretty-printed.
            stream -- The file-like output of this pretty-print.
        
        State variables, used in recursion:
            indent -- The "current" indentation level, as an integer count of columns.
            allowance -- The number of columns already "used up" on the current line,
                not counting indentation.  It seems that this value was totally broken
                in stdlib cpython pprint.
            context -- The set of all nested objects above this one, used for
                cycle detection.
            level -- The count of how many objects are nested "above" this one.
                This is used in implementing the "depth" feature of PrettyPrinter.
        """
        objid = id(object)
        write = stream.write
        if objid in context:
            rep = _recursion(object)
            write(rep)
            replen = len(rep)
            allowance += rep
            self._recursive = True
            self._readable = False
            return allowance
        rep = self._repr(object, context, level)
        replen = len(rep)
        if replen + indent + allowance >= self._width:
            p = self._dispatch.get(type(object).__repr__, None)
            if p is not None:
                context[objid] = 1
                allowance = p(self, object, stream, indent, allowance, context, level + 1)
                del context[objid]
                return allowance
            elif isinstance(object, dict):
                context[objid] = 1
                allowance = self._pprint_dict(object, stream, indent, allowance,
                                  context, level + 1)
                del context[objid]
                return allowance
        stream.write(rep)
        allowance += replen
        return allowance

    _dispatch = {}

    def _pprint_dict(self, object, stream, indent, allowance, context, level):
        write = stream.write
        write('{')
        length = len(object)
        if length:
            multibracket = length <= 1
            if not multibracket:
                indent += self._indent_per_level
                write('\n' + indent * ' ')
                allowance = 0
            items = sorted(object.items(), key=_safe_tuple)
            allowance = self._format_dict_items(items, stream, indent, allowance,
                                    context, level)
            if not multibracket:
                indent -= self._indent_per_level
                write(indent * ' ')
        write('}')
        allowance += 1
        return allowance

    _dispatch[dict.__repr__] = _pprint_dict

    def _pprint_ordered_dict(self, object, stream, indent, allowance, context, level):
        if len(object):
            args = (list(object.items()),)
        else:
            args = ()
        return self._pprint_constructor(
            object, args,
            stream, indent, allowance + 1, context, level,
        )

    _dispatch[_collections.OrderedDict.__repr__] = _pprint_ordered_dict

    def _pprint_list(self, object, stream, indent, allowance, context, level):
        stream.write('[')
        allowance = self._format_items(object, stream, indent, allowance + 2,
                           context, level)
        stream.write(']')
        return allowance + 1

    _dispatch[list.__repr__] = _pprint_list

    def _pprint_constructor(self, object, args, stream, indent, allowance, context, level, kwargs=None):
        name = clsname(object)
        stream.write(name)
        stream.write('(')
        allowance += len(name) + 2
        allowance = self._format_items(
            args, stream, indent, allowance, context, level,
        )
        if kwargs is not None:
            if allowance != 0:
                stream.write(', ')
                allowance += 2
            kwargs = sorted(kwargs.items(), key=_safe_tuple)
            allowance = self._format_kwargs(
                kwargs, stream, indent, allowance, context, level,
            )
        stream.write(')')
        return allowance + 1

    def _pprint_tuple(
            self, object, stream, indent, allowance, context, level,
    ):
        stream.write('(')
        allowance += 1
        allowance = self._format_items(
            object, stream, indent, allowance, context, level,
        )
        if len(object) == 1 and allowance != 0:
            endchar = ',)'
        else:
            endchar = ')'
        stream.write(endchar)
        return allowance + len(endchar)

    _dispatch[tuple.__repr__] = _pprint_tuple

    def _pprint_set(self, object, stream, indent, allowance, context, level):
        typ = object.__class__
        if typ is set:
            if not len(object):
                # because {} makes a dict...
                return self._pprint_constructor(
                    object, (),
                    stream, indent, allowance, context, level,
                )
            stream.write('{')
            object = sorted(object, key=_safe_key)
            allowance = self._format_items(
                object, stream, indent, allowance + 2, context, level,
            )
            stream.write('}')
            return allowance + 1
        else:
            return self._pprint_constructor(
                object, (set(object),), stream, indent, allowance, context, level,
            )

    _dispatch[set.__repr__] = _pprint_set
    _dispatch[frozenset.__repr__] = _pprint_set

    def _pprint_str(self, object, stream, indent, allowance, context, level):
        write = stream.write
        if not len(object):
            rep = repr(object)
            write(rep)
            return allowance + len(rep)
        chunks = []
        lines = object.splitlines(True)
        indent += self._indent_per_level
        max_width1 = max_width = self._width - indent
        for i, line in enumerate(lines):
            rep = repr(line)
            if len(rep) <= max_width1:
                chunks.append(rep)
            else:
                # A list of alternating (non-space, space) strings
                parts = re.findall(r'\S*\s*', line)
                assert parts
                assert not parts[-1]
                parts.pop()  # drop empty last part
                current = ''
                for j, part in enumerate(parts):
                    candidate = current + part
                    if len(repr(candidate)) >= max_width:
                        if current:
                            chunks.append(repr(current))
                        current = part
                    else:
                        current = candidate
                if current:
                    chunks.append(repr(current))
        if len(chunks) == 1:
            write(rep)
            replen = len(rep)
            return allowance + replen
        write('(')
        for i, rep in enumerate(chunks):
            write('\n' + ' '*indent)
            write(rep)
        indent -= self._indent_per_level
        write('\n' + ' '*indent)
        write(')')
        allowance = 1
        return allowance

    _dispatch[str.__repr__] = _pprint_str

    def _pprint_bytes(self, object, stream, indent, allowance, context, level):
        write = stream.write
        if len(object) <= 4:
            rep = repr(object)
            write(rep)
            return allowance + len(rep)
        write('(')
        indent += self._indent_per_level
        for rep in _wrap_bytes_repr(object, self._width - indent):
            write('\n' + ' '*indent)
            write(rep)
        indent -= self._indent_per_level
        write('\n' + ' '*indent)
        write(')')
        return 1

    _dispatch[bytes.__repr__] = _pprint_bytes

    def _pprint_bytearray(self, object, stream, indent, allowance, context, level):
        return self._pprint_constructor(
            object, (bytes(object),), stream, indent, allowance, context, level,
        )

    _dispatch[bytearray.__repr__] = _pprint_bytearray

    def _pprint_mappingproxy(self, object, stream, indent, allowance, context, level):
        return self._pprint_constructor(
            object, (object.copy(),),
            stream, indent, allowance, context, level,
        )

    _dispatch[_types.MappingProxyType.__repr__] = _pprint_mappingproxy

    def _format_dict_items(self, items, stream, indent, allowance, context,
                           level):
        write = stream.write
        delimnl = ',\n' + ' ' * indent
        last_index = len(items) - 1
        for i, (key, ent) in enumerate(items):
            last = i == last_index
            rep = self._repr(key, context, level)
            write(rep)
            write(': ')
            replen = len(rep)
            allowance += replen + 2
            allowance = self._format(ent, stream, indent, allowance, context, level)
            if not last:
                write(delimnl)
                allowance = 0
            elif i > 0:
                write(',\n')
                allowance = 0
        return allowance

    def _format_kwargs(self, items, stream, indent, allowance, context,
                           level):
        write = stream.write
        delimnl = ',\n' + ' ' * indent
        last_index = len(items) - 1
        for i, (key, ent) in enumerate(items):
            last = i == last_index
            write(key)
            write('=')
            allowance += len(key) + 1
            allowance = self._format(ent, stream, indent, allowance, context, level)
            if not last:
                write(delimnl)
                allowance = 0
            elif i > 0:
                write(',\n')
                allowance = 0
        return allowance

    def _format_items(self, items, stream, indent, allowance, context, level):
        write = stream.write
        length = len(items)
        multibracket = length <= 1
        if not multibracket:
            indent += self._indent_per_level
            write('\n')
            allowance = 0
        for ent in items:
            if not multibracket:
                write(' ' * indent)
                allowance += 1  # for the coming comma
            self._format(ent, stream, indent, allowance, context, level)
            if not multibracket:
                write(',\n')
                allowance = 0
        if not multibracket:
            indent -= self._indent_per_level
            write(' ' * indent)
            allowance = 0
        return allowance

    def _repr(self, object, context, level):
        repr, readable, recursive = self.format(object, context.copy(),
                                                self._depth, level)
        if not readable:
            self._readable = False
        if recursive:
            self._recursive = True
        return repr

    def format(self, object, context, maxlevels, level):
        """Format object for a specific context, returning a string
        and flags indicating whether the representation is 'readable'
        and whether the object represents a recursive construct.
        """
        return _safe_repr(object, context, maxlevels, level)

    def _pprint_default_dict(self, object, stream, indent, allowance, context, level):
        return self._pprint_constructor(
            object, (object.default_factory, dict(object)),
            stream, indent, allowance, context, level,
        )

    _dispatch[_collections.defaultdict.__repr__] = _pprint_default_dict

    def _pprint_counter(self, object, stream, indent, allowance, context, level):
        return self._pprint_constructor(
            object, (dict(object.most_common()),),
            stream, indent, allowance, context, level,
        )

    _dispatch[_collections.Counter.__repr__] = _pprint_counter

    def _pprint_chain_map(self, object, stream, indent, allowance, context, level):
        return self._pprint_constructor(
            object, object.maps,
            stream, indent, allowance, context, level,
        )

    _dispatch[_collections.ChainMap.__repr__] = _pprint_chain_map

    def _pprint_deque(self, object, stream, indent, allowance, context, level):
        if object.maxlen is not None:
            kwargs = {'maxlen': object.maxlen}
        else:
            kwargs = None
        return self._pprint_constructor(
            object, (list(object),),
            stream, indent, allowance, context, level,
            kwargs=kwargs,
        )

    _dispatch[_collections.deque.__repr__] = _pprint_deque

    def _pprint_user_dict(self, object, stream, indent, allowance, context, level):
        return self._format(object.data, stream, indent, allowance, context, level - 1)

    _dispatch[_collections.UserDict.__repr__] = _pprint_user_dict

    def _pprint_user_list(self, object, stream, indent, allowance, context, level):
        return self._format(object.data, stream, indent, allowance, context, level - 1)

    _dispatch[_collections.UserList.__repr__] = _pprint_user_list

    def _pprint_user_string(self, object, stream, indent, allowance, context, level):
        return self._format(object.data, stream, indent, allowance, context, level - 1)

    _dispatch[_collections.UserString.__repr__] = _pprint_user_string

# Return triple (repr_string, isreadable, isrecursive).

def _safe_repr(object, context, maxlevels, level):
    typ = type(object)
    if typ in _builtin_scalars:
        return repr(object), True, False

    r = getattr(typ, "__repr__", None)
    if issubclass(typ, dict) and r is dict.__repr__:
        if not object:
            return "{}", True, False
        objid = id(object)
        if maxlevels and level >= maxlevels:
            return "{...}", False, objid in context
        if objid in context:
            return _recursion(object), False, True
        context[objid] = 1
        readable = True
        recursive = False
        components = []
        append = components.append
        level += 1
        saferepr = _safe_repr
        items = sorted(object.items(), key=_safe_tuple)
        for k, v in items:
            krepr, kreadable, krecur = saferepr(k, context, maxlevels, level)
            vrepr, vreadable, vrecur = saferepr(v, context, maxlevels, level)
            append("%s: %s" % (krepr, vrepr))
            readable = readable and kreadable and vreadable
            if krecur or vrecur:
                recursive = True
        del context[objid]
        return "{%s}" % ", ".join(components), readable, recursive

    if (issubclass(typ, list) and r is list.__repr__) or \
       (issubclass(typ, tuple) and r is tuple.__repr__) or \
       (issubclass(typ, frozenset) and r is frozenset.__repr__) or \
       (issubclass(typ, set) and r is set.__repr__):
        if issubclass(typ, list):
            if not object:
                return "[]", True, False
            format = "[%s]"
        elif issubclass(typ, set):
            name = typ.__name__  # TODO qualname, module
            if not object:
                return name + "()", True, False
            if typ is set:
                format = "{%s}"
            else:
                format = name + "({%s})"
            object = sorted(object, key=_safe_key)
        elif issubclass(typ, frozenset):
            if not object:
                return "frozenset()", True, False
            format = "frozenset({%s})"
            object = sorted(object, key=_safe_key)
        elif len(object) == 1:
            format = "(%s,)"
        else:
            if not object:
                return "()", True, False
            format = "(%s)"
        objid = id(object)
        if maxlevels and level >= maxlevels:
            return format % "...", False, objid in context
        if objid in context:
            return _recursion(object), False, True
        context[objid] = 1
        readable = True
        recursive = False
        components = []
        append = components.append
        level += 1
        for o in object:
            orepr, oreadable, orecur = _safe_repr(o, context, maxlevels, level)
            append(orepr)
            if not oreadable:
                readable = False
            if orecur:
                recursive = True
        del context[objid]
        return format % ", ".join(components), readable, recursive

    rep = repr(object)
    return rep, (rep and not rep.startswith('<')), False

_builtin_scalars = frozenset({str, bytes, bytearray, int, float, complex,
                              bool, type(None)})

def _recursion(object):
    return ("<Recursion on %s with id=%s>"
            % (type(object).__name__, id(object)))


def _perfcheck(object=None):
    import time
    if object is None:
        object = [("string", (1, 2), [3, 4], {5: 6, 7: 8})] * 100000
    p = PrettyPrinter()
    t1 = time.time()
    _safe_repr(object, {}, None, 0)
    t2 = time.time()
    p.pformat(object)
    t3 = time.time()
    print("_safe_repr:", t2 - t1)
    print("pformat:", t3 - t2)

def _wrap_bytes_repr(object, width):
    current = b''
    last = len(object) // 4 * 4
    for i in range(0, len(object), 4):
        part = object[i: i+4]
        candidate = current + part
        if len(repr(candidate)) >= width:
            if current:
                yield repr(current)
            current = part
        else:
            current = candidate
    if current:
        yield repr(current)

if __name__ == "__main__":
    _perfcheck()
# vim:et:sts=4:sw=4:
