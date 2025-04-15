#!/usr/bin/env python3
import sys
import re
from collections import defaultdict, deque

# Глобальный счётчик для создания уникальных номеров состояний в НКА.
state_count = 0
def new_state():
    global state_count
    s = f"S{state_count}"
    state_count += 1
    return s

# Фрагмент НКА: имеет начальное (start) и конечное (accept) состояние.
class NFAFragment:
    def __init__(self, start, accept):
        self.start = start
        self.accept = accept

# Функция-токенизатор регулярного выражения.
def tokenize(regex):
    tokens = []
    i = 0
    while i < len(regex):
        c = regex[i]
        if c == ' ':
            i += 1
            continue
        if c in {'(', ')', '*', '+', '|'}:
            # Обработка пустых скобок: () означает ε
            if c == '(' and i+1 < len(regex) and regex[i+1] == ')':
                tokens.append('ε')
                i += 2
            else:
                tokens.append(c)
                i += 1
        else:
            # Любой другой символ трактуем как литерал
            tokens.append(c)
            i += 1
    return tokens

# Вставка явного оператора конкатенации ('.')
def insert_concat(tokens):
    result = []
    # Определим, какие типы токенов могут быть слева и справа, между которыми нужна конкатенация:
    # Если слева — литерал, ε, закрывающая скобка, звездочка или плюс,
    # а справа — литерал, ε, открывающая скобка
    for i, token in enumerate(tokens):
        result.append(token)
        if i < len(tokens)-1:
            left = token
            right = tokens[i+1]
            if (left not in {'|', '('} and right not in {'|', ')', '*', '+'}):
                result.append('.')
    return result

# Преобразование инфиксной записи в постфиксную с помощью алгоритма Шантинга-Ярда.
def to_postfix(tokens):
    prec = {'*':3, '+':3, '.':2, '|':1}
    output = []
    stack = []
    for token in tokens:
        if token not in prec and token not in {'(', ')'}:
            output.append(token)
        elif token in {'*', '+'}:
            output.append(token)
        elif token == '.':
            while stack and stack[-1] != '(' and prec.get(stack[-1],0) >= prec[token]:
                output.append(stack.pop())
            stack.append(token)
        elif token == '|':
            while stack and stack[-1] != '(' and prec.get(stack[-1],0) >= prec[token]:
                output.append(stack.pop())
            stack.append(token)
        elif token == '(':
            stack.append(token)
        elif token == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            if stack and stack[-1] == '(':
                stack.pop()
    while stack:
        output.append(stack.pop())
    return output

# Построение ε–НКА по алгоритму Томпсона.
def build_nfa(postfix):
    transitions = defaultdict(list)
    stack = []
    for token in postfix:
        if token not in {'*', '+', '.', '|'}:
            # Литерал или ε
            s0 = new_state()
            s1 = new_state()
            # Для ε-ленты, символ уже обозначен как 'ε'
            transitions[s0].append(( 'ε', s1 ))
            # Если литерал (не ε), добавляем переход по символу
            if token != 'ε':
                transitions[s0] = [(token, s1)]
            frag = NFAFragment(s0, s1)
            stack.append(frag)
        else:
            if token == '.':
                # Конкатенация: pop два фрагмента, соединяем
                frag2 = stack.pop()
                frag1 = stack.pop()
                # Добавляем ε-переход из accept первого фрагмента к start второго
                transitions[frag1.accept].append(('ε', frag2.start))
                frag = NFAFragment(frag1.start, frag2.accept)
                stack.append(frag)
            elif token == '|':
                # Альтернатива: pop два фрагмента, создаём новый start и accept
                frag2 = stack.pop()
                frag1 = stack.pop()
                s0 = new_state()
                s1 = new_state()
                transitions[s0].append(('ε', frag1.start))
                transitions[s0].append(('ε', frag2.start))
                transitions[frag1.accept].append(('ε', s1))
                transitions[frag2.accept].append(('ε', s1))
                frag = NFAFragment(s0, s1)
                stack.append(frag)
            elif token == '*':
                # Клини замыкание: pop фрагмент, создаём новый start и accept
                frag1 = stack.pop()
                s0 = new_state()
                s1 = new_state()
                transitions[s0].append(('ε', frag1.start))
                transitions[s0].append(('ε', s1))
                transitions[frag1.accept].append(('ε', frag1.start))
                transitions[frag1.accept].append(('ε', s1))
                frag = NFAFragment(s0, s1)
                stack.append(frag)
            elif token == '+':
                # Плюс: аналогично *, но минимум одно повторение
                frag1 = stack.pop()
                s0 = new_state()
                s1 = new_state()
                transitions[s0].append(('ε', frag1.start))
                transitions[frag1.accept].append(('ε', frag1.start))
                transitions[frag1.accept].append(('ε', s1))
                frag = NFAFragment(s0, s1)
                stack.append(frag)
    if len(stack) != 1:
        raise Exception("Ошибка построения НКА.")
    frag = stack.pop()
    return frag.start, frag.accept, transitions

# Функция вычисления ε–замыкания множества состояний.
def epsilon_closure(states, transitions):
    stack = list(states)
    closure = set(states)
    while stack:
        state = stack.pop()
        for sym, nxt in transitions.get(state, []):
            if sym == 'ε' and nxt not in closure:
                closure.add(nxt)
                stack.append(nxt)
    return closure

# Функция перехода: по символу sym из состояний.
def move(states, sym, transitions):
    result = set()
    for state in states:
        for t_sym, nxt in transitions.get(state, []):
            if t_sym == sym:
                result.add(nxt)
    return result

# Построение ДКА посредством алгоритма подмножеств.
def subset_construction(nfa_start, nfa_accept, transitions):
    # Собираем алфавит (терминальные символы) – все символы, кроме 'ε'
    alph = set()
    for state, trans in transitions.items():
        for sym, _ in trans:
            if sym != 'ε':
                alph.add(sym)
    # Начальное множество состояний = ε–замыкание от nfa_start
    start_set = frozenset(epsilon_closure({nfa_start}, transitions))
    dfa_states = {}  # frozenset -> state id
    dfa_states[start_set] = new_state()
    # Сохраним информацию о том, является ли состояние финальным
    dfa_final = set()
    if nfa_accept in start_set:
        dfa_final.add(dfa_states[start_set])
    dfa_trans = {}  # state id -> { symbol: dest_state_id }
    state_order = []
    queue = deque([start_set])
    while queue:
        current = queue.popleft()
        current_id = dfa_states[current]
        state_order.append(current_id)
        dfa_trans[current_id] = {}
        for sym in sorted(alph, key=lambda x: (0 if x[0].isdigit() else 1, x)):
            # Получаем переход: move(current, sym) и его ε–замыкание
            nxt = set()
            for state in current:
                nxt |= epsilon_closure(move({state}, sym, transitions), transitions)
            if not nxt:
                continue
            nxt_fs = frozenset(nxt)
            if nxt_fs not in dfa_states:
                dfa_states[nxt_fs] = new_state()
                if nfa_accept in nxt_fs:
                    dfa_final.add(dfa_states[nxt_fs])
                queue.append(nxt_fs)
            dfa_trans[current_id][sym] = dfa_states[nxt_fs]
    return dfa_trans, state_order, dfa_final, sorted(alph, key=lambda x: (0 if x[0].isdigit() else 1, x))

# Объединение всех финальных состояний в один.
def merge_final_states(dfa_trans, state_order, dfa_final):
    # Если ни одно состояние не финальное, ничего не меняем.
    if not dfa_final:
        return dfa_trans, state_order
    # Создадим новый финальный символ "H"
    merged_final = "H"
    new_trans = {}
    new_order = []
    for s in state_order:
        # Если состояние финальное, не сохраняем его отдельно
        if s in dfa_final:
            continue
        new_order.append(s)
    # Добавляем финальное состояние один раз в конец
    new_order.append(merged_final)
    # Обновляем переходы: если переход ведёт в любое финальное состояние, перенаправляем его в merged_final.
    for s, trans in dfa_trans.items():
        if s in dfa_final:
            # Состояния, которые были финальными, не копируем, они будут объединены.
            continue
        new_trans[s] = {}
        for sym, dest in trans.items():
            if dest in dfa_final:
                new_trans[s][sym] = merged_final
            else:
                new_trans[s][sym] = dest
    # Для финального состояния merged_final формируем пустые переходы (или можно скопировать их, но по условию автомата Мура финальное состояние не имеет исходящих сигналов)
    new_trans[merged_final] = {}
    return new_trans, new_order

# Функция формирования CSV-таблицы, аналогичная той, что была в изначальном варианте.
def format_table_with_q(transitions, states_order, terminals, q_mapping):
    num_states = len(states_order)
    # Первая строка заголовка: первые num_states-1 ячеек пустые, последняя – "F"
    header1 = ";" + ";".join("" for _ in range(num_states - 1)) + ";F"
    # Вторая строка заголовка: отображаем метки состояний согласно q_mapping
    header2 = ";" + ";".join(q_mapping[s] for s in states_order)
    rows = [header1, header2]
    for term in terminals:
        row = [term]
        for s in states_order:
            cell = ""
            if s in transitions and term in transitions[s]:
                dest = transitions[s][term]
                # Если целевое состояние – финальное (помечено как "H"), выводим "F"
                cell = "F" if dest == "H" else q_mapping[dest]
            row.append(cell)
        rows.append(";".join(row))
    return "\n".join(rows)

def generate_q_mapping(states_order):
    mapping = {}
    for i, s in enumerate(states_order):
        # Если s == "H", в таблице выводится как "F", а сама метка генерируется как q{i} – это нормально.
        mapping[s] = f"q{i}"
    return mapping

def main():
    if len(sys.argv) != 3:
        print("Usage: ./LAB5.py <output_file> <regex>")
        sys.exit(1)
    output_file = sys.argv[1]
    regex = sys.argv[2]

    # 1. Токенизация и преобразование регулярного выражения.
    tokens = tokenize(regex)
    tokens = insert_concat(tokens)
    postfix = to_postfix(tokens)
    # 2. Построение ε–НКА по алгоритму Томпсона.
    nfa_start, nfa_accept, nfa_trans = build_nfa(postfix)
    # 3. Построение ДКА методом подмножеств.
    dfa_trans, state_order, dfa_final, terminals = subset_construction(nfa_start, nfa_accept, nfa_trans)
    # 4. Объединение финальных состояний в одно.
    dfa_trans, state_order = merge_final_states(dfa_trans, state_order, dfa_final)
    # 5. Генерация отображения состояний (q-меток)
    q_mapping = generate_q_mapping(state_order)
    # 6. Формирование таблицы в формате CSV.
    result = format_table_with_q(dfa_trans, state_order, terminals, q_mapping)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result + "\n")

if __name__ == '__main__':
    main()