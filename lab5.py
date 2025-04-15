#!/usr/bin/env python3
import sys

# Глобальные структуры для построения НКА
transitions = {}  # transitions[state][symbol] = set(целевых состояний)
symbols = set()   # множество символов (включая 'ε')
state_count = 0   # для нумерации состояний

def new_state():
    """Создаёт новое состояние (идентификатор целого типа)."""
    global state_count
    s = state_count
    state_count += 1
    return s

def add_transition(frm, symbol, to):
    """Добавляет переход в таблицу переходов."""
    if frm not in transitions:
        transitions[frm] = {}
    if symbol not in transitions[frm]:
        transitions[frm][symbol] = set()
    transitions[frm][symbol].add(to)
    symbols.add(symbol)

# Функции для построения фрагментов НКА по алгоритму Томпсона
def literal_NFA(c):
    """НКА для литерального символа."""
    s = new_state()
    f = new_state()
    add_transition(s, c, f)
    return (s, f)

def epsilon_NFA():
    """НКА для пустой строки (ε-переход от s до f)."""
    s = new_state()
    f = new_state()
    add_transition(s, 'ε', f)
    return (s, f)

def concat_NFA(nfa1, nfa2):
    """Конкатенация двух НКА: соединяем финальное состояние первого ε-переходом к начальному второго."""
    (s1, f1) = nfa1
    (s2, f2) = nfa2
    add_transition(f1, 'ε', s2)
    return (s1, f2)

def union_NFA(nfa1, nfa2):
    """Объединение (альтернация) двух НКА."""
    s = new_state()
    f = new_state()
    (s1, f1) = nfa1
    (s2, f2) = nfa2
    add_transition(s, 'ε', s1)
    add_transition(s, 'ε', s2)
    add_transition(f1, 'ε', f)
    add_transition(f2, 'ε', f)
    return (s, f)

def star_NFA(nfa):
    """Построение НКА для конструкций r*."""
    s = new_state()
    f = new_state()
    (ns, nf) = nfa
    add_transition(s, 'ε', ns)
    add_transition(s, 'ε', f)
    add_transition(nf, 'ε', ns)
    add_transition(nf, 'ε', f)
    return (s, f)

def plus_NFA(nfa):
    """Построение НКА для конструкций r+ (однократное вхождение плюс цикл)."""
    s = new_state()
    f = new_state()
    (ns, nf) = nfa
    add_transition(s, 'ε', ns)
    add_transition(nf, 'ε', ns)
    add_transition(nf, 'ε', f)
    return (s, f)

# Реализация рекурсивного спуска для парсинга регулярного выражения.
# Поддерживаются операторы: | (альтернатива), неявная конкатенация, *, +, группировка ( ) и пустой символ: ()
class Parser:
    def __init__(self, regex):
        # удаляем пробелы для удобства
        self.regex = regex.replace(" ", "")
        self.pos = 0
        self.len = len(self.regex)

    def parse(self):
        nfa = self.parse_union()
        return nfa

    def current(self):
        if self.pos < self.len:
            return self.regex[self.pos]
        return None

    def eat(self, char):
        if self.current() == char:
            self.pos += 1
        else:
            sys.exit(f"Ожидался символ '{char}' в позиции {self.pos}")

    def parse_union(self):
        left = self.parse_concat()
        while self.current() == '|':
            self.eat('|')
            right = self.parse_concat()
            left = union_NFA(left, right)
        return left

    def parse_concat(self):
        # Конкатенация до встречи с | или закрывающей скобкой
        frag = None
        while self.current() and self.current() not in ')|':
            next_frag = self.parse_star()
            if frag is None:
                frag = next_frag
            else:
                frag = concat_NFA(frag, next_frag)
        if frag is None:
            # Если нет символов, возвращаем ε-НКА
            frag = epsilon_NFA()
        return frag

    def parse_star(self):
        frag = self.parse_basic()
        while self.current() in ['*', '+']:
            op = self.current()
            self.pos += 1
            if op == '*':
                frag = star_NFA(frag)
            elif op == '+':
                frag = plus_NFA(frag)
        return frag

    def parse_basic(self):
        c = self.current()
        if c == '(':
            self.eat('(')
            # Особый случай: пустые скобки означают пустой символ
            if self.current() == ')':
                self.eat(')')
                return epsilon_NFA()
            frag = self.parse_union()
            self.eat(')')
            return frag
        else:
            # Литерал
            self.pos += 1
            return literal_NFA(c)

# Функции для формирования таблицы переходов автомата Мура.
def generate_q_mapping(states_order):
    """
    Создает отображение: состояние -> метка (q0, q1, ...).
    Финальное состояние (при выводе заменяется на "F" в заголовке).
    """
    mapping = {}
    for i, s in enumerate(states_order):
        mapping[s] = f"q{i}"
    return mapping

def format_table_with_q(transitions, states_order, terminals, q_mapping):
    """
    Формирует CSV-таблицу с заголовками:
      Первая строка: пустые ячейки для всех столбцов, кроме последнего, где стоит "F"
      Вторая строка: метки состояний согласно q_mapping
    Затем для каждого символа входного алфавита (включая ε) формируются строки с переходами.
    Если переход отсутствует, ячейка остаётся пустой, а несколько переходов разделяются запятой.
    """
    num_states = len(states_order)
    header1 = ";" + ";".join("" for _ in range(num_states - 1)) + ";F"
    header2 = ";" + ";".join(q_mapping[s] for s in states_order)
    rows = [header1, header2]

    # Сортировка символов: цифры, потом буквы, потом ε
    def symbol_key(s):
        if s == 'ε':
            return (2, s)
        elif s[0].isdigit():
            return (0, s)
        else:
            return (1, s)
    sorted_terminals = sorted(terminals, key=symbol_key)

    for term in sorted_terminals:
        row = [term]
        for s in states_order:
            cell = ""
            if s in transitions and term in transitions[s]:
                dests = transitions[s][term]
                mapped = []
                for dst in states_order:
                    if dst in dests:
                        mapped.append("F" if dst == final_state else q_mapping[dst])
                cell = ",".join(mapped)
            row.append(cell)
        rows.append(";".join(row))
    return "\n".join(rows)

def main():
    # Ожидается запуск: ./LAB5.py output.csv "(r*|su*t)*su*"
    if len(sys.argv) != 3:
        print("Usage: ./LAB5.py <output_file> <regular_expression>")
        sys.exit(1)
    output_file = sys.argv[1]
    regex_input = sys.argv[2]

    # Построение НКА по регулярному выражению
    parser = Parser(regex_input)
    start_state, accept_state = parser.parse()

    # Финальное состояние автомата – то, которое было получено как accept_state фрагмента
    global final_state
    final_state = accept_state

    # Для состояний автомата собираем все упомянутые состояния
    all_states = set(transitions.keys())
    for trans in transitions.values():
        for dest_set in trans.values():
            all_states |= dest_set

    # Если финальное состояние не попало в ключи, добавляем его
    all_states.add(final_state)

    # Сортируем состояния по числовому значению, но перемещаем финальное состояние в конец
    ordered_states = sorted(list(all_states))
    if final_state in ordered_states:
        ordered_states.remove(final_state)
        ordered_states.append(final_state)
    # Если состояние не имеет переходов, добавляем пустой словарь
    for s in ordered_states:
        if s not in transitions:
            transitions[s] = {}

    # Формирование отображения состояний в метки q0, q1, ...
    q_mapping = generate_q_mapping(ordered_states)
    # Формирование таблицы переходов
    result = format_table_with_q(transitions, ordered_states, symbols, q_mapping)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result + "\n")

if __name__ == '__main__':
    main()
