import jsxA11y from "eslint-plugin-jsx-a11y";
import tseslint from "typescript-eslint";

// 접근성(jsx-a11y) 규칙만 검사한다.
// typescript-eslint 는 파서로만 쓴다 — .tsx 의 타입 문법을 읽기 위한 것이고, 규칙은 켜지 않는다.
export default [
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
    },
  },
  {
    ...jsxA11y.flatConfigs.recommended,
    files: ["src/**/*.tsx"],
  },
];
