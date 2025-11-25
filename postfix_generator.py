class PostfixCodeGenerator:
    def __init__(self):
        self.code = []  # Список інструкцій (.code)
        self.variables = []  # Список змінних (.vars)
        self.funcs = []  # Список функцій (.funcs) - НОВЕ
        self._label_counter = 0
        self.used_globals = set()

    # --- 1. Оголошення ---
    def declare_var(self, name: str, type_: str):
        """Додає запис у секцію .vars"""
        psm_type = type_.lower()
        if psm_type == "double":
            psm_type = "float"
        self.variables.append(f"{name}\t{psm_type}")

    def add_used_global(self, name: str):
        """Реєструє використання глобальної змінної"""
        self.used_globals.add(name)

    def declare_func(self, name: str, ret_type: str, args_count: int):
        """Додає запис у секцію .funcs (НОВЕ)"""
        psm_type = ret_type.lower() if ret_type else "void"
        if psm_type == "double":
            psm_type = "float"
        # Формат: name type count
        self.funcs.append(f"{name}\t{psm_type}\t{args_count}")

    # --- 2. Робота з операндами (PUSH) ---
    def push_int(self, value: str):
        self._emit(value, "int")

    def push_float(self, value: str):
        self._emit(value, "float")

    def push_bool(self, value: str):
        self._emit(value, "bool")

    def push_string(self, value: str):
        self._emit(value, "string")

    def push_var(self, name: str):
        self._emit(name, "r-val")

    def push_var_addr(self, name: str):
        self._emit(name, "l-val")

    # --- 3. Оператори ---
    def emit_binary_op(self, operator: str):
        if operator == "+":
            self._emit("+", "math_op")
        elif operator == "-":
            self._emit("-", "math_op")
        elif operator == "*":
            self._emit("*", "math_op")
        elif operator == "/":
            self._emit("/", "math_op")
        elif operator == "%":
            self._emit("%", "math_op")
        elif operator == "**":
            self._emit("^", "pow_op")

        elif operator == "==":
            self._emit("==", "rel_op")
        elif operator == "!=":
            self._emit("!=", "rel_op")
        elif operator == ">":
            self._emit(">", "rel_op")
        elif operator == "<":
            self._emit("<", "rel_op")
        elif operator == ">=":
            self._emit(">=", "rel_op")
        elif operator == "<=":
            self._emit("<=", "rel_op")

        elif operator == "&&":
            self._emit("AND", "bool_op")
        elif operator == "||":
            self._emit("OR", "bool_op")
        else:
            raise ValueError(f"Генератор коду: Невідомий бінарний оператор '{operator}'")

    def emit_unary_op(self, operator: str):
        if operator == '-':
            self._emit("NEG", "math_op")
        elif operator == '!':
            self._emit("NOT", "bool_op")
        else:
            raise ValueError(f"Генератор коду: Невідомий унарний оператор '{operator}'")

    def emit_assign(self):
        self._emit("=", "assign_op")

    # --- 4. Введення-виведення та Конвертація ---
    def emit_print(self):
        self._emit("OUT", "out_op")

    def emit_read(self):
        self._emit("INP", "inp_op")

    def emit_cast(self, from_type: str, to_type: str):
        f = from_type.lower().replace("double", "float")
        t = to_type.lower().replace("double", "float")

        if f == "int" and t == "float":
            self._emit("i2f", "conv")
        elif f == "float" and t == "int":
            self._emit("f2i", "conv")
        elif f == "int" and t == "string":
            self._emit("i2s", "conv")
        elif f == "float" and t == "string":
            self._emit("f2s", "conv")
        elif f == "string" and t == "int":
            self._emit("s2i", "conv")
        elif f == "string" and t == "float":
            self._emit("s2f", "conv")
        elif f == "int" and t == "bool":
            self._emit("i2b", "conv")
        elif f == "bool" and t == "int":
            self._emit("b2i", "conv")

    # --- 5. Керування потоком ---
    def new_label(self) -> str:
        self._label_counter += 1
        return f"m{self._label_counter}"

    def emit_label(self, label: str):
        self._emit(label, "label")
        self._emit(":", "colon")

    def emit_jump(self, label: str):
        self._emit(label, "label")
        self._emit("JMP", "jump")

    def emit_jump_if_false(self, label: str):
        self._emit(label, "label")
        self._emit("JF", "jf")

    # --- Внутрішній метод ---
    def _emit(self, lexeme, token):
        self.code.append(f"{lexeme}\t{token}")

    # --- Фінальне збереження ---
    def save_to_file(self, filename: str):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(".target: Postfix Machine\n")
            f.write(".version: 0.3\n\n")

            # Змінні
            if self.variables:
                f.write(".vars(\n")
                for var in self.variables:
                    f.write(f"\t{var}\n")
                f.write(")\n\n")

            # Глобальні змінні
            if self.used_globals:
                f.write(".globVarList(\n")
                for var_name in self.used_globals:
                    f.write(f"\t{var_name}\n")
                f.write(")\n\n")

            # Функції
            if self.funcs:
                f.write(".funcs(\n")
                for func in self.funcs:
                    f.write(f"\t{func}\n")
                f.write(")\n\n")

            # Код
            f.write(".code(\n")
            for line in self.code:
                f.write(f"\t{line}\n")
            f.write(")\n")