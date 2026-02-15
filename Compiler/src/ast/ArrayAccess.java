package ast;

import lexer.Token;

/**
 * Array element access:  arr[index]
 */
public class ArrayAccess extends Expr {
    public final Token name;
    public final Expr index;

    public ArrayAccess(Token name, Expr index) {
        this.name = name;
        this.index = index;
    }
}
