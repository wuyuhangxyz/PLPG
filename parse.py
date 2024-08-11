from lex import *
import types
import enum

class Product:
    def __init__(self, name, body, function = None):
        self.name = name
        self.body = body
        self.function = function
    def __str__(self):
        return f"{self.name} -> {' '.join(self.body)}"
    __repr__ = __str__
    def _eq__(self, other):
        return self.name == other.name and self.body == other.body
    def __hash__(self):
        return hash((self.name, tuple(self.body)))

class Item:
    STATUS = -1
    def __init__(self, product, pos, follow):
        Item.STATUS += 1
        self.status = Item.STATUS
        self.product = product
        self.pos = pos
        self.follow = follow
    def __str__(self):
        return f"{self.product} {self.pos} {self.follow}"
    __repr__ = __str__
    def __eq__(self, other):
        return self.product == other.product and self.pos == other.pos and self.follow == other.follow
    def __hash__(self):
        return hash((self.product, self.pos, self.follow))

class State:
    STATUS = -1
    def __init__(self, items):
        State.STATUS += 1
        self.status = State.STATUS
        self.items = items

def first(product, terminal, nonterminal):
    if product == "ε":
        return {"ε"}
    if product[0] == "ε":
        product = product[1:]
    if product[-1] == "$":
        product = product[:-1]
    if not product:
        return {"$"}
    if product in terminal:
        return {product}
    if product not in nonterminal:
        return {"ε"}
    products = nonterminal[product]
    first_set = set()
    for product in products:
        for term in product.body:
            if term in terminal:
                first_set.add(term)
                break
            if term != product.name:
                term_set = first(term, terminal, nonterminal)
                first_set.update(term_set - {"ε"})
                if "ε" not in term_set:
                    break
        else:
            first_set.add("ε")
    return first_set

def follow(product, terminal, nonterminal):
    follow_set = set()
    if product == "S":
        follow_set.add("$")
    for name, experissions in nonterminal.items():
        if name == product:
            continue
        for experission in experissions:
            for index, term in enumerate(experission.body):
                if term == product:
                    if index != len(experission.body) - 1:
                        first_set = first(experission.body[index+1], terminal, nonterminal)
                        follow_set.update(first_set - {"ε"})
                        if "ε" in first_set:
                            follow_set.update(follow(name, terminal, nonterminal))
                    else:
                        follow_set.update(follow(name, terminal, nonterminal))
    return follow_set

def closure(items, terminal, nonterminal):
    if not items:
        return []
    closure_set = [*items]
    index = 0
    next_ = closure_set[index]
    while next_ and next_.pos < len(next_.product.body):
        followed = next_.product.body[next_.pos]
        if followed in nonterminal and next_.pos < len(next_.product.body):
            terms = nonterminal[followed]
            for term in terms:
                next_char = next_.product.body[next_.pos + 1] if next_.pos + 1 < len(next_.product.body) else "ε"
                for b in first(next_char + next_.follow, terminal, nonterminal):
                    new_item = Item(term, 0, b)
                    if new_item not in closure_set:
                        closure_set.append(new_item)
        index += 1
        next_ = closure_set[index] if index < len(closure_set) else None
    return closure_set

def goto(items, char, terminal, nonterminal):
    goto_set = []
    for item in items:
        if item.pos < len(item.product.body) and item.product.body[item.pos] == char:
            new_item = Item(item.product, item.pos + 1, item.follow)
            if new_item not in goto_set:
                goto_set.append(new_item)
    return closure(goto_set, terminal, nonterminal)

def make_goto_table(terminal, nonterminal):
    goto_table = {}
    I0 = State(closure([Item(Product("S'", ["S"]), 0, "$")], terminal, nonterminal))
    keys = terminal + list(nonterminal.keys())
    state_list = [I0]
    for state in state_list:
        for char in keys:
            goto_set = goto(state.items, char, terminal, nonterminal)
            if goto_set:
                for s in state_list:
                    if s.items == goto_set:
                        goto_table[(state.status, char)] = s.status
                        break
                else:
                    new_state = State(goto_set)
                    state_list.append(new_state)
                    goto_table[(state.status, char)] = new_state.status
    return goto_table, state_list

def make_action_table(terminal, priority, goto_table, state_list):
    action_table = {}
    shift_reduce = []
    shifts = {}
    reduces = {}
    for state in state_list:
        for item in state.items:
            if item.pos < len(item.product.body):
                for char in terminal:
                    if (state.status, char) in goto_table:
                        goto_state = goto_table[(state.status, char)]
                        if (state.status, char) in action_table:
                            action = action_table[(state.status, char)]
                            if action[0] == "REDUCE":
                                shift_reduce.append((state.status, char, item, reduces[(state.status, char)], ("SHIFT", goto_state), action))
                                continue
                        action_table[(state.status, char)] = ("SHIFT", goto_state)
                        shifts[(state.status, char)] = item
            elif item.product.name != "S'":
                if (state.status, item.follow) in action_table:
                    action = action_table[(state.status, item.follow)]
                    if action[0] == "SHIFT":
                        shift_reduce.append((state.status, item.follow, shifts[(state.status, item.follow), item, action, ("REDUCE", item.product)]))
                        continue
                action_table[(state.status, item.follow)] = ("REDUCE", item.product)
                reduces[(state.status, item.follow)] = item
            elif item.follow == "$":
                action_table[(state.status, "$")] = ("ACCEPT", None)
    for status, character, shift_item, reduce_item, shift_action, reduce_action in shift_reduce:
        shift_priority, shift_associativity = priority.get(shift_item.product.body[shift_item.pos], None)
        for term in reduce_item.product.body[::-1]:
            if term in terminal:
                reduce_priority, reduce_associativity = priority.get(term, None)
                break
        if shift_priority is None or reduce_priority is None:
            action_table[{status, character}] = shift_action
        if shift_priority < reduce_priority:
            action_table[(status, character)] = shift_action
        elif shift_priority > reduce_priority:
            action_table[(status, character)] = reduce_action
        else:
            if shift_associativity == "LEFT" and reduce_associativity == "LEFT":
                action_table[(status, character)] = shift_action
            elif shift_associativity == "RIGHT" and reduce_associativity == "RIGHT":
                action_table[(status, character)] = reduce_action
    return action_table

class C: # Combinator
    List = []
    Id = -1
    def __init__(self, body = None):
        self.bodies = [body] if body else []
        self.is_closure = False
    def __and__(self, other):
        new_pg = C()
        if not (self.is_closure or other.is_closure):
            for i in self.bodies:
                for j in other.bodies:
                    new_pg.bodies.append(i + j)
        elif not self.is_closure:
            id_ = str(other.id)
            for i in self.bodies:
                new_pg.bodies.append([*i, id_])
        else:
            id_ = str(self.id)
            for i in other.bodies:
                new_pg.bodies.append([id_, *i])
        return new_pg
    def __or__(self, other):
        self.bodies += other.bodies
        if other in C.List:
            C.List.remove(other)
        return self
    def __mul__(self, count):
        for i in range(len(self.bodies)):
            self.bodies[i] *= count
        return self
    def optional(self):
        self.bodies.append([])
        return self
    def repeat(self, min_count, max_count):
        for i in range(len(self.bodies)):
            for j in range(min_count, max_count+1):
                self.bodies[i] *= j
        return self
    def one_to_n(self):
        C.Id += 1
        self.id = C.Id
        C.List.append(self)
        id_ = str(self.id)
        for i in range(len(self.bodies)):
            self.bodies.append([id_] + self.bodies[i])
        self.is_closure = True
        return self
    def zero_to_n(self):
        return self.one_to_n().optional()
    def generate(self, terminal, option):
        if self not in C.List:
            C.Id += 1
            self.id = C.Id
            C.List.append(self)
        res = {}
        for pg in C.List:
            id_ = str(pg.id)
            res[id_] = []
            for b in pg.bodies:
                if option == "ALL":
                    rets = [f"*args[{m}]" if b[m].isdigit() else f"args[{m}]" for m in range(len(b))]
                elif option == "T":
                    rets = []
                    for m in range(len(b)):
                        if b[m].isdigit():
                            rets.append(f"*args[{m}]")
                        elif b[m] in terminal:
                            rets.append(f"args[{m}]")
                elif option == "NT":
                    rets = []
                    for m in range(len(b)):
                        if b[m].isdigit():
                            rets.append(f"*args[{m}]")
                        elif b[m] not in terminal:
                            rets.append(f"args[{m}]")
                else:
                    raise ValueError(f"Invalid option: {option}")
                body = f"def fn(parser, args):\n    return [{','.join(rets)}]"
                fn = types.FunctionType(compile(body, "", "exec").co_consts[0], {})
                res[id_].append(Product(id_, b, fn))
        C.List = []
        return res

class TokenType(enum.Enum):
    CCL_END = 0
    CCL_START = 1
    OPEN_CURLY = 2
    CLOSE_CURLY = 3
    OPEN_PAREN = 4
    CLOSE_PAREN = 5
    CLOSURE = 6
    PLUS_CLOSE = 7
    OR = 8
    ID = 9
    OPTIONAL = 10
    NUMBER = 11
    COMMA = 12
    ARROW = 13
    EOF = 14

class Scanner:
    def __init__(self, pattern):
        self.pattern = pattern
        self.lexeme = ""
        self.pos = -1
        self.current_token = None
        self.tokens = {
            ']': TokenType.CCL_END,
            '[': TokenType.CCL_START,
            '{': TokenType.OPEN_CURLY,
            '}': TokenType.CLOSE_CURLY,
            '(': TokenType.OPEN_PAREN,
            ')': TokenType.CLOSE_PAREN,
            '*': TokenType.CLOSURE,
            '+': TokenType.PLUS_CLOSE,
            '|': TokenType.OR,
            "?": TokenType.OPTIONAL,
            ",": TokenType.COMMA,
        }
        self.advance()
    def advance(self):
        self.pos += 1
        if self.pos > len(self.pattern) - 1:
            self.current_token = TokenType.EOF
            self.lexeme = None
            return
        self.lexeme = self.pattern[self.pos]
        if self.lexeme.isspace():
            while self.pattern[self.pos].isspace():
                self.pos += 1
            self.pos -= 1
            self.advance()
            return
        if self.lexeme in self.tokens:
            self.current_token = self.tokens[self.lexeme]
        elif self.lexeme == "-" and self.pattern[self.pos + 1] == ">":
            self.pos += 1
            self.lexeme = "->"
            self.current_token = TokenType.ARROW
        elif self.lexeme.isalpha():
            self.lexeme = ""
            while self.pattern[self.pos].isalnum() or self.pattern[self.pos] == "_":
                self.lexeme += self.pattern[self.pos]
                self.pos += 1
                if self.pos > len(self.pattern) - 1:
                    break
            self.pos -= 1
            self.current_token = TokenType.ID
        elif self.lexeme.isdigit():
            self.lexeme = ""
            while self.pattern[self.pos].isdigit():
                self.lexeme += self.pattern[self.pos]
                self.pos += 1
                if self.pos > len(self.pattern) - 1:
                    break
            self.pos -= 1
            self.lexeme = int(self.lexeme)
            self.current_token = TokenType.NUMBER
        else:
            raise ValueError(f"Invalid character: {self.lexeme}")

class Analyzer:
    def __init__(self, lexer):
        self.lexer = lexer

    def atom(self):
        if self.lexer.current_token == TokenType.ID:
            product = C([self.lexer.lexeme])
            self.lexer.advance()
        elif self.lexer.current_token == TokenType.OPEN_PAREN:
            self.lexer.advance()
            product = self.expr()
            if self.lexer.current_token != TokenType.CLOSE_PAREN:
                raise ValueError("Missing closing parenthesis")
            self.lexer.advance()
        elif self.lexer.current_token == TokenType.CCL_START:
            self.lexer.advance()
            product = self.expr().optional()
            if self.lexer.current_token != TokenType.CCL_END:
                raise ValueError("Missing closing bracket")
            self.lexer.advance()
        return product
    def closure(self):
        atom = self.atom()
        if self.lexer.current_token == TokenType.CLOSURE:
            self.lexer.advance()
            product = atom.zero_to_n()
        elif self.lexer.current_token == TokenType.PLUS_CLOSE:
            self.lexer.advance()
            product = atom.one_to_n()
        elif self.lexer.current_token == TokenType.OPTIONAL:
            self.lexer.advance()
            product = atom.optional()
        elif self.lexer.current_token == TokenType.OPEN_CURLY:
            self.lexer.advance()
            if self.lexer.current_token != TokenType.NUMBER:
                raise ValueError("Missing number")
            min_count = self.lexer.lexeme
            self.lexer.advance()
            if self.lexer.current_token == TokenType.COMMA:
                self.lexer.advance()
                if self.lexer.current_token != TokenType.NUMBER:
                    raise ValueError("Missing number")
                max_count = self.lexer.lexeme
                self.lexer.advance()
                product = atom.repeat(min_count, max_count)
            elif self.lexer.current_token == TokenType.CLOSE_CURLY:
                self.lexer.advance()
                product = atom * min_count
            else:
                raise ValueError("Missing comma or closing curly bracket")
        else:
            product = atom
        return product
    def closure_conn(self):
        closure = self.closure()
        while self.lexer.current_token in (TokenType.ID, TokenType.OPEN_PAREN, TokenType.CCL_START):
            closure &= self.closure()
        return closure
    def expr(self):
        closure_conn = self.closure_conn()
        while self.lexer.current_token == TokenType.OR:
            self.lexer.advance()
            closure_conn |= self.closure_conn()
        return closure_conn
    def product(self):
        if self.lexer.current_token != TokenType.ID:
            raise ValueError("Missing ID")
        name = self.lexer.lexeme
        self.lexer.advance()
        if self.lexer.current_token != TokenType.ARROW:
            raise ValueError("Missing arrow")
        self.lexer.advance()
        expr = self.expr()
        return name, expr

class Parser:
    def __init__(self):
        self.terminals = []
        self.priorities = {}
        self.patterns = {}

    def pattern(self, text, option = "ALL"):
        def decorator(func):
            name, pattern = Analyzer(Scanner(text)).product()
            patterns = pattern.generate(self.terminals, option)
            id_ = str(pattern.id)
            def fn(parser, args):
                return func(parser, *args)
            patterns[name] = [Product(name, [id_], fn)]
            for k, v in patterns.items():
                if k in self.patterns:
                    self.patterns[k] += v
                else:
                    self.patterns[k] = v
            return func
        return decorator

    def error(self, func):
        self.err = func
        return func

    def compile(self):
        self.patterns["S'"] = [Product("S'", ["S"], None)]
        self.goto_table, state_list = make_goto_table(self.terminals, self.patterns)
        self.action_table = make_action_table(self.terminals, self.priorities, self.goto_table, state_list)

    def read(self, lexer):
        self.lexer = lexer

    def parse(self):
        self.value_stack = []
        self.state_stack = [0]
        self.index = 0
        self.token = self.lexer.lex()
        self.tp = self.token.type
        goto_table = self.goto_table
        action_table = self.action_table
        while True:
            self.state = self.state_stack[-1]
            if (self.state, self.tp) in action_table:
                action, arg = action_table[(self.state, self.tp)]
            elif (self.state, self.tp) in goto_table:
                self.state_stack.append(goto_table[(self.state, self.tp)])
                self.tp = self.token.type
                continue
            elif (self.state, "ε") in action_table:
                action, arg = action_table[(self.state, "ε")]
            else:
                self.err(self)
                break
            if action == "SHIFT":
                self.state_stack.append(arg)
                self.index += 1
                self.value_stack.append(self.token)
                self.token = self.lexer.lex()
                self.tp = self.token.type
            elif action == "REDUCE":
                num = len(arg.body)
                for _ in range(num):
                    self.state_stack.pop()
                if arg.function:
                    args = [self.value_stack.pop() for _ in range(num)][::-1]
                    res = arg.function(self, args)
                    self.value_stack.append(res)
                self.tp = arg.name
            elif action == "ACCEPT":
                break
        return self.value_stack.pop()
