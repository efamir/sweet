# type_system.py

from enum import Enum


class ValType(Enum):
    Int = "Int"
    Double = "Double"
    Bool = "Bool"
    String = "String"
    Error = "ErrorType"


# Оператори, що працюють з Int та Double
ARITHMETIC_OPS = {"+", "-", "*", "/", "**"}
# Оператори, що працюють з числовими та однаковими типами
RELATIONAL_OPS = {"<", ">", "<=", ">="}
# Оператори, що працюють тільки з однаковими типами
EQUALITY_OPS = {"==", "!="}


def calculate_type(left_type: ValType, operator: str, right_type: ValType | None = None) -> ValType:
    # Унарні оператори
    if right_type is None:
        if operator == "!" and left_type == ValType.Bool:
            return ValType.Bool
        if operator in ("+", "-") and left_type in (ValType.Int, ValType.Double):
            return left_type
        return ValType.Error

    # Бінарні оператори
    # Арифметичні операції
    if operator == "+":
        # Конкатенація рядків
        if left_type == ValType.String and right_type == ValType.String:
            return ValType.String

    if operator in ARITHMETIC_OPS:
        if left_type not in (ValType.Int, ValType.Double) or right_type not in (ValType.Int, ValType.Double):
            return ValType.Error
        if left_type == ValType.Double or right_type == ValType.Double:
            return ValType.Double
        return ValType.Int

    # Операції порівняння (числові)
    if operator in RELATIONAL_OPS:
        if left_type in (ValType.Int, ValType.Double) and right_type in (ValType.Int, ValType.Double):
            return ValType.Bool
        return ValType.Error

    # Операції рівності (працюють для всіх типів, якщо вони однакові)
    if operator in EQUALITY_OPS:
        if left_type == right_type:
            return ValType.Bool
        return ValType.Error

    # Специфічний випадок: присвоєння
    if operator == "=":
        # Дозволяємо присвоювати Int до Double
        if left_type == ValType.Double and right_type == ValType.Int:
            return ValType.Double
        if left_type == right_type:
            return left_type
        return ValType.Error

    return ValType.Error
