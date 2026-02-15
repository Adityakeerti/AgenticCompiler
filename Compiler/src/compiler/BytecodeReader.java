package compiler;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * Deserializes a .cpyc bytecode file back into a list of Instructions.
 */
public class BytecodeReader {

    public static List<Instruction> read(String filename) throws IOException {
        List<Instruction> instructions = new ArrayList<>();

        try (BufferedReader reader = new BufferedReader(new FileReader(filename))) {
            String line = reader.readLine();

            // Validate header
            if (line == null || !line.startsWith("#CPY_BYTECODE")) {
                throw new IOException("Invalid bytecode file: missing header");
            }

            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty()) continue;

                int spaceIdx = line.indexOf(' ');
                if (spaceIdx == -1) {
                    // No operand
                    OpCode op = OpCode.valueOf(line);
                    instructions.add(new Instruction(op));
                } else {
                    String opName = line.substring(0, spaceIdx);
                    String operand = line.substring(spaceIdx + 1);
                    OpCode op = OpCode.valueOf(opName);

                    // Strings are quoted — strip quotes and unescape
                    if (op == OpCode.CONST_STR) {
                        operand = operand.substring(1, operand.length() - 1); // remove quotes
                        operand = unescapeString(operand);
                    }

                    instructions.add(new Instruction(op, operand));
                }
            }
        }

        return instructions;
    }

    private static String unescapeString(String s) {
        return s.replace("\\n", "\n")
                .replace("\\r", "\r")
                .replace("\\t", "\t")
                .replace("\\\"", "\"")
                .replace("\\\\", "\\");
    }
}
