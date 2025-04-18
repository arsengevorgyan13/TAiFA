import sys
import re

# Класс для токена
type_alias = str 
class Token:
    def __init__(self, type: str, line: int, col: int, lexeme: str):
        self.type = type
        self.line = line
        self.col = col
        self.lexeme = lexeme

    def __str__(self):
        return f'{self.type} ({self.line}, {self.col}) "{self.lexeme}"'

class Lexer:
    def __init__(self, infile: str):
        self.infile = open(infile, 'r', encoding='utf-8')
        self.buffer = ''
        self.eof = False
        self.line = 1
        self.col = 1
        self.keywords = {"ARRAY", "BEGIN", "ELSE", "END", "IF", "OF", "OR", "PROGRAM", "PROCEDURE", "THEN", "TYPE", "VAR"}

    def close(self):
        self.infile.close()

    def read_char(self) -> str:
        ch = self.infile.read(1)
        if ch == '':
            self.eof = True
            return None
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def peek_char(self) -> str:
        if self.buffer:
            return self.buffer[0]
        self.buffer = self.infile.read(1)
        if self.buffer == '':
            self.eof = True
            return None
        return self.buffer[0]

    def get_char(self) -> str:
        if self.buffer:
            ch = self.buffer[0]
            self.buffer = self.buffer[1:]
            if ch == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            return ch
        return self.read_char()

    def peek_next_is_digit(self) -> bool:
        # Проверяет, что следующий символ (после текущего) — цифра
        if self.buffer and len(self.buffer) > 1:
            return self.buffer[1].isdigit()
        pos = self.infile.tell()
        ch = self.infile.read(1)
        self.infile.seek(pos)
        return ch.isdigit() if ch else False

    def next_token(self) -> Token:
        # Пропуск пробельных символов
        while True:
            ch = self.peek_char()
            if ch is None:
                return None
            if ch.isspace():
                self.get_char()
                continue
            break

        start_line, start_col = self.line, self.col
        ch = self.peek_char()

        # Блочный комментарий { ... }
        if ch == '{':
            self.get_char()
            while True:
                ch = self.peek_char()
                if ch is None or ch == '}':
                    if ch == '}':
                        self.get_char()
                    break
                self.get_char()
            return self.next_token()

        # Однострочный комментарий //...
        if ch == '/':
            self.get_char()
            if self.peek_char() == '/':
                self.get_char()
                while True:
                    ch = self.peek_char()
                    if ch is None or ch == '\n':
                        break
                    self.get_char()
                return self.next_token()
            else:
                return Token('DIVIDE', start_line, start_col, '/')

        # Строковый литерал в одинарных кавычках
        if ch == "'":
            lex = self.get_char()
            while True:
                ch = self.peek_char()
                if ch is None or ch == '\n':
                    return Token('BAD', start_line, start_col, lex)
                lex += self.get_char()
                if ch == "'":
                    break
            return Token('STRING', start_line, start_col, lex)

        # Числовые литералы (INTEGER или FLOAT)
        if ch.isdigit() or (ch == '.' and self.peek_next_is_digit()):
            lex = ''
            is_float = False
            # Целая часть
            while True:
                ch = self.peek_char()
                if ch and ch.isdigit():
                    lex += self.get_char()
                else:
                    break
            # Дробная часть
            if self.peek_char() == '.' and self.peek_next_is_digit():
                is_float = True
                lex += self.get_char()
                while True:
                    ch = self.peek_char()
                    if ch and ch.isdigit():
                        lex += self.get_char()
                    else:
                        break
            # Экспонента
            if self.peek_char() and self.peek_char().upper() == 'E':
                is_float = True
                lex += self.get_char()
                if self.peek_char() in ['+', '-']:
                    lex += self.get_char()
                while True:
                    ch = self.peek_char()
                    if ch and ch.isdigit():
                        lex += self.get_char()
                    else:
                        break
            if is_float:
                return Token('FLOAT', start_line, start_col, lex)
            # Ограничение длины INTEGER
            if len(lex) > 16:
                return Token('BAD', start_line, start_col, lex)
            return Token('INTEGER', start_line, start_col, lex)

        # Идентификаторы и ключевые слова
        if ch.isalpha() or ch == '_':
            lex = ''
            while True:
                ch = self.peek_char()
                if ch and (ch.isalnum() or ch == '_'):
                    lex += self.get_char()
                else:
                    break
            if len(lex) > 256 or re.search(r'[а-яА-Я]', lex):
                return Token('BAD', start_line, start_col, lex)
            up = lex.upper()
            if up in self.keywords:
                return Token(up, start_line, start_col, lex)
            return Token('IDENTIFIER', start_line, start_col, lex)

        # Операторы и пунктуация
        ch = self.get_char()
        pc = self.peek_char()
        # Двухсимвольные операторы
        if ch == ':' and pc == '=':
            return Token('ASSIGN', start_line, start_col, ch + self.get_char())
        if ch == '<' and pc == '=':
            return Token('LESS_EQ', start_line, start_col, ch + self.get_char())
        if ch == '<' and pc == '>':
            return Token('NOT_EQ', start_line, start_col, ch + self.get_char())
        if ch == '<':
            return Token('LESS', start_line, start_col, ch)
        if ch == '>' and pc == '=':
            return Token('GREATER_EQ', start_line, start_col, ch + self.get_char())
        if ch == '>':
            return Token('GREATER', start_line, start_col, ch)

        single = {
            '*': 'MULTIPLICATION', '+': 'PLUS', '-': 'MINUS',
            ';': 'SEMICOLON', ',': 'COMMA', '(': 'LEFT_PAREN',
            ')': 'RIGHT_PAREN', '[': 'LEFT_BRACKET', ']': 'RIGHT_BRACKET',
            '=': 'EQ', ':': 'COLON'
        }
        if ch in single:
            return Token(single[ch], start_line, start_col, ch)
        if ch == '.':
            return Token('DOT', start_line, start_col, ch)

        return Token('BAD', start_line, start_col, ch)


def main():
    if len(sys.argv) != 3:
        print("Usage: python PascalLexer.py <input_file> <output_file>")
        sys.exit(1)

    lexer = Lexer(sys.argv[1])
    with open(sys.argv[2], 'w', encoding='utf-8') as out:
        while True:
            token = lexer.next_token()
            if not token:
                break
            out.write(str(token) + "\n")
    lexer.close()

if __name__ == '__main__':
    main()
