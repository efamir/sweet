from lexical_analyzer import get_lexemes_and_print_result
from syntatic_analyzer import ProgramParser
from pathlib import Path

if __name__ == "__main__":
    FILE_NAME = "test_examples/syntatic/example.sweet"
    try:
        lexemes, ids, consts = get_lexemes_and_print_result(Path(FILE_NAME))
        if not ProgramParser(lexemes)():
            exit(1)
    except SystemExit as e:
        print(f"Lexer: Аварійне завершення програми з кодом {e}")
    except Exception as e:
        print(f"Lexer: Аварійне завершення програми з помилкою: {e}")
