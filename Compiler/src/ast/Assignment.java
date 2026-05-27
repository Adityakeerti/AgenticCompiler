package ast;

import lexer.Token;

/**
 * Assignment:  x = expr;
 */
public class Assignment extends Stmt {
    public final Token name;
    public final Expr value;

    public Assignment(Token name, Expr value) {
        this.name = name;
        this.value = value;
    }
}
