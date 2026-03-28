package vm;

import compiler.Instruction;
import compiler.OpCode;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Stack;

/**
 * Stack-based virtual machine that executes compiled CPY bytecode.
 *
 * Architecture:
 *   - Operand stack  : holds intermediate values
 *   - Environment    : maps variable names to values
 *   - Program counter: index into the instruction list
 */
public class VM {
    private final List<Instruction> program;
    private final Stack<Object> stack = new Stack<>();
    private final Map<String, Object> env = new HashMap<>();
    private int pc = 0;  // program counter

    public VM(List<Instruction> program) {
        this.program = program;
    }

    // ── Public API ──────────────────────────────────────────

    public void run() {
        while (pc < program.size()) {
            Instruction instr = program.get(pc);
            execute(instr);
            if (instr.opCode == OpCode.HALT) break;
        }
    }

    // ── Instruction dispatch ────────────────────────────────

    private void execute(Instruction instr) {
        switch (instr.opCode) {
            // ── Constants ──
            case CONST_NUM:
                stack.push(Double.parseDouble(instr.operand));
                pc++;
                break;

            case CONST_STR:
                stack.push(instr.operand);
                pc++;
                break;

            case CONST_CHAR:
                stack.push(instr.operand.charAt(0));
                pc++;
                break;

            case CONST_BOOL:
                stack.push(Boolean.parseBoolean(instr.operand));
                pc++;
                break;

            case CONST_NULL:
                stack.push(null);
                pc++;
                break;

            // ── Variables ──
            case LOAD:
                if (!env.containsKey(instr.operand)) {
                    throw error("Undefined variable '" + instr.operand + "'");
                }
                stack.push(env.get(instr.operand));
                pc++;
                break;

            case STORE:
                env.put(instr.operand, stack.pop());
                pc++;
                break;

            // ── Arithmetic ──
            case ADD: {
                Object b = stack.pop();
                Object a = stack.pop();
                if (a instanceof Double && b instanceof Double) {
                    stack.push((double) a + (double) b);
                } else if (a instanceof String || b instanceof String) {
                    stack.push(stringify(a) + stringify(b));
                } else {
                    throw error("ADD requires two numbers or at least one string");
                }
                pc++;
                break;
            }
            case SUB: {
                Object b = stack.pop();
                Object a = stack.pop();
                checkNumbers("SUB", a, b);
                stack.push((double) a - (double) b);
                pc++;
                break;
            }
            case MUL: {
                Object b = stack.pop();
                Object a = stack.pop();
                checkNumbers("MUL", a, b);
                stack.push((double) a * (double) b);
                pc++;
                break;
            }
            case DIV: {
                Object b = stack.pop();
                Object a = stack.pop();
                checkNumbers("DIV", a, b);
                if ((double) b == 0) throw error("Division by zero");
                stack.push((double) a / (double) b);
                pc++;
                break;
            }

            // ── Unary ──
            case NEG: {
                Object val = stack.pop();
                if (!(val instanceof Double)) throw error("NEG requires a number");
                stack.push(-(double) val);
                pc++;
                break;
            }
            case NOT: {
                Object val = stack.pop();
                stack.push(!isTruthy(val));
                pc++;
                break;
            }

            // ── Comparison ──
            case EQ: {
                Object b = stack.pop();
                Object a = stack.pop();
                stack.push(isEqual(a, b));
                pc++;
                break;
            }
            case NEQ: {
                Object b = stack.pop();
                Object a = stack.pop();
                stack.push(!isEqual(a, b));
                pc++;
                break;
            }
            case GT: {
                Object b = stack.pop();
                Object a = stack.pop();
                checkNumbers("GT", a, b);
                stack.push((double) a > (double) b);
                pc++;
                break;
            }
            case GTE: {
                Object b = stack.pop();
                Object a = stack.pop();
                checkNumbers("GTE", a, b);
                stack.push((double) a >= (double) b);
                pc++;
                break;
            }
            case LT: {
                Object b = stack.pop();
                Object a = stack.pop();
                checkNumbers("LT", a, b);
                stack.push((double) a < (double) b);
                pc++;
                break;
            }
            case LTE: {
                Object b = stack.pop();
                Object a = stack.pop();
                checkNumbers("LTE", a, b);
                stack.push((double) a <= (double) b);
                pc++;
                break;
            }

            // ── Logical ──
            case AND: {
                Object b = stack.pop();
                Object a = stack.pop();
                stack.push(isTruthy(a) && isTruthy(b));
                pc++;
                break;
            }
            case OR: {
                Object b = stack.pop();
                Object a = stack.pop();
                stack.push(isTruthy(a) || isTruthy(b));
                pc++;
                break;
            }

            // ── Control flow ──
            case JUMP:
                pc = Integer.parseInt(instr.operand);
                break;

            case JUMP_IF_FALSE: {
                Object condition = stack.pop();
                if (!isTruthy(condition)) {
                    pc = Integer.parseInt(instr.operand);
                } else {
                    pc++;
                }
                break;
            }

            // ── I/O ──
            case PRINT:
                System.out.println(stringify(stack.pop()));
                pc++;
                break;

            // ── Arrays ──
            case MAKE_ARRAY: {
                int count = Integer.parseInt(instr.operand);
                List<Object> array = new ArrayList<>();
                // Elements were pushed left-to-right, so they're on the stack
                // with the last element on top. We need to reverse.
                Object[] temp = new Object[count];
                for (int i = count - 1; i >= 0; i--) {
                    temp[i] = stack.pop();
                }
                for (Object o : temp) {
                    array.add(o);
                }
                stack.push(array);
                pc++;
                break;
            }

            case ARRAY_LOAD: {
                Object idxVal = stack.pop();
                Object arrVal = stack.pop();
                if (!(arrVal instanceof List)) throw error("ARRAY_LOAD: not an array");
                int idx = toIndex(idxVal);
                @SuppressWarnings("unchecked")
                List<Object> list = (List<Object>) arrVal;
                if (idx < 0 || idx >= list.size()) {
                    throw error("Array index " + idx + " out of bounds (size " + list.size() + ")");
                }
                stack.push(list.get(idx));
                pc++;
                break;
            }

            case ARRAY_STORE: {
                Object idxVal = stack.pop();
                Object value = stack.pop();
                Object arrVal = env.get(instr.operand);
                if (!(arrVal instanceof List)) throw error("ARRAY_STORE: '" + instr.operand + "' is not an array");
                int idx = toIndex(idxVal);
                @SuppressWarnings("unchecked")
                List<Object> list = (List<Object>) arrVal;
                if (idx < 0 || idx >= list.size()) {
                    throw error("Array index " + idx + " out of bounds (size " + list.size() + ")");
                }
                list.set(idx, value);
                pc++;
                break;
            }

            // ── Program ──
            case HALT:
                break;

            default:
                throw error("Unknown opcode: " + instr.opCode);
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

    private int toIndex(Object value) {
        if (!(value instanceof Double)) throw error("Array index must be a number");
        return (int) (double) value;
    }

    private void checkNumbers(String op, Object a, Object b) {
        if (a instanceof Double && b instanceof Double) return;
        throw error(op + " requires two numbers");
    }

    private RuntimeException error(String message) {
        return new RuntimeException("VM error at instruction " + pc + ": " + message);
    }
}
