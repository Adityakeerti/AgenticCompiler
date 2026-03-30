package ast;

/**
 * Print statement:  print(expr);
 */
public class PrintStmt extends Stmt {
    public final Expr expression;

    public PrintStmt(Expr expression) {
        this.expression = expression;
    }
}
