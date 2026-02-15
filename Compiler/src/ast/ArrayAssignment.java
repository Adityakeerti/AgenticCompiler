package ast;

import lexer.Token;

/**
 * Array element assignment:  arr[index] = value;
 */
public class ArrayAssignment extends Stmt {
    public final Token name;
    public final Expr index;
    public final Expr value;

    public ArrayAssignment(Token name, Expr index, Expr value) {
        this.name = name;
        this.index = index;
        this.value = value;
    }
}
