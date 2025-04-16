import sys
import csv
from collections import deque

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
    # Список входных символов (порядок строк)
    input_symbols = []
    # Структура переходов: transitions[state][input] = (target, output)
    transitions = { st: {} for st in state_names }
    # Сохраняем «сырые» строки для дальнейшего построения Moore-отображения:
    # список: (inp, [ (src, target, out) для каждого столбца ])
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

# Чтение автомата Moore из CSV-файла
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

# Удаление недостижимых состояний
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

# Вспомогательная функция для сравнения выходов.
# Если выход можно преобразовать целиком в число, то используется оно;
# иначе, предполагаем, что выход имеет вид <буква><число> и извлекаем числовую часть.
def output_key(o):
    try:
        return int(o)
    except ValueError:
        return int(o[1:])

# Преобразование Mealy -> Moore
def convert_mealy_to_moore(mealy):
    mealy_trans = mealy['transitions']
    inputs = mealy['inputs']
    state_names = mealy['states']  # список имен (например, F1, F2, F3) в порядке заголовка
    raw_rows = mealy['raw']

    # Для каждого состояния Mealy вычисляем множество "incoming" выходов,
    # то есть всех выходов, с которыми это состояние появляется в качестве целевого.
    incoming = { s: set() for s in state_names }
    for src in state_names:
        for a in inputs:
            if a in mealy_trans[src]:
                target, out = mealy_trans[src][a]
                incoming[target].add(out)
    # Если у стартового состояния нет входящих переходов, берём выход из его первого перехода
    start = mealy['start']
    if not incoming[start]:
        first_inp = inputs[0]
        _, out = mealy_trans[start][first_inp]
        incoming[start].add(out)
    
    # Формируем отображение для Moore-состояний.
    # Для каждого состояния q (в порядке появления в заголовке) создаём для каждого
    # значения из incoming[q] копию, упорядочив их по возрастанию числовой части.
    moore_mapping = {}
    new_state_counter = 0
    for q in state_names:
        for out in sorted(incoming[q], key=output_key):
            moore_mapping[(q, out)] = f"R{new_state_counter}"
            new_state_counter += 1

    # Определяем стартовое Moore-состояние: для стартового Mealy берём ту копию,
    # которая соответствует минимальному выходу (по числовой части).
    start_out = sorted(incoming[start], key=output_key)[0]
    start_moore = moore_mapping[(start, start_out)]
    
    # Формируем таблицу переходов для автомата Moore.
    # Для каждого Moore-состояния (q, x) и входа a берём переход Mealy из q: (r, y)
    # и переходим в Moore-состояние, соответствующее (r, y).
    moore_transitions = { moore_mapping[key]: {} for key in moore_mapping }
    for (q, x), m_state in list(moore_mapping.items()):
        for a in inputs:
            if a not in mealy_trans[q]:
                continue
            r, y = mealy_trans[q][a]
            # Предполагаем, что для состояния r уже создана копия с выходом y.
            if (r, y) not in moore_mapping:
                # Если вдруг нет, создадим её.
                moore_mapping[(r, y)] = f"R{new_state_counter}"
                new_state_counter += 1
                moore_transitions[moore_mapping[(r, y)]] = {}
            moore_transitions[m_state][a] = moore_mapping[(r, y)]
    
    # Собираем список состояний для экспорта.
    # Порядок: сначала по порядку появления состояния q из исходного заголовка,
    # затем для одного q по возрастанию числовой части выходного значения.
    sorted_states = sorted(moore_mapping.items(), key=lambda x: (state_names.index(x[0][0]), output_key(x[0][1])))
    moore_states = [{'name': m, 'output': str(output_key(o))} for ((q, o), m) in sorted_states]
    
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

# Вывод автомата Mealy в формате CSV
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
        mealy = load_mealy(input_file)
        moore = convert_mealy_to_moore(mealy)
        csv_rows = export_moore(moore)
    elif mode == "moore-to-mealy":
        moore = load_moore(input_file)
        mealy = convert_moore_to_mealy(moore)
        csv_rows = export_mealy(mealy)
    else:
        print("Неверный режим. Используйте mealy-to-moore или moore-to-mealy")
        sys.exit(1)
    write_csv(output_file, csv_rows)
    print(f"Преобразование завершено. Результат записан в {output_file}")

if __name__ == '__main__':
    main()