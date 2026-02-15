package interpreter;

import ast.*;

import java.util.ArrayList;
import lexer.Token;
import lexer.TokenType;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Tree-walking interpreter for the .cpy language.
 * Evaluates AST nodes directly — no bytecode generation.
 */
public class Interpreter {
    private final Map<String, Object> environment = new HashMap<>();

    // ── Public API ──────────────────────────────────────────

    public void interpret(List<Stmt> statements) {
        for (Stmt stmt : statements) {
            execute(stmt);
        }
    }

    // ── Statement execution ─────────────────────────────────

    private void execute(Stmt stmt) {
        if (stmt instanceof VarDecl) {
            VarDecl v = (VarDecl) stmt;
            Object value = evaluate(v.initializer);
            environment.put(v.name.lexeme, value);

        } else if (stmt instanceof Assignment) {
            Assignment a = (Assignment) stmt;
            Object value = evaluate(a.value);
            environment.put(a.name.lexeme, value);

        } else if (stmt instanceof PrintStmt) {
            Object value = evaluate(((PrintStmt) stmt).expression);
            System.out.println(stringify(value));

        } else if (stmt instanceof IfStmt) {
            IfStmt i = (IfStmt) stmt;
            if (isTruthy(evaluate(i.condition))) {
                execute(i.thenBranch);
            } else if (i.elseBranch != null) {
                execute(i.elseBranch);
            }

        } else if (stmt instanceof WhileStmt) {
            WhileStmt w = (WhileStmt) stmt;
            while (isTruthy(evaluate(w.condition))) {
                execute(w.body);
            }

        } else if (stmt instanceof ForStmt) {
            ForStmt f = (ForStmt) stmt;
            if (f.init != null) execute(f.init);
            while (f.condition == null || isTruthy(evaluate(f.condition))) {
                execute(f.body);
                if (f.increment != null) execute(f.increment);
            }

        } else if (stmt instanceof ArrayAssignment) {
            ArrayAssignment aa = (ArrayAssignment) stmt;
            Object arr = environment.get(aa.name.lexeme);
            if (!(arr instanceof List)) {
                throw new RuntimeException("Runtime error at line " + aa.name.line + ": '" + aa.name.lexeme + "' is not an array");
            }
            int idx = toIndex(evaluate(aa.index), aa.name);
            @SuppressWarnings("unchecked")
            List<Object> list = (List<Object>) arr;
            if (idx < 0 || idx >= list.size()) {
                throw new RuntimeException("Runtime error at line " + aa.name.line + ": Array index " + idx + " out of bounds (size " + list.size() + ")");
            }
            list.set(idx, evaluate(aa.value));

        } else if (stmt instanceof Block) {
            for (Stmt s : ((Block) stmt).statements) {
                execute(s);
            }
        }
    }

    // ── Expression evaluation ───────────────────────────────

    private Object evaluate(Expr expr) {
        if (expr instanceof Literal) {
            return ((Literal) expr).value;
        }

        if (expr instanceof Variable) {
            Variable v = (Variable) expr;
            if (!environment.containsKey(v.name.lexeme)) {
                throw runtimeError("Undefined variable '" + v.name.lexeme + "'", v.name);
            }
            return environment.get(v.name.lexeme);
        }

        if (expr instanceof UnaryExpr) {
            UnaryExpr u = (UnaryExpr) expr;
            Object operand = evaluate(u.operand);

            switch (u.operator.type) {
                case MINUS:
                    checkNumber(u.operator, operand);
                    return -(double) operand;
                case NOT:
                    return !isTruthy(operand);
                default:
                    throw runtimeError("Unknown unary operator", u.operator);
            }
        }

        if (expr instanceof BinaryExpr) {
            return evaluateBinary((BinaryExpr) expr);
        }

        if (expr instanceof ArrayExpr) {
            ArrayExpr a = (ArrayExpr) expr;
            List<Object> elements = new ArrayList<>();
            for (Expr elem : a.elements) {
                elements.add(evaluate(elem));
            }
            return elements;
        }

        if (expr instanceof ArrayAccess) {
            ArrayAccess aa = (ArrayAccess) expr;
            Object arr = environment.get(aa.name.lexeme);
            if (!(arr instanceof List)) {
                throw runtimeError("'" + aa.name.lexeme + "' is not an array", aa.name);
            }
            int idx = toIndex(evaluate(aa.index), aa.name);
            @SuppressWarnings("unchecked")
            List<Object> list = (List<Object>) arr;
            if (idx < 0 || idx >= list.size()) {
                throw runtimeError("Array index " + idx + " out of bounds (size " + list.size() + ")", aa.name);
            }
            return list.get(idx);
        }

        throw new RuntimeException("Unknown expression type: " + expr.getClass().getName());
    }

    private Object evaluateBinary(BinaryExpr b) {
        Object left  = evaluate(b.left);
        Object right = evaluate(b.right);

        switch (b.operator.type) {
            // Arithmetic
            case PLUS:
                if (left instanceof Double && right instanceof Double)
                    return (double) left + (double) right;
                if (left instanceof String || right instanceof String)
                    return stringify(left) + stringify(right);
                throw runtimeError("Operands must be two numbers or at least one string", b.operator);
            case MINUS:
                checkNumbers(b.operator, left, right);
                return (double) left - (double) right;
            case STAR:
                checkNumbers(b.operator, left, right);
                return (double) left * (double) right;
            case SLASH:
                checkNumbers(b.operator, left, right);
                if ((double) right == 0)
                    throw runtimeError("Division by zero", b.operator);
                return (double) left / (double) right;

            // Comparison
            case GREATER:
                checkNumbers(b.operator, left, right);
                return (double) left > (double) right;
            case GREATER_EQUAL:
                checkNumbers(b.operator, left, right);
                return (double) left >= (double) right;
            case LESS:
                checkNumbers(b.operator, left, right);
                return (double) left < (double) right;
            case LESS_EQUAL:
                checkNumbers(b.operator, left, right);
                return (double) left <= (double) right;

            // Equality
            case EQUAL_EQUAL:
                return isEqual(left, right);
            case BANG_EQUAL:
                return !isEqual(left, right);

            // Logical
            case AND:
                return isTruthy(left) && isTruthy(right);
            case OR:
                return isTruthy(left) || isTruthy(right);

            default:
                throw runtimeError("Unknown operator", b.operator);
        }
    }

    // ── Helpers ─────────────────────────────────────────────

    private boolean isTruthy(Object value) {
        if (value == null) return false;
        if (value instanceof Boolean) return (boolean) value;
        if (value instanceof Double) return (double) value != 0;
        return true;
    }

    private boolean isEqual(Object a, Object b) {
        if (a == null && b == null) return true;
        if (a == null) return false;
        return a.equals(b);
    }

    private String stringify(Object value) {
        if (value == null) return "null";
        if (value instanceof Double) {
            String text = value.toString();
            // Print 10.0 as "10" for cleaner output
            if (text.endsWith(".0")) {
                text = text.substring(0, text.length() - 2);
            }
            return text;
        }
        if (value instanceof Character) {
            return value.toString();
        }
        if (value instanceof List) {
            @SuppressWarnings("unchecked")
            List<Object> list = (List<Object>) value;
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < list.size(); i++) {
                if (i > 0) sb.append(", ");
                sb.append(stringify(list.get(i)));
            }
            sb.append("]");
            return sb.toString();
        }
        return value.toString();
    }

    private int toIndex(Object value, Token token) {
        if (!(value instanceof Double)) {
            throw runtimeError("Array index must be a number", token);
        }
        return (int) (double) value;
    }

    private void checkNumber(Token operator, Object operand) {
        if (operand instanceof Double) return;
        throw runtimeError("Operand must be a number", operator);
    }

    private void checkNumbers(Token operator, Object left, Object right) {
        if (left instanceof Double && right instanceof Double) return;
        throw runtimeError("Operands must be numbers", operator);
    }

    private RuntimeException runtimeError(String message, Token token) {
        return new RuntimeException("Runtime error at line " + token.line + ": " + message);
    }
}
