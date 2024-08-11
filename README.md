# PLPG : Python Lexer and Parser Generator

使用最小DFA进行词法分析，使用带二义性处理的LR(1)进行语法分析。

速度估计比不上PLY，但纯自学纯手搓。

懒得写文档，以下是一个使用PLPG实现的JSON解析器代码：

```python
from lex import *
from parse import *

lexer = Lexer()
lexer.ignore = [" ", "\n", "\r", "\t"]
symbols = {"," : "comma", ":" : "colon", "{" : "lbrace", "}" : "rbrace", "[" : "lbracket", "]" : "rbracket"}
booleans = {"true": True, "false": False, "null": None}
@lexer.pattern(",|:|\\{|\\}|\\[|\\]")
def symbol(lexer):
    return Token(symbols[lexer.buffer], None)
@lexer.pattern("\\-?[0-9](\\.[0-9][0-9]*)?")
def number(lexer):
    string = lexer.buffer
    return Token("number", int(string) if string.isdigit() or string.replace("-", "").isdigit() else float(string))
@lexer.pattern('"[^"]*"')
def string(lexer):
    return Token("string", lexer.buffer[1:-1])
@lexer.pattern("true|false|null")
def boolean(lexer):
    return Token("boolean", booleans[lexer.buffer])
@lexer.eof()
def eof(lexer):
    return Token("$", None)
@lexer.undefined
def undefined(lexer):
    raise Exception("Undefined token: " + lexer.buffer)
lexer.compile()

parser = Parser()
parser.terminals = ["comma", "colon", "lbrace", "rbrace", "lbracket", "rbracket", "number", "string", "boolean", "$"]
@parser.pattern("S -> Value")
def S(parser, args):
    return args[0]
@parser.pattern("Array -> lbracket [Value (comma Value)*] rbracket", option = "NT")
def Array(parser, args):
    return args
@parser.pattern("Key -> string")
def Key(parser, args):
    return args[0].value
@parser.pattern("Object -> lbrace [Key colon Value (comma Key colon Value)*] rbrace", option = "NT")
def Object(parser, args):
    res = {}
    for i in range(0, len(args), 2):
        res[args[i]] = args[i+1]
    return res
@parser.pattern("Value -> string | number | boolean")
def Value_literal(parser, args):
    return args[0].value
@parser.pattern("Value -> Object | Array")
def Value_iterable(parser, args):
    return args[0]
@parser.error
def error(parser):
    raise Exception("Syntax error: " + parser.token.type + " at " + str(parser.lexer.line))
parser.compile()

with open("./test.json", "r") as f:
    text = f.read()
lexer.read(text)
parser.read(lexer)
print(parser.parse())
```
