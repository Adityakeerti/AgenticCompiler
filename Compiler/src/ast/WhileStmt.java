package ast;

/**
 * While loop:  while (condition) { body }
 */
public class WhileStmt extends Stmt {
    public final Expr condition;
    public final Stmt body;

    public WhileStmt(Expr condition, Stmt body) {
        this.condition = condition;
        this.body = body;
    }
}
