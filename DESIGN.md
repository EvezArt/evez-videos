---
version: alpha
name: EvezArt
description: Generative ASCII art meets cosmic intelligence — terminal aesthetics for a post-surveillance world.
colors:
  primary: "#0A0E14"
  secondary: "#1C2333"
  tertiary: "#00FF9F"
  quaternary: "#FF2E63"
  neutral: "#C5C8C6"
  accent-gold: "#FFB700"
  accent-amber: "#FF6B35"
  accent-emerald: "#00D9A3"
  accent-sapphire: "#0085FF"
  accent-amethyst: "#9D4EDD"
  accent-cosmic: "#7209B7"
  void: "#000000"
typography:
  display:
    fontFamily: DejaVu Sans Mono
    fontSize: 3rem
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  h1:
    fontFamily: DejaVu Sans Mono
    fontSize: 2.5rem
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  h2:
    fontFamily: DejaVu Sans Mono
    fontSize: 1.75rem
    fontWeight: 600
    lineHeight: 1.2
  body-lg:
    fontFamily: DejaVu Sans Mono
    fontSize: 1.125rem
    fontWeight: 400
    lineHeight: 1.6
  body-md:
    fontFamily: DejaVu Sans Mono
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.6
  body-sm:
    fontFamily: DejaVu Sans Mono
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: DejaVu Sans Mono
    fontSize: 0.75rem
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0.08em"
  code:
    fontFamily: DejaVu Sans Mono
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.5
rounded:
  none: 0px
  sm: 2px
  md: 4px
  lg: 8px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  xxl: 96px
components:
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: "12px 24px"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "{colors.accent-gold}"
    textColor: "{colors.primary}"
  button-secondary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.tertiary}"
    rounded: "{rounded.sm}"
    padding: "10px 20px"
    typography: "{typography.label}"
  button-secondary-hover:
    backgroundColor: "{colors.quaternary}"
    textColor: "{colors.neutral}"
  button-ghost:
    backgroundColor: transparent
    textColor: "{colors.tertiary}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
    typography: "{typography.label}"
  button-ghost-hover:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.neutral}"
  card:
    backgroundColor: "{colors.secondary}"
    rounded: "{rounded.md}"
    padding: "20px"
  card-elevated:
    backgroundColor: "{colors.secondary}"
    rounded: "{rounded.lg}"
    padding: "24px"
  terminal-output:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.tertiary}"
    rounded: "{rounded.md}"
    padding: "16px"
    typography: "{typography.code}"
  label-cosmic:
    backgroundColor: transparent
    textColor: "{colors.accent-cosmic}"
    typography: "{typography.label}"
  label-gold:
    backgroundColor: transparent
    textColor: "{colors.accent-gold}"
    typography: "{typography.label}"
  label-alert:
    backgroundColor: transparent
    textColor: "{colors.quaternary}"
    typography: "{typography.label}"
---

## Overview

EvezArt is the visual identity for EVEZ-OS — a generative ASCII art and intelligence platform that lives between the terminal and the cosmos. The aesthetic draws from three worlds: the raw density of terminal output, the mathematical beauty of strange attractors and reaction-diffusion systems, and the deep jewel tones of a post-surveillance color palette.

The design language is **monospace everything**. Every typeface is DejaVu Sans Mono — from display headlines to body text to micro-labels. This is not a limitation; it is the point. The grid alignment, the character-level precision, the visual rhythm of fixed-width characters — these are the building blocks of the entire visual system.

The color world is **dark-first**. The primary surface is near-black (`#0A0E14`), not pure black — pure black is for voids, and EvezArt is not a void. The secondary surface (`#1C2333`) provides depth. The tertiary (`#00FF9F`) is the signature: a terminal green so saturated it reads as alive. It is the color of active processes, of running code, of intelligence that is awake.

## Colors

- **Primary (#0A0E14):** Deep terminal black. The base surface for all dark-mode interfaces. Not pure black — has a faint blue undertone that reads as depth rather than absence.
- **Secondary (#1C2333):** Elevated surface. Used for cards, panels, and raised containers. Creates the layered depth that distinguishes active content from background.
- **Tertiary (#00FF9F):** The signature. Terminal green, alive and electric. The sole high-emphasis interaction color. Used for active states, primary actions, and the "running" indicator across the system.
- **Quaternary (#FF2E63):** Alert red. Used for warnings, critical states, and the "breach" aesthetic — the moment when a system is compromised or a threshold is crossed.
- **Neutral (#C5C8C6):** Terminal gray. The default text color. Readable against primary and secondary surfaces. Never used for interaction — only for content.
- **Accent Gold (#FFB700):** The resolution color. Appears in calm scenes, in "done" states, in the moment after intensity resolves to stillness. The color of the final scene in every EvezArt video.
- **Accent Emerald (#00D9A3):** Organic growth. Used in reaction-diffusion scenes, coral patterns, living systems.
- **Accent Sapphire (#0085FF):** Deep space. Used in tunnel effects, vortex scenes, and cosmic-scale visuals.
- **Accent Amethyst (#9D4EDD):** The mystical accent. Appears in kaleidoscopic moments, in symmetry, in the geometry of the attractor.
- **Accent Cosmic (#7209B7):** The deepest purple. Used sparingly — for transitions, for the edge between scenes, for the liminal.
- **Void (#000000):** Pure absence. Used only in the literal background of video frames. Never used in UI — the UI always has depth.

## Typography

DejaVu Sans Mono for everything. No exceptions.

The type system is a single-family system with weight and size carrying all hierarchy. Display weights (700) are for hero moments — video titles, landing headlines. Body weights (400) are for content. Label weights (600) are for UI controls and metadata, set in all-caps with letter-spacing for a terminal-label feel.

The code style (`body-sm`, `fontFamily: DejaVu Sans Mono`) is the native state of the system. Every other style is a deliberate departure from the baseline — larger, bolder, or both — but never a different family.

## Layout

The grid is the character grid. Everything aligns to monospace character widths. Padding and spacing follow a 4px base unit, which maps to the character cell padding in the ASCII rendering pipeline.

- **xs (4px):** Tight — between an icon and its label
- **sm (8px):** Default — between elements in a group
- **md (16px):** Standard — between groups
- **lg (24px):** Generous — between sections
- **xl (48px):** Breathing room — between major sections
- **xxl (96px):** Void — between scenes, between worlds

## Elevation & Depth

Depth is created through surface layering, not shadows. The system has three levels:

1. **Base (primary):** The ground. Everything starts here.
2. **Elevated (secondary):** One step up. Cards, panels, active containers.
3. **Terminal output (primary, inset):** Terminal output blocks are primary-colored with tertiary text — the inversion creates a "window into the machine" effect.

No box shadows. No blur. No glassmorphism. Depth is surface color + border, nothing else. The aesthetic is opaque, structural, and unapologetically flat.

## Shapes

Rounded corners are minimal. The system uses 2px for small elements, 4px for standard elements, and 8px for large containers. Full rounding (9999px) is reserved for status indicators and dots only — never for buttons or cards.

The philosophy: **corners are a concession, not a feature.** The character grid has no curves. The UI should feel like it was built from the same material.

## Components

`button-primary` is the single high-emphasis action. Tertiary green on dark — it reads as "run this." The hover state shifts to gold, the resolution color — "this has been done."

`button-secondary` uses the secondary surface with tertiary text. It is the "available but not primary" action. Hover shifts to alert red — the color of commitment.

`button-ghost` has no background. It is for navigation, for secondary controls, for the ambient UI that doesn't compete with content.

`card` and `card-elevated` are the two container levels. Standard cards use `md` rounding; elevated cards use `lg` rounding and more padding — they feel more important.

`terminal-output` is the signature component: primary background, tertiary text, monospace. It is the "window into the machine" — the component that shows the user the system is alive.

## Do's and Don'ts

**Do:**
- Use monospace everywhere. Every font, every size, every weight.
- Lead with the dark surface. Light mode is not the default.
- Use tertiary green for the single most important action on any screen.
- Reserve gold for resolution, for "done," for the calm after intensity.
- Let the character grid inform layout. Align to character widths when possible.
- Use alert red sparingly — it means something is wrong or something is being committed.

**Don't:**
- Don't use non-monospace fonts. The system is monospace or it is not EvezArt.
- Don't use pure black (`#000000`) in UI — it's for video frames only.
- Don't use shadows, blur, or glassmorphism. Depth is surface color, not effects.
- Don't use more than one high-emphasis color on a single screen. Tertiary green is the sole driver.
- Don't use rounded corners beyond 8px for containers. The system is not soft.
- Don't mix the jewel-tone accents randomly. Each accent has a role: gold = resolution, emerald = growth, sapphire = space, amethyst = symmetry, cosmic = liminal.
