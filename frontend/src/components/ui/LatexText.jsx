import "katex/dist/katex.min.css";
import Latex from "react-latex-next";

// LaTeX command words that commonly lose their backslash due to JSON parsing issues.
// These appear inside $...$ regions without a leading backslash.
const LATEX_COMMANDS = [
  // Greek letters (most common)
  "alpha",
  "beta",
  "gamma",
  "delta",
  "epsilon",
  "zeta",
  "eta",
  "theta",
  "iota",
  "kappa",
  "lambda",
  "mu",
  "nu",
  "xi",
  "pi",
  "rho",
  "sigma",
  "tau",
  "upsilon",
  "phi",
  "chi",
  "psi",
  "omega",
  "Gamma",
  "Delta",
  "Theta",
  "Lambda",
  "Xi",
  "Pi",
  "Sigma",
  "Phi",
  "Psi",
  "Omega",
  // Math operators
  "frac",
  "sqrt",
  "sum",
  "prod",
  "int",
  "lim",
  "infty",
  "partial",
  "nabla",
  "times",
  "div",
  "cdot",
  "pm",
  "mp",
  "leq",
  "geq",
  "neq",
  "approx",
  "equiv",
  "sim",
  "in",
  "notin",
  "subset",
  "supset",
  "cup",
  "cap",
  "emptyset",
  "forall",
  "exists",
  "rightarrow",
  "leftarrow",
  "Rightarrow",
  "Leftarrow",
  "leftrightarrow",
  "to",
  "gets",
  "mapsto",
  "land",
  "lor",
  "lnot",
  "neg",
  // Brackets
  "left",
  "right",
  "langle",
  "rangle",
  "lceil",
  "rceil",
  "lfloor",
  "rfloor",
  // Formatting
  "text",
  "mathrm",
  "mathbf",
  "mathit",
  "mathbb",
  "mathcal",
  "operatorname",
  "begin",
  "end",
  "bmatrix",
  "pmatrix",
  "vmatrix",
  "matrix",
  // Trig/functions
  "sin",
  "cos",
  "tan",
  "sec",
  "csc",
  "cot",
  "arcsin",
  "arccos",
  "arctan",
  "log",
  "ln",
  "exp",
  "max",
  "min",
  "gcd",
  "lcm",
  "det",
  "tr",
  "rank",
  "adj",
  // Spaces and misc
  "quad",
  "qquad",
  "hspace",
  "vspace",
  "cdots",
  "ldots",
  "vdots",
  "ddots",
  "hat",
  "vec",
  "bar",
  "dot",
  "ddot",
  "tilde",
  "overline",
  "underline",
];

const LATEX_RE = new RegExp(
  "(?<![\\\\a-zA-Z])(" + LATEX_COMMANDS.join("|") + ")(?=[^a-zA-Z]|$)",
  "g",
);

// Some API payloads can arrive double-escaped in production (e.g., "\\\\lim").
// Collapse repeated backslashes before known commands so KaTeX can parse them.
const DOUBLE_ESCAPED_COMMAND_RE = new RegExp(
  "\\\\\\\\+(?=(" + LATEX_COMMANDS.join("|") + ")(?=[^a-zA-Z]|$))",
  "g",
);

// Wrap full LaTeX command spans including common arguments/superscripts/subscripts.
const COMMAND_SPAN_RE =
  /(\\[a-zA-Z]+(?:\s*(?:\{[^{}]*\}|\[[^\[\]]*\]|_\{[^{}]*\}|\^\{[^{}]*\}|_[A-Za-z0-9]|\^[A-Za-z0-9]))*)/g;

// Wrap variables/functions that use superscripts/subscripts without backslash commands.
const SUBSUP_SPAN_RE =
  /(\b[A-Za-z][A-Za-z0-9]*(?:\s*(?:_\{[^{}]*\}|\^\{[^{}]*\}|_[A-Za-z0-9]|\^[A-Za-z0-9]))+)/g;

const OUTSIDE_MATH_REPLACEMENTS = [
  [/\\times/g, "×"],
  [/\\cdot/g, "·"],
  [/\\to|\\rightarrow/g, "→"],
  [/\\leftarrow/g, "←"],
  [/\\pm/g, "±"],
  [/\\mu/g, "μ"],
  [/\\rho/g, "ρ"],
  [/\\pi/g, "π"],
  [/\\theta/g, "θ"],
  [/\\alpha/g, "α"],
  [/\\beta/g, "β"],
  [/\\gamma/g, "γ"],
  [/\\lambda/g, "λ"],
  [/\\omega/g, "ω"],
  [/\\neq/g, "≠"],
  [/\\leq/g, "≤"],
  [/\\geq/g, "≥"],
  [/\\bar\s+/g, ""],
  [/\\_/g, "_"],
];

function normalizeOutsideMath(segment) {
  let value = segment;
  for (const [pattern, replacement] of OUTSIDE_MATH_REPLACEMENTS) {
    value = value.replace(pattern, replacement);
  }
  return value;
}

function ensureBalancedDollarPairs(text) {
  let escaped = false;
  let dollarCount = 0;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (ch === "\\") {
      escaped = true;
      continue;
    }
    if (ch === "$") dollarCount += 1;
  }

  if (dollarCount % 2 === 0) return text;
  const lastDollar = text.lastIndexOf("$");
  if (lastDollar === -1) return text;
  return `${text.slice(0, lastDollar)}\\$${text.slice(lastDollar + 1)}`;
}

function fixMathBlock(block) {
  return block.replace(/\$([^$]+)\$/g, (match, inner) => {
    const fixed = inner.replace(LATEX_RE, (command, _p1, offset, full) => {
      const before = full.slice(0, offset);
      if (before.endsWith("{")) return command;
      return "\\" + command;
    });
    return "$" + fixed + "$";
  });
}

/**
 * Sanitizes AI-generated text that may have LaTeX commands missing their backslash.
 * Only replaces inside $...$ math regions to avoid false positives in plain text.
 */
export function sanitizeLatex(text) {
  if (!text) return text;

  let processed = String(text);
  processed = processed.replace(DOUBLE_ESCAPED_COMMAND_RE, "\\");
  processed = processed.replace(/\\\$/g, "$");
  processed = ensureBalancedDollarPairs(processed);

  // 1. If no $ delimiters are present, try to find and wrap math commands surgically
  if (!processed.includes("$")) {
    // Add backslashes where missing first (Smartly)
    processed = processed.replace(LATEX_RE, (m, p1, offset, string) => {
      const before = string.slice(0, offset);
      if (before.endsWith("{")) return m;
      return "\\" + m;
    });

    // 1b. Surgical Wrap: Find sequences of LaTeX commands, math ops, and numbers

    // Heuristic: If it contains matrix delimiters (\\ or &), wrap the whole thing
    if (processed.includes("\\\\") || processed.includes(" & ")) {
      return `$${processed}$`;
    }

    // Safer fallback: wrap only likely math spans.
    // This avoids malformed expressions caused by token-level wrapping.
    if (processed.includes("\\") || /[=<>^_]/.test(processed)) {
      const wrappedCommands = processed.replace(COMMAND_SPAN_RE, (match) => {
        const trimmed = match.trim();
        return trimmed ? `$${trimmed}$` : match;
      });

      const wrappedSubSup = wrappedCommands.replace(SUBSUP_SPAN_RE, (match) => {
        // Do not double-wrap already wrapped spans.
        if (match.startsWith("$") && match.endsWith("$")) return match;
        const trimmed = match.trim();
        return trimmed ? `$${trimmed}$` : match;
      });

      return wrappedSubSup;
    }

    return normalizeOutsideMath(processed);
  }

  // 2. If $ are present, process math and non-math parts independently
  const parts = processed.split(/(\$[^$]*\$)/g);
  return parts
    .map((part) => {
      if (!part) return part;
      if (part.startsWith("$") && part.endsWith("$")) {
        return fixMathBlock(part);
      }
      return normalizeOutsideMath(part);
    })
    .join("");
}

/**
 * Renders text with LaTeX, preserving \n as line breaks.
 * Handles both actual newlines and literal \n sequences.
 */
export default function LatexText({ children }) {
  if (!children) return null;
  const sanitized = sanitizeLatex(String(children));
  // Split only on actual newline characters.
  // We removed |\\n because it was breaking LaTeX commands like \neq, \nu, \nabla
  const parts = sanitized.split(/\n/);
  return (
    <>
      {parts.map((part, i) => (
        <span key={i}>
          <Latex strict="ignore" throwOnError={false}>
            {part}
          </Latex>
          {i < parts.length - 1 && <br />}
        </span>
      ))}
    </>
  );
}
