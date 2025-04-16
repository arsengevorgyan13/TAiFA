import sys
import re

def combine_lines(lines):
    combined = []
    buffer = ""
    for line in lines:
        stripped = line.rstrip("\n")
        if not stripped:
            continue
        if re.match(r'^\s+', stripped):
            buffer += " " + stripped.lstrip()
        else:
            if buffer:
                combined.append(buffer)
            buffer = stripped
    if buffer:
        combined.append(buffer)
    return combined

def parse_grammar(lines):
    transitions = {}
    nonterminals = set()
    terminals = set()
    start_symbol = None
    grammar_type = None

    # Сбор всех нетерминалов и определение типа грамматики
    for line in lines:
        line = line.strip()
        if not line or "->" not in line:
            continue
        left, right = line.split("->", 1)
        left = re.sub(r"[<>]", "", left).strip()
        nonterminals.add(left)
        
        # Анализ типа грамматики по первой альтернативе
        if grammar_type is None:
            first_alt = right.split("|")[0].strip()
            if re.search(r"<[^>]+>\s*$", first_alt):
                grammar_type = "right"
            else:
                grammar_type = "left"

    # Добавление всех нетерминалов из правых частей
    for line in lines:
        line = line.strip()
        if not line or "->" not in line:
            continue
        _, right = line.split("->", 1)
        for alt in right.split("|"):
            alt = alt.strip()
            for nt in re.findall(r"<([^>]+)>", alt):
                nonterminals.add(nt)

    # Порядок состояний
    nonterminals = sorted(nonterminals)
    if grammar_type == "right":
        states_order = nonterminals
    else:
        states_order = list(reversed(nonterminals))

    # Парсинг переходов
    for line in lines:
        line = line.strip()
        if not line or "->" not in line:
            continue
        left, right = line.split("->", 1)
        left = re.sub(r"[<>]", "", left).strip()
        
        for alt in right.split("|"):
            alt = alt.strip()
            if not alt:
                continue

            parts = re.split(r"(<[^>]+>)", alt)
            parts = [p.strip() for p in parts if p.strip()]

            if grammar_type == "right":
                term = parts[0][0]
                dest = parts[1][1:-1] if len(parts) > 1 else None
            else:
                term = parts[-1][0]
                dest = parts[0][1:-1] if len(parts) > 1 else None

            if dest is None:
                continue  # Пропускаем терминальные переходы без состояния

            if left not in transitions:
                transitions[left] = {}
            if term not in transitions[left]:
                transitions[left][term] = set()
            transitions[left][term].add(dest)
            terminals.add(term)

    terminals = sorted(terminals)
    return transitions, states_order, terminals, grammar_type

def format_table(transitions, states, terminals, state_map):
    def cell_str(cell_set):
        if not cell_set:
            return ""
        ordered = [s for s in states if s in cell_set]
        mapped = [state_map[s] for s in ordered]
        return ",".join(mapped)

    header_states = ";" + ";".join(state_map[s] for s in states)
    final_row = ";" * len(states) + "F"
    rows = [final_row, header_states]

    for term in terminals:
        row = term
        for s in states:
            if s in transitions and term in transitions[s]:
                cell = cell_str(transitions[s][term])
            else:
                cell = ""
            row += ";" + cell
        rows.append(row)
    return "\n".join(rows)

def main():
    if len(sys.argv) != 3:
        print("Usage: ./lab3 <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    with open(input_file, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    lines = combine_lines(raw_lines)
    transitions, states, terminals, grammar_type = parse_grammar(lines)
    # Создаём отображение нетерминалов в состояния: порядок состояний задаётся states
    state_map = {state: f"q{i}" for i, state in enumerate(states)}
    result = format_table(transitions, states, terminals, state_map)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result + "\n")

if __name__ == '__main__':
    main()