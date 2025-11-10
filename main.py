from lexical_analyzer.lexical_analyzer import CodeReader, LexicalAnalyzer, StatesManager
from lexical_analyzer.states import states_dict
from syntatic_analyzer import ProgramParser
from pathlib import Path

if __name__ == "__main__":
    FILE_NAME = "test_examples/syntatic/example.sweet"
    try:
        code_reader = CodeReader(Path(FILE_NAME))
        code_title = f"Вхідний код з файлу \"{FILE_NAME}\""
        print(f"{code_title:-^42}")
        code_rows = code_reader.code_rows
        print(*[f"{i + 1:2}| {code_rows[i]}" for i in range(len(code_rows))], sep="")
        states_manager = StatesManager(states_dict)
        analyzer = LexicalAnalyzer(code_reader, states_manager)

        print(f"{'Результати лексичного аналізу':-^42}\n")
        res = analyzer.get_lexemes()
        if not res:
            exit(1)
        lexemes, ids, consts = analyzer.get_lexemes()

        print(f"{'Таблиця разбору':^42}")
        print(f"┌{'-'*5}┬{'-'*13}┬{'-'*17}┬{'-'*2}┐")
        print(f"|{'Рядок':^5}|{'Значення':^13}|{'Токен':^17}|{'ID':^2}|")
        print(f"|{'-' * 5}┼{'-' * 13}┼{'-' * 17}┼{'-' * 2}|")
        for i, lexeme in enumerate(lexemes):
            print(f"|{lexeme.row:5}|{lexeme.value:^13}|{lexeme.token:^17}|{lexeme.ext_id if lexeme.ext_id else '':2}|")
        print(f"└{'-' * 5}┴{'-' * 13}┴{'-' * 17}┴{'-' * 2}┘")
        print()

        print(f"{'Таблиця iдентифiкаторiв':^42}")
        print(f"┌{'-' * 2}┬{'-' * 13}┐")
        print(f"|{'ID':^2}|{'Ідентифікатор':^13}|")
        print(f"|{'-' * 2}┬{'-' * 13}|")
        for value, _id in ids.items():
            print(f"|{_id:2}|{value:^13}|")
        print(f"└{'-' * 2}┴{'-' * 13}┘")
        print()

        print(f"{'Таблиця констант':^42}")
        print(f"┌{'-' * 2}┬{'-' * 13}┐")
        print(f"|{'ID':^2}|{'Константа':^13}|")
        print(f"|{'-' * 2}┬{'-' * 13}|")
        for value, _id in consts.items():
            print(f"|{_id:2}|{value:^13}|")
        print(f"└{'-' * 2}┴{'-' * 13}┘")
        print()

        print("Lexer: Лексичний аналiз завершено успiшно")
        print(f"\n{'Результати синтаксичного аналізу':-^42}\n")
        if not ProgramParser(lexemes)():
            exit(1)
    except SystemExit as e:
        print(f"Lexer: Аварійне завершення програми з кодом {e}")
    except Exception as e:
        print(f"Lexer: Аварійне завершення програми з помилкою: {e}")
