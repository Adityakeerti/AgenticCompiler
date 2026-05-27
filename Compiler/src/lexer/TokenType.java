package lexer;

public enum TokenType {
    // Keywords
    LET, IF, ELSE, WHILE, FOR, PRINT,

    // Identifiers & literals
    IDENTIFIER, NUMBER, STRING, CHAR,

    // Operators
    PLUS, MINUS, STAR, SLASH,
    EQUAL, EQUAL_EQUAL, BANG_EQUAL,
    GREATER, GREATER_EQUAL,
    LESS, LESS_EQUAL,
    AND, OR, NOT,

    // Symbols
    LPAREN, RPAREN,
    LBRACE, RBRACE,
    LBRACKET, RBRACKET,
    SEMICOLON, COMMA,

    // End of file
    EOF
}
