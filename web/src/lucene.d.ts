/**
 * @see {@link https://github.com/bripkens/lucene}
 */
declare module "lucene" {
  interface FieldExpression {
    field: string;
    term: string;
    prefix?: string | null;
    boost?: number | null;
    similarity?: number | null;
    proximity?: number | null;
    quoted?: boolean;
    regex?: boolean;
  }

  interface NodeExpression {
    field?: string;
    left?: FieldExpression | NodeExpression;
    operator?: string;
    parenthesized?: boolean;
    right?: FieldExpression | NodeExpression;
  }

  type Node = FieldExpression | NodeExpression;

  export function parse(query: string): NodeExpression;

  export function toString(ast: NodeExpression): string;
}
