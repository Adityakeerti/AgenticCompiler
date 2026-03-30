package ast;

/**
 * If statement:  if (condition) { thenBranch } else { elseBranch }
 * elseBranch may be null.
 */
public class IfStmt extends Stmt {
    public final Expr condition;
    public final Stmt thenBranch;
    public final Stmt elseBranch; // nullable

    public IfStmt(Expr condition, Stmt thenBranch, Stmt elseBranch) {
        this.condition = condition;
        this.thenBranch = thenBranch;
        this.elseBranch = elseBranch;
    }
}
