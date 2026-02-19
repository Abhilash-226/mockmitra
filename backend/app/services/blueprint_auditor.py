"""
Blueprint Auditor - Identifies and reports issues in blueprint YAML files

Run this script to find blueprints that need fixing:
    python -m app.services.blueprint_auditor

Issues detected:
- Missing answer_type field
- Categorical questions without answer_options
- Numerical questions without formula
- Formulas that can't be evaluated
- Unit conversion issues
"""

import os
import yaml
import math
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class IssueSeverity(str, Enum):
    ERROR = "error"      # Must fix
    WARNING = "warning"  # Should fix
    INFO = "info"        # Could fix


@dataclass
class BlueprintIssue:
    """A single issue found in a blueprint."""
    severity: IssueSeverity
    blueprint_id: str
    field: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class AuditReport:
    """Complete audit report for all blueprints."""
    total_blueprints: int
    issues: List[BlueprintIssue] = field(default_factory=list)
    blueprints_by_type: Dict[str, int] = field(default_factory=dict)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)
    
    def summary(self) -> str:
        lines = [
            "=== BLUEPRINT AUDIT REPORT ===",
            f"Total Blueprints: {self.total_blueprints}",
            f"Errors: {self.error_count}",
            f"Warnings: {self.warning_count}",
            "",
            "By Type:",
        ]
        
        for type_name, count in self.blueprints_by_type.items():
            lines.append(f"  {type_name}: {count}")
        
        if self.issues:
            lines.append("")
            lines.append("Issues Found:")
            
            # Group by blueprint
            by_blueprint: Dict[str, List[BlueprintIssue]] = {}
            for issue in self.issues:
                if issue.blueprint_id not in by_blueprint:
                    by_blueprint[issue.blueprint_id] = []
                by_blueprint[issue.blueprint_id].append(issue)
            
            for bp_id, bp_issues in list(by_blueprint.items())[:20]:
                lines.append(f"\n  {bp_id}:")
                for issue in bp_issues:
                    symbol = "❌" if issue.severity == IssueSeverity.ERROR else "⚠️"
                    lines.append(f"    {symbol} [{issue.field}] {issue.message}")
                    if issue.suggestion:
                        lines.append(f"       💡 {issue.suggestion}")
            
            if len(by_blueprint) > 20:
                lines.append(f"\n  ... and {len(by_blueprint) - 20} more blueprints with issues")
        
        return "\n".join(lines)


class BlueprintAuditor:
    """Audits blueprint YAML files for common issues."""
    
    # Keywords that suggest categorical questions
    CATEGORICAL_KEYWORDS = [
        "hybridization", "configuration", "geometry", "shape",
        "color", "nature", "type", "order", "name",
        "identify", "classify", "which compound", "which element",
    ]
    
    # Keywords that suggest coordinate questions
    COORDINATE_KEYWORDS = [
        "coordinate", "point", "vertex", "center",
        "(x, y)", "intersection", "roots",
    ]
    
    def __init__(self, blueprints_dir: Optional[str] = None):
        if blueprints_dir is None:
            # Default to backend/blueprints
            base_path = Path(__file__).parent.parent.parent
            blueprints_dir = base_path / "blueprints"
        
        self.blueprints_dir = Path(blueprints_dir)
    
    def audit_all(self) -> AuditReport:
        """Audit all blueprints in the directory."""
        report = AuditReport(total_blueprints=0)
        
        # Find all YAML files
        yaml_files = list(self.blueprints_dir.rglob("*.yaml"))
        
        for yaml_path in yaml_files:
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                
                if isinstance(content, list):
                    for bp in content:
                        if isinstance(bp, dict) and 'id' in bp:
                            report.total_blueprints += 1
                            issues = self._audit_blueprint(bp)
                            report.issues.extend(issues)
                            
                            # Track by type
                            bp_type = bp.get('answer_type', 'numeric')
                            report.blueprints_by_type[bp_type] = \
                                report.blueprints_by_type.get(bp_type, 0) + 1
                
            except Exception as e:
                report.issues.append(BlueprintIssue(
                    severity=IssueSeverity.ERROR,
                    blueprint_id=str(yaml_path),
                    field="file",
                    message=f"Failed to parse YAML: {e}",
                ))
        
        return report
    
    def _audit_blueprint(self, bp: Dict[str, Any]) -> List[BlueprintIssue]:
        """Audit a single blueprint."""
        issues = []
        bp_id = bp.get('id', 'UNKNOWN')
        
        # Check template content
        templates = bp.get('template_variants', [])
        if bp.get('template'):
            templates.append(bp.get('template'))
        template_text = ' '.join(templates).lower()
        
        # 1. Check answer_type exists and is valid
        answer_type = bp.get('answer_type', None)
        if answer_type is None:
            # Infer what it should be
            inferred = self._infer_answer_type(bp, template_text)
            issues.append(BlueprintIssue(
                severity=IssueSeverity.WARNING,
                blueprint_id=bp_id,
                field="answer_type",
                message="Missing answer_type field",
                suggestion=f"Add: answer_type: {inferred}",
            ))
            answer_type = inferred
        
        # 2. Check categorical questions have answer_options
        if answer_type in ['categorical', 'boolean']:
            answer_options = bp.get('answer_options', [])
            if not answer_options or len(answer_options) < 4:
                issues.append(BlueprintIssue(
                    severity=IssueSeverity.ERROR,
                    blueprint_id=bp_id,
                    field="answer_options",
                    message=f"Categorical question needs 4+ answer_options, has {len(answer_options)}",
                    suggestion="Add answer_options with at least 4 choices",
                ))
        
        # 3. Check numerical questions have formula
        if answer_type in ['numerical', 'numeric', None]:
            formula = bp.get('formula')
            answer_options = bp.get('answer_options', [])
            
            if not formula and not answer_options:
                # Check if it looks categorical
                if self._looks_categorical(template_text):
                    issues.append(BlueprintIssue(
                        severity=IssueSeverity.ERROR,
                        blueprint_id=bp_id,
                        field="answer_type",
                        message="Appears to be categorical but marked as numerical",
                        suggestion="Change to answer_type: categorical and add answer_options",
                    ))
                else:
                    issues.append(BlueprintIssue(
                        severity=IssueSeverity.ERROR,
                        blueprint_id=bp_id,
                        field="formula",
                        message="Numerical question has no formula",
                        suggestion="Add a formula or change to categorical with answer_options",
                    ))
            
            # 4. Check formula is evaluable
            if formula:
                can_eval, error = self._check_formula(formula, bp.get('variables', {}))
                if not can_eval:
                    issues.append(BlueprintIssue(
                        severity=IssueSeverity.WARNING,
                        blueprint_id=bp_id,
                        field="formula",
                        message=f"Formula may not evaluate: {error}",
                        suggestion="Ensure formula uses Python syntax with explicit operators",
                    ))
        
        # 5. Check for physics unit issues
        if bp.get('subject') == 'Physics':
            issues.extend(self._check_physics_units(bp))
        
        # 6. Check template has variables
        variables = bp.get('variables', {})
        for template in templates:
            vars_in_template = re.findall(r'\{(\w+)\}', template)
            for var in vars_in_template:
                if var not in variables:
                    issues.append(BlueprintIssue(
                        severity=IssueSeverity.WARNING,
                        blueprint_id=bp_id,
                        field="variables",
                        message=f"Template uses {{{var}}} but variable not defined",
                        suggestion=f"Add variable '{var}' to variables section",
                    ))
        
        return issues
    
    def _infer_answer_type(self, bp: Dict[str, Any], template_text: str) -> str:
        """Infer what answer_type should be."""
        # Check for coordinate patterns
        if any(kw in template_text for kw in self.COORDINATE_KEYWORDS):
            return "coordinate"
        
        # Check for categorical patterns
        if any(kw in template_text for kw in self.CATEGORICAL_KEYWORDS):
            return "categorical"
        
        # Check if has numeric formula
        if bp.get('formula'):
            return "numerical"
        
        # Check if has answer_options
        if bp.get('answer_options'):
            return "categorical"
        
        # Default to numerical
        return "numerical"
    
    def _looks_categorical(self, template_text: str) -> bool:
        """Check if template looks like a categorical question."""
        return any(kw in template_text for kw in self.CATEGORICAL_KEYWORDS)
    
    def _check_formula(
        self,
        formula: str,
        variables: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Check if formula can be evaluated."""
        try:
            # Build mock variable values
            mock_vars = {}
            for var_name, var_config in variables.items():
                if isinstance(var_config, dict):
                    var_type = var_config.get('type', 'integer')
                    if var_type in ['integer', 'float']:
                        range_vals = var_config.get('range', [1, 10])
                        mock_vars[var_name] = range_vals[0]
                    elif var_type == 'choice':
                        values = var_config.get('values', [1])
                        first_val = values[0] if values else 1
                        if isinstance(first_val, dict):
                            mock_vars.update(first_val)
                        else:
                            mock_vars[var_name] = first_val
                else:
                    mock_vars[var_name] = var_config
            
            # Build eval context
            eval_context = {
                'math': math,
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'log': math.log,
                'log10': math.log10,
                'exp': math.exp,
                'pi': math.pi,
                'e': math.e,
                'abs': abs,
                'h': 6.626e-34,  # Planck's constant
                'm': 9.109e-31,  # Electron mass
                'c': 3e8,        # Speed of light
                **mock_vars
            }
            
            # Normalize formula
            test_formula = formula
            if '=' in test_formula and '==' not in test_formula:
                parts = test_formula.split('=')
                if len(parts) == 2:
                    test_formula = parts[1].strip()
            
            # Try to eval
            eval(test_formula, {"__builtins__": {}}, eval_context)
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _check_physics_units(self, bp: Dict[str, Any]) -> List[BlueprintIssue]:
        """Check for common physics unit issues."""
        issues = []
        bp_id = bp.get('id', 'UNKNOWN')
        formula = bp.get('formula', '')
        answer_unit = bp.get('answer_unit', '')
        concept = bp.get('concept', '').lower()
        
        # De Broglie wavelength should output in Å or nm
        if 'de broglie' in concept or 'wavelength' in concept:
            if answer_unit in ['Å', 'angstrom', 'nm']:
                # Check if formula has unit conversion
                if '1e10' not in formula and '1e9' not in formula and '* 10' not in formula:
                    issues.append(BlueprintIssue(
                        severity=IssueSeverity.WARNING,
                        blueprint_id=bp_id,
                        field="formula",
                        message=f"Wavelength formula may need unit conversion for {answer_unit}",
                        suggestion="Add * 1e10 for Å or * 1e9 for nm",
                    ))
        
        return issues


def audit_blueprints(blueprints_dir: Optional[str] = None) -> AuditReport:
    """Convenience function to audit blueprints."""
    auditor = BlueprintAuditor(blueprints_dir)
    return auditor.audit_all()


if __name__ == "__main__":
    # Run audit
    report = audit_blueprints()
    print(report.summary())
    
    # Exit with error code if issues found
    import sys
    sys.exit(1 if report.error_count > 0 else 0)
