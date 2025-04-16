import sys
import csv
from collections import deque
from graphviz import Digraph  # Для визуализации

def read_csv(filename, delimiter=';'):
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=delimiter)
        return [row for row in reader if any(cell.strip() for cell in row)]

def write_csv(filename, rows, delimiter=';'):
    with open(filename, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=delimiter)
        writer.writerows(rows)

def load_mealy(filename):
    rows = read_csv(filename)
    # Первая строка – заголовок, в ней указаны имена столбцов (состояний)
    state_names = [s.strip() for s in rows[0][1:]]
    input_symbols = []
    transitions = { st: {} for st in state_names }
    raw_rows = []
    for row in rows[1:]:
        inp = row[0].strip()
        input_symbols.append(inp)
        row_transitions = []
        for i, cell in enumerate(row[1:]):
            cell = cell.strip()
            if '/' not in cell:
                print(f"Некорректный формат ячейки: {cell}")
                sys.exit(1)
            target, out = cell.split('/', 1)
            target = target.strip()
            out = out.strip()
            src = state_names[i]
            transitions[src][inp] = (target, out)
            row_transitions.append((src, target, out))
        raw_rows.append((inp, row_transitions))
    start_state = state_names[0]
    return {'states': state_names, 'inputs': input_symbols, 
            'transitions': transitions, 'start': start_state, 'raw': raw_rows}

def load_moore(filename):
    rows = read_csv(filename)
    if len(rows) < 3:
        print("Неверный формат Moore автомата")
        sys.exit(1)
    outputs = [s.strip() for s in rows[0][1:]]
    state_names = [s.strip() for s in rows[1][1:]]
    moore_states = []
    for st, out in zip(state_names, outputs):
        moore_states.append({'name': st, 'output': out})
    input_symbols = []
    transitions = { st: {} for st in state_names }
    for row in rows[2:]:
        inp = row[0].strip()
        input_symbols.append(inp)
        for i, cell in enumerate(row[1:]):
            target = cell.strip()
            transitions[state_names[i]][inp] = target
    start_state = state_names[0]
    return {'states': moore_states, 'inputs': input_symbols, 'transitions': transitions, 'start': start_state}

def remove_unreachable_automaton(states, inputs, transitions, start):
    reachable = set()
    queue = deque([start])
    while queue:
        s = queue.popleft()
        if s in reachable:
            continue
        reachable.add(s)
        for a in inputs:
            if a in transitions[s]:
                nxt = transitions[s][a]
                if nxt not in reachable:
                    queue.append(nxt)
    new_states = [s for s in states if s in reachable]
    new_transitions = { s: transitions[s] for s in reachable }
    return new_states, new_transitions

# Функция для извлечения числовой части из выхода (если нужно для сортировки)
def output_key(o):
    try:
        return int(o)
    except ValueError:
        return int(o[1:])

# Преобразование Mealy -> Moore с сохранением порядка появления выходов
def convert_mealy_to_moore(mealy):
    mealy_trans = mealy['transitions']
    inputs = mealy['inputs']
    state_names = mealy['states']  # список имён состояний Мили
    raw_rows = mealy['raw']

    # Для каждого состояния Мили накапливаем список выходов (с повторениями) по переходам,
    # в которых это состояние является целью, с сохранением порядка первого появления.
    incoming = { s: [] for s in state_names }
    for inp, transitions_list in raw_rows:
        for src, target, out in transitions_list:
            if out not in incoming[target]:
                incoming[target].append(out)

    # Если у стартового состояния отсутствуют входящие переходы – берём выход из его первого перехода
    start = mealy['start']
    if not incoming[start]:
        first_inp = inputs[0]
        _, out = mealy_trans[start][first_inp]
        incoming[start].append(out)
    
    # Формируем отображение для состояний автомата Мура.
    moore_mapping = {}
    new_state_counter = 0
    for q in state_names:
        for out in incoming[q]:
            moore_mapping[(q, out)] = f"q{new_state_counter}"
            new_state_counter += 1

    # Определяем стартовое состояние автомата Мура
    start_out = incoming[start][0]
    start_moore = moore_mapping[(start, start_out)]
    
    # Формируем таблицу переходов для автомата Мура.
    moore_transitions = { moore_mapping[key]: {} for key in moore_mapping }
    for (q, out), m_state in list(moore_mapping.items()):
        for a in inputs:
            if a not in mealy_trans[q]:
                continue
            r, y = mealy_trans[q][a]
            if (r, y) not in moore_mapping:
                moore_mapping[(r, y)] = f"q{new_state_counter}"
                new_state_counter += 1
                moore_transitions[moore_mapping[(r, y)]] = {}
            moore_transitions[m_state][a] = moore_mapping[(r, y)]
    
    # Собираем список состояний для экспорта.
    sorted_states = []
    for q in state_names:
        for out in incoming[q]:
            sorted_states.append( ((q, out), moore_mapping[(q, out)]) )
    moore_states = [{'name': m, 'output': o} for ((q, o), m) in sorted_states]
    
    # Удаляем недостижимые состояния.
    state_names_moore = [s['name'] for s in moore_states]
    reachable, new_moore_transitions = remove_unreachable_automaton(
        states=state_names_moore,
        inputs=inputs,
        transitions=moore_transitions,
        start=start_moore
    )
    moore_states = [s for s in moore_states if s['name'] in reachable]
    moore_transitions = new_moore_transitions

    return {'states': moore_states, 'inputs': inputs, 'transitions': moore_transitions, 'start': start_moore}

# Преобразование Moore -> Mealy
def convert_moore_to_mealy(moore):
    inputs = moore['inputs']
    moore_states = moore['states']
    output_by_state = {st['name']: st['output'] for st in moore_states}
    moore_trans = moore['transitions']
    mealy_states = [st['name'] for st in moore_states]
    mealy_transitions = {st: {} for st in mealy_states}
    
    for st in mealy_states:
        for a in inputs:
            if a not in moore_trans[st]:
                continue
            target = moore_trans[st][a]
            out = output_by_state[target]
            mealy_transitions[st][a] = (target, out)
    
    transitions_without_output = {
        state: {a: trans_tuple[0] for a, trans_tuple in trans.items()}
        for state, trans in mealy_transitions.items()
    }
    
    reachable, _ = remove_unreachable_automaton(
        states=mealy_states,
        inputs=inputs,
        transitions=transitions_without_output,
        start=moore['start']
    )
    
    filtered_transitions = {
        state: {
            a: mealy_transitions[state][a]
            for a in inputs if a in mealy_transitions[state]
        }
        for state in reachable
    }
    
    mealy_states = reachable
    return {
        'states': mealy_states, 
        'inputs': inputs, 
        'transitions': filtered_transitions, 
        'start': moore['start']
    }

def export_moore(moore):
    states = moore['states']
    inputs = moore['inputs']
    transitions = moore['transitions']
    state_names = [st['name'] for st in states]
    header1 = [''] + [st['output'] for st in states]
    header2 = [''] + state_names
    rows = [header1, header2]
    for a in inputs:
        row = [a]
        for st in state_names:
            row.append(transitions[st].get(a, ""))
        rows.append(row)
    return rows

def export_mealy(mealy):
    states = mealy['states']
    inputs = mealy['inputs']
    transitions = mealy['transitions']
    header = [''] + states
    rows = [header]
    for a in inputs:
        row = [a]
        for st in states:
            if a in transitions[st]:
                target, out = transitions[st][a]
                cell = f"{target}/{out}"
            else:
                cell = ""
            row.append(cell)
        rows.append(row)
    return rows

# Функции визуализации автоматов с использованием Graphviz

def visualize_mealy(mealy, filename):
    """Визуализация Mealy автомата.
       Узлы обозначаются именами состояний,
       а рёбра подписаны в формате 'input/output'."""
    dot = Digraph(comment='Mealy Automaton')
    states = mealy['states']
    inputs = mealy['inputs']
    transitions = mealy['transitions']
    start = mealy['start']
    for st in states:
        label = st
        if st == start:
            label += "\n(start)"
            dot.node(st, label=label, color='green')
        else:
            dot.node(st, label=label)
    for st in states:
        if st not in transitions:
            continue
        for a, (target, out) in transitions[st].items():
            dot.edge(st, target, label=f"{a}/{out}")
    dot.render(filename, view=False, format='png')
    print(f"Визуализация Mealy автомата сохранена в {filename}.png")

def visualize_moore(moore, filename):
    """Визуализация Moore автомата.
       Узлы подписаны именем состояния и выходом,
       а рёбра подписаны входными символами."""
    dot = Digraph(comment='Moore Automaton')
    moore_states = moore['states']
    inputs = moore['inputs']
    transitions = moore['transitions']
    start = moore['start']
    outputs = { st['name']: st['output'] for st in moore_states }
    for st in outputs:
        label = f"{st}\nOutput: {outputs[st]}"
        if st == start:
            label += "\n(start)"
            dot.node(st, label=label, color='green')
        else:
            dot.node(st, label=label)
    for st, trans in transitions.items():
        for a, target in trans.items():
            dot.edge(st, target, label=a)
    dot.render(filename, view=False, format='png')
    print(f"Визуализация Moore автомата сохранена в {filename}.png")

def main():
    if len(sys.argv) != 4:
        print("Использование:")
        print("  program mealy-to-moore mealy.csv moore.csv")
        print("  program moore-to-mealy moore.csv mealy.csv")
        sys.exit(1)
    mode = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3]
    
    if mode == "mealy-to-moore":
        # Загрузка исходного Mealy автомата
        mealy = load_mealy(input_file)
        # Визуализация исходного Mealy автомата
        visualize_mealy(mealy, "mealy_original")
        # Преобразование в Moore автомат
        moore = convert_mealy_to_moore(mealy)
        # Визуализация полученного Moore автомата
        visualize_moore(moore, "moore_converted")
        csv_rows = export_moore(moore)
    elif mode == "moore-to-mealy":
        # Загрузка исходного Moore автомата
        moore = load_moore(input_file)
        # Визуализация исходного Moore автомата
        visualize_moore(moore, "moore_original")
        # Преобразование в Mealy автомат
        mealy = convert_moore_to_mealy(moore)
        # Визуализация полученного Mealy автомата
        visualize_mealy(mealy, "mealy_converted")
        csv_rows = export_mealy(mealy)
    else:
        print("Неверный режим. Используйте mealy-to-moore или moore-to-mealy")
        sys.exit(1)
        
    write_csv(output_file, csv_rows)
    print(f"Преобразование завершено. Результат записан в {output_file}")

if __name__ == '__main__':
    main()
