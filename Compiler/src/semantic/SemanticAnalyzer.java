package semantic;

import ast.*;
import lexer.Token;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Walks the AST before interpretation to catch semantic errors:
 *   - Duplicate variable declarations
 *   - Use of undeclared variables
 */
public class SemanticAnalyzer {
    private final Map<String, String> symbolTable = new HashMap<>();
    private final List<String> errors = new java.util.ArrayList<>();

    // ── Public API ──────────────────────────────────────────

    public void analyze(List<Stmt> statements) {
        for (Stmt stmt : statements) {
            analyzeStmt(stmt);
        }

        if (!errors.isEmpty()) {
            StringBuilder sb = new StringBuilder("Semantic errors:\n");
            for (String err : errors) {
                sb.append("  • ").append(err).append("\n");
            }
            throw new RuntimeException(sb.toString());
        }
    }

    // ── Statement analysis ──────────────────────────────────

    private void analyzeStmt(Stmt stmt) {
        if (stmt instanceof VarDecl) {
            VarDecl v = (VarDecl) stmt;
            if (symbolTable.containsKey(v.name.lexeme)) {
                errors.add("Variable '" + v.name.lexeme + "' already declared (line " + v.name.line + ")");
            }
            analyzeExpr(v.initializer);
            symbolTable.put(v.name.lexeme, "any");

        } else if (stmt instanceof Assignment) {
            Assignment a = (Assignment) stmt;
            if (!symbolTable.containsKey(a.name.lexeme)) {
                errors.add("Variable '" + a.name.lexeme + "' used before declaration (line " + a.name.line + ")");
            }
            analyzeExpr(a.value);

        } else if (stmt instanceof ArrayAssignment) {
            ArrayAssignment aa = (ArrayAssignment) stmt;
            if (!symbolTable.containsKey(aa.name.lexeme)) {
                errors.add("Variable '" + aa.name.lexeme + "' used before declaration (line " + aa.name.line + ")");
            }
            analyzeExpr(aa.index);
            analyzeExpr(aa.value);

        } else if (stmt instanceof PrintStmt) {
            analyzeExpr(((PrintStmt) stmt).expression);

        } else if (stmt instanceof IfStmt) {
            IfStmt i = (IfStmt) stmt;
            analyzeExpr(i.condition);
            analyzeStmt(i.thenBranch);
            if (i.elseBranch != null) analyzeStmt(i.elseBranch);

        } else if (stmt instanceof WhileStmt) {
            WhileStmt w = (WhileStmt) stmt;
            analyzeExpr(w.condition);
            analyzeStmt(w.body);

        } else if (stmt instanceof ForStmt) {
            ForStmt f = (ForStmt) stmt;
            if (f.init != null) analyzeStmt(f.init);
            if (f.condition != null) analyzeExpr(f.condition);
            if (f.increment != null) analyzeStmt(f.increment);
            analyzeStmt(f.body);

        } else if (stmt instanceof Block) {
            for (Stmt s : ((Block) stmt).statements) {
                analyzeStmt(s);
            }
        }
    }

    // ── Expression analysis ─────────────────────────────────

    private void analyzeExpr(Expr expr) {
        if (expr instanceof BinaryExpr) {
            BinaryExpr b = (BinaryExpr) expr;
            analyzeExpr(b.left);
            analyzeExpr(b.right);

        } else if (expr instanceof UnaryExpr) {
            analyzeExpr(((UnaryExpr) expr).operand);

        } else if (expr instanceof Variable) {
            Variable v = (Variable) expr;
            if (!symbolTable.containsKey(v.name.lexeme)) {
                errors.add("Variable '" + v.name.lexeme + "' used before declaration (line " + v.name.line + ")");
            }

        } else if (expr instanceof Literal) {
            // nothing to check

        } else if (expr instanceof ArrayExpr) {
            for (Expr elem : ((ArrayExpr) expr).elements) {
                analyzeExpr(elem);
            }

        } else if (expr instanceof ArrayAccess) {
            ArrayAccess aa = (ArrayAccess) expr;
            if (!symbolTable.containsKey(aa.name.lexeme)) {
                errors.add("Variable '" + aa.name.lexeme + "' used before declaration (line " + aa.name.line + ")");
            }
            analyzeExpr(aa.index);
        }
    }
}
