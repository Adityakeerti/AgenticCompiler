package compiler;

import ast.*;
import lexer.Token;
import lexer.TokenType;

import java.util.ArrayList;
import java.util.List;

/**
 * Compiles a validated AST into a linear sequence of bytecode instructions.
 * Uses jump-patching for control flow (if/else, while, for).
 */
public class BytecodeCompiler {
    private final List<Instruction> instructions = new ArrayList<>();

    // ── Public API ──────────────────────────────────────────

    public List<Instruction> compile(List<Stmt> statements) {
        for (Stmt stmt : statements) {
            compileStmt(stmt);
        }
        emit(OpCode.HALT);
        return instructions;
    }

    // ── Statement compilation ───────────────────────────────

    private void compileStmt(Stmt stmt) {
        if (stmt instanceof VarDecl) {
            VarDecl v = (VarDecl) stmt;
            compileExpr(v.initializer);
            emit(OpCode.STORE, v.name.lexeme);

        } else if (stmt instanceof Assignment) {
            Assignment a = (Assignment) stmt;
            compileExpr(a.value);
            emit(OpCode.STORE, a.name.lexeme);

        } else if (stmt instanceof ArrayAssignment) {
            ArrayAssignment aa = (ArrayAssignment) stmt;
            compileExpr(aa.value);
            compileExpr(aa.index);
            emit(OpCode.ARRAY_STORE, aa.name.lexeme);

        } else if (stmt instanceof PrintStmt) {
            compileExpr(((PrintStmt) stmt).expression);
            emit(OpCode.PRINT);

        } else if (stmt instanceof IfStmt) {
            compileIf((IfStmt) stmt);

        } else if (stmt instanceof WhileStmt) {
            compileWhile((WhileStmt) stmt);

        } else if (stmt instanceof ForStmt) {
            compileFor((ForStmt) stmt);

        } else if (stmt instanceof Block) {
            for (Stmt s : ((Block) stmt).statements) {
                compileStmt(s);
            }
        }
    }

    // ── Control flow ────────────────────────────────────────

    private void compileIf(IfStmt stmt) {
        // Compile condition
        compileExpr(stmt.condition);

        // Jump past then-branch if false
        int jumpToElse = emitJump(OpCode.JUMP_IF_FALSE);

        // Compile then-branch
        compileStmt(stmt.thenBranch);

        if (stmt.elseBranch != null) {
            // Jump past else-branch after then completes
            int jumpPastElse = emitJump(OpCode.JUMP);
            patchJump(jumpToElse);         // else starts here
            compileStmt(stmt.elseBranch);
            patchJump(jumpPastElse);       // after else
        } else {
            patchJump(jumpToElse);
        }
    }

    private void compileWhile(WhileStmt stmt) {
        int loopStart = currentIndex();

        // Compile condition
        compileExpr(stmt.condition);
        int jumpExit = emitJump(OpCode.JUMP_IF_FALSE);

        // Compile body
        compileStmt(stmt.body);
        emit(OpCode.JUMP, String.valueOf(loopStart));

        patchJump(jumpExit);
    }

    private void compileFor(ForStmt stmt) {
        // Init
        if (stmt.init != null) compileStmt(stmt.init);

        int loopStart = currentIndex();

        // Condition
        if (stmt.condition != null) {
            compileExpr(stmt.condition);
        } else {
            emit(OpCode.CONST_BOOL, "true");
        }
        int jumpExit = emitJump(OpCode.JUMP_IF_FALSE);

        // Body
        compileStmt(stmt.body);

        // Increment
        if (stmt.increment != null) compileStmt(stmt.increment);

        emit(OpCode.JUMP, String.valueOf(loopStart));
        patchJump(jumpExit);
    }

    // ── Expression compilation ──────────────────────────────

    private void compileExpr(Expr expr) {
        if (expr instanceof Literal) {
            Literal lit = (Literal) expr;
            if (lit.value instanceof Double) {
                emit(OpCode.CONST_NUM, lit.value.toString());
            } else if (lit.value instanceof String) {
                emit(OpCode.CONST_STR, (String) lit.value);
            } else if (lit.value instanceof Character) {
                emit(OpCode.CONST_CHAR, lit.value.toString());
            } else if (lit.value instanceof Boolean) {
                emit(OpCode.CONST_BOOL, lit.value.toString());
            } else if (lit.value == null) {
                emit(OpCode.CONST_NULL);
            }

        } else if (expr instanceof Variable) {
            emit(OpCode.LOAD, ((Variable) expr).name.lexeme);

        } else if (expr instanceof UnaryExpr) {
            UnaryExpr u = (UnaryExpr) expr;
            compileExpr(u.operand);
            switch (u.operator.type) {
                case MINUS: emit(OpCode.NEG); break;
                case NOT:   emit(OpCode.NOT); break;
                default: break;
            }

        } else if (expr instanceof BinaryExpr) {
            BinaryExpr b = (BinaryExpr) expr;
            compileExpr(b.left);
            compileExpr(b.right);
            switch (b.operator.type) {
                case PLUS:          emit(OpCode.ADD); break;
                case MINUS:         emit(OpCode.SUB); break;
                case STAR:          emit(OpCode.MUL); break;
                case SLASH:         emit(OpCode.DIV); break;
                case EQUAL_EQUAL:   emit(OpCode.EQ);  break;
                case BANG_EQUAL:    emit(OpCode.NEQ); break;
                case GREATER:       emit(OpCode.GT);  break;
                case GREATER_EQUAL: emit(OpCode.GTE); break;
                case LESS:          emit(OpCode.LT);  break;
                case LESS_EQUAL:    emit(OpCode.LTE); break;
                case AND:           emit(OpCode.AND); break;
                case OR:            emit(OpCode.OR);  break;
                default: break;
            }

        } else if (expr instanceof ArrayExpr) {
            ArrayExpr a = (ArrayExpr) expr;
            for (Expr elem : a.elements) {
                compileExpr(elem);
            }
            emit(OpCode.MAKE_ARRAY, String.valueOf(a.elements.size()));

        } else if (expr instanceof ArrayAccess) {
            ArrayAccess aa = (ArrayAccess) expr;
            emit(OpCode.LOAD, aa.name.lexeme);
            compileExpr(aa.index);
            emit(OpCode.ARRAY_LOAD);
        }
    }

    // ── Helpers ─────────────────────────────────────────────

    private void emit(OpCode op) {
        instructions.add(new Instruction(op));
    }

    private void emit(OpCode op, String operand) {
        instructions.add(new Instruction(op, operand));
    }

    private int currentIndex() {
        return instructions.size();
    }

    /**
     * Emit a jump instruction with a placeholder target.
     * Returns the index of the emitted instruction (for patching later).
     */
    private int emitJump(OpCode jumpOp) {
        instructions.add(new Instruction(jumpOp, "0"));
        return instructions.size() - 1;
    }

    /**
     * Patch a previously emitted jump to point at the current instruction index.
     */
    private void patchJump(int instructionIndex) {
        instructions.get(instructionIndex).operand = String.valueOf(instructions.size());
    }
}
