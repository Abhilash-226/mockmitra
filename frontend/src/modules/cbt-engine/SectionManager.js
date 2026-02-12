/**
 * SectionManager - Handles multi-section exam logic
 *
 * Responsibilities:
 * - Section switching rules
 * - Section time limits (if applicable)
 * - Section-wise question grouping
 */

class SectionManager {
  constructor(sections = []) {
    this.sections = sections;
    this.currentSectionIndex = 0;
  }

  getCurrentSection() {
    return this.sections[this.currentSectionIndex] || null;
  }

  canSwitchToSection(targetIndex) {
    // Check if section switching is allowed
    return targetIndex >= 0 && targetIndex < this.sections.length;
  }

  switchToSection(targetIndex) {
    if (this.canSwitchToSection(targetIndex)) {
      this.currentSectionIndex = targetIndex;
      return true;
    }
    return false;
  }

  getSectionQuestions(sectionIndex) {
    const section = this.sections[sectionIndex];
    return section ? section.questions : [];
  }

  getTotalSections() {
    return this.sections.length;
  }
}

export default SectionManager;
