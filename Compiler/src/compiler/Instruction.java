package compiler;

/**
 * A single bytecode instruction: an opcode with an optional operand.
 */
public class Instruction {
    public final OpCode opCode;
    public String operand;   // mutable for jump patching

    public Instruction(OpCode opCode) {
        this.opCode = opCode;
        this.operand = null;
    }

    public Instruction(OpCode opCode, String operand) {
        this.opCode = opCode;
        this.operand = operand;
    }

    @Override
    public String toString() {
        return operand != null ? opCode + " " + operand : opCode.toString();
    }
}
