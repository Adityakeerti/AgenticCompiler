package parser;

import ast.*;
import lexer.Token;
import lexer.TokenType;

import java.util.ArrayList;
import java.util.List;

/**
 * Recursive-descent parser for the .cpy language.
 *
 * Grammar (simplified):
 *   program     → statement* EOF
 *   statement   → varDecl | assignment | ifStmt | whileStmt | forStmt | printStmt | block
 *   varDecl     → "let" IDENTIFIER "=" expression ";"
 *   assignment  → IDENTIFIER "=" expression ";"
 *   ifStmt      → "if" "(" expression ")" block ( "else" block )?
 *   whileStmt   → "while" "(" expression ")" block
 *   forStmt     → "for" "(" (varDecl | assignment | ";") expression? ";" assignment? ")" block
 *   printStmt   → "print" "(" expression ")" ";"
 *   block       → "{" statement* "}"
 *   expression  → or
 *   or          → and ( "or" and )*
 *   and         → equality ( "and" equality )*
 *   equality    → comparison ( ( "==" | "!=" ) comparison )*
 *   comparison  → term ( ( ">" | ">=" | "<" | "<=" ) term )*
 *   term        → factor ( ( "+" | "-" ) factor )*
 *   factor      → unary ( ( "*" | "/" ) unary )*
 *   unary       → ( "-" | "not" ) unary | primary
 *   primary     → NUMBER | STRING | IDENTIFIER | "(" expression ")"
 */
public class Parser {
    private final List<Token> tokens;
    private int current = 0;

    public Parser(List<Token> tokens) {
        this.tokens = tokens;
    }

    // ── Public API ──────────────────────────────────────────

    public List<Stmt> parse() {
        List<Stmt> statements = new ArrayList<>();
        while (!isAtEnd()) {
            statements.add(statement());
        }
        return statements;
    }

    // ── Statement Parsing ───────────────────────────────────

    private Stmt statement() {
        if (check(TokenType.LET))    return varDeclaration();
        if (check(TokenType.IF))     return ifStatement();
        if (check(TokenType.WHILE))  return whileStatement();
        if (check(TokenType.FOR))    return forStatement();
        if (check(TokenType.PRINT))  return printStatement();
        if (check(TokenType.LBRACE)) return block();

        // Must be an assignment or array assignment: IDENTIFIER = expr ; or IDENTIFIER[expr] = expr ;
        return assignmentOrArrayAssignment();
    }

    /**
     * Disambiguate:  name = expr ;   vs   name[index] = expr ;
     */
    private Stmt assignmentOrArrayAssignment() {
        Token name = consume(TokenType.IDENTIFIER, "Expected variable name");

        if (match(TokenType.LBRACKET)) {
            // Array element assignment:  name[index] = expr ;
            Expr index = expression();
            consume(TokenType.RBRACKET, "Expected ']' after array index");
            consume(TokenType.EQUAL, "Expected '=' after array element");
            Expr value = expression();
            consume(TokenType.SEMICOLON, "Expected ';' after array assignment");
            return new ArrayAssignment(name, index, value);
        }

        // Regular assignment:  name = expr ;
        consume(TokenType.EQUAL, "Expected '=' after variable name");
        Expr value = expression();
        consume(TokenType.SEMICOLON, "Expected ';' after assignment");
        return new Assignment(name, value);
    }

    private Stmt varDeclaration() {
        consume(TokenType.LET, "Expected 'let'");
        Token name = consume(TokenType.IDENTIFIER, "Expected variable name after 'let'");
        consume(TokenType.EQUAL, "Expected '=' after variable name");
        Expr initializer = expression();
        consume(TokenType.SEMICOLON, "Expected ';' after variable declaration");
        return new VarDecl(name, initializer);
    }

    private Stmt assignmentStatement() {
        Token name = consume(TokenType.IDENTIFIER, "Expected variable name in for increment");
        consume(TokenType.EQUAL, "Expected '=' after variable name");
        Expr value = expression();
        consume(TokenType.SEMICOLON, "Expected ';' after assignment");
        return new Assignment(name, value);
    }

    private Stmt ifStatement() {
        consume(TokenType.IF, "Expected 'if'");
        consume(TokenType.LPAREN, "Expected '(' after 'if'");
        Expr condition = expression();
        consume(TokenType.RPAREN, "Expected ')' after if condition");

        Stmt thenBranch = block();
        Stmt elseBranch = null;

        if (match(TokenType.ELSE)) {
            elseBranch = block();
        }

        return new IfStmt(condition, thenBranch, elseBranch);
    }

    private Stmt whileStatement() {
        consume(TokenType.WHILE, "Expected 'while'");
        consume(TokenType.LPAREN, "Expected '(' after 'while'");
        Expr condition = expression();
        consume(TokenType.RPAREN, "Expected ')' after while condition");

        Stmt body = block();
        return new WhileStmt(condition, body);
    }

    private Stmt forStatement() {
        consume(TokenType.FOR, "Expected 'for'");
        consume(TokenType.LPAREN, "Expected '(' after 'for'");

        // Initializer
        Stmt init = null;
        if (check(TokenType.LET)) {
            init = varDeclaration();
        } else if (!check(TokenType.SEMICOLON)) {
            init = assignmentStatement();
        } else {
            consume(TokenType.SEMICOLON, "Expected ';'");
        }

        // Condition
        Expr condition = null;
        if (!check(TokenType.SEMICOLON)) {
            condition = expression();
        }
        consume(TokenType.SEMICOLON, "Expected ';' after for condition");

        // Increment
        Stmt increment = null;
        if (!check(TokenType.RPAREN)) {
            Token name = consume(TokenType.IDENTIFIER, "Expected variable name in for increment");
            consume(TokenType.EQUAL, "Expected '=' in for increment");
            Expr value = expression();
            increment = new Assignment(name, value);
        }
        consume(TokenType.RPAREN, "Expected ')' after for clauses");

        Stmt body = block();
        return new ForStmt(init, condition, increment, body);
    }

    private Stmt printStatement() {
        consume(TokenType.PRINT, "Expected 'print'");
        consume(TokenType.LPAREN, "Expected '(' after 'print'");
        Expr value = expression();
        consume(TokenType.RPAREN, "Expected ')' after print expression");
        consume(TokenType.SEMICOLON, "Expected ';' after print statement");
        return new PrintStmt(value);
    }

    private Stmt block() {
        consume(TokenType.LBRACE, "Expected '{'");
        List<Stmt> statements = new ArrayList<>();

        while (!check(TokenType.RBRACE) && !isAtEnd()) {
            statements.add(statement());
        }

        consume(TokenType.RBRACE, "Expected '}'");
        return new Block(statements);
    }

    // ── Expression Parsing (precedence climbing) ────────────

    private Expr expression() {
        return or();
    }

    private Expr or() {
        Expr left = and();
        while (match(TokenType.OR)) {
            Token op = previous();
            Expr right = and();
            left = new BinaryExpr(left, op, right);
        }
        return left;
    }

    private Expr and() {
        Expr left = equality();
        while (match(TokenType.AND)) {
            Token op = previous();
            Expr right = equality();
            left = new BinaryExpr(left, op, right);
        }
        return left;
    }

    private Expr equality() {
        Expr left = comparison();
        while (match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL)) {
            Token op = previous();
            Expr right = comparison();
            left = new BinaryExpr(left, op, right);
        }
        return left;
    }

    private Expr comparison() {
        Expr left = term();
        while (match(TokenType.GREATER, TokenType.GREATER_EQUAL,
                     TokenType.LESS, TokenType.LESS_EQUAL)) {
            Token op = previous();
            Expr right = term();
            left = new BinaryExpr(left, op, right);
        }
        return left;
    }

    private Expr term() {
        Expr left = factor();
        while (match(TokenType.PLUS, TokenType.MINUS)) {
            Token op = previous();
            Expr right = factor();
            left = new BinaryExpr(left, op, right);
        }
        return left;
    }

    private Expr factor() {
        Expr left = unary();
        while (match(TokenType.STAR, TokenType.SLASH)) {
            Token op = previous();
            Expr right = unary();
            left = new BinaryExpr(left, op, right);
        }
        return left;
    }

    private Expr unary() {
        if (match(TokenType.MINUS, TokenType.NOT)) {
            Token op = previous();
            Expr operand = unary();
            return new UnaryExpr(op, operand);
        }
        return primary();
    }

    private Expr primary() {
        if (match(TokenType.NUMBER)) {
            return new Literal(Double.parseDouble(previous().lexeme));
        }

        if (match(TokenType.STRING)) {
            // Strip surrounding quotes from the lexeme
            String raw = previous().lexeme;
            return new Literal(raw.substring(1, raw.length() - 1));
        }

        if (match(TokenType.CHAR)) {
            // Strip surrounding single quotes:  'a' → Character 'a'
            String raw = previous().lexeme;
            return new Literal(raw.charAt(1));
        }

        if (match(TokenType.IDENTIFIER)) {
            Token name = previous();
            // Check for array access:  name[expr]
            if (match(TokenType.LBRACKET)) {
                Expr index = expression();
                consume(TokenType.RBRACKET, "Expected ']' after array index");
                return new ArrayAccess(name, index);
            }
            return new Variable(name);
        }

        if (match(TokenType.LPAREN)) {
            Expr expr = expression();
            consume(TokenType.RPAREN, "Expected ')' after grouped expression");
            return expr;
        }

        // Array literal:  [expr, expr, ...]
        if (match(TokenType.LBRACKET)) {
            List<Expr> elements = new ArrayList<>();
            if (!check(TokenType.RBRACKET)) {
                do {
                    elements.add(expression());
                } while (match(TokenType.COMMA));
            }
            consume(TokenType.RBRACKET, "Expected ']' after array literal");
            return new ArrayExpr(elements);
        }

        throw error("Unexpected token: " + peek().lexeme);
    }

    // ── Utilities ───────────────────────────────────────────

    private boolean match(TokenType... types) {
        for (TokenType type : types) {
            if (check(type)) {
                advance();
                return true;
            }
        }
        return false;
    }

    private boolean check(TokenType type) {
        if (isAtEnd()) return false;
        return peek().type == type;
    }

    private Token advance() {
        if (!isAtEnd()) current++;
        return previous();
    }

    private Token peek() {
        return tokens.get(current);
    }

    private Token previous() {
        return tokens.get(current - 1);
    }

    private boolean isAtEnd() {
        return peek().type == TokenType.EOF;
    }

    private Token consume(TokenType type, String message) {
        if (check(type)) return advance();
        throw error(message + " (got '" + peek().lexeme + "' at line " + peek().line + ")");
    }

    private RuntimeException error(String message) {
        return new RuntimeException("Parse error: " + message);
    }
}
