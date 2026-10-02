/**
 * Built-in reading stylesheet shipped inside every exported EPUB package.
 * The artifact is a self-contained ZIP, so the CSS travels with it and each
 * chapter links to it; readers may still override these declarations with
 * their own typography. The font stack starts with Songti/SimSun and degrades
 * to the generic serif family, and the paragraph indent mirrors the DOCX
 * two-character first-line indent so both formats read alike.
 */
export const EPUB_STYLESHEET_ID = "reading-styles";
export const EPUB_STYLESHEET_HREF = "styles/reading.css";

export const EPUB_READING_CSS = [
  '@charset "utf-8";',
  'body { font-family: "Songti SC", "SimSun", "Source Han Serif SC", "Noto Serif CJK SC", serif; line-height: 1.75; margin: 0 5%; text-align: justify; }',
  "h1 { font-size: 1.4em; font-weight: 600; margin: 1.2em 0 1.6em; text-align: center; text-indent: 0; }",
  "p { margin: 0; text-indent: 2em; }",
  "p.image-placeholder { color: #666666; font-size: 0.9em; text-align: center; text-indent: 0; }",
  "pre { background: #f5f5f5; font-size: 0.9em; line-height: 1.5; margin: 0.8em 0; padding: 0.6em; text-indent: 0; white-space: pre-wrap; }",
  'code { font-family: "Courier New", monospace; }',
  "",
].join("\n");
