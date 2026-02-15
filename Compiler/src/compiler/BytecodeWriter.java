package compiler;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.util.List;

/**
 * Serializes compiled bytecode instructions to a .cpyc file.
 *
 * Format (text-based, one instruction per line):
 *   Line 1:  #CPY_BYTECODE v1.0
 *   Line N:  OPCODE
 *         or OPCODE <operand>
 *         or OPCODE "string with spaces"
 */
public class BytecodeWriter {

    public static void write(List<Instruction> instructions, String filename) throws IOException {
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(filename))) {
            writer.write("#CPY_BYTECODE v1.0");
            writer.newLine();

            for (Instruction instr : instructions) {
                if (instr.operand == null) {
                    writer.write(instr.opCode.name());
                } else if (instr.opCode == OpCode.CONST_STR) {
                    // Strings are quoted to preserve spaces
                    writer.write(instr.opCode.name() + " \"" + escapeString(instr.operand) + "\"");
                } else {
                    writer.write(instr.opCode.name() + " " + instr.operand);
                }
                writer.newLine();
            }
        }
    }

    private static String escapeString(String s) {
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}
