package ast;

import java.util.List;

/**
 * Array literal expression:  [expr, expr, ...]
 */
public class ArrayExpr extends Expr {
    public final List<Expr> elements;

    public ArrayExpr(List<Expr> elements) {
        this.elements = elements;
    }
}
