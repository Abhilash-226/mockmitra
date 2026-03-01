import "katex/dist/katex.min.css";
import Latex from "react-latex-next";

// LaTeX command words that commonly lose their backslash due to JSON parsing issues.
// These appear inside $...$ regions without a leading backslash.
const LATEX_COMMANDS = [
  // Greek letters (most common)
  'alpha','beta','gamma','delta','epsilon','zeta','eta','theta','iota','kappa',
  'lambda','mu','nu','xi','pi','rho','sigma','tau','upsilon','phi','chi','psi','omega',
  'Gamma','Delta','Theta','Lambda','Xi','Pi','Sigma','Phi','Psi','Omega',
  // Math operators
  'frac','sqrt','sum','prod','int','lim','infty','partial','nabla',
  'times','div','cdot','pm','mp','leq','geq','neq','approx','equiv','sim',
  'in','notin','subset','supset','cup','cap','emptyset','forall','exists',
  'rightarrow','leftarrow','Rightarrow','Leftarrow','leftrightarrow',
  'to','gets','mapsto','land','lor','lnot','neg',
  // Brackets
  'left','right','langle','rangle','lceil','rceil','lfloor','rfloor',
  // Formatting
  'text','mathrm','mathbf','mathit','mathbb','mathcal','operatorname',
  'begin','end','bmatrix','pmatrix','vmatrix','matrix',
  // Trig/functions
  'sin','cos','tan','sec','csc','cot','arcsin','arccos','arctan',
  'log','ln','exp','max','min','gcd','lcm','det','tr','rank','adj',
  // Spaces and misc
  'quad','qquad','hspace','vspace','cdots','ldots','vdots','ddots',
  'hat','vec','bar','dot','ddot','tilde','overline','underline',
];

const LATEX_RE = new RegExp(
  '(?<![\\\\a-zA-Z])(' + LATEX_COMMANDS.join('|') + ')(?=[^a-zA-Z]|$)',
  'g'
);

/**
 * Sanitizes AI-generated text that may have LaTeX commands missing their backslash.
 * Only replaces inside $...$ math regions to avoid false positives in plain text.
 */
export function sanitizeLatex(text) {
  if (!text) return text;
  
  let processed = String(text);
  
  // 1. If no $ delimiters are present, try to find and wrap math commands surgically
  if (!processed.includes('$')) {
    // Add backslashes where missing first (Smartly)
    processed = processed.replace(LATEX_RE, (m, p1, offset, string) => {
        const before = string.slice(0, offset);
        if (before.endsWith('{')) return m;
        return '\\' + m;
    });
    
    // 1b. Surgical Wrap: Find sequences of LaTeX commands, math ops, and numbers
    
    // Heuristic: If it contains matrix delimiters (\\ or &), wrap the whole thing 
    if (processed.includes('\\\\') || processed.includes(' & ')) {
      return `$${processed}$`;
    }

    // Otherwise, wrap individual commands and their arguments
    const MATH_BLOCK_RE = /(\\[a-zA-Z]+({[^{}]*})*|[=<>+\-*/^_{}]+|(?:\d+[\d,]*\d|\d+))/g;
    
    // We only want to wrap if it actually looks like math.
    // If it's just a plain number in a sentence, we might not want to wrap it, 
    // but usually in these papers even numbers are better in math mode for font consistency.
    // However, to be safe, only wrap if there's at least one backslash or comparison op.
    if (processed.includes('\\') || /[=<>^_]/.test(processed)) {
        let surgicallyWrapped = processed.replace(MATH_BLOCK_RE, (match) => {
            // Don't wrap if it's just a single digit/number and no actual math context
            if (/^\d+$/.test(match) && !processed.includes('\\') && !/[=<>^_]/.test(processed)) {
                return match;
            }
            return `$${match}$`;
        });
        
        // Merge adjacent $ blocks: $a$$+$$b$ -> $a+b$
        return surgicallyWrapped.replace(/\$\$\$/g, '$').replace(/\$\$/g, '');
    }
    
    return processed;
  }

  // 2. If $ are present, fix backslashes inside regions
  return processed.replace(/\$([^$]+)\$/g, (match, inner) => {
    // Only add backslash if NOT already there AND not part of a word inside {}
    // (like \begin{bmatrix})
    const fixed = inner.replace(LATEX_RE, (m, p1, offset, string) => {
        // Lookbehind: check if preceded by '{'
        const before = string.slice(0, offset);
        if (before.endsWith('{')) return m;
        return '\\' + m;
    });
    return '$' + fixed + '$';
  });
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
          <Latex>{part}</Latex>
          {i < parts.length - 1 && <br />}
        </span>
      ))}
    </>
  );
}
