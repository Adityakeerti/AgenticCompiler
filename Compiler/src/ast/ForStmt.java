package ast;

import lexer.Token;

/**
 * For-loop statement:  for (init; condition; increment) { body }
 * All parts are optional (nullable).
 */
public class ForStmt extends Stmt {
    public final Stmt init;        // VarDecl or Assignment, nullable
    public final Expr condition;   // nullable (defaults to true)
    public final Stmt increment;   // Assignment, nullable
    public final Stmt body;

    public ForStmt(Stmt init, Expr condition, Stmt increment, Stmt body) {
        this.init = init;
        this.condition = condition;
        this.increment = increment;
        this.body = body;
    }
}
