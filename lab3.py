import sys
import re

def combine_lines(lines):
    """
    Объединяет строки, если правило продолжается на следующей строке.
    Строка, начинающаяся с пробельных символов, считается продолжением предыдущей.
    """
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
    nonterminals_order = []
    terminals = set()
    final_used = False
    grammar_type = None

    # Определяем тип грамматики (левосторонняя или правосторонняя)
    for line in lines:
        line = line.strip()
        if not line or "->" not in line:
            continue
        _, right = line.split("->", 1)
        alternatives = right.split("|")
        for alt in alternatives:
            alt = alt.strip()
            if alt:
                if alt.startswith("<"):
                    grammar_type = "left"
                else:
                    grammar_type = "right"
                break
        if grammar_type is not None:
            break
    if grammar_type is None:
        grammar_type = "right"

    def add_transition(src, term, dst):
        nonlocal final_used
        if src not in transitions:
            transitions[src] = {}
        if term not in transitions[src]:
            transitions[src][term] = []
        if dst not in transitions[src][term]:
            transitions[src][term].append(dst)
        terminals.add(term)
        if dst == "H":
            final_used = True

    # Разбираем правило и заполняем переходы
    for line in lines:
        line = line.strip()
        if not line or "->" not in line:
            continue
        left, right = line.split("->", 1)
        left_state = re.sub(r"[<>]", "", left).strip()
        if left_state not in nonterminals_order:
            nonterminals_order.append(left_state)
        alternatives = right.split("|")
        for alt in alternatives:
            alt = alt.strip()
            if not alt:
                continue
            if grammar_type == "right":
                if alt.startswith("<"):
                    m = re.match(r"<([^>]+)>", alt)
                    if not m:
                        continue
                    nonterm = m.group(1)
                    term = alt[m.end():].strip()
                    if not term:
                        continue
                    term = term[0]
                    dst = nonterm
                else:
                    term = alt[0]
                    m = re.search(r"<([^>]+)>", alt)
                    if m:
                        dst = m.group(1)
                    else:
                        dst = "H"
                add_transition(left_state, term, dst)
            else:
                if alt.startswith("<"):
                    m = re.match(r"<([^>]+)>", alt)
                    if not m:
                        continue
                    nonterm = m.group(1)
                    term = alt[m.end():].strip()
                    if not term:
                        continue
                    term = term[0]
                    add_transition(nonterm, term, left_state)
                else:
                    term = alt[0]
                    add_transition("H", term, left_state)

    # Формирование порядка состояний.
    if grammar_type == "right":
        if final_used and "H" not in nonterminals_order:
            nonterminals_order.append("H")
        states_order = nonterminals_order
    else:
        if "H" not in nonterminals_order:
            nonterminals_order = ["H"] + nonterminals_order
        else:
            nonterminals_order.remove("H")
            nonterminals_order = ["H"] + nonterminals_order
        states_order = [nonterminals_order[0]] + list(reversed(nonterminals_order[1:]))

    sorted_terminals = sorted(terminals, key=lambda x: (not x.isdigit(), x))
    return transitions, states_order, sorted_terminals, grammar_type

def format_table(transitions, states, terminals, state_map):
    def cell_str(cell_set):
        if not cell_set:
            return "-"
        ordered = [s for s in states if s in cell_set]
        mapped = [state_map[s] for s in ordered]
        return ",".join(mapped)

    header_states = ";" + ";".join(state_map[s] for s in states)
    final_row = ";" * len(states) + ";F"
    rows = [final_row, header_states]

    for term in terminals:
        row = term
        for s in states:
            if s in transitions and term in transitions[s]:
                cell = cell_str(transitions[s][term])
            else:
                cell = "-"
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