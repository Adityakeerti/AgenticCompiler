package ast;

import lexer.Token;

/**
 * Variable declaration:  let x = expr;
 */
public class VarDecl extends Stmt {
    public final Token name;
    public final Expr initializer;

    public VarDecl(Token name, Expr initializer) {
        this.name = name;
        this.initializer = initializer;
    }
}
