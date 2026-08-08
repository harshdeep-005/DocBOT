---
name: Glacier
colors:
  surface: '#040e21'
  surface-dim: '#040e21'
  surface-bright: '#1c2c4a'
  surface-container-lowest: '#000000'
  surface-container-low: '#071328'
  surface-container: '#0c1931'
  surface-container-high: '#111f39'
  surface-container-highest: '#162541'
  on-surface: '#dce5ff'
  on-surface-variant: '#a1abc4'
  inverse-surface: '#f9f9ff'
  inverse-on-surface: '#4b556b'
  outline: '#6b758d'
  outline-variant: '#3e485e'
  surface-tint: '#63bdea'
  primary: '#63bdea'
  on-primary: '#00374b'
  primary-container: '#4eaad6'
  on-primary-container: '#002635'
  inverse-primary: '#006789'
  secondary: '#b1ddf7'
  on-secondary: '#215065'
  secondary-container: '#1c4c60'
  on-secondary-container: '#aad7ef'
  tertiary: '#e0bfff'
  on-tertiary: '#56337a'
  tertiary-container: '#d6adff'
  on-tertiary-container: '#4c2970'
  error: '#ff716c'
  on-error: '#490006'
  error-container: '#9f0519'
  on-error-container: '#ffa8a3'
  primary-fixed: '#63bdea'
  primary-fixed-dim: '#54b0db'
  on-primary-fixed: '#001e2b'
  on-primary-fixed-variant: '#004058'
  secondary-fixed: '#b1ddf7'
  secondary-fixed-dim: '#a3cfe8'
  on-secondary-fixed: '#063d51'
  on-secondary-fixed-variant: '#2c596f'
  tertiary-fixed: '#d6adff'
  tertiary-fixed-dim: '#c8a0f0'
  on-tertiary-fixed: '#361059'
  on-tertiary-fixed-variant: '#55327a'
  primary-dim: '#54b0db'
  secondary-dim: '#a3cfe8'
  tertiary-dim: '#c8a0f0'
  error-dim: '#d7383b'
  background: '#040e21'
  on-background: '#dce5ff'
  surface-variant: '#162541'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
---

# Glacier — Glassmorphism (Dark Mode)

## North Star: "Frozen Light"
Ethereal depth through layered translucent surfaces. Cool, luminous, and premium.

## Colors
- **Primary (`#46a4cf`):** Deep ice-blue for interactive elements and accents, optimized for dark mode luminosity.
- **Background:** Deep midnight surfaces (`#1a2438`) with subtle cool-neutral undertones.
- **Tertiary (`#c8a0f0`):** Soft lavender for secondary accents and highlight variety.
- All surface containers should feel like frosted, dark-tinted glass layers.

## Glass Effect (Core Pattern)
- **Cards/Panels:** `background: rgba(26, 36, 56, 0.6)`, `backdrop-filter: blur(16px)`, `border: 1px solid rgba(70, 164, 207, 0.2)`.
- **Elevated glass:** Increase opacity to 0.75 and blur to 24px for higher hierarchy.
- **Borders:** Always use semi-transparent primary or a cool neutral at 10-25% opacity to catch "light" against the dark background.

## Typography
- **All fonts:** Inter for clean, modern readability.
- Headlines: semibold, slightly tracked. Body: regular weight.
- Text colors: Light neutral (`#e2e8f0`) for primary content to ensure high legibility on dark glass.

## Elevation
- Depth through blur intensity, opacity, and tonal stacking, not heavy black shadows.
- Layer 0: Solid dark background. Layer 1: 60% opacity + 16px blur. Layer 2: 75% + 24px blur.
- Subtle glow effects: `box-shadow: 0 0 30px rgba(70, 164, 207, 0.12)`.

## Components
- **Buttons:** Primary = semi-transparent primary fill with luminous border. Hover = increase internal glow/opacity.
- **Cards:** Frosted dark glass with thin luminous border and subtle rounded corners (8-16px).
- **Inputs:** Dark glass background, thin border, primary blue glow on focus.

## Rules
- Never use opaque solid backgrounds on floating elements.
- Keep borders subtle — luminous and light-catching, defining edges in the dark.
- Maintain high contrast for typography as surfaces become more translucent.