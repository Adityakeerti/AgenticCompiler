package compiler;

/**
 * Bytecode instruction set for the CPY virtual machine.
 * Stack-based architecture — most instructions operate on the operand stack.
 */
public enum OpCode {
    // Constants
    CONST_NUM,      // push number:      operand = "3.14"
    CONST_STR,      // push string:      operand = "hello"
    CONST_CHAR,     // push char:        operand = "A"
    CONST_BOOL,     // push boolean:     operand = "true" / "false"
    CONST_NULL,     // push null

    // Variables
    LOAD,           // push variable:    operand = variable name
    STORE,          // pop into variable: operand = variable name

    // Arithmetic (pop 2, push result)
    ADD,
    SUB,
    MUL,
    DIV,

    // Unary
    NEG,            // negate top of stack
    NOT,            // logical not

    // Comparison (pop 2, push boolean)
    EQ,
    NEQ,
    GT,
    GTE,
    LT,
    LTE,

    // Logical (pop 2, push boolean)
    AND,
    OR,

    // Control flow
    JUMP,           // unconditional:    operand = target instruction index
    JUMP_IF_FALSE,  // conditional:      operand = target instruction index

    // I/O
    PRINT,          // pop and print to stdout

    // Arrays
    MAKE_ARRAY,     // operand = element count; pops N elements, pushes array
    ARRAY_LOAD,     // pop index, pop array → push array[index]
    ARRAY_STORE,    // pop index, pop value; operand = var name → var[index]=value

    // Program
    HALT            // stop execution
}
