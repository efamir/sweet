# rule_parsers.py

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple

from lexical_analyzer.custom_types import Lexeme
from .type_system import ValType
from postfix_generator import PostfixCodeGenerator

class TokenLexemeOption(NamedTuple):
    token: str
    lexeme: str | None = None

    def __str__(self):
        return f"(token: {self.token}, lexeme: {self.lexeme if self.lexeme else 'any'})"


class IndKind(Enum):
    var = 1
    let = 2
    func = 3


@dataclass
class Symbol:
    name: str
    type: ValType
    kind: IndKind
    params: list[ValType] | None = None
    initialized: bool = False


@dataclass
class Scope:
    name: str
    symbols: list[Symbol] = field(default_factory=list)
    name_symbol_map: dict[str, Symbol] = field(default_factory=dict)


class SymbolTable:
    def __init__(self):
        self.__scopes: list[Scope] = [Scope("main")]
        self.__scope_name_scope_map: dict[str, Scope] = {}
        self.__current_scope: Scope = self.__scopes[-1]

    def add(self, symbol: Symbol) -> bool:
        if symbol.name in self.__current_scope.name_symbol_map:
            return False
        self.__current_scope.name_symbol_map[symbol.name] = symbol
        self.__current_scope.symbols.append(symbol)
        return True

    @contextmanager
    def new_scope(self, name: str):
        assert self.lookup(name) is not None
        try:
            new_scope = Scope(name)
            self.__scope_name_scope_map[name] = new_scope
            self.__scopes.append(new_scope)
            self.__current_scope = new_scope
            yield None
        finally:
            self.__scopes.pop()
            self.__current_scope = self.__scopes[-1]

    def is_global(self, name: str) -> bool:
        if len(self.__scopes) == 1:
            return False

        return (name in self.__scopes[0].name_symbol_map) and (len(self.__scopes) > 1)

    def lookup(self, name: str) -> Symbol | None:
        for scope in self.__scopes[::-1]:
            search_res = scope.name_symbol_map.get(name)
            if search_res:
                return search_res

    def set_initialized(self, name: str):
        symbol = self.lookup(name)
        if not symbol:
            return
        symbol.initialized = True

    @property
    def current_scope_name(self) -> str:
        return self.__current_scope.name


class ParserContext:
    def __init__(self, lexemes: list[Lexeme], generator: PostfixCodeGenerator):
        self._lexemes = lexemes
        self._lexemes_len = len(lexemes)
        self._ind = 0
        self._indent = 0
        self.return_value = None
        self.symbol_table = SymbolTable()
        self.generator = generator
        self.functions_to_save = []

    def peek(self, offset=0) -> Lexeme | None:
        if self._ind + offset >= self.lexemes_len:
            return None
        return self._lexemes[self._ind + offset]

    def consume(self) -> Lexeme:
        token = self.peek()
        self._ind += 1
        return token

    @contextmanager
    def call(self):
        try:
            self.return_value = None
            self._indent += 2
            yield None
        finally:
            self._indent -= 2

    @property
    def index(self):
        return self._ind

    @property
    def lexemes_len(self):
        return self._lexemes_len

    @property
    def indent(self):
        return self._indent


class RuleParser(ABC):
    def __init__(self, context: ParserContext | tuple[list[Lexeme], PostfixCodeGenerator]):
        self.context = context if isinstance(context, ParserContext) else ParserContext(context[0], context[1])

    def parse_token(self, token: str, lexeme: str | None = None, check=False):
        lex = self.context.consume() if not check else self.context.peek()
        if lex is None:
            self.__failure_pr(check,
                              "Parser ERROR: \n\t Неочiкуваний кiнець програми - в таблицi символiв (розбору) "
                              f"немає запису з номером {self.context.index}.\n\t"
                              f" Очiкувалось - {TokenLexemeOption(token, lexeme)}"
                              )
            return False
        if lex.token != token:
            self.__failure_pr(check,
                              f"Parser ERROR: \n\t В рядку {lex.row} неочiкуваний елемент "
                              f"{TokenLexemeOption(lex.token, lex.value)}.\n\t "
                              f"Очiкувався - {TokenLexemeOption(token, lexeme)}."
                              )
            return False
        if not lexeme:
            self.__token_pr(check, lex)
            return True
        if lex.value == lexeme:
            self.__token_pr(check, lex)
            return True

        self.__failure_pr(check,
                          f"Parser ERROR: \n\t В рядку {lex.row} неочiкуваний елемент "
                          f"{TokenLexemeOption(lex.token, lex.value)}.\n\t "
                          f"Очiкувався - {TokenLexemeOption(token, lexeme)}."
                          )
        return False

    def parse_token_with_options(self, options: list[TokenLexemeOption], with_empty_option=False, check=False):
        correct_option = None

        for option in options:
            if self.parse_token(option.token, option.lexeme, check=True):
                correct_option = option
                break

        if not correct_option and not with_empty_option:
            lex = self.context.peek()
            options_s = ";\n\t\t".join(map(str, options))
            self.__failure_pr(check,
                              f"Parser ERROR: \n\t В рядку {lex.row} неочiкуваний елемент "
                              f"{TokenLexemeOption(lex.token, lex.value)}.\n\t "
                              f"Очiкувався один з наступних варіантів:\n\t\t{options_s}."
                              )
            return False

        return correct_option

    @staticmethod
    def __failure_pr(check, *args, **kwargs):
        if check:
            return
        print(*args, **kwargs)

    def __token_pr(self, check, lexeme: Lexeme):
        if check:
            return
        print(" " * self.context.indent, end="")
        print(f"parseToken: В рядку {lexeme.row} токен {TokenLexemeOption(lexeme.token, lexeme.value)}")

    @abstractmethod
    def __call__(self, *args, **kwargs):
        pass

    @abstractmethod
    def check(self):
        pass


class IfStatementParser(RuleParser):
    def __call__(self, *args, **kwargs):
        pass

    def check(self):
        return self if self.parse_token("keyword", "if", check=True) else None


class Parser(RuleParser):
    def __call__(self, *args, **kwargs):
        pass

    def check(self):
        pass
