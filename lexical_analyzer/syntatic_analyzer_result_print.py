from lexical_analyzer.lexical_analyzer import CodeReader, LexicalAnalyzer, StatesManager
from lexical_analyzer.states import states_dict
from pathlib import Path


def get_lexemes_and_print_result(code_path: Path):
    code_reader = CodeReader(code_path)
    code_title = f"Вхідний код з файлу \"{code_path.name}\""
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
    print(f"┌{'-' * 5}┬{'-' * 13}┬{'-' * 17}┬{'-' * 2}┐")
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
    return lexemes, ids, consts
