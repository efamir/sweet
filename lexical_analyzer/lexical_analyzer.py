from .custom_types import *
from pathlib import Path


def get_char_group(char: str):
    if len(char) < 1:
        raise ValueError
    char = char[0]
    if not char or char in "\n\r":
        return "EndOfLine"

    if char.isalpha():
        return "Letter"

    if char.isdigit():
        return "Digit"

    if char == ".":
        return "dot"

    if char in " \t":
        return "ws"

    if char in SINGLE_CHAR_TOKENS:
        return char

    return "other"


class CodeReader:
    def __init__(self, code_path: Path):
        self._code_rows = []
        with code_path.open("r", encoding="utf-8") as f:
            for line in f:
                self._code_rows.append(line)
        if not self._code_rows:
            raise ValueError("The code can't be empty")
        self._rows = len(self._code_rows)
        self._row_index = 0
        self._index = 0
        self._has_next = True
        self._current_row = self._code_rows[self._row_index]
        self._current_row_len = len(self._current_row)

    def get_next_char(self):
        if self._row_index == self._rows:
            return ""
        res = (self._current_row[self._index], self._row_index + 1)
        if self._index != (self._current_row_len - 1):
            self._index += 1
            return res

        self._row_index += 1
        self._index = 0
        if self._row_index == self._rows:
            self._has_next = False
            return res
        self._current_row = self._code_rows[self._row_index]
        self._current_row_len = len(self._current_row)
        if self._current_row_len == 0:
            raise ValueError("Row can't have length 0")
        return res

    def put_back(self):
        if self._index < 1 and self._row_index == 0:
            raise RuntimeError("There is nothing to put back")
        self._has_next = True
        if not self._index < 1:
            self._index -= 1
            return

        self._row_index -= 1
        self._current_row = self._code_rows[self._row_index]
        self._current_row_len = len(self._current_row)
        self._index = self._current_row_len - 1

    @property
    def has_next(self):
        return self._has_next

    @property
    def code_rows(self):
        return self._code_rows.copy()

    def reset(self):
        if not self._code_rows:
            raise ValueError("The code can't be empty")
        self._rows = len(self._code_rows)
        self._row_index = 0
        self._index = 0
        self._has_next = True
        self._current_row = self._code_rows[self._row_index]
        self._current_row_len = len(self._current_row)


class StatesManager:
    def __init__(
            self,
            states_dict: dict[int, dict[str, int | FinalStateResult]],
            starting_state=0,
    ):
        if starting_state not in states_dict:
            raise ValueError(
                f"There is no q{starting_state} in states_dict, please specify the correct starting_state."
            )
        self._states_dict = states_dict
        self._starting_state = starting_state
        self._current_state = states_dict[starting_state]

    def next_state(self, ch: str) -> int | FinalStateResult:
        """
        Sets the next state based on provided character.
        Returns keyword: FinalStateResult if end state is reached, otherwise returns next state: int if not start, None if start state
        """

        state = self._current_state
        next_state = state.get(get_char_group(ch)) if state.get(get_char_group(ch)) is not None else state.get("other")
        if next_state is None:
            raise RuntimeError(
                f"State {self._current_state} has no rule for '{get_char_group(ch)}' or 'other'"
            )

        if next_state not in self._states_dict:
            raise RuntimeError(
                "There is error in states dictionary: got state from function that is not specified in dictionary."
            )
        self._current_state = self._states_dict[next_state]
        if isinstance(self._current_state, FinalStateResult):
            res = self._current_state
            self.reset()
            return res
        return next_state if next_state != self._starting_state else None

    def reset(self):
        self._current_state = self._states_dict[self._starting_state]


class LexicalAnalyzer:
    def __init__(self, code_reader: CodeReader, states_manager: StatesManager):
        self._code_reader = code_reader
        self._states_manager = states_manager

    def get_lexemes(self) -> tuple[list[Lexeme], dict[str, int], dict[str, int]] | None:
        res: list[Lexeme] = []
        current_lexeme_value = ""
        try:
            while True:
                if not self._code_reader.has_next:
                    break
                ch, row = self._code_reader.get_next_char()

                char_group = get_char_group(ch)
                if not current_lexeme_value and (
                        char_group == "ws" or char_group == "EndOfLine"
                ):
                    continue

                next_state = self._states_manager.next_state(ch)
                if isinstance(next_state, FinalStateResult):
                    if next_state.put_back:
                        self._code_reader.put_back()
                    else:
                        current_lexeme_value += ch
                    if next_state.error:
                        self._process_error(next_state, row, ch)
                        return None
                    res.append(Lexeme(next_state.token, repr(current_lexeme_value)[1:-1], row))
                    current_lexeme_value = ""
                elif next_state:
                    current_lexeme_value += ch
                else:
                    current_lexeme_value = ""
        finally:
            self._code_reader.reset()
            self._states_manager.reset()

        return self._post_process_lexemes(res)

    @staticmethod
    def _process_error(state, row, ch):
        match state.error:
            case 101:
                print(f"Lexer: у рядку {row} неочiкуваний символ {repr(ch)}")
            case 102:
                print(f"Lexer: у рядку {row} очiкувався чисельний символ (Digit), а не {repr(ch)}")
            case _:
                print(f"Lexer: у рядку {row} невідома помилка на символі {repr(ch)}")

    @staticmethod
    def _post_process_lexemes(lexemes: list[Lexeme]) -> tuple[list[Lexeme], dict[str, int], dict[str, int]]:
        res = []
        ids_i, consts_i = 1, 1
        ids, consts = dict(), dict()
        for lexeme in lexemes:
            if lexeme.token == "id" and lexeme.value in KEYWORDS:
                res.append(Lexeme("keyword", lexeme.value, lexeme.row))
            elif lexeme.token == "punct":
                specific_token = PUNCTUATION_MAP.get(lexeme.value, "unknown_punct")
                res.append(Lexeme(specific_token, lexeme.value, lexeme.row))
            elif lexeme.token == "id":
                if lexeme.value not in ids:
                    ids[lexeme.value] = ids_i
                    ids_i += 1
                res.append(Lexeme(lexeme.token, lexeme.value, lexeme.row, ids[lexeme.value]))
            elif lexeme.token in CONSTANT_TOKENS:
                if lexeme.value not in consts:
                    consts[lexeme.value] = consts_i
                    consts_i += 1
                res.append(Lexeme(lexeme.token, lexeme.value, lexeme.row, consts[lexeme.value]))
            else:
                res.append(lexeme)
        return res, ids, consts
