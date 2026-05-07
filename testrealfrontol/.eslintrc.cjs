module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:vue/vue3-recommended",
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
    "no-console": "warn",
    "no-debugger": "warn",
    "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "prefer-const": "warn",
    "no-var": "error",
  },
};
