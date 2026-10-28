module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:vue/recommended",
  ],
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
  rules: {
    // Vue
    "vue/multi-word-component-names": "off",
    "vue/no-v-html": "warn",

    // General
    // console.error/warn are intentional production diagnostics (global error
    // handler, API failure logging, a11y warnings). Only debug-level residue
    // (log/info/debug/...) stays forbidden.
    "no-console": ["warn", { allow: ["error", "warn"] }],
    "no-debugger": "warn",
    "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "prefer-const": "warn",
    "no-var": "warn",
    "no-empty": "warn",
  },
};
