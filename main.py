from lexical_analyzer import get_lexemes_and_print_result
from parser import ProgramParser
from pathlib import Path
from postfix_generator import PostfixCodeGenerator

if __name__ == "__main__":
    FILE_NAME = "test_examples/psm/test_input.sweet"

    try:
        lexemes, ids, consts = get_lexemes_and_print_result(Path(FILE_NAME))
        generator = PostfixCodeGenerator()
        if not ProgramParser((lexemes, generator))():
            exit(1)
        generator.save_to_file("example.postfix")
    except SystemExit as e:
        print(f"Аварійне завершення програми з кодом {e}")
    except Exception as e:
        print(f"Аварійне завершення програми з помилкою: {e}")
