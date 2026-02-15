package ast;

/**
 * Literal value node — numbers and strings.
 * The value is stored as a generic Object (Double for numbers, String for strings).
 */
public class Literal extends Expr {
    public final Object value;

    public Literal(Object value) {
        this.value = value;
    }
}
