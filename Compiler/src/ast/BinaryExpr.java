package ast;

import lexer.Token;

/**
 * Binary expression: left operator right
 * e.g.  a + b,  x == 10,  i < n
 */
public class BinaryExpr extends Expr {
    public final Expr left;
    public final Token operator;
    public final Expr right;

    public BinaryExpr(Expr left, Token operator, Expr right) {
        this.left = left;
        this.operator = operator;
        this.right = right;
    }
}
