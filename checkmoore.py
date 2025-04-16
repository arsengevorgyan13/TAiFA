#!/usr/bin/env python3
import csv
import sys
from collections import deque, defaultdict

def read_moore_automaton(file_path):
    """
    Считывает автомат Мура из CSV-файла.
    
    Формат CSV:
      - Первая строка: столбцы с выходными сигналами для состояний (например, y2;y4;y5;…).
      - Вторая строка: имена состояний (например, q0;q1;q2;…).
      - Последующие строки: переходы для каждого входного символа;
        первая ячейка строки – имя входного символа, остальные ячейки – целевые состояния (может быть несколько, разделённых запятой).
    
    Возвращает словарь с ключами:
      "states"      - список состояний (как они заданы во второй строке)
      "outputs"     - словарь: состояние -> выход (из первой строки)
      "transitions" - словарь: состояние -> { input_symbol -> set(целевых состояний) }
      "inputs"      - множество входных символов
    """
    with open(file_path, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f, delimiter=";"))
    
    # Считываем выходы и состояния
    outputs = [cell.strip() for cell in reader[0][1:]]  # пропускаем первый пустой элемент
    states  = [cell.strip() for cell in reader[1][1:]]
    
    # Формируем словарь выходов: state -> output
    state_outputs = {state: output for state, output in zip(states, outputs)}
    
    # Инициализируем таблицу переходов для каждого состояния
    transitions = {state: defaultdict(set) for state in states}
    input_symbols = set()
    
    # Обрабатываем оставшиеся строки – переходы
    # Каждая такая строка: первый элемент – входной символ, далее – целевые состояния для каждого состояния в порядке states.
    for row in reader[2:]:
        if not row or len(row) < 2:
            continue
        symbol = row[0].strip()
        input_symbols.add(symbol)
        for state, cell in zip(states, row[1:]):
            cell = cell.strip()
            if cell:
                # Если в ячейке несколько состояний, они разделены запятой
                targets = [t.strip() for t in cell.split(",") if t.strip()]
                transitions[state][symbol].update(targets)
    
    return {
        "states": states,
        "outputs": state_outputs,
        "transitions": transitions,
        "inputs": input_symbols
    }

def are_moore_automata_equivalent(auto1, auto2):
    """
    Проверяет изоморфизм (эквивалентность) двух автоматов Мура.
    
    Для автомата Мура эквивалентность означает, что существует взаимно однозначное отображение
    между состояниями двух автоматов (переименование состояний), при котором:
      - Выходные сигналы для соответствующих состояний совпадают.
      - Переходы по каждому входному символу согласованы.
      
    Алгоритм запускается от начальных состояний (первое состояние из списка) и по BFS проверяет все достижимые состояния.
    Если найдено расхождение — возвращается False.
    """
    # Функция для сравнения выходов двух состояний (их «ярлыки» y)
    def outputs_equal(s1, s2):
        return auto1["outputs"][s1] == auto2["outputs"][s2]
    
    # Начальные состояния – первые в списке
    s1_init = auto1["states"][0]
    s2_init = auto2["states"][0]
    
    # Если выход начальных состояний различается, автоматы не эквивалентны.
    if not outputs_equal(s1_init, s2_init):
        return False

    # Будем накапливать отображение из состояний auto1 в состояния auto2
    mapping = {s1_init: s2_init}
    # Используем очередь для обхода в ширину
    queue = deque([(s1_init, s2_init)])
    
    # Объединённое множество входных символов обоих автоматов
    all_inputs = auto1["inputs"] | auto2["inputs"]
    
    while queue:
        state1, state2 = queue.popleft()
        
        # Для каждого входного символа проверяем переходы
        for symbol in all_inputs:
            # Получаем целевые состояния для state1 и state2 по символу symbol
            targets1 = auto1["transitions"].get(state1, {}).get(symbol, set())
            targets2 = auto2["transitions"].get(state2, {}).get(symbol, set())
            
            # Если количество переходов различается — автоматы не изоморфны.
            if len(targets1) != len(targets2):
                return False
            
            # Для детерминированных автоматов набор должен быть либо пустым, либо содержать единственный элемент.
            # Но если автомата недетерминированы, сравнение проводится для каждого соответствия.
            # Здесь мы рассматриваем случай, когда из каждого состояния по каждому входу получаем
            # упорядоченные множества (сортировка по имени помогает установить соответствие).
            sorted_t1 = sorted(targets1)
            sorted_t2 = sorted(targets2)
            
            # Если соответствие уже установлено, проверяем его корректность.
            for tgt1, tgt2 in zip(sorted_t1, sorted_t2):
                if tgt1 in mapping:
                    # Если отображение уже есть, выходы должны совпадать
                    if mapping[tgt1] != tgt2 or not outputs_equal(tgt1, tgt2):
                        return False
                else:
                    # Если отображения ещё нет, устанавливаем его и добавляем в очередь
                    mapping[tgt1] = tgt2
                    if not outputs_equal(tgt1, tgt2):
                        return False
                    queue.append((tgt1, tgt2))
    return True

def main():
    if len(sys.argv) != 3:
        print("Usage: python check_moore_equivalence.py <automaton1.csv> <automaton2.csv>")
        sys.exit(1)
    
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    
    auto1 = read_moore_automaton(file1)
    auto2 = read_moore_automaton(file2)
    
    if are_moore_automata_equivalent(auto1, auto2):
        print("Автоматы Мура эквивалентны.")
    else:
        print("Автоматы Мура НЕ эквивалентны.")

if __name__ == "__main__":
    main()
