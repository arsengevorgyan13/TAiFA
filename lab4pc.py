import sys
import csv
from collections import defaultdict, deque

EPSILON = "ε"

def read_nfa(filename):
    with open(filename, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        rows = [row for row in reader if any(cell.strip() for cell in row)]

    state_flags = rows[0][1:]
    raw_states = rows[1]
    terminals = [row[0] for row in rows[2:]]

    nfa_states = [s.strip() for s in raw_states[1:]]
    final_states = {nfa_states[i] for i, flag in enumerate(state_flags) if flag.strip().upper() == "F"}

    transitions = {state: defaultdict(set) for state in nfa_states}
    for row in rows[2:]:
        symbol = row[0].strip()
        for i, cell in enumerate(row[1:]):
            state = nfa_states[i]
            for target in cell.split(","):
                target = target.strip()
                if target:
                    transitions[state][symbol].add(target)

    start_state = nfa_states[0]
    return nfa_states, terminals, transitions, start_state, final_states

def epsilon_closure(state, transitions):
    stack = [state]
    closure = {state}
    while stack:
        current = stack.pop()
        for neighbor in transitions[current].get(EPSILON, []):
            if neighbor not in closure:
                closure.add(neighbor)
                stack.append(neighbor)
    return closure

def epsilon_closure_set(states, transitions):
    closure = set()
    for state in states:
        closure |= epsilon_closure(state, transitions)
    return closure

def nfa_to_dfa(nfa_states, terminals, transitions, start_state, final_states):
    terminals = [t for t in terminals if t != EPSILON]
    dfa_states = []
    dfa_transitions = {}
    dfa_final = set()
    state_map = {}
    reverse_map = {}
    
    initial_closure = frozenset(epsilon_closure(start_state, transitions))
    queue = deque([initial_closure])
    state_map[initial_closure] = "S0"
    reverse_map["S0"] = initial_closure
    dfa_states.append(initial_closure)
    counter = 1

    while queue:
        current = queue.popleft()
        current_label = state_map[current]
        dfa_transitions[current_label] = {}

        for symbol in terminals:
            target = set()
            for state in current:
                target |= transitions[state].get(symbol, set())
            target_closure = epsilon_closure_set(target, transitions)
            if not target_closure:
                continue
            frozen_target = frozenset(target_closure)
            if frozen_target not in state_map:
                state_name = f"S{counter}"
                counter += 1
                state_map[frozen_target] = state_name
                reverse_map[state_name] = frozen_target
                dfa_states.append(frozen_target)
                queue.append(frozen_target)
            dfa_transitions[current_label][symbol] = state_map[frozen_target]

    for fs, label in reverse_map.items():
        if label & final_states:
            dfa_final.add(fs)

    return state_map, dfa_transitions, terminals, state_map[initial_closure], dfa_final

def write_dfa(filename, state_map, dfa_transitions, terminals, start_label, final_state_labels):
    dfa_states = sorted(dfa_transitions.keys(), key=lambda x: int(x[1:]))

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        header = [""] + [("F" if s in final_state_labels else "") for s in dfa_states]
        writer.writerow(header)
        writer.writerow([""] + dfa_states)
        for term in terminals:
            row = [term]
            for s in dfa_states:
                row.append(dfa_transitions.get(s, {}).get(term, ""))
            writer.writerow(row)

def main():
    if len(sys.argv) != 3:
        print("Usage: python lab4.py NFAin.csv DFAout.csv")
        sys.exit(1)

    nfa_file = sys.argv[1]
    dfa_file = sys.argv[2]

    nfa_states, terminals, transitions, start_state, final_states = read_nfa(nfa_file)
    state_map, dfa_transitions, used_terminals, start_label, final_state_labels = nfa_to_dfa(
        nfa_states, terminals, transitions, start_state, final_states
    )
    write_dfa(dfa_file, state_map, dfa_transitions, used_terminals, start_label, final_state_labels)

if __name__ == "__main__":
    main()