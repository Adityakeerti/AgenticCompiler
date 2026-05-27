package ast;

import lexer.Token;

/**
 * Variable reference expression.
 * e.g.  a   (used inside expressions like  a + 1)
 */
public class Variable extends Expr {
    public final Token name;

    public Variable(Token name) {
        this.name = name;
    }
}
