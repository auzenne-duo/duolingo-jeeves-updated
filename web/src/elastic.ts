import * as lucene from "lucene";

interface FieldExpression extends lucene.FieldExpression {
  /** Can be used to traverse the tree in opposite direction. */
  parent: NodeExpression;
}

interface NodeExpression extends lucene.NodeExpression {
  /** Can be used to traverse the tree in opposite direction. */
  parent?: NodeExpression;
}

const buildParenthesizedNode = (
  values: string[],
  operator = "OR",
): lucene.Node => {
  if (!values.length) {
    throw Error("Cannot build parenthesized node for empty array.");
  }
  if (values.length === 1) {
    return {
      field: "<implicit>",
      term: escapeTerm(values[0]),
    };
  }
  return {
    left: buildParenthesizedNode(values.slice(0, 1), operator),
    operator,
    right: buildParenthesizedNode(values.slice(1), operator),
  };
};

/**
 * Escapes a string for usage in an Elasticsearch query.
 *
 * @param term The search term to escape.
 * @param quoted If true, spaces won't be escaped.
 *
 * @see {@link https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html#_reserved_characters}
 */
export const escapeTerm = (term: string, quoted = false) => {
  term = term
    .replace(/([+\-=!(){}[\]^"~*?:\\/]|&&|\|\|)/g, "\\$1")
    // Remove characters that cannot be escaped.
    .replace(/[<>]/g, "");
  if (!quoted) {
    // Escape spaces.
    term = term.replace(/ /g, "\\ ");
  }
  return term;
};

/** Finds an area by name, ignoring case. */
const getArea = (name: string, areas: JSONAPI.Area[]) =>
  areas.find(a => a.area_name.toLowerCase() === name.toLowerCase());

/** Gets all features for an area or team. */
const getFeatures = (entity: JSONAPI.Area | JSONAPI.Team) =>
  "area_name" in entity
    ? entity.teams.flatMap(t => t.features)
    : entity.features;

/** Finds a team by name, ignoring case. */
const getTeam = (name: string, areas: JSONAPI.Area[]) =>
  areas
    .flatMap(a => a.teams)
    .find(t => t.team_name.toLowerCase() === name.toLowerCase());

const isFieldExpression = (node: lucene.Node): node is lucene.FieldExpression =>
  "term" in node;

const isNodeExpression = (node: lucene.Node): node is lucene.NodeExpression =>
  "left" in node;

/**
 * Removes the given branch of a node and recursively traverses
 * the tree to remove any nodes that now only have empty children.
 */
const removeNode = (node: NodeExpression, branch: "left" | "right") => {
  delete node[branch];
  delete node.operator;
  if (node.parent && !node.left && !node.right) {
    removeNode(node.parent, node === node.parent.left ? "left" : "right");
  }
};

/**
 * Transforms a user-supplied query to a format that can be processed
 * by Elasticsearch. Specifically, this replaces area and team fields
 * with their feature equivalents as we don't currently store areas
 * and teams directly.
 *
 * @param query A user-supplied Elasticsearch query string.
 * @param areas An array of organization areas, teams, and their features.
 *
 * @see {@link https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html#query-string-syntax}
 */
export const transformQuery = (query: string, areas: JSONAPI.Area[]) => {
  const ast = lucene.parse(query);
  for (const { field, node } of visit(ast)) {
    if (field === "area" || field === "team") {
      const branch = node === node.parent.left ? "left" : "right";
      const entity = (field === "area" ? getArea : getTeam)(
        node.quoted ? node.term : unescapeSpaces(node.term),
        areas,
      );
      const features = entity ? getFeatures(entity) : undefined;
      if (features?.length === 1) {
        // Replace the field node with another field node expression.
        node.parent[branch] = {
          field: "feature",
          term: escapeTerm(features[0]),
        };
      } else if (features?.length) {
        // Replace the field node with a parenthesized node expression.
        node.parent[branch] = {
          field: "feature",
          parenthesized: true,
          ...buildParenthesizedNode(features),
        };
        // Only unset parenthesized if the parent node is a field group.
        // Parenthesis might also be used for regular grouping.
        if (node.parent.field) {
          delete node.parent.field;
          delete node.parent.parenthesized;
        }
      } else {
        // Remove the field node. Don't move branches as that would break the generator;
        // AST serialization still works if a node expression just has a right branch
        // or no children at all.
        removeNode(node.parent, branch);
      }
    }
  }
  return lucene.toString(ast);
};

/** Unescapes spaces in an unquoted term. */
export const unescapeSpaces = (term: string) => term.replace(/\\ /g, " ");

/**
 * Visits each node of a Lucene AST and returns all field expressions.
 * Parenthesized field groups are returned as individual field expressions.
 *
 * @see {@link https://github.com/thoward/lucene-query-parser.js/wiki}
 * @see {@link https://github.com/bripkens/lucene}
 */
function* visit(
  node: lucene.NodeExpression,
  /** The field name that identifies a parenthesized field group. */
  context = node.field,
): Generator<{
  field: string;
  node: FieldExpression;
}> {
  for (const branch of ["left", "right"] as const) {
    if (node[branch]) {
      const child: FieldExpression | NodeExpression = {
        ...node[branch],
        parent: node,
      };
      // Replace the original node to allow for reference comparisons.
      node[branch] = child;
      if (isFieldExpression(child)) {
        yield {
          field:
            child.field === "<implicit>" && context ? context : child.field,
          node: child,
        };
      } else if (isNodeExpression(child)) {
        yield* visit(child, context);
      }
    }
  }
}
