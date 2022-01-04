module.exports = {
  extends: ["duolingo"],
  parserOptions: {
    project: "tsconfig.eslint.json",
  },
  rules: {
    // This seems to give false positives.
    "@typescript-eslint/no-confusing-void-expression": "off",
    "react/jsx-no-literals": "off",
  },
};
