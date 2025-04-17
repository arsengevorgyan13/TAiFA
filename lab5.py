import sys
from collections import defaultdict, deque
# from graphviz import Digraph

def preprocess_regex(regex):
    return regex.replace("()", "@")

def add_concat(regex):
    new_regex = ""
    symbols = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@абвгдеёжзийклмнопрстуфхцчшщьыъэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЬЫЪЭЮЯ")
    prev = None
    for char in regex:
        if prev:
            if (prev in symbols or prev in ")*+") and (char in symbols or char == "("):
                new_regex += "."
        new_regex += char
        prev = char
    return new_regex

def to_postfix(regex):
    precedence = {'*': 3, '+': 3, '.': 2, '|': 1}
    output = []
    stack = []
    for char in regex:
        if char.isalnum() or char == '@':
            output.append(char)
        elif char == "(":
            stack.append(char)
        elif char == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            stack.pop()
        else:
            while stack and stack[-1] != "(" and precedence.get(stack[-1], 0) >= precedence.get(char, 0):
                output.append(stack.pop())
            stack.append(char)
    while stack:
        output.append(stack.pop())
    return "".join(output)

class State:
    _id_counter = 0
    def __init__(self):
        self.edges = defaultdict(list)
        self.name = f"S{State._id_counter}"
        State._id_counter += 1

class NFA:
    def __init__(self, start, end):
        self.start = start
        self.end = end

def build_nfa(postfix):
    State._id_counter = 0
    stack = []
    for char in postfix:
        if char.isalnum() or char == '@':
            s0 = State()
            s1 = State()
            s0.edges[char].append(s1)
            stack.append(NFA(s0, s1))
        elif char == '.':
            nfa2 = stack.pop()
            nfa1 = stack.pop()
            nfa1.end.edges['@'].append(nfa2.start)
            stack.append(NFA(nfa1.start, nfa2.end))
        elif char == '|':
            nfa2 = stack.pop()
            nfa1 = stack.pop()
            s0 = State()
            s1 = State()
            s0.edges['@'].extend([nfa1.start, nfa2.start])
            nfa1.end.edges['@'].append(s1)
            nfa2.end.edges['@'].append(s1)
            stack.append(NFA(s0, s1))
        elif char == '*':
            nfa1 = stack.pop()
            s0 = State()
            s1 = State()
            s0.edges['@'].extend([nfa1.start, s1])
            nfa1.end.edges['@'].extend([nfa1.start, s1])
            stack.append(NFA(s0, s1))
        elif char == '+':
            nfa1 = stack.pop()
            s0 = nfa1.start
            s1 = State()
            nfa1.end.edges['@'].extend([nfa1.start, s1])
            stack.append(NFA(s0, s1))
        else:
            raise ValueError(f"Неизвестный символ {char}")
    if len(stack) != 1:
        raise ValueError("Ошибка построения NFA")
    return stack[0]

def collect_all_states(start_state):
    visited = set()
    stack = [start_state]
    while stack:
        state = stack.pop()
        if state in visited:
            continue
        visited.add(state)
        for targets in state.edges.values():
            stack.extend(targets)
    return visited

def collect_symbols(states):
    symbols = set()
    for state in states:
        for sym in state.edges:
            symbols.add(sym)
    return sorted(s for s in symbols if s != '@')

def save_nfa_csv(nfa, output_file):
    all_states = sorted(collect_all_states(nfa.start), key=lambda s: int(s.name[1:]))
    alphabet = collect_symbols(all_states)
    state_names = [s.name for s in all_states]
    final_flags = ["F" if s == nfa.end else "" for s in all_states]

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(";;" + ";".join(final_flags) + "\n")
        f.write(";" + ";".join(state_names) + "\n")
        for symbol in alphabet + ['ε']:
            row = [symbol]
            for state in all_states:
                if symbol == 'ε':
                    targets = state.edges.get('@', [])
                else:
                    targets = state.edges.get(symbol, [])
                row.append(",".join(sorted(t.name for t in targets)))
            f.write(";".join(row) + "\n")

# def visualize_nfa_graph(nfa, filename):
#     dot = Digraph(comment="NFA")
#     dot.attr(rankdir="LR")

#     all_states = collect_all_states(nfa.start)
#     for state in all_states:
#         shape = "doublecircle" if state == nfa.end else "circle"
#         dot.node(state.name, shape=shape)

#     dot.node("", shape="none")
#     dot.edge("", nfa.start.name)

#     for state in all_states:
#         for symbol, targets in state.edges.items():
#             label = "ε" if symbol == "@" else symbol
#             for target in targets:
#                 dot.edge(state.name, target.name, label=label)

#     output_path = filename.rsplit(".", 1)[0]
#     dot.render(output_path, format="png", cleanup=True)
#     print(f"Граф NFA сохранён в {output_path}")

def main():
    if len(sys.argv) != 3:
        print("Использование: ./regexToNFA output.csv \"регулярное_выражение\"")
        sys.exit(1)

    output_file, regex = sys.argv[1], sys.argv[2]
    regex = preprocess_regex(regex)
    print(f"Исходное выражение: {regex}")

    regex = add_concat(regex)
    postfix = to_postfix(regex)
    print(f"Постфикс: {postfix}")

    nfa = build_nfa(postfix)
    save_nfa_csv(nfa, output_file)
    # visualize_nfa_graph(nfa, output_file)

if __name__ == "__main__":
    main()
