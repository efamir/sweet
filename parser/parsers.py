# parsers.py

from parser.rule_parsers import RuleParser, TokenLexemeOption, Symbol, IndKind
from parser.type_system import ValType, calculate_type
from postfix_generator import PostfixCodeGenerator


class TypeParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        if next_token and next_token.token == "keyword":
            if next_token.value in ("Int", "Double", "Bool", "String"):
                return self
        return None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "Type:")
            options = [
                TokenLexemeOption("keyword", "Int"), TokenLexemeOption("keyword", "Double"),
                TokenLexemeOption("keyword", "Bool"), TokenLexemeOption("keyword", "String")
            ]
            correct_option = self.parse_token_with_options(options, check=True)
            if correct_option:
                self.context.return_value = ValType(correct_option.lexeme)
                return self.parse_token(correct_option.token, correct_option.lexeme)
            return False


class VariableDeclarationParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value == "var" else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "VariableDeclaration:")
            if not self.parse_token("keyword", "var"): return False

            var_name_token = self.context.peek()
            if not self.parse_token("id"): return False
            if not self.parse_token("colon"): return False
            if not TypeParser(self.context)(): return False
            var_type = self.context.return_value

            symbol = Symbol(name=var_name_token.value, type=var_type, kind=IndKind.var, params=None)

            if not self.context.symbol_table.add(symbol):
                lex = var_name_token
                print(
                    f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Повторне оголошення ідентифікатора '{lex.value}'")
                return False

            # GEN: Оголошуємо змінну
            self.context.generator.declare_var(var_name_token.value, var_type.value)

            if self.context.peek() and self.context.peek().token == "assign_op":
                # GEN: l-val
                self.context.generator.push_var_addr(var_name_token.value)

                if not self.parse_token("assign_op"): return False
                if not ExpressionParser(self.context)(): return False
                expr_type = self.context.return_value

                if calculate_type(var_type, "=", expr_type) == ValType.Error:
                    lex = self.context.peek(-1)
                    print(
                        f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Неможливо присвоїти вираз типу {expr_type.value} змінній типу {var_type.value}")
                    return False

                # GEN: Cast
                if var_type == ValType.Double and expr_type == ValType.Int:
                    self.context.generator.emit_cast("Int", "Double")

                # GEN: Assign
                self.context.generator.emit_assign()

                self.context.symbol_table.set_initialized(var_name_token.value)

            return self.parse_token("semicolon")


class ConstantDeclarationParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value == "let" else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "ConstantDeclaration:")
            if not self.parse_token("keyword", "let"): return False

            const_name_token = self.context.peek()
            if not self.parse_token("id"): return False
            if not self.parse_token("colon"): return False
            if not TypeParser(self.context)(): return False
            const_type = self.context.return_value

            # GEN
            self.context.generator.declare_var(const_name_token.value, const_type.value)
            self.context.generator.push_var_addr(const_name_token.value)

            if not self.parse_token("assign_op"): return False
            if not ExpressionParser(self.context)(): return False
            expr_type = self.context.return_value

            if calculate_type(const_type, "=", expr_type) == ValType.Error:
                lex = self.context.peek(-1)
                print(
                    f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Неможливо присвоїти вираз типу {expr_type.value} константі типу {const_type.value}")
                return False

            # GEN
            if const_type == ValType.Double and expr_type == ValType.Int:
                self.context.generator.emit_cast("Int", "Double")
            self.context.generator.emit_assign()

            symbol = Symbol(name=const_name_token.value, type=const_type, kind=IndKind.let, initialized=True,
                            params=None)
            if not self.context.symbol_table.add(symbol):
                lex = const_name_token
                print(
                    f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Повторне оголошення ідентифікатора '{lex.value}'")
                return False

            return self.parse_token("semicolon")


class DeclarationParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value in ("var", "let", "func") else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "Declaration:")
            active_parser = (
                    VariableDeclarationParser(self.context).check() or
                    ConstantDeclarationParser(self.context).check() or
                    FunctionDeclarationParser(self.context).check()
            )
            if active_parser:
                return active_parser()
            return False


# --- Expressions ---

class PrimaryParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        if next_token is None: return None
        if FunctionCallParser(self.context).check(): return self
        is_const = next_token.token in ("id", "intnum", "realnum", "stringlit")
        is_bool = next_token.token == "keyword" and next_token.value in ("true", "false")
        is_lparen = next_token.token == "lparen"
        return self if is_const or is_bool or is_lparen else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "Primary:")
            if FunctionCallParser(self.context).check():
                return FunctionCallParser(self.context)()

            next_token = self.context.peek()
            if next_token.token == "lparen":
                if not self.parse_token("lparen"): return False
                if not ExpressionParser(self.context)(): return False
                return self.parse_token("rparen")

            current_token = self.context.peek()

            # GEN: Генерація операндів
            if current_token.token == "intnum":
                self.context.return_value = ValType.Int
                self.context.generator.push_int(current_token.value)
            elif current_token.token == "realnum":
                self.context.return_value = ValType.Double
                self.context.generator.push_float(current_token.value)
            elif current_token.token == "stringlit":
                self.context.return_value = ValType.String
                self.context.generator.push_string(current_token.value)
            elif current_token.value in ("true", "false"):
                self.context.return_value = ValType.Bool
                self.context.generator.push_bool(current_token.value)
            elif current_token.token == "id":
                symbol = self.context.symbol_table.lookup(current_token.value)
                if not symbol:
                    lex = current_token
                    print(
                        f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Використання неоголошеного ідентифікатора '{lex.value}'")
                    return False
                if not symbol.initialized and symbol.kind != IndKind.func:
                    lex = current_token
                    print(
                        f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Використання неініціалізованої змінної '{lex.value}'")
                    return False

                if self.context.symbol_table.is_global(current_token.value):
                    self.context.generator.add_used_global(current_token.value)

                self.context.return_value = symbol.type
                self.context.generator.push_var(current_token.value)
            else:
                return False

            return self.parse_token(current_token.token)


class FactorParser(RuleParser):
    def check(self):
        return self if PrimaryParser(self.context).check() else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "Factor:")
            if not PrimaryParser(self.context)(): return False
            left_type = self.context.return_value

            next_token = self.context.peek()
            if next_token and next_token.token == "pow_op":
                operator = self.context.consume()
                if not FactorParser(self.context)(): return False
                right_type = self.context.return_value

                result_type = calculate_type(left_type, operator.value, right_type)
                if result_type == ValType.Error:
                    lex = operator
                    print(
                        f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Операція '{lex.value}' не може бути застосована до операндів з типами {left_type.value} та {right_type.value}")
                    return False

                # --- ВИПРАВЛЕННЯ ДЛЯ PSM (pow_op) ---
                # PSM вимагає float для степеня, навіть якщо ми рахуємо Int ** Int

                # 1. Примусова конвертація операндів у float (Double)
                if right_type == ValType.Int:
                    self.context.generator.emit_cast("Int", "Double")

                if left_type == ValType.Int:
                    self.context.generator._emit("SWAP", "stack_op")
                    self.context.generator.emit_cast("Int", "Double")
                    self.context.generator._emit("SWAP", "stack_op")

                # 2. Виконуємо операцію
                self.context.generator.emit_binary_op(operator.value)

                # 3. Якщо семантично результат має бути Int (Int ** Int -> Int),
                #    але PSM повернула Float, конвертуємо результат назад у Int
                if result_type == ValType.Int:
                    self.context.generator.emit_cast("Double", "Int")

                self.context.return_value = result_type
            else:
                self.context.return_value = left_type
            return True


class TermParser(RuleParser):
    def check(self):
        return self if FactorParser(self.context).check() else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "Term:")
            if not FactorParser(self.context)(): return False
            left_type = self.context.return_value

            while True:
                next_token = self.context.peek()
                if not (next_token and next_token.token in ("mul_op", "div_op")):
                    break
                operator = self.context.consume()
                if not FactorParser(self.context)(): return False
                right_type = self.context.return_value

                result_type = calculate_type(left_type, operator.value, right_type)
                if result_type == ValType.Error:
                    lex = operator
                    print(
                        f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Операція '{lex.value}' не може бути застосована до операндів з типами {left_type.value} та {right_type.value}")
                    return False

                # GEN
                if result_type == ValType.Double:
                    if right_type == ValType.Int:
                        self.context.generator.emit_cast("Int", "Double")
                    if left_type == ValType.Int:
                        self.context.generator._emit("SWAP", "stack_op")
                        self.context.generator.emit_cast("Int", "Double")
                        self.context.generator._emit("SWAP", "stack_op")

                self.context.generator.emit_binary_op(operator.value)

                # цілочисельне ділення
                if operator.value == "/" and result_type == ValType.Int:
                    self.context.generator.emit_cast("Double", "Int")

                left_type = result_type

            self.context.return_value = left_type
            return True


class SimpleExpressionParser(RuleParser):
    def check(self):
        return self if TermParser(self.context).check() else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "SimpleExpression:")
            unary_op_token = None
            next_token = self.context.peek()
            if next_token and next_token.token in ("add_op", "sub_op", "not_op"):
                unary_op_token = self.context.consume()

            if not TermParser(self.context)(): return False
            expr_type = self.context.return_value

            if unary_op_token:
                result_type = calculate_type(expr_type, unary_op_token.value)
                if result_type == ValType.Error:
                    lex = unary_op_token
                    print(
                        f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Унарний оператор '{lex.value}' не може бути застосований до виразу типу {expr_type.value}")
                    return False
                expr_type = result_type
                # GEN
                self.context.generator.emit_unary_op(unary_op_token.value)

            left_type = expr_type
            while True:
                next_token = self.context.peek()
                if not (next_token and next_token.token in ("add_op", "sub_op")):
                    break
                operator = self.context.consume()
                if not TermParser(self.context)(): return False
                right_type = self.context.return_value

                result_type = calculate_type(left_type, operator.value, right_type)
                if result_type == ValType.Error:
                    lex = operator
                    print(
                        f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Операція '{lex.value}' не може бути застосована до операндів з типами {left_type.value} та {right_type.value}")
                    return False

                # GEN
                if operator.value == "+" and result_type == ValType.String:
                    if right_type != ValType.String:
                        self.context.generator.emit_cast(right_type.value, "String")
                    if left_type != ValType.String:
                        self.context.generator._emit("SWAP", "stack_op")
                        self.context.generator.emit_cast(left_type.value, "String")
                        self.context.generator._emit("SWAP", "stack_op")
                        self.context.generator._emit("CAT", "cat_op")  # Для рядків CAT
                    else:
                        self.context.generator._emit("CAT", "cat_op")  # Для рядків CAT

                elif result_type == ValType.Double:
                    if right_type == ValType.Int:
                        self.context.generator.emit_cast("Int", "Double")
                    if left_type == ValType.Int:
                        self.context.generator._emit("SWAP", "stack_op")
                        self.context.generator.emit_cast("Int", "Double")
                        self.context.generator._emit("SWAP", "stack_op")
                    self.context.generator.emit_binary_op(operator.value)
                else:
                    self.context.generator.emit_binary_op(operator.value)

                left_type = result_type

            self.context.return_value = left_type
            return True


class ExpressionParser(RuleParser):
    def check(self):
        return self if SimpleExpressionParser(self.context).check() else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "Expression:")
            if not SimpleExpressionParser(self.context)(): return False
            left_type = self.context.return_value

            next_token = self.context.peek()
            is_rel_op = next_token and next_token.token.endswith(("_op", "_equal_op")) and \
                        next_token.token not in (
                            "add_op", "sub_op", "mul_op", "div_op", "pow_op", "assign_op", "not_op")

            if is_rel_op:
                operator = self.context.consume()
                if not SimpleExpressionParser(self.context)(): return False
                right_type = self.context.return_value

                result_type = calculate_type(left_type, operator.value, right_type)
                if result_type == ValType.Error:
                    lex = operator
                    print(
                        f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Операція '{lex.value}' не може бути застосована до операндів з типами {left_type.value} та {right_type.value}")
                    return False

                # GEN
                if left_type == ValType.Double or right_type == ValType.Double:
                    if right_type == ValType.Int:
                        self.context.generator.emit_cast("Int", "Double")
                    if left_type == ValType.Int:
                        self.context.generator._emit("SWAP", "stack_op")
                        self.context.generator.emit_cast("Int", "Double")
                        self.context.generator._emit("SWAP", "stack_op")

                self.context.generator.emit_binary_op(operator.value)
                self.context.return_value = result_type
            else:
                self.context.return_value = left_type
            return True


# --- Statements ---

class AssignmentStatementParser(RuleParser):
    def check(self):
        is_id = self.context.peek(0) and self.context.peek(0).token == "id"
        is_assign = self.context.peek(1) and self.context.peek(1).token == "assign_op"
        return self if is_id and is_assign else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "AssignmentStatement:")
            var_token = self.context.peek()
            if not self.parse_token("id"): return False

            symbol = self.context.symbol_table.lookup(var_token.value)
            if not symbol:
                print(
                    f"Parser ERROR:\n\tВ рядку {var_token.row} семантична помилка: Спроба присвоєння значення неоголошеній змінній '{var_token.value}'")
                return False
            if symbol.kind == IndKind.let:
                print(
                    f"Parser ERROR:\n\tВ рядку {var_token.row} семантична помилка: Неможливо присвоїти нове значення константі '{var_token.value}'")
                return False

            if self.context.symbol_table.is_global(var_token.value):
                self.context.generator.add_used_global(var_token.value)

            # GEN
            self.context.generator.push_var_addr(var_token.value)

            if not self.parse_token("assign_op"): return False
            if not ExpressionParser(self.context)(): return False
            expr_type = self.context.return_value

            if calculate_type(symbol.type, "=", expr_type) == ValType.Error:
                lex = self.context.peek(-1)
                print(
                    f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Неможливо присвоїти вираз типу {expr_type.value} змінній '{var_token.value}' типу {symbol.type.value}")
                return False

            # GEN
            if symbol.type == ValType.Double and expr_type == ValType.Int:
                self.context.generator.emit_cast("Int", "Double")

            self.context.generator.emit_assign()

            self.context.symbol_table.set_initialized(var_token.value)
            return self.parse_token("semicolon")


class IfStatementParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value == "if" else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "IfStatement:")
            if not self.parse_token("keyword", "if"): return False
            if not ExpressionParser(self.context)(): return False
            expr_type = self.context.return_value

            if expr_type != ValType.Bool:
                lex = self.context.peek(-1)
                print(
                    f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Умова інструкції 'if' повинна мати тип Bool, а не {expr_type.value}")
                return False

            # GEN: Мітки для if
            else_label = self.context.generator.new_label()
            end_label = self.context.generator.new_label()
            self.context.generator.emit_jump_if_false(else_label)

            if not self.parse_token("lcurly"): return False
            if not StatementListParser(self.context)(): return False
            if not self.parse_token("rcurly"): return False

            self.context.generator.emit_jump(end_label)
            self.context.generator.emit_label(else_label)

            if self.context.peek() and self.context.peek().value == "else":
                if not self.parse_token("keyword", "else"): return False
                if not self.parse_token("lcurly"): return False
                if not StatementListParser(self.context)(): return False
                if not self.parse_token("rcurly"): return False

            self.context.generator.emit_label(end_label)
            return True


class WhileStatementParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value == "while" else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "WhileStatement:")

            # GEN: Мітки для while
            start_label = self.context.generator.new_label()
            end_label = self.context.generator.new_label()
            self.context.generator.emit_label(start_label)

            if not self.parse_token("keyword", "while"): return False
            if not ExpressionParser(self.context)(): return False
            expr_type = self.context.return_value

            if expr_type != ValType.Bool:
                lex = self.context.peek(-1)
                print(
                    f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Умова інструкції 'while' повинна мати тип Bool, а не {expr_type.value}")
                return False

            self.context.generator.emit_jump_if_false(end_label)

            if not self.parse_token("lcurly"): return False
            if not StatementListParser(self.context)(): return False

            self.context.generator.emit_jump(start_label)
            self.context.generator.emit_label(end_label)

            return self.parse_token("rcurly")


class IOStatementParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.value in ("read", "write") else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "IOStatement:")
            next_token = self.context.peek()
            if next_token.value == "read":
                if not self.parse_token("keyword", "read"): return False
                if not self.parse_token("lparen"): return False

                id_token = self.context.peek()
                if not self.parse_token("id"): return False

                symbol = self.context.symbol_table.lookup(id_token.value)
                if not symbol:
                    print(
                        f"Parser ERROR:\n\tВ рядку {id_token.row} семантична помилка: Спроба читання в неоголошену змінну '{id_token.value}'")
                    return False
                if symbol.kind == IndKind.let:
                    print(
                        f"Parser ERROR:\n\tВ рядку {id_token.row} семантична помилка: Неможливо читати значення в константу '{id_token.value}'")
                    return False

                if self.context.symbol_table.is_global(id_token.value):
                    self.context.generator.add_used_global(id_token.value)

                # GEN
                self.context.generator.push_var_addr(id_token.value)
                self.context.generator.emit_read()

                if symbol.type == ValType.Int:
                    self.context.generator.emit_cast("String", "Int")
                elif symbol.type == ValType.Double:
                    self.context.generator.emit_cast("String", "Double")

                self.context.generator.emit_assign()

                self.context.symbol_table.set_initialized(id_token.value)
                if not self.parse_token("rparen"): return False
            elif next_token.value == "write":
                if not self.parse_token("keyword", "write"): return False
                if not self.parse_token("lparen"): return False
                if not ExpressionParser(self.context)(): return False

                # GEN
                self.context.generator.emit_print()

                if not self.parse_token("rparen"): return False

            return self.parse_token("semicolon")


class CompoundStatementParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token is not None and next_token.token == "lcurly" else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "CompoundStatement:")
            if not self.parse_token("lcurly"): return False
            if not StatementListParser(self.context)(): return False
            return self.parse_token("rcurly")


class StatementParser(RuleParser):
    def check(self):
        return self if self.context.peek() is not None else None

    def __call__(self):
        with self.context.call():
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
                    f"Parser ERROR:\n\tВ рядку {lex.row} неочікувана інструкція, що починається з {TokenLexemeOption(lex.token, lex.value)}")
                return False


class StatementListParser(RuleParser):
    def check(self):
        return self

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "StatementList:")
            while True:
                next_token = self.context.peek()
                if not next_token or next_token.token == "rcurly":
                    break
                if not StatementParser(self.context)():
                    return False
            return True


# --- FUNCTIONS ---

class ReturnStatementParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token and next_token.value == "return" else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "ReturnStatement:")

            current_scope_name = self.context.symbol_table.current_scope_name
            if current_scope_name == "main":
                lex = self.context.peek()
                print(
                    f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Інструкція 'return' не може знаходитись поза тілом функції.")
                return False

            current_function_symbol = self.context.symbol_table.lookup(current_scope_name)

            if not self.parse_token("keyword", "return"): return False

            has_expression = self.context.peek() and self.context.peek().token != "semicolon"

            if has_expression:
                if current_function_symbol.type is None:
                    lex = self.context.peek(-1)
                    print(
                        f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Функція '{current_scope_name}' не повинна повертати значення, але інструкція 'return' його повертає.")
                    return False

                if not ExpressionParser(self.context)(): return False
                expr_type = self.context.return_value

                if calculate_type(current_function_symbol.type, "=", expr_type) == ValType.Error:
                    lex = self.context.peek(-1)
                    print(
                        f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Тип виразу '{expr_type.value}' не відповідає типу повернення функції '{current_function_symbol.type.value}'.")
                    return False

                # GEN: Cast for return
                if current_function_symbol.type == ValType.Double and expr_type == ValType.Int:
                    self.context.generator.emit_cast("Int", "Double")
            else:
                if current_function_symbol.type is not None:
                    lex = self.context.peek(-1)
                    print(
                        f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Функція '{current_scope_name}' повинна повертати значення типу '{current_function_symbol.type.value}', але інструкція 'return' нічого не повертає.")
                    return False

            # GEN
            self.context.generator._emit("RET", "RET")

            return self.parse_token("semicolon")


class ArgumentListParser(RuleParser):
    def check(self):
        return self if ExpressionParser(self.context).check() else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "ArgumentList:")
            arg_types = []
            if not ExpressionParser(self.context)(): return False
            arg_types.append(self.context.return_value)

            while self.context.peek() and self.context.peek().token == "comma":
                if not self.parse_token("comma"): return False
                if not ExpressionParser(self.context)(): return False
                arg_types.append(self.context.return_value)

            self.context.return_value = arg_types
            return True


class FunctionCallParser(RuleParser):
    def check(self):
        is_id = self.context.peek(0) and self.context.peek(0).token == "id"
        is_lparen = self.context.peek(1) and self.context.peek(1).token == "lparen"
        return self if is_id and is_lparen else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "FunctionCall:")
            func_name_token = self.context.peek()
            if not self.parse_token("id"): return False

            symbol = self.context.symbol_table.lookup(func_name_token.value)
            if not symbol or symbol.kind != IndKind.func:
                print(
                    f"Parser ERROR:\n\tВ рядку {func_name_token.row} семантична помилка: Спроба виклику неоголошеної або не-функції '{func_name_token.value}'")
                return False

            if not self.parse_token("lparen"): return False

            arg_types = []
            # GEN: Аргументи вже будуть на стеку
            if self.context.peek() and self.context.peek().token != "rparen":
                if not ArgumentListParser(self.context)(): return False
                arg_types = self.context.return_value

            if not self.parse_token("rparen"): return False

            if len(arg_types) != len(symbol.params):
                print(
                    f"Parser ERROR:\n\tВ рядку {func_name_token.row} семантична помилка: Неправильна кількість аргументів при виклику функції '{symbol.name}'. Очікувалось {len(symbol.params)}, знайдено {len(arg_types)}")
                return False

            for i, (param_type, arg_type) in enumerate(zip(symbol.params, arg_types)):
                if calculate_type(param_type, "=", arg_type) == ValType.Error:
                    print(
                        f"Parser ERROR:\n\tВ рядку {func_name_token.row} семантична помилка: Тип {i + 1}-го аргументу не співпадає з типом параметра у функції '{symbol.name}'. Очікувався {param_type.value}, знайдено {arg_type.value}")
                    return False

            # GEN: CALL
            self.context.generator._emit(func_name_token.value, "CALL")

            self.context.return_value = symbol.type
            return True


class FunctionCallStatementParser(RuleParser):
    def check(self):
        return self if FunctionCallParser(self.context).check() else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "FunctionCallStatement:")
            if not FunctionCallParser(self.context)(): return False
            return self.parse_token("semicolon")


class ParameterParser(RuleParser):
    def check(self):
        is_id = self.context.peek(0) and self.context.peek(0).token == "id"
        is_colon = self.context.peek(1) and self.context.peek(1).token == "colon"
        return self if is_id and is_colon else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "Parameter:")
            param_name_token = self.context.peek()
            if not self.parse_token("id"): return False
            if not self.parse_token("colon"): return False
            if not TypeParser(self.context)(): return False
            param_type = self.context.return_value

            self.context.return_value = (param_name_token.value, param_type)
            return True


class ParameterListParser(RuleParser):
    def check(self):
        return self if ParameterParser(self.context).check() else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "ParameterList:")

            params = []
            if not ParameterParser(self.context)(): return False
            params.append(self.context.return_value)

            while self.context.peek() and self.context.peek().token == "comma":
                if not self.parse_token("comma"): return False
                if not ParameterParser(self.context)(): return False
                params.append(self.context.return_value)

            self.context.return_value = params
            return True


class FunctionDeclarationParser(RuleParser):
    def check(self):
        next_token = self.context.peek()
        return self if next_token and next_token.value == "func" else None

    def __call__(self):
        with self.context.call():
            print(" " * self.context.indent + "FunctionDeclaration:")
            if not self.parse_token("keyword", "func"): return False

            func_name_token = self.context.peek()
            if not self.parse_token("id"): return False

            if self.context.symbol_table.current_scope_name != "main":
                lex = func_name_token
                print(
                    f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Оголошення вкладених функцій не підтримується ('{lex.value}').")
                return False

            if not self.parse_token("lparen"): return False

            params = []
            if self.context.peek() and self.context.peek().token != "rparen":
                if not ParameterListParser(self.context)(): return False
                params = self.context.return_value

            if not self.parse_token("rparen"): return False

            return_type = None
            if self.context.peek() and self.context.peek().token == "sub_op" and self.context.peek(
                    1) and self.context.peek(1).token == "greater_op":
                if not self.parse_token("sub_op", "-"): return False
                if not self.parse_token("greater_op", ">"): return False
                if not TypeParser(self.context)(): return False
                return_type = self.context.return_value

            param_types = [p[1] for p in params]
            func_symbol = Symbol(name=func_name_token.value, type=return_type, kind=IndKind.func, params=param_types,
                                 initialized=True)

            if not self.context.symbol_table.add(func_symbol):
                lex = func_name_token
                print(
                    f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Повторне оголошення функції '{lex.value}'")
                return False

            # GEN: Swap Generators
            main_generator = self.context.generator
            # Реєструємо функцію в головному генераторі
            main_generator.declare_func(func_name_token.value, return_type.value if return_type else None, len(params))

            func_generator = PostfixCodeGenerator()
            self.context.generator = func_generator

            # GEN: Declare params
            for param_name, param_type in params:
                self.context.generator.declare_var(param_name, param_type.value)

            if not self.parse_token("lcurly"): return False

            with self.context.symbol_table.new_scope(name=func_name_token.value):
                for param_name, param_type in params:
                    param_symbol = Symbol(name=param_name, type=param_type, kind=IndKind.var, initialized=True,
                                          params=None)
                    if not self.context.symbol_table.add(param_symbol):
                        lex = func_name_token
                        print(
                            f"Parser ERROR:\n\tВ рядку {lex.row} семантична помилка: Повторне оголошення параметра '{param_name}' у функції '{func_name_token.value}'")
                        return False

                if not StatementListParser(self.context)():
                    return False

            # GEN: Save and Restore
            func_filename = f"example${func_name_token.value}.postfix"
            self.context.functions_to_save.append((func_filename, func_generator))
            self.context.generator = main_generator

            return self.parse_token("rcurly")


class ProgramParser(RuleParser):
    def check(self):
        return self if self.context.peek() is not None else None

    def __call__(self):
        print(f"\n{'Результати синтаксичного аналізу':-^42}\n")
        print("Program:")

        if not StatementListParser(self.context)():
            print("Parser: Аналіз завершився з помилками.")
            return False

        if self.context.peek() is not None:
            lex = self.context.peek()
            print(
                f"Parser ERROR:\n\tВ рядку {lex.row} неочікувані символи після завершення програми, "
                f"починаючи з {TokenLexemeOption(lex.token, lex.value)}"
            )
            return False

        all_known_funcs = self.context.generator.funcs

        for filename, func_gen in self.context.functions_to_save:
            func_gen.funcs = list(all_known_funcs)
            func_gen.save_to_file(filename)

        print("Parser: Синтаксичний аналіз завершився успішно.")
        return True
