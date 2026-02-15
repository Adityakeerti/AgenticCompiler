package lexer;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class Lexer {
    private final String source;
    private final List<Token> tokens = new ArrayList<>();
    private int start = 0;
    private int current = 0;
    private int line = 1;

    private static final Map<String, TokenType> keywords = new HashMap<>();

    static {
        keywords.put("let",   TokenType.LET);
        keywords.put("if",    TokenType.IF);
        keywords.put("else",  TokenType.ELSE);
        keywords.put("while", TokenType.WHILE);
        keywords.put("for",   TokenType.FOR);
        keywords.put("print", TokenType.PRINT);
        keywords.put("and",   TokenType.AND);
        keywords.put("or",    TokenType.OR);
        keywords.put("not",   TokenType.NOT);
    }

    public Lexer(String source) {
        this.source = source;
    }

    // ── Public API ──────────────────────────────────────────

    public List<Token> scanTokens() {
        while (!isAtEnd()) {
            start = current;
            scanToken();
        }
        tokens.add(new Token(TokenType.EOF, "", line));
        return tokens;
    }

    // ── Core scanning ───────────────────────────────────────

    private void scanToken() {
        char c = advance();
        switch (c) {
            // Single-character tokens
            case '(': addToken(TokenType.LPAREN);    break;
            case ')': addToken(TokenType.RPAREN);    break;
            case '{': addToken(TokenType.LBRACE);    break;
            case '}': addToken(TokenType.RBRACE);    break;
            case '+': addToken(TokenType.PLUS);      break;
            case '-': addToken(TokenType.MINUS);     break;
            case '*': addToken(TokenType.STAR);      break;
            case '/':
                if (peek() == '/') {
                    // Single-line comment — skip until end of line
                    while (!isAtEnd() && peek() != '\n') advance();
                } else {
                    addToken(TokenType.SLASH);
                }
                break;
            case ';': addToken(TokenType.SEMICOLON); break;
            case ',': addToken(TokenType.COMMA);     break;
            case '[': addToken(TokenType.LBRACKET);  break;
            case ']': addToken(TokenType.RBRACKET);  break;

            // One-or-two-character tokens
            case '=':
                addToken(match('=') ? TokenType.EQUAL_EQUAL : TokenType.EQUAL);
                break;
            case '!':
                addToken(match('=') ? TokenType.BANG_EQUAL : TokenType.NOT);
                break;
            case '>':
                addToken(match('=') ? TokenType.GREATER_EQUAL : TokenType.GREATER);
                break;
            case '<':
                addToken(match('=') ? TokenType.LESS_EQUAL : TokenType.LESS);
                break;

            // Whitespace
            case ' ':
            case '\r':
            case '\t':
                break;
            case '\n':
                line++;
                break;

            // String literals
            case '"': string(); break;

            // Char literals
            case '\'': charLiteral(); break;

            default:
                if (isDigit(c)) {
                    number();
                } else if (isAlpha(c)) {
                    identifier();
                } else {
                    throw new RuntimeException("Unexpected character '" + c + "' at line " + line);
                }
                break;
        }
    }

    // ── Literal scanners ────────────────────────────────────

    private void number() {
        while (!isAtEnd() && isDigit(peek())) advance();

        // Look for a decimal part
        if (!isAtEnd() && peek() == '.' && isDigit(peekNext())) {
            advance(); // consume '.'
            while (!isAtEnd() && isDigit(peek())) advance();
        }

        addToken(TokenType.NUMBER);
    }

    private void identifier() {
        while (!isAtEnd() && isAlphaNumeric(peek())) advance();

        String text = source.substring(start, current);
        TokenType type = keywords.getOrDefault(text, TokenType.IDENTIFIER);
        addToken(type);
    }

    private void string() {
        while (!isAtEnd() && peek() != '"') {
            if (peek() == '\n') line++;
            advance();
        }

        if (isAtEnd()) {
            throw new RuntimeException("Unterminated string at line " + line);
        }

        advance(); // closing "

        // Trim surrounding quotes from the lexeme
        addToken(TokenType.STRING);
    }

    private void charLiteral() {
        if (isAtEnd() || peek() == '\'') {
            throw new RuntimeException("Empty char literal at line " + line);
        }

        advance(); // consume the character

        if (isAtEnd() || peek() != '\'') {
            throw new RuntimeException("Unterminated or multi-character char literal at line " + line);
        }

        advance(); // closing '
        addToken(TokenType.CHAR);
    }

    // ── Helper methods ──────────────────────────────────────

    private char advance() {
        return source.charAt(current++);
    }

    private char peek() {
        if (isAtEnd()) return '\0';
        return source.charAt(current);
    }

    private char peekNext() {
        if (current + 1 >= source.length()) return '\0';
        return source.charAt(current + 1);
    }

    private boolean match(char expected) {
        if (isAtEnd()) return false;
        if (source.charAt(current) != expected) return false;
        current++;
        return true;
    }

    private boolean isAtEnd() {
        return current >= source.length();
    }

    private boolean isDigit(char c) {
        return c >= '0' && c <= '9';
    }

    private boolean isAlpha(char c) {
        return (c >= 'a' && c <= 'z') ||
               (c >= 'A' && c <= 'Z') ||
               c == '_';
    }

    private boolean isAlphaNumeric(char c) {
        return isAlpha(c) || isDigit(c);
    }

    private void addToken(TokenType type) {
        String text = source.substring(start, current);
        tokens.add(new Token(type, text, line));
    }
}
