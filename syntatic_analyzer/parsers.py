# parsers.py

from syntatic_analyzer.rule_parsers import RuleParser, TokenLexemeOption


class TypeParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        if next_token and next_token.token == "keyword":
            if next_token.value in ("Int", "Double", "Bool", "String"):
                return self
        return None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "Type:")
            options = [
                TokenLexemeOption("keyword", "Int"),
                TokenLexemeOption("keyword", "Double"),
                TokenLexemeOption("keyword", "Bool"),
                TokenLexemeOption("keyword", "String")
            ]
            correct_option = self.parse_token_with_options(options)
            if correct_option:
                return self.parse_token(correct_option.token, correct_option.lexeme)
            return False


class VariableDeclarationParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value == "var" else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "VariableDeclaration:")

            if not self.parse_token("keyword", "var"): return False
            if not self.parse_token("id"): return False
            if not self.parse_token("colon"): return False

            if not TypeParser(self.context)(): return False

            if self.context.peek() and self.context.peek().token == "assign_op":
                if not self.parse_token("assign_op"): return False
                if not ExpressionParser(self.context)(): return False

            return self.parse_token("semicolon")


class ConstantDeclarationParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value == "let" else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "ConstantDeclaration:")

            if not self.parse_token("keyword", "let"): return False
            if not self.parse_token("id"): return False
            if not self.parse_token("colon"): return False
            if not TypeParser(self.context)(): return False
            if not self.parse_token("assign_op"): return False
            if not ExpressionParser(self.context)(): return False

            return self.parse_token("semicolon")


class DeclarationParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value in ("var", "let", "func") else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "Declaration:")

            active_parser = (
                    VariableDeclarationParser(self.context).check() or
                    ConstantDeclarationParser(self.context).check() or
                    FunctionDeclarationParser(self.context).check()
            )
            if active_parser:
                return active_parser()

            return False


class PrimaryParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        if next_token is None: return None

        if FunctionCallParser(self.context).check():
            return self

        is_const = next_token.token in ("id", "intnum", "realnum", "stringlit")
        is_bool = next_token.token == "keyword" and next_token.value in ("true", "false")
        is_lparen = next_token.token == "lparen"
        return self if is_const or is_bool or is_lparen else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "Primary:")

            if FunctionCallParser(self.context).check():
                return FunctionCallParser(self.context)()

            next_token = self.context.peek()
            if next_token.token == "lparen":
                if not self.parse_token("lparen"): return False
                if not ExpressionParser(self.context)(): return False
                return self.parse_token("rparen")

            options = [
                TokenLexemeOption("id"),
                TokenLexemeOption("intnum"),
                TokenLexemeOption("realnum"),
                TokenLexemeOption("stringlit"),
                TokenLexemeOption("keyword", "true"),
                TokenLexemeOption("keyword", "false")
            ]
            if self.parse_token_with_options(options):
                return self.parse_token(self.context.peek().token)
            return False


class FactorParser(RuleParser):
    def check(self):
        return self if PrimaryParser(self.context).check() else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "Factor:")

            if not PrimaryParser(self.context)(): return False

            next_token = self.context.peek()
            if next_token and next_token.token == "pow_op":
                if not self.parse_token("pow_op"): return False
                return FactorParser(self.context)()  # Рекурсивний виклик для правої асоціативності

            return True


class TermParser(RuleParser):
    def check(self):
        return self if FactorParser(self.context).check() else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "Term:")

            if not FactorParser(self.context)(): return False

            while True:
                next_token = self.context.peek()
                if not (next_token and next_token.token in ("mul_op", "div_op")):
                    break

                self.parse_token(next_token.token)  # Споживаємо '*' або '/'

                if not FactorParser(self.context)(): return False

            return True


class SimpleExpressionParser(RuleParser):
    def check(self):
        return self if TermParser(self.context).check() else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "SimpleExpression:")

            next_token = self.context.peek()
            if next_token and next_token.token in ("add_op", "sub_op", "not_op"):
                self.parse_token(next_token.token)

            if not TermParser(self.context)(): return False

            while True:
                next_token = self.context.peek()
                if not (next_token and next_token.token in ("add_op", "sub_op")):
                    break

                self.parse_token(next_token.token)  # Споживаємо '+' або '-'

                if not TermParser(self.context)(): return False

            return True


class ExpressionParser(RuleParser):
    def check(self):
        return self if SimpleExpressionParser(self.context).check() else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "Expression:")

            if not SimpleExpressionParser(self.context)(): return False

            next_token = self.context.peek()
            # Умова перевірки, чи є токен оператором відношення
            is_rel_op = next_token and next_token.token.endswith(("_op", "_equal_op")) and \
                        next_token.token not in (
                            "add_op", "sub_op", "mul_op", "div_op", "pow_op", "assign_op", "not_op")

            if is_rel_op:
                if not self.parse_token(next_token.token): return False
                if not SimpleExpressionParser(self.context)(): return False

            return True


class AssignmentStatementParser(RuleParser):
    def check(self):
        is_id = self.context.peek(0) and self.context.peek(0).token == "id"
        is_assign = self.context.peek(1) and self.context.peek(1).token == "assign_op"
        return self if is_id and is_assign else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "AssignmentStatement:")
            if not self.parse_token("id"): return False
            if not self.parse_token("assign_op"): return False
            if not ExpressionParser(self.context)(): return False
            return self.parse_token("semicolon")


class IfStatementParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value == "if" else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "IfStatement:")
            if not self.parse_token("keyword", "if"): return False
            if not ExpressionParser(self.context)(): return False
            if not self.parse_token("lcurly"): return False
            if not StatementListParser(self.context)(): return False
            if not self.parse_token("rcurly"): return False

            if self.context.peek() and self.context.peek().value == "else":
                if not self.parse_token("keyword", "else"): return False
                if not self.parse_token("lcurly"): return False
                if not StatementListParser(self.context)(): return False
                if not self.parse_token("rcurly"): return False

            return True


class WhileStatementParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value == "while" else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "WhileStatement:")
            if not self.parse_token("keyword", "while"): return False
            if not ExpressionParser(self.context)(): return False
            if not self.parse_token("lcurly"): return False
            if not StatementListParser(self.context)(): return False
            return self.parse_token("rcurly")


class IOStatementParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value in ("read", "write") else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "IOStatement:")
            next_token = self.context.peek()
            if next_token.value == "read":
                if not self.parse_token("keyword", "read"): return False
                if not self.parse_token("lparen"): return False
                if not self.parse_token("id"): return False
                if not self.parse_token("rparen"): return False
            elif next_token.value == "write":
                if not self.parse_token("keyword", "write"): return False
                if not self.parse_token("lparen"): return False
                if not ExpressionParser(self.context)(): return False
                if not self.parse_token("rparen"): return False

            return self.parse_token("semicolon")


class CompoundStatementParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.token == "lcurly" else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "CompoundStatement:")
            if not self.parse_token("lcurly"): return False
            if not StatementListParser(self.context)(): return False
            return self.parse_token("rcurly")


class StatementParser(RuleParser):
    def check(self):
        return self if self.context.peek() is not None else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "Statement:")

            active_parser = (
                    DeclarationParser(self.context).check() or
                    IfStatementParser(self.context).check() or
                    WhileStatementParser(self.context).check() or
                    IOStatementParser(self.context).check() or
                    CompoundStatementParser(self.context).check() or
                    ReturnStatementParser(self.context).check() or
                    FunctionCallStatementParser(self.context).check() or
                    AssignmentStatementParser(self.context).check()
            )

            if active_parser:
                return active_parser()
            else:
                lex = self.context.peek()
                print(
                    f"Parser ERROR: \n\t В рядку {lex.row} неочікувана інструкція, "
                    f"що починається з {TokenLexemeOption(lex.token, lex.value)}"
                )
                return False


class StatementListParser(RuleParser):
    def check(self):
        return self

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "StatementList:")

            while True:
                next_token = self.context.peek()
                if not next_token or next_token.token == "rcurly":
                    break

                if not StatementParser(self.context)():
                    return False

            return True


class ReturnStatementParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token and next_token.value == "return" else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "ReturnStatement:")
            if not self.parse_token("keyword", "return"): return False

            # Необов'язковий вираз
            if self.context.peek() and self.context.peek().token != "semicolon":
                if not ExpressionParser(self.context)(): return False

            return self.parse_token("semicolon")


class ArgumentListParser(RuleParser):
    def check(self):
        return self if ExpressionParser(self.context).check() else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "ArgumentList:")

            if not ExpressionParser(self.context)(): return False

            # Обробка списку аргументів через кому
            while self.context.peek() and self.context.peek().token == "comma":
                if not self.parse_token("comma"): return False
                if not ExpressionParser(self.context)(): return False

            return True


class FunctionCallParser(RuleParser):
    def check(self):
        # Виклик функції - це id, за яким іде '('
        is_id = self.context.peek(0) and self.context.peek(0).token == "id"
        is_lparen = self.context.peek(1) and self.context.peek(1).token == "lparen"
        return self if is_id and is_lparen else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "FunctionCall:")
            if not self.parse_token("id"): return False
            if not self.parse_token("lparen"): return False

            # Необов'язковий список аргументів
            if self.context.peek() and self.context.peek().token != "rparen":
                if not ArgumentListParser(self.context)(): return False

            return self.parse_token("rparen")


class FunctionCallStatementParser(RuleParser):
    def check(self):
        is_func_call = FunctionCallParser(self.context).check()
        if not is_func_call: return None

        # Для спрощення, довіряємо FunctionCallParser.check()
        return self

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "FunctionCallStatement:")
            if not FunctionCallParser(self.context)(): return False
            return self.parse_token("semicolon")


class ParameterParser(RuleParser):
    def check(self):
        is_id = self.context.peek(0) and self.context.peek(0).token == "id"
        is_colon = self.context.peek(1) and self.context.peek(1).token == "colon"
        return self if is_id and is_colon else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "Parameter:")
            if not self.parse_token("id"): return False
            if not self.parse_token("colon"): return False
            return TypeParser(self.context)()


class ParameterListParser(RuleParser):
    def check(self):
        return self if ParameterParser(self.context).check() else None

    def __call__(self):
        with self.context.next_indent():
            print(" " * self.context.indent + "ParameterList:")
            if not ParameterParser(self.context)(): return False

            while self.context.peek() and self.context.peek().token == "comma":
                if not self.parse_token("comma"): return False
                if not ParameterParser(self.context)(): return False

            return True


class FunctionDeclarationParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token and next_token.value == "func" else None

    def __call__(self):
        with (self.context.next_indent()):
            print(" " * self.context.indent + "FunctionDeclaration:")
            if not self.parse_token("keyword", "func"): return False
            if not self.parse_token("id"): return False
            if not self.parse_token("lparen"): return False

            # Необов'язковий список параметрів
            if self.context.peek() and self.context.peek().token != "rparen":
                if not ParameterListParser(self.context)(): return False

            if not self.parse_token("rparen"): return False

            # Необов'язковий тип повернення
            if self.context.peek() and self.context.peek().token == "sub_op" and self.context.peek(
                    1) and self.context.peek(1).token == "greater_op":
                if not self.parse_token("sub_op", "-"): return False
                if not self.parse_token("greater_op", ">"): return False
                if not TypeParser(self.context)(): return False

            if not self.parse_token("lcurly"): return False
            if not StatementListParser(self.context)(): return False
            return self.parse_token("rcurly")


class ProgramParser(RuleParser):
    def check(self):
        return self if self.context.peek() is not None else None

    def __call__(self):
        print("Program:")

        if not StatementListParser(self.context)():
            print("Parser: Аналіз завершився з помилками.")
            return False

        if self.context.peek() is not None:
            lex = self.context.peek()
            print(
                f"Parser ERROR: \n\t В рядку {lex.row} неочікувані символи після завершення програми, "
                f"починаючи з {TokenLexemeOption(lex.token, lex.value)}"
            )
            return False

        print("Parser: Синтаксичний аналіз завершився успішно.")
        return True
