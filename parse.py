class Product:
    def __init__(self, name, body, function = None, priority = None):
        self.name = name
        self.body = body
        self.function = function
    def __str__(self):
        return f"{self.name} -> {''.join(self.body)}"
    __repr__ = __str__
    def _eq__(self, other):
        return self.name == other.name and self.body == other.body

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
            pass
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

class Parser:
    def __init__(self):
        self.terminal = []
        self.priority = {}
        self.patterns = {}

    def pattern(self, name, pattern):
        def decorator(func):
            product = Product(name, pattern, func)
            if pattern.name in self.patterns:
                self.patterns[name].append(product)
            else:
                self.patterns[name] = [product]
            return func
        return decorator
    
    def set_terminal(self, terminal):
        self.terminal = terminal

    def set_priority(self, priority):
        self.priority = priority

    def compile(self):
        self.goto_table, state_list = make_goto_table(self.terminal, self.patterns)
        self.action_table = make_action_table(self.terminal, self.priority, self.goto_table, state_list)

    def parse(self, text):
        state_stack = [0]
        value_stack = []
        index = 0
        char = text[index]
        x = char
        goto_table = self.goto_table
        action_table = self.action_table
        while True:
            state = state_stack[-1]
            if (state, x) in action_table:
                action, arg = action_table[(state, x)]
            elif (state, x) in goto_table:
                state_stack.append(goto_table[(state, x)])
                x = char
                continue
            elif (state, "ε") in action_table:
                action, arg = action_table[(state, "ε")]
            else:
                print("Error!")
                break
            if action == "SHIFT":
                state_stack.append(arg)
                index += 1
                char = text[index] if index < len(text) else "$"
                x = char
            elif action == "REDUCE":
                for _ in range(len(arg.body)):
                    state_stack.pop()
                if arg.function:
                    arg.function(value_stack, text[index - 1])
                x = arg.name
            elif action == "ACCEPT":
                break
