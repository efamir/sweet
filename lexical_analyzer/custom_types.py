from typing import NamedTuple


class FinalStateResult(NamedTuple):
    token: str
    put_back: bool = False
    error: int | None = None


class Lexeme(NamedTuple):
    token: str
    value: str
    row: int
    ext_id: int | None = None


SINGLE_CHAR_TOKENS = {"/", "=", "_", "!", "<", ">", "*", "+", "-", '"', "(", ")", "{", "}", ",", ";", ":"}

KEYWORDS = {
    "var", "let", "if", "else", "for", "while", "in",
    "Int", "Double", "Bool", "String", "true", "false",
    "func", "return", "write", "read"
}

PUNCTUATION_MAP = {
    "(": "lparen", ")": "rparen", "{": "lcurly", "}": "rcurly",
    ",": "comma", ";": "semicolon", ":": "colon"
}

CONSTANT_TOKENS = {"intnum", "realnum", "stringlit"}
