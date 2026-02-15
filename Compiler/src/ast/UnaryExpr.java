package ast;

import lexer.Token;

/**
 * Unary expression: operator operand
 * e.g.  -x,  not flag
 */
public class UnaryExpr extends Expr {
    public final Token operator;
    public final Expr operand;

    public UnaryExpr(Token operator, Expr operand) {
        this.operator = operator;
        this.operand = operand;
    }
}
