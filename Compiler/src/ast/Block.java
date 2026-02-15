package ast;

import java.util.List;

/**
 * Block of statements enclosed in { }.
 */
public class Block extends Stmt {
    public final List<Stmt> statements;

    public Block(List<Stmt> statements) {
        this.statements = statements;
    }
}
