import yaml
import sys
import re
import os

# Mapping from (Old Section, Old Topic) to (New Section, New Topic)
MAPPING = {
    # Mathematics
    ("Algebra", "Functions"): ("Algebra", "functions"),
    ("Algebra", "Matrices"): ("Algebra", "matrices"),
    ("Algebra", "Complex Numbers"): ("Algebra", "complex_numbers"),
    ("Algebra", "Theory of Equations"): ("Algebra", "theory_of_equations"),
    ("Algebra", "Quadratic Expressions"): ("Algebra", "quadratic_expressions"),
    ("Algebra", "Binomial Theorem"): ("Algebra", "binomial_theorem"),
    ("Algebra", "Permutations and Combinations"): ("Algebra", "permutations_and_combinations"),
    ("Algebra", "De Moivre's Theorem"): ("Algebra", "de_moivres_theorem"),
    ("Algebra", "Partial Fractions"): ("Algebra", "partial_fractions"),
    ("Algebra", "Mathematical Induction"): ("Algebra", "mathematical_induction"),
    
    ("Trigonometry", "Trigonometric Functions"): ("Trigonometry", "trigonometric_ratios_up_to_transformations"),
    ("Trigonometry", "Trigonometric transformations"): ("Trigonometry", "trigonometric_ratios_up_to_transformations"),
    ("Trigonometry", "Trigonometric Transformations"): ("Trigonometry", "trigonometric_ratios_up_to_transformations"),
    ("Trigonometry", "Inverse Trigonometric Functions"): ("Trigonometry", "inverse_trigonometric_functions"),
    ("Trigonometry", "Inverse Hyperbolic Functions"): ("Trigonometry", "hyperbolic_functions"),
    ("Trigonometry", "Hyperbolic Functions"): ("Trigonometry", "hyperbolic_functions"),
    ("Trigonometry", "Properties of Triangles"): ("Trigonometry", "properties_of_triangles"),
    ("Trigonometry", "Trigonometric Equations"): ("Trigonometry", "trigonometric_equations"),

    ("Coordinate Geometry", "Locus"): ("Coordinate Geometry", "locus"),
    ("Coordinate Geometry", "Straight Lines"): ("Coordinate Geometry", "straight_line"),
    ("Coordinate Geometry", "Straight Line"): ("Coordinate Geometry", "straight_line"),
    ("Coordinate Geometry", "Transformation of Axes"): ("Coordinate Geometry", "transformation_of_axes"),
    ("Coordinate Geometry", "Pair of Straight Lines"): ("Coordinate Geometry", "pair_of_straight_lines"),
    ("Coordinate Geometry", "Circles"): ("Coordinate Geometry", "circle"),
    ("Coordinate Geometry", "Circle"): ("Coordinate Geometry", "circle"),
    ("Coordinate Geometry", "System of Circles"): ("Coordinate Geometry", "system_of_circles"),
    ("Coordinate Geometry", "Parabola"): ("Coordinate Geometry", "parabola"),
    ("Coordinate Geometry", "Ellipse"): ("Coordinate Geometry", "ellipse"),
    ("Coordinate Geometry", "Hyperbola"): ("Coordinate Geometry", "hyperbola"),
    ("Coordinate Geometry", "Three Dimensional Geometry"): ("Coordinate Geometry", "three_dimensional_coordinates"),
    ("Coordinate Geometry", "Three Dimensional Coordinates"): ("Coordinate Geometry", "three_dimensional_coordinates"),
    ("Coordinate Geometry", "Direction Cosines and Direction Ratios"): ("Coordinate Geometry", "direction_cosines_and_ratios"),
    ("Coordinate Geometry", "Direction Cosines and Ratios"): ("Coordinate Geometry", "direction_cosines_and_ratios"),
    ("Coordinate Geometry", "Plane"): ("Coordinate Geometry", "plane"),

    ("Vector Algebra", "Addition of Vectors"): ("Vector Algebra", "addition_of_vectors"),
    ("Vector Algebra", "Scalar Product"): ("Vector Algebra", "scalar_product"),
    ("Vector Algebra", "Vector Product"): ("Vector Algebra", "vector_product"),
    ("Vector Algebra", "Scalar Triple Product"): ("Vector Algebra", "scalar_triple_product"),
    ("Algebra", "Addition of Vectors"): ("Vector Algebra", "addition_of_vectors"),
    ("Algebra", "Scalar Product"): ("Vector Algebra", "scalar_product"),
    ("Algebra", "Vector Product"): ("Vector Algebra", "vector_product"),
    ("Algebra", "Scalar Triple Product"): ("Vector Algebra", "scalar_triple_product"),

    ("Probability and Statistics", "Probability"): ("Probability & Statistics", "probability"),
    ("Probability and Statistics", "Random Variables"): ("Probability & Statistics", "random_variables_and_distributions"),
    ("Probability and Statistics", "Measures of Dispersion"): ("Probability & Statistics", "measures_of_dispersion"),
    ("Probability and Statistics", "Probability Detailed"): ("Probability & Statistics", "probability"),
    ("Probability and Statistics", "Random Variables Probability"): ("Probability & Statistics", "random_variables_and_distributions"),

    ("Calculus", "Limits and Continuity"): ("Calculus", "limits_and_continuity"),
    ("Calculus", "Differentiation"): ("Calculus", "differentiation"),
    ("Calculus", "Applications of Derivatives"): ("Calculus", "applications_of_derivatives"),
    ("Calculus", "Integration"): ("Calculus", "integration"),
    ("Calculus", "Definite Integrals"): ("Calculus", "definite_integrals"),
    ("Calculus", "Differential Equations"): ("Calculus", "differential_equations"),

    # Physics
    ("Mechanics", "Physical World"): ("Physical World & Measurement", "physical_world"),
    ("Mechanics", "Units and Measurements"): ("Physical World & Measurement", "units_and_measurements"),
    ("Mechanics", "Motion in a Straight Line"): ("Mechanics", "motion_in_a_straight_line"),
    ("Mechanics", "Motion in a Plane"): ("Mechanics", "motion_in_a_plane"),
    ("Mechanics", "Laws of Motion"): ("Mechanics", "laws_of_motion"),
    ("Mechanics", "Work Energy and Power"): ("Mechanics", "work_energy_and_power"),
    ("Mechanics", "Work, Energy and Power"): ("Mechanics", "work_energy_and_power"),
    ("Mechanics", "Systems of Particles and Rotational Motion"): ("Mechanics", "systems_of_particles_and_rotational_motion"),
    ("Mechanics", "Systems of Particles & Rotational Motion"): ("Mechanics", "systems_of_particles_and_rotational_motion"),
    ("Mechanics", "Gravitation"): ("Mechanics", "gravitation"),
    ("Mechanics", "Oscillations"): ("Mechanics", "oscillations"),
    ("Mechanics", "Mechanical Properties of Solids"): ("Properties of Matter", "mechanical_properties_of_solids"),
    ("Mechanics", "Mechanical Properties of Fluids"): ("Properties of Matter", "mechanical_properties_of_fluids"),

    ("Thermodynamics", "Thermal Properties of Matter"): ("Properties of Matter", "thermal_properties_of_matter"),
    ("Thermodynamics", "Thermodynamics"): ("Thermodynamics & Kinetic Theory", "thermodynamics"),
    ("Thermodynamics", "Thermodynamics Detailed"): ("Thermodynamics & Kinetic Theory", "thermodynamics"),
    ("Thermodynamics", "Kinetic Theory of Gases"): ("Thermodynamics & Kinetic Theory", "kinetic_theory_of_gases"),
    ("Thermodynamics", "Kinetic Theory"): ("Thermodynamics & Kinetic Theory", "kinetic_theory_of_gases"),

    ("Waves", "Waves"): ("Waves & Optics", "waves"),
    ("Optics", "Ray Optics"): ("Waves & Optics", "ray_optics_and_optical_instruments"),
    ("Optics", "Wave Optics"): ("Waves & Optics", "wave_optics"),
    ("Optics", "Ray Optics & Optical Instruments"): ("Waves & Optics", "ray_optics_and_optical_instruments"),
    ("Optics", "Ray Optics Optical Instruments"): ("Waves & Optics", "ray_optics_and_optical_instruments"),

    ("Electrostatics", "Electric Charges and Fields"): ("Electricity & Magnetism", "electric_charges_and_fields"),
    ("Electrostatics", "Electrostatic Potential and Capacitance"): ("Electricity & Magnetism", "electrostatic_potential_and_capacitance"),
    ("Electrostatics", "Electric Potential"): ("Electricity & Magnetism", "electrostatic_potential_and_capacitance"),
    ("Electrostatics", "Capacitance"): ("Electricity & Magnetism", "electrostatic_potential_and_capacitance"),
    ("Current Electricity", "Current Electricity"): ("Electricity & Magnetism", "current_electricity"),
    ("Magnetism", "Moving Charges and Magnetism"): ("Electricity & Magnetism", "moving_charges_and_magnetism"),
    ("Magnetism", "Magnetism and Matter"): ("Electricity & Magnetism", "magnetism_and_matter"),
    ("Electromagnetic Induction and AC", "Electromagnetic Induction"): ("Electricity & Magnetism", "electromagnetic_induction"),
    ("Electromagnetic Induction and AC", "Alternating Current"): ("Electricity & Magnetism", "alternating_currents"),
    ("Electromagnetic Induction and AC", "Alternating Currents"): ("Electricity & Magnetism", "alternating_currents"),
    ("Magnetism", "Electromagnetic Induction"): ("Electricity & Magnetism", "electromagnetic_induction"),
    ("Magnetism", "Alternating Current"): ("Electricity & Magnetism", "alternating_currents"),
    ("Magnetism", "Electromagnetic Waves"): ("Electricity & Magnetism", "electromagnetic_waves"),

    ("Modern Physics", "Dual Nature of Radiation and Matter"): ("Modern Physics", "dual_nature_of_matter_and_radiation"),
    ("Modern Physics", "Duel Nature of Radiation and Matter"): ("Modern Physics", "dual_nature_of_matter_and_radiation"),
    ("Modern Physics", "Dual Nature of Matter & Radiation"): ("Modern Physics", "dual_nature_of_matter_and_radiation"),
    ("Modern Physics", "Atoms"): ("Modern Physics", "atoms"),
    ("Modern Physics", "Nuclei"): ("Modern Physics", "nuclei"),
    ("Modern Physics", "Semiconductor Electronics"): ("Modern Physics", "semiconductor_electronics"),
    ("Modern Physics", "Communication Systems"): ("Modern Physics", "communication_systems"),
    ("Modern Physics", "Electromagnetic Waves"): ("Electricity & Magnetism", "electromagnetic_waves"),

    # Chemistry
    ("Physical Chemistry", "Atomic Structure"): ("Physical Chemistry", "atomic_structure"),
    ("Physical Chemistry", "States of Matter"): ("Physical Chemistry", "states_of_matter"),
    ("Physical Chemistry", "States of Matter (Gases and Liquids)"): ("Physical Chemistry", "states_of_matter"),
    ("Physical Chemistry", "States of Matter Gases Liquids"): ("Physical Chemistry", "states_of_matter"),
    ("Physical Chemistry", "Stoichiometry"): ("Physical Chemistry", "stoichiometry"),
    ("Physical Chemistry", "Thermodynamics"): ("Physical Chemistry", "thermodynamics"),
    ("Physical Chemistry", "Thermodynamics Chemistry"): ("Physical Chemistry", "thermodynamics"),
    ("Physical Chemistry", "Chemical Equilibrium"): ("Physical Chemistry", "chemical_equilibrium"),
    ("Physical Chemistry", "Chemical Equilibrium and Acids-Bases"): ("Physical Chemistry", "chemical_equilibrium"),
    ("Physical Chemistry", "Chemical Equilibrium Acids Bases"): ("Physical Chemistry", "chemical_equilibrium"),
    ("Physical Chemistry", "Redox Reactions"): ("Physical Chemistry", "redox_reactions"),
    ("Physical Chemistry", "Chemical Kinetics"): ("Physical Chemistry", "chemical_kinetics"),
    ("Physical Chemistry", "Surface Chemistry"): ("Physical Chemistry", "surface_chemistry"),
    ("Physical Chemistry", "Solutions"): ("Physical Chemistry", "solutions"),
    ("Physical Chemistry", "Electrochemistry"): ("Physical Chemistry", "electrochemistry"),
    ("Physical Chemistry", "Solid State"): ("Physical Chemistry", "states_of_matter"),

    ("Inorganic Chemistry", "Classification of Elements and Periodicity"): ("Inorganic Chemistry", "classification_of_elements_and_periodicity"),
    ("Inorganic Chemistry", "Classification Periodicity"): ("Inorganic Chemistry", "classification_of_elements_and_periodicity"),
    ("Inorganic Chemistry", "Classification & Periodicity"): ("Inorganic Chemistry", "classification_of_elements_and_periodicity"),
    ("Inorganic Chemistry", "Chemical Bonding and Molecular Structure"): ("Inorganic Chemistry", "chemical_bonding_and_molecular_structure"),
    ("Inorganic Chemistry", "Chemical Bonding & Molecular Structure"): ("Inorganic Chemistry", "chemical_bonding_and_molecular_structure"),
    ("Inorganic Chemistry", "Hydrogen and its Compounds"): ("Inorganic Chemistry", "hydrogen_and_its_compounds"),
    ("Inorganic Chemistry", "Hydrogen & Its Compounds"): ("Inorganic Chemistry", "hydrogen_and_its_compounds"),
    ("Inorganic Chemistry", "Hydrogen and Compounds"): ("Inorganic Chemistry", "hydrogen_and_its_compounds"),
    ("Inorganic Chemistry", "s-block Elements"): ("Inorganic Chemistry", "s_block_elements"),
    ("Inorganic Chemistry", "p-block Elements Group 13"): ("Inorganic Chemistry", "p_block_elements_groups_13_16"),
    ("Inorganic Chemistry", "p-block Elements Group 14"): ("Inorganic Chemistry", "p_block_elements_groups_13_16"),
    ("Inorganic Chemistry", "p-block Elements Groups 15-18"): ("Inorganic Chemistry", "p_block_elements_groups_13_16"),
    ("Inorganic Chemistry", "p-block Elements Groups 15–18"): ("Inorganic Chemistry", "p_block_elements_groups_13_16"),
    ("Inorganic Chemistry", "d and f Block Elements & Coordination Compounds"): ("Inorganic Chemistry", "coordination_compounds"),
    ("Inorganic Chemistry", "d- & f-block Elements + Coordination Compounds"): ("Inorganic Chemistry", "coordination_compounds"),
    ("Inorganic Chemistry", "d f block coordination"): ("Inorganic Chemistry", "coordination_compounds"),
    ("Inorganic Chemistry", "Environmental Chemistry"): ("Inorganic Chemistry", "environmental_chemistry"),
    ("Inorganic Chemistry", "General Principles of Metallurgy"): ("Inorganic Chemistry", "general_principles_of_metallurgy"),

    ("Organic Chemistry", "Basic Principles of Organic Chemistry"): ("Organic Chemistry", "basic_principles_of_organic_chemistry"),
    ("Organic Chemistry", "Organic Principles Hydrocarbons"): ("Organic Chemistry", "basic_principles_of_organic_chemistry"),
    ("Organic Chemistry", "Organic Chemistry-Some Basic Principles and Techniques and Hydrocarbons"): ("Organic Chemistry", "basic_principles_of_organic_chemistry"),
    ("Organic Chemistry", "Environmental Chemistry"): ("Inorganic Chemistry", "environmental_chemistry"),
    ("Organic Chemistry", "Haloalkanes and Haloarenes"): ("Organic Chemistry", "haloalkanes_and_haloarenes"),
    ("Organic Chemistry", "Haloalkanes & Haloarenes"): ("Organic Chemistry", "haloalkanes_and_haloarenes"),
    ("Organic Chemistry", "Alcohols, Phenols and Ethers"): ("Organic Chemistry", "alcohols_phenols_and_ethers"),
    ("Organic Chemistry", "Alcohols, Phenols & Ethers"): ("Organic Chemistry", "alcohols_phenols_and_ethers"),
    ("Organic Chemistry", "Phenols Ethers Aldehydes Ketones Carboxylic Acids"): ("Organic Chemistry", "aldehydes_ketones_and_carboxylic_acids"),
    ("Organic Chemistry", "Aldehydes, Ketones and Carboxylic Acids"): ("Organic Chemistry", "aldehydes_ketones_and_carboxylic_acids"),
    ("Organic Chemistry", "Aldehydes, Ketones & Carboxylic Acids"): ("Organic Chemistry", "aldehydes_ketones_and_carboxylic_acids"),
    ("Organic Chemistry", "Amines"): ("Organic Chemistry", "amines"),
    ("Organic Chemistry", "Organic Compounds Nitrogen"): ("Organic Chemistry", "amines"),
    ("Organic Chemistry", "Biomolecules"): ("Organic Chemistry", "biomolecules"),
    ("Organic Chemistry", "Polymers"): ("Organic Chemistry", "polymers"),
    ("Organic Chemistry", "Chemistry in Everyday Life"): ("Organic Chemistry", "chemistry_in_everyday_life"),
    ("Organic Chemistry", "Organic Compounds Containing C, H and O"): ("Organic Chemistry", "alcohols_phenols_and_ethers"),
    ("Organic Chemistry", "Organic Compounds ch o"): ("Organic Chemistry", "alcohols_phenols_and_ethers"),
    ("Organic Chemistry", "Organic Compounds Containing Nitrogen"): ("Organic Chemistry", "amines"),
}

def replacer_with_indent(match):
    indent = match.group(1)
    old_sec = match.group(2).strip().strip('"').strip("'")
    old_top = match.group(3).strip().strip('"').strip("'")
    
    if (old_sec, old_top) in MAPPING:
        new_sec, new_top = MAPPING[(old_sec, old_top)]
    else:
        new_sec, new_top = old_sec, old_top
        
    return f'{indent}section: {new_sec}\n{indent}topic: {new_top}\n'

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Consistently indent section and topic based on section's indentation
    updated_content = re.sub(r'(\s+)section: (.*?)\n\s+topic: (.*?)\n', replacer_with_indent, content)
    
    # Fix YAML escape character issues by converting double quotes to single quotes
    # if the string contains backslashes.
    def fix_string_quotes(match):
        key = match.group(1)
        val = match.group(2)
        if '\\' in val and val.startswith('"') and val.endswith('"'):
            inner = val[1:-1]
            inner = inner.replace("'", "''") # Escape single quotes for YAML single-quoted string
            return f'{key}: ''{inner}'''
        return match.group(0)

    # Simplified regex for text: "..." or options: A: "..."
    # This might be too broad or narrow, let's use a common pattern
    updated_content = re.sub(r'(text|options|A|B|C|D): ("[^"]*")', fix_string_quotes, updated_content)
    
    return updated_content

# Run for all files
files = [
    "c:/Users/ashad/Desktop/abhilash/Projects/MockMitra/backend/pyq_papers/ts_eamcet/ts_eamcet_2021_2.yaml",
    "c:/Users/ashad/Desktop/abhilash/Projects/MockMitra/backend/pyq_papers/ts_eamcet/ts_eamcet_2021_3.yaml",
]

for f in files:
    if not os.path.exists(f):
        print(f"Skipping {f} - not found")
        continue
    try:
        updated = update_file(f)
        with open(f, 'w', encoding='utf-8') as file:
            file.write(updated)
        print(f"Updated {f}")
    except Exception as e:
        print(f"Error updating {f}: {e}")
