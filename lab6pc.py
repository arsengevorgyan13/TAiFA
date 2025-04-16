import sys
import re

# Класс для токена
class Token:
    def __init__(self, type, line, col, lexeme):
        self.type = type
        self.line = line
        self.col = col
        self.lexeme = lexeme

    def __str__(self):
        return f'{self.type} ({self.line}, {self.col}) "{self.lexeme}"'

class Lexer:
    def __init__(self, infile):
        self.infile = open(infile, 'r', encoding='utf-8')
        self.buffer = ""
        self.eof = False
        self.line = 1
        self.col = 1
        self.keywords = {"ARRAY", "BEGIN", "ELSE", "END", "IF", "OF", "OR", "PROGRAM", "PROCEDURE", "THEN", "TYPE", "VAR"}

    def close(self):
        self.infile.close()

    def read_char(self):
        """Читает следующий символ из файла, обновляет позицию и возвращает его."""
        ch = self.infile.read(1)
        if ch == "":
            self.eof = True
            return None
        # Обновляем позицию
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def peek_char(self):
        """Возвращает следующий символ без продвижения указателя."""
        if self.buffer:
            return self.buffer[0]
        self.buffer = self.infile.read(1)
        if self.buffer == "":
            self.eof = True
            return None
        return self.buffer[0]

    def get_char(self):
        """Возвращает символ из буфера, если он там, иначе читает из файла."""
        if self.buffer:
            ch = self.buffer[0]
            self.buffer = self.buffer[1:]
            # Обновляем позицию для символа из буфера
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            return ch
        else:
            return self.read_char()

    def next_token(self):
        if self.eof:
            return None

        # Пропуск пробельных символов
        while True:
            ch = self.peek_char()
            if ch is None:
                return None
            if ch.isspace():
                self.get_char()
                continue
            break

        start_line = self.line
        # Для столбца учитываем, что позиция до считывания текущего символа равна текущей col
        start_col = self.col

        ch = self.peek_char()

        # Обработка блочного комментария { ... }
        if ch == '{':
            lexeme = self.get_char()  # читаем '{'
            closed = False
            while True:
                ch = self.peek_char()
                if ch is None:
                    break
                lexeme += self.get_char()
                if ch == '}':
                    closed = True
                    break
            if not closed:
                return Token("BAD", start_line, start_col, lexeme)
            return Token("BLOCK_COMMENT", start_line, start_col, lexeme)

        # Обработка однострочного комментария: //
        if ch == '/' and self.buffer == "" and self.infile.tell() != 0:
            pos = self.infile.tell()
            self.buffer = ""  # чистим буфер, если вдруг там что-то осталось
        if ch == '/' :
            # Временно получим символ и проверим следующий
            first = self.get_char()  # '/'
            next_ch = self.peek_char()
            if next_ch == '/':
                lexeme = first + self.get_char()  # читаем второй '/'
                # Читаем до конца строки
                while True:
                    ch_line = self.peek_char()
                    if ch_line is None or ch_line == "\n":
                        break
                    lexeme += self.get_char()
                return Token("LINE_COMMENT", start_line, start_col, lexeme)
            else:
                # Если не комментарий, рассматриваем символ '/' как оператор DIVIDE
                return Token("DIVIDE", start_line, start_col, first)

        # Строковый литерал
        if ch == "'":
            lexeme = self.get_char()  # читаем начальную кавычку
            closed = False
            while True:
                ch = self.peek_char()
                if ch is None or ch == "\n":  # однострочный литерал
                    break
                lexeme += self.get_char()
                if ch == "'":
                    closed = True
                    break
            if not closed:
                return Token("BAD", start_line, start_col, lexeme)
            return Token("STRING", start_line, start_col, lexeme)

        # Числовые литералы (целые и вещественные)
        if ch.isdigit() or (ch == '.' and self.peek_next_is_digit()):
            lexeme = ""
            is_float = False

            # Читаем целую часть
            while True:
                ch = self.peek_char()
                if ch is not None and ch.isdigit():
                    lexeme += self.get_char()
                else:
                    break

            # Если символ '.' и следующий за ним цифра, или обнаружена точка в числе
            if self.peek_char() == '.' and self.peek_next_is_digit():
                is_float = True
                lexeme += self.get_char()  # точка
                while True:
                    ch = self.peek_char()
                    if ch is not None and ch.isdigit():
                        lexeme += self.get_char()
                    else:
                        break

            # Проверка экспоненты
            if self.peek_char() is not None and self.peek_char().upper() == 'E':
                is_float = True
                lexeme += self.get_char()  # читаем 'E'
                # Опциональный знак
                if self.peek_char() in ['+', '-']:
                    lexeme += self.get_char()
                # Читаем цифры экспоненты
                exp_digits = ""
                while True:
                    ch = self.peek_char()
                    if ch is not None and ch.isdigit():
                        exp_digits += self.get_char()
                    else:
                        break
                lexeme += exp_digits

            if is_float:
                return Token("FLOAT", start_line, start_col, lexeme)
            else:
                # Ограничение: целое число не длиннее 16 символов
                if len(lexeme) > 16:
                    return Token("BAD", start_line, start_col, lexeme)
                return Token("INTEGER", start_line, start_col, lexeme)

        # Идентификаторы и ключевые слова (начинаются с буквы или _)
        if ch.isalpha() or ch == '_':
            lexeme = ""
            while True:
                ch = self.peek_char()
                if ch is not None and (ch.isalnum() or ch == '_'):
                    lexeme += self.get_char()
                else:
                    break
            if len(lexeme) > 256:
                return Token("BAD", start_line, start_col, lexeme)
            # Если в идентификаторе встречаются русские буквы, считаем ошибку
            if re.search(r'[а-яА-Я]', lexeme):
                return Token("BAD", start_line, start_col, lexeme)
            # Если лексема совпадает с ключевым словом
            if lexeme.upper() in self.keywords:
                return Token(lexeme.upper(), start_line, start_col, lexeme)
            else:
                return Token("IDENTIFIER", start_line, start_col, lexeme)

        # Обработка двухсимвольных операторов и знаков
        ch = self.get_char()
        next_ch = self.peek_char()
        # Проверяем комбинации
        if ch == ':' and next_ch == '=':
            lexeme = ch + self.get_char()
            return Token("ASSIGN", start_line, start_col, lexeme)
        if ch == '<':
            if next_ch == '=':
                lexeme = ch + self.get_char()
                return Token("LESS_EQ", start_line, start_col, lexeme)
            if next_ch == '>':
                lexeme = ch + self.get_char()
                return Token("NOT_EQ", start_line, start_col, lexeme)
            return Token("LESS", start_line, start_col, ch)
        if ch == '>':
            if next_ch == '=':
                lexeme = ch + self.get_char()
                return Token("GREATER_EQ", start_line, start_col, lexeme)
            return Token("GREATER", start_line, start_col, ch)

        # Одиночные операторы и знаки пунктуации
        if ch == '*':
            return Token("MULTIPLICATION", start_line, start_col, ch)
        if ch == '+':
            return Token("PLUS", start_line, start_col, ch)
        if ch == '-':
            return Token("MINUS", start_line, start_col, ch)
        if ch == ';':
            return Token("SEMICOLON", start_line, start_col, ch)
        if ch == ',':
            return Token("COMMA", start_line, start_col, ch)
        if ch == '(':
            return Token("LEFT_PAREN", start_line, start_col, ch)
        if ch == ')':
            return Token("RIGHT_PAREN", start_line, start_col, ch)
        if ch == '[':
            return Token("LEFT_BRACKET", start_line, start_col, ch)
        if ch == ']':
            return Token("RIGHT_BRACKET", start_line, start_col, ch)
        if ch == '=':
            return Token("EQ", start_line, start_col, ch)
        if ch == ':':
            return Token("COLON", start_line, start_col, ch)
        if ch == '.':
            return Token("DOT", start_line, start_col, ch)

        # Если символ не распознан – регистрируем ошибку
        return Token("BAD", start_line, start_col, ch)

    def peek_next_is_digit(self):
        # Сохраняем буфер и позицию
        if self.buffer:
            ch = self.buffer[0]
            return ch.isdigit()
        pos = self.infile.tell()
        ch = self.infile.read(1)
        self.infile.seek(pos)
        return ch.isdigit() if ch else False

def main():
    if len(sys.argv) != 3:
        print("Usage: python PascalLexer.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    lexer = Lexer(input_file)
    try:
        with open(output_file, 'w', encoding='utf-8') as out:
            while True:
                token = lexer.next_token()
                if token is None:
                    break
                out.write(str(token) + "\n")
    finally:
        lexer.close()

if __name__ == "__main__":
    main()
