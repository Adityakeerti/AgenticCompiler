import lexer.Lexer;
import lexer.Token;
import parser.Parser;
import ast.Stmt;
import semantic.SemanticAnalyzer;
import interpreter.Interpreter;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;

public class Main {
    public static void main(String[] args) {
        // Determine source file
        String filename;
        if (args.length >= 1) {
            filename = args[0];
        } else {
            filename = "test.cpy";
        }

        // Read source
        String source;
        try {
            source = new String(Files.readAllBytes(Paths.get(filename)));
        } catch (IOException e) {
            System.err.println("Error: Could not read file '" + filename + "'");
            System.exit(1);
            return;
        }

        System.out.println("=== CPY Compiler ===");
        System.out.println("Running: " + filename);
        System.out.println();

        try {
            // 1. Lexing
            Lexer lexer = new Lexer(source);
            List<Token> tokens = lexer.scanTokens();

            // 2. Parsing
            Parser parser = new Parser(tokens);
            List<Stmt> statements = parser.parse();

            // 3. Semantic Analysis
            SemanticAnalyzer analyzer = new SemanticAnalyzer();
            analyzer.analyze(statements);

            // 4. Interpretation
            Interpreter interpreter = new Interpreter();
            interpreter.interpret(statements);

        } catch (RuntimeException e) {
            System.err.println(e.getMessage());
            System.exit(1);
        }
    }
}
