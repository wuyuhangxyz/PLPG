import enum

class NFA:
    def __init__(self):
        self.edge = "EPSILON"
        self.next_1 = None
        self.next_2 = None
        self.function = None
class DFA:
    STATUS = -1
    def __init__(self, nfas):
        DFA.STATUS += 1
        self.nfas = nfas
        self.accepted = False
        self.function = None
        for i in nfas:
            if i.next_1 is None and i.next_2 is None:
                self.accepted = True
            if i.function is not None and self.function is None:
                self.function = i.function
        self.status = DFA.STATUS
    def __eq__(self, other):
        return self.status == other.status
class DFAGroup:
    STATUS = -1
    def __init__(self, dfas):
        DFAGroup.STATUS += 1
        self.status = DFAGroup.STATUS
        self.dfas = dfas
        self.function = None
        for i in dfas:
            if i.function is not None and self.function is None:
                self.function = i.function
    def get(self, index):
        return self.dfas[index] if index < len(self.dfas) else None
    def __str__(self):
        return str(list(map(lambda x:x.status, self.dfas)))
    __repr__ = __str__
    def __eq__(self, other):
        return self.dfas == other.dfas
class Token(enum.Enum):
    EOS = 0
    ANY = 1
    AT_BOL = 2
    AT_EOL = 3
    CCL_END = 4
    CCL_START = 5
    CLOSE_CURLY = 6
    CLOSE_PAREN = 7
    CLOSURE = 8
    DASH = 9
    END_OF_INPUT = 10
    L = 11
    OPEN_CURLY = 12
    OPEN_PAREN = 13
    OPTIONAL = 14
    OR = 15
    PLUS_CLOSE = 16

class Lexer:
    def __init__(self, pattern):
        self.pattern = pattern
        self.lexeme = ""
        self.pos = -1
        self.current_token = None
        self.ev = {
            '\0': '\\',
            'b': '\b',
            'f': '\f',
            'n': '\n',
            's': ' ',
            't': '\t',
            'e': '\033',
        }
        self.tokens = {
            '.': Token.ANY,
            '^': Token.AT_BOL,
            '$': Token.AT_EOL,
            ']': Token.CCL_END,
            '[': Token.CCL_START,
            '}': Token.CLOSE_CURLY,
            ')': Token.CLOSE_PAREN,
            '*': Token.CLOSURE,
            '-': Token.DASH,
            '{': Token.OPEN_CURLY,
            '(': Token.OPEN_PAREN,
            '?': Token.OPTIONAL,
            '|': Token.OR,
            '+': Token.PLUS_CLOSE,
        }
        self.advance()
    def advance(self):
        self.pos += 1
        if self.pos > len(self.pattern) - 1:
            self.current_token = Token.EOS
            self.lexeme = None
            return False
        self.lexeme = self.pattern[self.pos]
        if self.lexeme == "\\":
            self.pos += 1
            char = self.pattern[self.pos].lower()
            self.lexeme = self.ev.get(char, char)
            self.current_token = Token.L
        else:
            self.current_token = self.tokens.get(self.lexeme, Token.L)
class Parser:
    """
    group ::= ("(" expr ")")*
    expr ::= factor_conn ("|" factor_conn)*
    factor_conn ::= factor | factor factor*
    factor ::= (term | term ("*" | "+" | "?"))*
    term ::= char | "[" char "-" char "]" | .
    """
    def __init__(self, lexer):
        self.lexer = lexer
        self.ascii_table = set([chr(i) for i in range(127)])
        
    def dodash(self):
        first = ""
        char_set = set()
        while self.lexer.current_token != Token.CCL_END:
            if self.lexer.current_token == Token.DASH:
                self.lexer.advance()
                for c in range(ord(first), ord(self.lexer.lexeme) + 1):
                    char_set.add(chr(c))
                self.lexer.advance()
            else:
                first = self.lexer.lexeme
                char_set.add(self.lexer.lexeme)
                self.lexer.advance()
        return char_set
    def term(self):
        start = NFA()
        if self.lexer.current_token == Token.L:
            start.edge = self.lexer.lexeme
            start.next_1 = NFA()
            end = start.next_1
            self.lexer.advance()
        elif self.lexer.current_token == Token.ANY:
            start.edge = self.ascii_table
            start.next_1 = NFA()
            end = start.next_1
            self.lexer.advance()
        elif self.lexer.current_token == Token.CCL_START:
            self.lexer.advance()
            if self.lexer.current_token == Token.AT_BOL:
                self.lexer.advance()
                char_set = self.dodash()
                self.lexer.advance()
                start.edge = self.ascii_table - char_set
                start.next_1 = NFA()
                end = start.next_1
            else:
                char_set = self.dodash()
                self.lexer.advance()
                start.edge = char_set
                start.next_1 = NFA()
                end = start.next_1
        elif self.lexer.current_token == Token.OPEN_PAREN:
            self.lexer.advance()
            start, end = self.expr()
            if self.lexer.current_token != Token.CLOSE_PAREN:
                raise ValueError("Missing closing parenthesis")
            self.lexer.advance()
        return start, end
    def factor(self):
        start, end = self.term()
        new_start = NFA()
        new_end = NFA()
        if self.lexer.current_token == Token.CLOSURE:
            new_start.next_1 = start
            new_start.next_2 = new_end
            end.next_1 = start
            end.next_2 = new_end
            start, end = new_start, new_end
            self.lexer.advance()
        elif self.lexer.current_token == Token.PLUS_CLOSE:
            new_start.next_1 = start
            end.next_1 = start
            end.next_2 = new_end
            self.lexer.advance()
            start, end = new_start, new_end
        elif self.lexer.current_token == Token.OPTIONAL:
            new_start.next_1 = start
            new_start.next_2 = new_end
            end.next_2 = new_end
            self.lexer.advance()
            start, end = new_start, new_end
        return start, end
    def factor_conn(self):
        start, end = self.factor()
        while self.lexer.current_token in (Token.L, Token.ANY, Token.CCL_START, Token.OPEN_PAREN):
            new_start, new_end = self.factor()
            end.next_1 = new_start
            end = new_end
        return start, end
    def expr(self):
        start, end = self.factor_conn()
        while self.lexer.current_token == Token.OR:
            self.lexer.advance()
            head = NFA()
            tail = NFA()
            new_start, new_end = self.factor_conn()
            head.next_1 = start
            head.next_2 = new_start
            end.next_1 = tail
            new_end.next_1 = tail
            start = head
            end = tail
        return start, end

def closure(input_set):
    output_set = []
    if not len(input_set) > 0:
        return None
    stack = []
    for i in input_set:
        stack.append(i)
        output_set.append(i)
    while len(stack) > 0:
        current = stack.pop()
        if current.edge == "EPSILON":
            if current.next_1 and current.next_1 not in output_set:
                output_set.append(current.next_1)
                stack.append(current.next_1)
            if current.next_2 and current.next_2 not in output_set:
                output_set.append(current.next_2)
                stack.append(current.next_2)
    return output_set
def move(input_set, char):
    output_set = []
    for i in input_set:
        if i.edge == char if isinstance(i.edge, str) else char in i.edge:
            output_set.append(i.next_1)
    return output_set
def nfa_to_dfa(nfa):
    dfa_list = []
    dfa_list.append(DFA(closure([nfa])))
    jump_table = [{}]
    index = 0
    while index < len(dfa_list):
        current = dfa_list[index]
        for i in range(127):
            char = chr(i)
            moved = move(current.nfas, char)
            if not moved:
                continue
            nfa_closure = closure(moved)
            for j in dfa_list:
                if j.nfas == nfa_closure:
                    new_dfa = j
                    break
            else:
                new_dfa = DFA(nfa_closure)
                dfa_list.append(new_dfa)
                jump_table.append({})
            jump_table[current.status][char] = new_dfa.status
            if new_dfa.accepted:
                jump_table[new_dfa.status]["ACCEPT"] = True
        index += 1
    return dfa_list, jump_table
def dfa_in_group(dfa_node, group_list):
    for group in group_list:
        for dfa in group.dfas:
            if dfa.status == dfa_node:
                output = group
                return output
def minimize_dfa(dfa_list, jump_table):
    accept = []
    non_accept = []
    for i in dfa_list:
        if i.accepted:
            accept.append(i)
        else:
            non_accept.append(i)
    group_list = []
    if non_accept:
        group_list.append(DFAGroup(non_accept))
    if accept:
        group_list.append(DFAGroup(accept))
    index = 0
    group = group_list[index]
    while group:
        if len(group.dfas) == 1:
            index += 1
            group = group_list[index] if index < len(group_list) else None
            continue
        group_keys = []
        group_values = []
        for x in group.dfas:
            if x.accepted:
                gotos = x.function
            else:
                gotos = []
                for i in range(127):
                    char = chr(i)
                    goto = jump_table[x.status].get(char)
                    goto_group = dfa_in_group(goto, group_list)
                    gotos.append(goto_group.status if goto_group is not None else None)
            if gotos in group_keys:
                group_values[group_keys.index(gotos)].append(x)
            else:
                group_keys.append(gotos)
                group_values.append([x])
        if len(group_values) == 1 and group_values[0] == group.dfas:
            index += 1
            group = group_list[index] if index < len(group_list) else None
            continue
        group_list.remove(group)
        DFAGroup.STATUS -= 1
        for groups in group_values:
            new_group = DFAGroup(groups)
            group_list.insert(index, new_group)
            index -= 1
        index += 1
        group = group_list[index] if index < len(group_list) else None
        
    return group_list
def create_transition_table(dfa_list, jump_table, group_list):
    transition_table = [{} for i in range(len(group_list))]
    for dfa in dfa_list:
        for i in range(127):
            char = chr(i)
            to = jump_table[dfa.status].get(char)
            if to is None:
                continue
            from_group = dfa_in_group(dfa.status, group_list)
            to_group = dfa_in_group(to, group_list)
            transition_table[from_group.status][char] = to_group.status
        if dfa.accepted:
            from_group = dfa_in_group(dfa.status, group_list)
            transition_table[from_group.status]["ACCEPT"] = from_group.function
    return transition_table

class Lexer:
    def __init__(self):
        self.patterns = []
    
    def pattern(self, pattern):
        def decorator(func):
            self.patterns.append((pattern, func))
            return func
        return decorator
    
    def compile(self):
        pattern, function = self.patterns[0]
        lexer = Lexer(pattern)
        parser = Parser(lexer)
        start, end = parser.expr()
        end.function = function
        root = NFA()
        root.next_1 = start
        for pattern, function in self.patterns[1:]:
            lexer = Lexer(pattern)
            parser = Parser(lexer)
            start, end = parser.expr()
            end.function = function
            root.next_2 = start
            new_root = NFA()
            new_root.next_1 = root
            root = new_root
        dfa_list, jump_table = nfa_to_dfa(root)
        self.group_list = minimize_dfa(dfa_list, jump_table)
        self.transition_table = create_transition_table(dfa_list, jump_table, self.group_list)

    def lex(self, string):
        pos = 0
        char = string[pos]
        status = start = dfa_in_group(0, self.group_list).status
        back = None
        buffer = ""
        while char is not None:
            buffer += char
            status = self.transition_table[status].get(char)
            if status is None:
                if back is None:
                    print("Error!")
                    break
                else:
                    pos, function = back
                    status = start
                    back = None
                    buffer = buffer[:-1]
                    function(buffer)
                    buffer = ""
            else:
                if "ACCEPT" in self.transition_table[status]:
                    function = self.transition_table[status]["ACCEPT"]
                    if pos == len(string) - 1:
                        function(buffer)
                    back = (pos, function)
            pos += 1
            char = string[pos] if pos < len(string) else None
