#!/usr/bin/env python3
import sys
import csv
import argparse
from graphviz import Digraph

def parse_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    data = [line.split(';') for line in lines]
    # Если во второй строке первая ячейка пустая – это автомат Мура
    if len(data) >= 2 and data[1][0] == "":
        return 'moore', data
    else:
        return 'mealy', data

def parse_mealy(data):
    # data[0] – заголовок; data[1:] – строки с переходами
    header = data[0][1:]
    rows = data[1:]
    row_labels = [row[0] for row in rows]
    # Если в заголовке первой ячейки пусто, то состояния заданы в заголовке (вариант "by_header")
    if data[0][0] == "":
        variant = "by_header"
        states = header[:]         # имена состояний автомата
        input_symbols = row_labels   # входные символы
        # Собираем переходы: для каждого состояния – список переходов для каждого входа
        transitions = { state: [] for state in states }
        for row in rows:
            cells = row[1:]
            for j, cell in enumerate(cells):
                if '/' in cell:
                    dest, out = cell.split('/')
                else:
                    dest, out = cell, ""
                transitions[states[j]].append((dest, out))
    else:
        variant = "by_rows"
        states = row_labels[:]       # имена состояний автомата
        input_symbols = header       # входные символы
        transitions = {}
        for row in rows:
            state = row[0]
            trans = []
            for cell in row[1:]:
                if '/' in cell:
                    dest, out = cell.split('/')
                else:
                    dest, out = cell, ""
                trans.append((dest, out))
            transitions[state] = trans
    return input_symbols, states, transitions, variant

def minimize_mealy(inputs, states, transitions):
    # Начальное разбиение: группировка по вектору выходов для каждого входа
    P = {}
    for s in states:
        sig = tuple(transitions[s][i][1] for i in range(len(inputs)))
        P.setdefault(sig, []).append(s)
    P = list(P.values())
    changed = True
    while changed:
        changed = False
        new_P = []
        for group in P:
            buckets = {}
            for s in group:
                dest_partitions = []
                for i, (dest, out) in enumerate(transitions[s]):
                    for idx, g in enumerate(P):
                        if dest in g:
                            dest_partitions.append(idx)
                            break
                sig = (tuple(transitions[s][i][1] for i in range(len(inputs))), tuple(dest_partitions))
                buckets.setdefault(sig, []).append(s)
            if len(buckets) > 1:
                changed = True
            for bucket in buckets.values():
                new_P.append(bucket)
        P = new_P
    # Создаем отображение: старое имя состояния -> новое имя (s0, s1, …)
    mapping = {}
    new_states = []
    for i, group in enumerate(P):
        new_name = f"s{i}"
        new_states.append(new_name)
        for s in group:
            mapping[s] = new_name
    # Формируем таблицу переходов для минимизированного автомата (берем представителя каждого класса)
    new_transitions = {}
    for group in P:
        rep = group[0]
        new_state = mapping[rep]
        new_transitions[new_state] = []
        for (dest, out) in transitions[rep]:
            new_transitions[new_state].append((mapping[dest], out))
    return new_states, new_transitions, mapping, P

# Запись для варианта "by_rows" (когда состояния – в первой колонке)
def write_mealy_by_rows(filename, inputs, states, transitions):
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([''] + inputs)
        for s in states:
            row = [s]
            for (dest, out) in transitions[s]:
                row.append(f"{dest}/{out}")
            writer.writerow(row)

# Запись для варианта "by_header" (когда состояния заданы в заголовке, а строки – входные символы)
def write_mealy_by_header(filename, inputs, states, transitions):
    # transitions – словарь: для каждого состояния (из исходного автомата) список переходов по входам
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([''] + states)
        for i, inp in enumerate(inputs):
            row = [inp]
            for s in states:
                dest, out = transitions[s][i]
                row.append(f"{dest}/{out}")
            writer.writerow(row)

def parse_moore(data):
    # Первая строка – выходы для состояний, вторая – имена состояний
    header_outputs = data[0][1:]
    header_states = data[1][1:]
    Q = header_states[:]  # исходные состояния
    state_output = { state: out for state, out in zip(Q, header_outputs) }
    inputs = []
    transitions = {}  # для каждого входа – список переходов (по позициям Q)
    for row in data[2:]:
        inp = row[0]
        inputs.append(inp)
        transitions[inp] = row[1:]
    return inputs, Q, transitions, state_output

def build_moore_transition_function(inputs, Q, transitions):
    delta = { state: [] for state in Q }
    for inp in inputs:
        col = transitions[inp]
        for i, state in enumerate(Q):
            delta[state].append(col[i])
    return delta

def minimize_moore(Q, state_output, delta, inputs):
    P = {}
    for s in Q:
        out = state_output[s]
        P.setdefault(out, []).append(s)
    P = list(P.values())
    changed = True
    while changed:
        changed = False
        new_P = []
        for group in P:
            buckets = {}
            for s in group:
                dest_partitions = []
                for a in range(len(inputs)):
                    dest = delta[s][a]
                    for idx, g in enumerate(P):
                        if dest in g:
                            dest_partitions.append(idx)
                            break
                sig = (state_output[s], tuple(dest_partitions))
                buckets.setdefault(sig, []).append(s)
            if len(buckets) > 1:
                changed = True
            for bucket in buckets.values():
                new_P.append(bucket)
        P = new_P
    mapping = {}
    new_states = []
    for i, group in enumerate(P):
        new_name = f"s{i}"
        new_states.append(new_name)
        for s in group:
            mapping[s] = new_name
    new_delta = {}
    for group in P:
        rep = group[0]
        new_state = mapping[rep]
        new_delta[new_state] = []
        for a in range(len(inputs)):
            new_delta[new_state].append(mapping[delta[rep][a]])
    new_state_output = { mapping[s]: state_output[s] for s in Q if s in mapping }
    return new_states, new_state_output, new_delta, mapping, P

def write_moore(filename, inputs, new_states, new_state_output, new_delta):
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        header_out = [''] + [new_state_output[s] for s in new_states]
        header_states = [''] + new_states
        writer.writerow(header_out)
        writer.writerow(header_states)
        for i, inp in enumerate(inputs):
            row = [inp]
            for s in new_states:
                row.append(new_delta[s][i])
            writer.writerow(row)

def main():
    # Определяем аргументы командной строки:
    #   argv[1] – тип автомата: mealy или moore
    #   argv[2] – имя входного файла CSV
    #   argv[3] – имя выходного файла CSV (результат минимизации)
    parser = argparse.ArgumentParser(description="Минимизация автомата Мили или Мура")
    parser.add_argument("autom_type", choices=["mealy", "moore"], help="Тип автомата: mealy или moore")
    parser.add_argument("input_file", help="Имя входного CSV файла")
    parser.add_argument("output_file", help="Имя выходного CSV файла с минимизированным автоматом")
    args = parser.parse_args()

    # Для совместимости с ранее определённой логикой определяем тип автомата по файлу, если необходимо.
    file_type, data = parse_file(args.input_file)
    if args.autom_type != file_type:
        print(f"Предупреждение: аргумент autom_type = {args.autom_type}, а файл определён как {file_type}.")
    if args.autom_type == 'mealy':
        inputs, states, transitions, variant = parse_mealy(data)
        new_states, new_transitions, mapping, parts = minimize_mealy(inputs, states, transitions)
        # Записываем результат минимизации с сохранением исходного формата
        if variant == "by_rows":
            write_mealy_by_rows(args.output_file, inputs, new_states, new_transitions)
        else:
            write_mealy_by_header(args.output_file, inputs, new_states, new_transitions)
        print("Минимизация автомата Мили завершена.")
    else:  # moore
        inputs, Q, transitions, state_output = parse_moore(data)
        delta = build_moore_transition_function(inputs, Q, transitions)
        new_states, new_state_output, new_delta, mapping, parts = minimize_moore(Q, state_output, delta, inputs)
        write_moore(args.output_file, inputs, new_states, new_state_output, new_delta)
        print("Минимизация автомата Мура завершена.")

if __name__ == '__main__':
    main()