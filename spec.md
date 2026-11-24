# Beam Designer

## Application

Build the application as a Python desktop program using Tkinter for its
interface. The program runs locally in a desktop window and does not require a
web browser or a network connection for its core analysis. Organize the window
so users can enter beam, support, load, section, material, and check inputs;
run the analysis; and review the schematic, diagrams, reactions, and checks.
Keep inputs and results clearly labeled with units, and provide a visible way
to load the populated validation example. This specification describes the
intended application; it does not prescribe implementation details beyond
Python and Tkinter.

## Purpose

Analyze a single beam under static vertical loads. Show support reactions,
shear, bending moment, and deflection, with preliminary bending-stress and
deflection checks.

## Version 1 scope and assumptions

- One prismatic beam with either simply supported or cantilever supports.
- Linear-elastic, small-deflection Euler-Bernoulli beam analysis.
- No continuous spans, frame action, dynamic loads, shear deformation, or
  buckling checks.
- Results are an engineering aid, not a code-compliance determination or
  substitute for review by a qualified professional.

## Inputs

- Support condition and span.
- Any number of vertical point loads, each with a magnitude and position.
- Any number of constant uniform loads, each with a magnitude and start/end
  positions. Loads may act upward or downward; downward is positive.
- Optional beam self-weight, shown as a load when enabled.
- A selected beam section and material properties.
- Allowable bending stress for the bending check.
- Deflection limit, defaulting to span/360.

Use feet for span and load positions, kips for point loads, kip/ft for uniform
loads, inches for section dimensions, in^3 for section modulus, in^4 for moment
of inertia, ksi for modulus and stress, and inches for deflection. Show units
with every input and result.

## Beam properties

- Steel: provide a catalog of AISC W-shapes with shape designation, weight per
  length, strong-axis section modulus Sx, and strong-axis moment of inertia Ix.
  Record the AISC Shapes Database release used. Select steel modulus E and
  allowable bending stress explicitly; do not infer a code allowable from
  shape designation alone.
- Sawn lumber: identify nominal size, actual dressed dimensions, species, and
  grade. Derive rectangular-section Sx and Ix from actual dimensions. Show the
  source and release for any catalog E or reference bending value. Allow the
  user to enter the allowable bending stress used for the check; do not imply
  that reference values include code-required adjustment factors. The initial
  data release includes common 2x section geometry only; require the user to
  provide species, grade, E, and allowable bending stress.
- Any catalog data source and release must be documented alongside the data.

## Calculations and checks

- Reactions, shear, and bending moment from static equilibrium.
- Deflection for the stated beam model, loads, and selected E and Ix.
- Maximum absolute bending stress: fb = |M|max / Sx.
- Bending check: pass when fb does not exceed the user-provided allowable
  bending stress. Label this a bending-stress check, not a complete beam
  strength or code check.
- Deflection check: pass when maximum absolute deflection does not exceed the
  selected limit. The initial default is span/360.
- Identify the governing location and value for each check.

## Outputs

- Beam/load schematic with supports, section, dimensions, and loads.
- Shear-force, bending-moment, and deflection diagrams, with axes, units,
  extrema, and governing locations.
- Support reactions.
- Bending-stress and deflection check results, including demand, limit, and
  pass/fail status.

## Look and feel

Clean and professional. Open with the validation example populated. Keep the
beam/load schematic visually distinct from the three result diagrams.

## Validation

For a 20 ft simply supported W12x26 with a full-span downward uniform load of
1 kip/ft and self-weight excluded:

- Maximum moment: 50.0 kip-ft.
- Maximum deflection: 0.609 in when E = 29,000 ksi and Ix = 204 in^4.

Use the exact section properties from the selected catalog release in the
application test and record them with the test case.

## Out of scope

Continuous beams, buckling and lateral restraint checks, shear-strength checks,
load combinations, connection design, and code-compliant member design.
