import { resolve } from "path";

import type { Config } from "@jest/types";

const config: Config.InitialOptions = {
  globals: {
    "ts-jest": {
      tsconfig: "<rootDir>/../tsconfig.test.json",
    },
  },
  // Prefer .ts and .tsx files in import statements without a file extension,
  // in case JavaScript equivalents have been emitted by TypeScript.
  moduleFileExtensions: ["ts", "tsx", "js", "json"],
  preset: "ts-jest",
  rootDir: resolve(__dirname, "../src"),
  // Exclude .js and .jsx files in case these have been emitted by TypeScript.
  // See: https://jestjs.io/docs/en/configuration#testregex-string--arraystring
  testRegex: "((\\.|/)(test|spec))\\.tsx?$",
};

module.exports = config;
