declare module "classnames" {
  import { ClassNamesFn } from "classnames/types";

  const cn: ClassNamesFn;

  // Rename the default export from classNames to cn
  // to match what's used in the code.
  export default cn;
}
