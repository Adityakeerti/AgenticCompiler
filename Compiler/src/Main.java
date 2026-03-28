import lexer.Lexer;
import lexer.Token;
import parser.Parser;
import ast.Stmt;
import semantic.SemanticAnalyzer;
import compiler.BytecodeCompiler;
import compiler.BytecodeWriter;
import compiler.BytecodeReader;
import compiler.Instruction;
import vm.VM;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;

public class Main {
    public static void main(String[] args) {
        if (args.length == 0) {
            printUsage();
            System.exit(1);
            return;
        }

        String command = args[0];

        switch (command) {
            case "compile":
                if (args.length < 2) { System.err.println("Usage: cpy compile <file.cpy>"); System.exit(1); }
                compile(args[1]);
                break;

            case "run":
                if (args.length < 2) { System.err.println("Usage: cpy run <file.cpyc>"); System.exit(1); }
                run(args[1]);
                break;

            default:
                System.err.println("Unknown command: " + command);
                printUsage();
                System.exit(1);
                break;
        }
    }

    // ── Compile: .cpy → .cpyc ──────────────────────────────

    private static void compile(String sourceFile) {
        String source = readFile(sourceFile);

        try {
            // 1. Lex
            List<Token> tokens = new Lexer(source).scanTokens();

            // 2. Parse
            List<Stmt> stmts = new Parser(tokens).parse();

            // 3. Semantic check
            new SemanticAnalyzer().analyze(stmts);

            // 4. Compile to bytecode
            List<Instruction> bytecode = new BytecodeCompiler().compile(stmts);

            // 5. Write .cpyc file
            String outFile = sourceFile.replaceAll("\\.cpy$", ".cpyc");
            BytecodeWriter.write(bytecode, outFile);

            System.out.println("Compiled: " + sourceFile + " -> " + outFile);
            System.out.println(bytecode.size() + " instructions generated.");

        } catch (RuntimeException e) {
            System.err.println(e.getMessage());
            System.exit(1);
        } catch (IOException e) {
            System.err.println("Error writing bytecode: " + e.getMessage());
            System.exit(1);
        }
    }

    // ── Run: execute .cpyc bytecode ─────────────────────────

    private static void run(String bytecodeFile) {
        try {
            List<Instruction> bytecode = BytecodeReader.read(bytecodeFile);
            new VM(bytecode).run();

        } catch (IOException e) {
            System.err.println("Error reading bytecode: " + e.getMessage());
            System.exit(1);
        } catch (RuntimeException e) {
            System.err.println(e.getMessage());
            System.exit(1);
        }
    }

    // ── Helpers ─────────────────────────────────────────────

    private static String readFile(String filename) {
        try {
            return new String(Files.readAllBytes(Paths.get(filename)));
        } catch (IOException e) {
            System.err.println("Error: Could not read file '" + filename + "'");
            System.exit(1);
            return "";
        }
    }

    private static void printUsage() {
        System.out.println("=== CPY Compiler ===");
        System.out.println("Usage:");
        System.out.println("  java -cp out Main compile <file.cpy>   Compile to bytecode");
        System.out.println("  java -cp out Main run <file.cpyc>      Execute bytecode");
    }
}
