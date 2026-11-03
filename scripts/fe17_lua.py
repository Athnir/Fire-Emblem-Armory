"""A small Lua interpreter for Fire Emblem Engage's battle scripts (data-raw/fe17/romfs/scripts/*.lua).

The game runs them in MoonSharp, a Lua 5.2 for C#: numbers are doubles (an integral one prints without ".0"), `!=` is `~=`, names
may be Japanese, and bit32 is there. This reads that dialect into a tree and runs it; the game's own functions (Dispos, ItemGain,
EventEntryTurn...) are Python callables the caller puts in `Lua.globals` (fe17_events.py), and any other unknown function is a
no-op that returns nothing, so a script runs through to see what it would do.

    lua = Lua()
    lua.globals['Dispos'] = lambda group, flag: ...      # each takes the Lua values, returns a value, a list (several) or None
    lua.run(source)                                       # defines the script's functions and globals
    lua.call('Startup')                                   # runs one
"""
import functools
import math
import re

KEYWORDS = {'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function', 'goto', 'if', 'in', 'local', 'nil', 'not',
            'or', 'repeat', 'return', 'then', 'true', 'until', 'while'}
OPS = ['...', '..', '==', '~=', '!=', '<=', '>=', '<<', '>>', '//', '::', '+', '-', '*', '/', '%', '^', '#', '&', '~', '|', '<', '>',
       '=', '(', ')', '{', '}', '[', ']', ';', ':', ',', '.']
NUMBER = re.compile(r'0[xX][0-9a-fA-F]+|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?')
NAME = re.compile(r'[^\W\d][\w]*', re.UNICODE)


class LuaError(Exception):
    pass


def tokens(src):
    """The source as (kind, value, line) tokens: kind 'name', 'number', 'string', 'op', 'kw' or 'eof'."""
    out, i, line, n = [], 0, 1, len(src)
    while i < n:
        c = src[i]
        if c == '\n':
            line += 1
            i += 1
        elif c.isspace():
            i += 1
        elif src.startswith('--', i):
            m = re.match(r'--\[(=*)\[', src[i:])
            if m:
                end = src.index(']' + m.group(1) + ']', i)
                line += src.count('\n', i, end)
                i = end + len(m.group(1)) + 2
            else:
                j = src.find('\n', i)
                i = n if j < 0 else j
        elif c in '"\'':
            j, s = i + 1, []
            while src[j] != c:
                if src[j] == '\\':
                    e = src[j + 1]
                    esc = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'", '\n': '\n', 'a': '\a', 'b': '\b',
                           'f': '\f', 'v': '\v'}
                    if e in esc:
                        s.append(esc[e])
                        j += 2
                    elif e.isdigit():
                        m = re.match(r'\d{1,3}', src[j + 1:])
                        s.append(chr(int(m.group())))
                        j += 1 + len(m.group())
                    else:
                        raise LuaError(f'line {line}: escape \\{e}')
                else:
                    s.append(src[j])
                    j += 1
            out.append(('string', ''.join(s), line))
            i = j + 1
        elif src.startswith('[', i) and re.match(r'\[=*\[', src[i:]):
            m = re.match(r'\[(=*)\[', src[i:])
            start = i + len(m.group())
            end = src.index(']' + m.group(1) + ']', start)
            body = src[start:end]
            out.append(('string', body[1:] if body.startswith('\n') else body, line))
            line += src.count('\n', i, end)
            i = end + len(m.group(1)) + 2
        elif c.isdigit() or (c == '.' and i + 1 < n and src[i + 1].isdigit()):
            m = NUMBER.match(src, i)
            t = m.group()
            v = int(t, 16) if t[:2] in ('0x', '0X') else (float(t) if any(ch in t for ch in '.eE') else int(t))
            out.append(('number', v, line))
            i = m.end()
        else:
            m = NAME.match(src, i)
            if m:
                w = m.group()
                out.append(('kw' if w in KEYWORDS else 'name', w, line))
                i = m.end()
                continue
            for op in OPS:
                if src.startswith(op, i):
                    out.append(('op', '~=' if op == '!=' else op, line))
                    i += len(op)
                    break
            else:
                raise LuaError(f'line {line}: unexpected {c!r}')
    out.append(('eof', None, line))
    return out


# Binary operators: (left priority, right priority), Lua's own table.
BINARY = {'or': (1, 1), 'and': (2, 2), '<': (3, 3), '>': (3, 3), '<=': (3, 3), '>=': (3, 3), '~=': (3, 3), '==': (3, 3),
          '|': (4, 4), '~': (5, 5), '&': (6, 6), '<<': (7, 7), '>>': (7, 7), '..': (9, 8), '+': (10, 10), '-': (10, 10),
          '*': (11, 11), '/': (11, 11), '//': (11, 11), '%': (11, 11), '^': (14, 13)}
UNARY_PRIORITY = 12


class Parser:
    """Lua source -> a tree of tuples (each node's first item names it)."""

    def __init__(self, src):
        self.t = tokens(src)
        self.i = 0

    def peek(self, k=0):
        return self.t[self.i + k]

    def next(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def check(self, kind, value=None):
        tok = self.t[self.i]
        return tok[0] == kind and (value is None or tok[1] == value)

    def accept(self, kind, value=None):
        if self.check(kind, value):
            return self.next()
        return None

    def expect(self, kind, value=None):
        tok = self.next()
        if tok[0] != kind or (value is not None and tok[1] != value):
            raise LuaError(f'line {tok[2]}: expected {value or kind}, got {tok[1]!r}')
        return tok

    def chunk(self):
        body = self.block()
        self.expect('eof')
        return body

    def block(self):
        stmts = []
        while True:
            if self.check('kw', 'return'):
                self.next()
                values = [] if self.block_end() or self.check('op', ';') else self.exprlist()
                self.accept('op', ';')
                stmts.append(('Return', values))
                break
            if self.block_end():
                break
            s = self.statement()
            if s is not None:
                stmts.append(s)
        return stmts

    def block_end(self):
        tok = self.peek()
        return tok[0] == 'eof' or (tok[0] == 'kw' and tok[1] in ('end', 'else', 'elseif', 'until'))

    def statement(self):
        tok = self.peek()
        if tok[0] == 'op' and tok[1] == ';':
            self.next()
            return None
        if tok[0] == 'op' and tok[1] == '::':
            self.next()
            name = self.expect('name')[1]
            self.expect('op', '::')
            return ('Label', name)
        if tok[0] == 'kw':
            w = tok[1]
            if w == 'if':
                self.next()
                arms = [(self.expr(), self.then_block())]
                orelse = None
                while True:
                    # MoonSharp's if takes another `if` where `elseif` goes (a block a return ended can be followed by one: g001's and
                    # g004's ボスのPIDを取得), so it reads as an elseif.
                    if self.accept('kw', 'elseif') or self.accept('kw', 'if'):
                        arms.append((self.expr(), self.then_block()))
                    elif self.accept('kw', 'else'):
                        orelse = self.block()
                        self.expect('kw', 'end')
                        break
                    else:
                        self.expect('kw', 'end')
                        break
                return ('If', arms, orelse)
            if w == 'while':
                self.next()
                cond = self.expr()
                self.expect('kw', 'do')
                body = self.block()
                self.expect('kw', 'end')
                return ('While', cond, body)
            if w == 'do':
                self.next()
                body = self.block()
                self.expect('kw', 'end')
                return ('Do', body)
            if w == 'for':
                self.next()
                first = self.expect('name')[1]
                if self.accept('op', '='):
                    start = self.expr()
                    self.expect('op', ',')
                    stop = self.expr()
                    step = self.expr() if self.accept('op', ',') else ('Number', 1)
                    self.expect('kw', 'do')
                    body = self.block()
                    self.expect('kw', 'end')
                    return ('NumFor', first, start, stop, step, body)
                names = [first]
                while self.accept('op', ','):
                    names.append(self.expect('name')[1])
                self.expect('kw', 'in')
                exprs = self.exprlist()
                self.expect('kw', 'do')
                body = self.block()
                self.expect('kw', 'end')
                return ('GenFor', names, exprs, body)
            if w == 'repeat':
                self.next()
                body = self.block()
                self.expect('kw', 'until')
                return ('Repeat', body, self.expr())
            if w == 'function':
                self.next()
                path = [self.expect('name')[1]]
                method = False
                while self.accept('op', '.'):
                    path.append(self.expect('name')[1])
                if self.accept('op', ':'):
                    path.append(self.expect('name')[1])
                    method = True
                f = self.funcbody(path[-1], method)
                return ('FunctionStat', path, f)
            if w == 'local':
                self.next()
                if self.accept('kw', 'function'):
                    name = self.expect('name')[1]
                    return ('LocalFunction', name, self.funcbody(name, False))
                names = [self.expect('name')[1]]
                while self.accept('op', ','):
                    names.append(self.expect('name')[1])
                exprs = self.exprlist() if self.accept('op', '=') else []
                return ('Local', names, exprs)
            if w == 'break':
                self.next()
                return ('Break',)
            if w == 'goto':
                self.next()
                return ('Goto', self.expect('name')[1])
        # an assignment or a call
        target = self.suffixed()
        if self.check('op', '=') or self.check('op', ','):
            targets = [target]
            while self.accept('op', ','):
                targets.append(self.suffixed())
            self.expect('op', '=')
            return ('Assign', targets, self.exprlist())
        if target[0] not in ('Call', 'Method'):
            raise LuaError(f'line {self.peek()[2]}: not a statement')
        return ('CallStat', target)

    def then_block(self):
        self.expect('kw', 'then')
        return self.block()

    def funcbody(self, name, method):
        line = self.expect('op', '(')[2]
        params, vararg = (['self'] if method else []), False
        if not self.check('op', ')'):
            while True:
                if self.accept('op', '...'):
                    vararg = True
                    break
                params.append(self.expect('name')[1])
                if not self.accept('op', ','):
                    break
        self.expect('op', ')')
        body = self.block()
        self.expect('kw', 'end')
        return ('Function', name, params, vararg, body, line)

    def exprlist(self):
        out = [self.expr()]
        while self.accept('op', ','):
            out.append(self.expr())
        return out

    def expr(self, limit=0):
        tok = self.peek()
        if (tok[0] == 'kw' and tok[1] == 'not') or (tok[0] == 'op' and tok[1] in ('-', '#', '~')):
            self.next()
            left = ('Unary', tok[1], self.expr(UNARY_PRIORITY))
        else:
            left = self.simple()
        while True:
            tok = self.peek()
            op = tok[1] if tok[0] in ('op', 'kw') else None
            if op not in BINARY or BINARY[op][0] <= limit:
                return left
            self.next()
            right = self.expr(BINARY[op][1])
            left = ('Binary', op, left, right, tok[2])

    def simple(self):
        tok = self.peek()
        if tok[0] == 'number':
            self.next()
            return ('Number', tok[1])
        if tok[0] == 'string':
            self.next()
            return ('String', tok[1])
        if tok[0] == 'kw':
            if tok[1] in ('nil', 'true', 'false'):
                self.next()
                return ('Const', {'nil': None, 'true': True, 'false': False}[tok[1]])
            if tok[1] == 'function':
                self.next()
                return self.funcbody('(anonymous)', False)
        if tok[0] == 'op' and tok[1] == '...':
            self.next()
            return ('Vararg',)
        if tok[0] == 'op' and tok[1] == '{':
            return self.table()
        return self.suffixed()

    def primary(self):
        tok = self.next()
        if tok[0] == 'name':
            return ('Name', tok[1])
        if tok[0] == 'op' and tok[1] == '(':
            e = self.expr()
            self.expect('op', ')')
            return ('Paren', e)
        raise LuaError(f'line {tok[2]}: unexpected {tok[1]!r}')

    def suffixed(self):
        e = self.primary()
        while True:
            tok = self.peek()
            if tok[0] == 'op' and tok[1] == '.':
                self.next()
                e = ('Index', e, ('String', self.expect('name')[1]))
            elif tok[0] == 'op' and tok[1] == '[':
                self.next()
                key = self.expr()
                self.expect('op', ']')
                e = ('Index', e, key)
            elif tok[0] == 'op' and tok[1] == ':':
                self.next()
                name = self.expect('name')[1]
                e = ('Method', e, name, self.args(), tok[2])
            elif (tok[0] == 'op' and tok[1] in ('(', '{')) or tok[0] == 'string':
                e = ('Call', e, self.args(), tok[2])
            else:
                return e

    def args(self):
        tok = self.peek()
        if tok[0] == 'string':
            self.next()
            return [('String', tok[1])]
        if tok[0] == 'op' and tok[1] == '{':
            return [self.table()]
        self.expect('op', '(')
        if self.accept('op', ')'):
            return []
        out = self.exprlist()
        self.expect('op', ')')
        return out

    def table(self):
        self.expect('op', '{')
        items = []
        while not self.check('op', '}'):
            if self.check('op', '['):
                self.next()
                k = self.expr()
                self.expect('op', ']')
                self.expect('op', '=')
                items.append(('keyed', k, self.expr()))
            elif self.check('name') and self.peek(1)[0] == 'op' and self.peek(1)[1] == '=':
                k = self.next()[1]
                self.next()
                items.append(('keyed', ('String', k), self.expr()))
            else:
                items.append(('item', self.expr()))
            if not (self.accept('op', ',') or self.accept('op', ';')):
                break
        self.expect('op', '}')
        return ('Table', items)


class Table:
    """A Lua table: its fields in a dict (an integral float key is the same key as the integer)."""

    def __init__(self, items=None):
        self.d = {}
        self._n = 0
        for k, v in (items or {}).items():
            self[k] = v

    @staticmethod
    def _key(k):
        return int(k) if isinstance(k, float) and k.is_integer() else k

    def __getitem__(self, k):
        return self.d.get(self._key(k))

    def __setitem__(self, k, v):
        k = self._key(k)
        if v is None:
            self.d.pop(k, None)
        else:
            self.d[k] = v

    def length(self):
        # A border (n set, n + 1 not), from the last one found: any border is a Lua length, and loops ask for it every step.
        n = self._n
        if n and n not in self.d:
            n = 0
        while (n + 1) in self.d:
            n += 1
        self._n = n
        return n

    def array(self):
        return [self.d[k] for k in range(1, self.length() + 1)]

    def __repr__(self):
        return f'Table({self.d!r})'


class Function:
    def __init__(self, node, scope):
        _, self.name, self.params, self.vararg, self.body, self.line = node
        self.scope = scope

    def __repr__(self):
        return f'<function {self.name}>'


class Return(Exception):
    def __init__(self, values):
        self.values = values


class Break(Exception):
    pass


class Scope:
    __slots__ = ('vars', 'parent')

    def __init__(self, parent=None):
        self.vars, self.parent = {}, parent

    def find(self, name):
        s = self
        while s is not None:
            if name in s.vars:
                return s
            s = s.parent
        return None


def tostr(v):
    if v is None:
        return 'nil'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, float):
        if v.is_integer() and abs(v) < 1e15:
            return str(int(v))
        return repr(v)
    if isinstance(v, (int, str)):
        return str(v)
    return f'{type(v).__name__}: {id(v):x}'


def truthy(v):
    return v is not None and v is not False


def number(v):
    if isinstance(v, bool) or v is None:
        raise LuaError(f'arithmetic on {tostr(v)}')
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            return float(v)
    return v


def tidy(v):
    """MoonSharp's numbers are doubles: keep an integral result an int so it prints and indexes as one."""
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


@functools.lru_cache(maxsize=None)
def parsed(src):
    """A chunk's syntax tree, parsed once however many times it's run (the trees are never changed)."""
    return Parser(src).chunk()


class Lua:
    def __init__(self):
        g = self.globals = {}
        g['print'] = lambda *a: None
        g['tostring'] = tostr
        g['tonumber'] = lambda v, base=None: (tidy(number(v)) if base is None else int(v, int(base))) if v is not None else None
        g['type'] = lambda v: ('nil' if v is None else 'boolean' if isinstance(v, bool) else 'number' if isinstance(v, (int, float))
                               else 'string' if isinstance(v, str) else 'table' if isinstance(v, Table) else 'function')
        g['pairs'] = self._pairs
        g['ipairs'] = self._ipairs
        g['next'] = self._next
        g['select'] = lambda n, *a: [len(a)] if n == '#' else list(a[int(n) - 1:])
        g['unpack'] = lambda t, i=1, j=None: t.array()[int(i) - 1:None if j is None else int(j)]
        g['assert'] = lambda v, *a: [v, *a]
        g['error'] = self._error
        g['rawget'] = lambda t, k: t[k]
        g['rawset'] = lambda t, k, v: t.__setitem__(k, v)
        g['math'] = Table({'floor': lambda x: math.floor(number(x)), 'ceil': lambda x: math.ceil(number(x)),
                           'abs': lambda x: abs(number(x)), 'max': lambda *a: max(a), 'min': lambda *a: min(a),
                           'sqrt': lambda x: tidy(math.sqrt(x)), 'sin': math.sin, 'cos': math.cos, 'acos': math.acos,
                           'rad': math.radians, 'deg': math.degrees, 'pi': math.pi, 'huge': math.inf,
                           'random': lambda a=None, b=None: 1 if a is None else (a if b is None else a),
                           'fmod': lambda a, b: tidy(math.fmod(a, b))})
        g['table'] = Table({'insert': self._insert, 'remove': self._remove, 'sort': self._sort,
                            'concat': lambda t, sep='', i=1, j=None: sep.join(tostr(v) for v in t.array()[int(i) - 1:j]),
                            'unpack': g['unpack']})
        g['string'] = Table({'format': self._format, 'len': lambda s: len(s.encode('utf-8')), 'sub': self._sub,
                             'upper': str.upper, 'lower': str.lower, 'rep': lambda s, n: s * int(n)})
        g['bit32'] = Table({'band': lambda *a: self._fold(a, lambda x, y: x & y, 0xFFFFFFFF),
                            'bor': lambda *a: self._fold(a, lambda x, y: x | y, 0),
                            'bxor': lambda *a: self._fold(a, lambda x, y: x ^ y, 0),
                            'bnot': lambda x: ~int(x) & 0xFFFFFFFF,
                            'lshift': lambda x, n: (int(x) << int(n)) & 0xFFFFFFFF, 'rshift': lambda x, n: (int(x) & 0xFFFFFFFF) >> int(n),
                            'btest': lambda *a: self._fold(a, lambda x, y: x & y, 0xFFFFFFFF) != 0})
        g['coroutine'] = Table({'yield': lambda *a: None})
        self.calls = 0
        self.limit = 2_000_000

    # -- the library ---------------------------------------------------------------------------------------------------
    @staticmethod
    def _fold(args, f, start):
        v = start
        for a in args:
            v = f(v, int(a) & 0xFFFFFFFF)
        return v

    @staticmethod
    def _error(msg=None, level=None):
        raise LuaError(tostr(msg))

    @staticmethod
    def _pairs(t):
        keys = list(t.d.keys())
        it = iter(keys)

        def step(_t, _k):
            for k in it:
                if k in t.d:
                    return [k, t.d[k]]
            return [None]
        return [step, t, None]

    @staticmethod
    def _ipairs(t):
        def step(_t, i):
            i = int(i) + 1
            v = t[i]
            return [None] if v is None else [i, v]
        return [step, t, 0]

    @staticmethod
    def _next(t, k=None):
        keys = list(t.d.keys())
        i = 0 if k is None else keys.index(Table._key(k)) + 1
        return [keys[i], t.d[keys[i]]] if i < len(keys) else [None]

    @staticmethod
    def _insert(t, *a):
        if len(a) == 1:
            t[t.length() + 1] = a[0]
        else:
            pos, v = int(a[0]), a[1]
            n = t.length()
            for k in range(n, pos - 1, -1):
                t[k + 1] = t[k]
            t[pos] = v

    @staticmethod
    def _remove(t, pos=None):
        n = t.length()
        if n == 0:
            return None
        pos = n if pos is None else int(pos)
        v = t[pos]
        for k in range(pos, n):
            t[k] = t[k + 1]
        t[n] = None
        return v

    def _sort(self, t, comp=None):
        items = t.array()
        if comp is None:
            items.sort()
        else:
            items.sort(key=functools.cmp_to_key(lambda a, b: -1 if truthy(self.call_value(comp, [a, b])[0])
                                                else (1 if truthy(self.call_value(comp, [b, a])[0]) else 0)))
        for k, v in enumerate(items, 1):
            t[k] = v

    @staticmethod
    def _format(fmt, *args):
        args = list(args)

        def one(m):
            spec = m.group()
            if spec == '%%':
                return '%'
            v = args.pop(0)
            if spec[-1] in 'di':
                return (spec[:-1] + 'd') % int(v)
            if spec[-1] == 's':
                return spec % tostr(v)
            return spec % v
        return re.sub(r'%[-+ #0]*\d*(?:\.\d+)?[sdifgxXc%]', one, fmt)

    @staticmethod
    def _sub(s, i, j=-1):
        b = s.encode('utf-8')
        n = len(b)
        i, j = int(i), int(j)
        i = max(1, n + i + 1 if i < 0 else i)
        j = min(n, n + j + 1 if j < 0 else j)
        return b[i - 1:j].decode('utf-8', 'replace') if i <= j else ''

    # -- running ---------------------------------------------------------------------------------------------------------
    def run(self, src, name='chunk'):
        self.exec_block(parsed(src), Scope(), new_scope=False)

    def call(self, name, *args):
        f = self.globals.get(name)
        if f is None:
            return []
        return self.call_value(f, list(args))

    def call_value(self, f, args):
        """Call a Lua function or a host callable with a list of arguments: its results as a list."""
        if isinstance(f, Function):
            self.calls += 1
            if self.calls > self.limit:
                raise LuaError('too many calls')
            scope = Scope(f.scope)
            for k, p in enumerate(f.params):
                scope.vars[p] = args[k] if k < len(args) else None
            if f.vararg:
                scope.vars['...'] = list(args[len(f.params):])
            try:
                self.exec_block(f.body, scope, new_scope=False)
            except Return as r:
                return r.values
            return []
        if callable(f):
            r = f(*args)
            if r is None:
                return []
            return r if isinstance(r, list) else [r]
        raise LuaError(f'call of {tostr(f)}')

    def exec_block(self, stmts, scope, new_scope=True):
        if new_scope:
            scope = Scope(scope)
        for s in stmts:
            self.exec(s, scope)

    def exec(self, s, scope):
        kind = s[0]
        if kind == 'CallStat':
            self.eval_multi(s[1], scope)
        elif kind == 'Assign':
            values = self.eval_list(s[2], scope)
            for k, t in enumerate(s[1]):
                v = values[k] if k < len(values) else None
                if t[0] == 'Name':
                    found = scope.find(t[1])
                    if found is not None:
                        found.vars[t[1]] = v
                    else:
                        self.globals[t[1]] = v
                elif t[0] == 'Index':
                    obj = self.eval(t[1], scope)
                    if not isinstance(obj, Table):
                        raise LuaError(f'index of {tostr(obj)}')
                    obj[self.eval(t[2], scope)] = v
                else:
                    raise LuaError('bad assignment')
        elif kind == 'Local':
            values = self.eval_list(s[2], scope)
            for k, name in enumerate(s[1]):
                scope.vars[name] = values[k] if k < len(values) else None
        elif kind == 'If':
            for cond, body in s[1]:
                if truthy(self.eval(cond, scope)):
                    self.exec_block(body, scope)
                    return
            if s[2] is not None:
                self.exec_block(s[2], scope)
        elif kind == 'While':
            try:
                guard = 0
                while truthy(self.eval(s[1], scope)):
                    self.exec_block(s[2], scope)
                    guard += 1
                    if guard > 100000:
                        raise LuaError('loop without end')
            except Break:
                pass
        elif kind == 'NumFor':
            _, name, a, b, c, body = s
            start, stop, step = (number(self.eval(x, scope)) for x in (a, b, c))
            try:
                v = start
                while (v <= stop) if step > 0 else (v >= stop):
                    inner = Scope(scope)
                    inner.vars[name] = tidy(v)
                    self.exec_block(body, inner, new_scope=False)
                    v += step
            except Break:
                pass
        elif kind == 'GenFor':
            _, names, exprs, body = s
            vals = self.eval_list(exprs, scope)
            f, state, ctl = (vals + [None, None, None])[:3]
            try:
                while True:
                    r = self.call_value(f, [state, ctl])
                    if not r or r[0] is None:
                        break
                    ctl = r[0]
                    inner = Scope(scope)
                    for k, n in enumerate(names):
                        inner.vars[n] = r[k] if k < len(r) else None
                    self.exec_block(body, inner, new_scope=False)
            except Break:
                pass
        elif kind == 'Repeat':
            try:
                while True:
                    inner = Scope(scope)
                    self.exec_block(s[1], inner, new_scope=False)
                    if truthy(self.eval(s[2], inner)):
                        break
            except Break:
                pass
        elif kind == 'Do':
            self.exec_block(s[1], scope)
        elif kind == 'FunctionStat':
            path, node = s[1], s[2]
            f = Function(node, scope)
            if len(path) == 1:
                found = scope.find(path[0])
                if found is not None:
                    found.vars[path[0]] = f
                else:
                    self.globals[path[0]] = f
            else:
                obj = self.lookup(path[0], scope)
                for p in path[1:-1]:
                    obj = obj[p]
                obj[path[-1]] = f
        elif kind == 'LocalFunction':
            scope.vars[s[1]] = None
            scope.vars[s[1]] = Function(s[2], scope)
        elif kind == 'Return':
            raise Return(self.eval_list(s[1], scope))
        elif kind == 'Break':
            raise Break()
        elif kind == 'Label':
            pass
        else:
            raise LuaError(f'statement {kind}')

    def lookup(self, name, scope):
        found = scope.find(name)
        if found is not None:
            return found.vars[name]
        return self.globals.get(name)

    def eval_list(self, exprs, scope):
        out = []
        for k, e in enumerate(exprs):
            if k == len(exprs) - 1:
                out.extend(self.eval_multi(e, scope))
            else:
                out.append(self.eval(e, scope))
        return out

    def eval_multi(self, e, scope):
        kind = e[0]
        if kind == 'Call':
            f = self.eval(e[1], scope)
            args = self.eval_list(e[2], scope)
            if f is None:
                return self.unknown(e[1], args)
            if isinstance(f, Function):
                return self.call_value(f, args)
            try:
                return self.call_value(f, args)
            except LuaError as err:
                raise LuaError(f'line {e[3]}: {err}') from err
            except (TypeError, AttributeError, KeyError, ValueError, IndexError) as err:
                name = e[1][1] if e[1][0] == 'Name' else '?'
                raise LuaError(f'line {e[3]}: {name}: {type(err).__name__}: {err}') from err
        if kind == 'Method':
            obj = self.eval(e[1], scope)
            f = obj[e[2]] if isinstance(obj, Table) else None
            if f is None:
                raise LuaError(f'line {e[4]}: method {e[2]} of {tostr(obj)}')
            return self.call_value(f, [obj] + self.eval_list(e[3], scope))
        if kind == 'Vararg':
            return list(self.lookup('...', scope) or [])
        return [self.eval(e, scope)]

    def unknown(self, fexpr, args):
        """A call of a function nothing defines: a game function the caller didn't provide. It does nothing."""
        return []

    def eval(self, e, scope):
        kind = e[0]
        if kind == 'Name':
            found = scope.find(e[1])
            return found.vars[e[1]] if found is not None else self.globals.get(e[1])
        if kind == 'Number' or kind == 'String' or kind == 'Const':
            return e[1]
        if kind in ('Call', 'Method', 'Vararg'):
            r = self.eval_multi(e, scope)
            return r[0] if r else None
        if kind == 'Paren':
            return self.eval(e[1], scope)
        if kind == 'Index':
            obj = self.eval(e[1], scope)
            if isinstance(obj, Table):
                return obj[self.eval(e[2], scope)]
            if isinstance(obj, str):
                return self.globals['string'][self.eval(e[2], scope)]
            if obj is None:
                return None
            raise LuaError(f'index of {tostr(obj)}')
        if kind == 'Binary':
            op = e[1]
            if op == 'and':
                a = self.eval(e[2], scope)
                return self.eval(e[3], scope) if truthy(a) else a
            if op == 'or':
                a = self.eval(e[2], scope)
                return a if truthy(a) else self.eval(e[3], scope)
            try:
                return self.binary(op, self.eval(e[2], scope), self.eval(e[3], scope))
            except LuaError as err:
                if str(err).startswith('line '):
                    raise
                raise LuaError(f'line {e[4]}: {err}') from err
        if kind == 'Unary':
            v = self.eval(e[2], scope)
            op = e[1]
            if op == 'not':
                return not truthy(v)
            if op == '-':
                return -number(v)
            if op == '#':
                return len(v.encode('utf-8')) if isinstance(v, str) else v.length()
            if op == '~':
                return ~int(v)
        if kind == 'Table':
            t, n = Table(), 0
            items = e[1]
            for k, item in enumerate(items):
                if item[0] == 'keyed':
                    t[self.eval(item[1], scope)] = self.eval(item[2], scope)
                elif k == len(items) - 1:
                    for v in self.eval_multi(item[1], scope):
                        n += 1
                        t[n] = v
                else:
                    n += 1
                    t[n] = self.eval(item[1], scope)
            return t
        if kind == 'Function':
            return Function(e, scope)
        raise LuaError(f'expression {kind}')

    @staticmethod
    def binary(op, a, b):
        if op == '==':
            return equal(a, b)
        if op == '~=':
            return not equal(a, b)
        if op == '..':
            return tostr(a) + tostr(b) if not (a is None or b is None or isinstance(a, (bool, Table)) or
                                                 isinstance(b, (bool, Table))) else _concat_error(a, b)
        if op in ('<', '>', '<=', '>='):
            if a is None or b is None:
                raise LuaError(f'compare {tostr(a)} {op} {tostr(b)}')
            return {'<': a < b, '>': a > b, '<=': a <= b, '>=': a >= b}[op]
        a, b = number(a), number(b)
        if op == '+':
            return tidy(a + b)
        if op == '-':
            return tidy(a - b)
        if op == '*':
            return tidy(a * b)
        if op == '/':
            return tidy(a / b) if b else (math.inf if a > 0 else -math.inf if a < 0 else math.nan)
        if op == '//':
            return math.floor(a / b)
        if op == '%':
            return tidy(a - math.floor(a / b) * b)
        if op == '^':
            return tidy(float(a) ** b)
        if op == '&':
            return int(a) & int(b)
        if op == '|':
            return int(a) | int(b)
        if op == '~':
            return int(a) ^ int(b)
        if op == '<<':
            return int(a) << int(b)
        if op == '>>':
            return int(a) >> int(b)
        raise LuaError(f'operator {op}')


def equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    return a is b


def _concat_error(a, b):
    raise LuaError(f'concatenate {tostr(a)} .. {tostr(b)}')
