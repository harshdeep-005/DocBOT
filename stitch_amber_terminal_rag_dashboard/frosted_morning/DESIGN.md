---
name: Frosted Morning
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3f484e'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6f787e'
  outline-variant: '#bec8ce'
  surface-tint: '#006686'
  primary: '#006686'
  on-primary: '#ffffff'
  primary-container: '#7dd3fc'
  on-primary-container: '#005b78'
  inverse-primary: '#7bd1fa'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#835500'
  on-tertiary: '#ffffff'
  tertiary-container: '#febc60'
  on-tertiary-container: '#754b00'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#c0e8ff'
  primary-fixed-dim: '#7bd1fa'
  on-primary-fixed: '#001e2b'
  on-primary-fixed-variant: '#004d66'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#ffddb5'
  tertiary-fixed-dim: '#fcba5e'
  on-tertiary-fixed: '#2a1800'
  on-tertiary-fixed-variant: '#633f00'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-md:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
---

## Brand & Style

The design system embodies a "Frosted Morning" aesthetic—a blend of high-precision minimalism and soft glassmorphism. It is designed for professional SaaS and technology environments that require a sense of clarity, focus, and modern sophistication. 

The emotional response should be one of "calm productivity." By utilizing high-contrast typography against crystalline, translucent surfaces, the UI feels both structured and ethereal. The style avoids heavy shadows in favor of light-refractive properties, emphasizing layered depth and crisp edges.

## Colors

The light mode palette is driven by a high-contrast, "Arctic" logic. The foundation is a cool-toned off-white background that prevents screen glare while maintaining a bright atmosphere. 

- **Primary Accent:** Ice Blue (#7dd3fc). When used for text or critical actions on white surfaces, it must be paired with a darker tint or a high-contrast container to ensure accessibility.
- **Surfaces:** Pure White (#FFFFFF) with a 75% opacity frost effect to allow background colors to bleed through subtly.
- **Typography:** Deep Charcoal (#0F172A) provides maximum legibility for primary content, while Cool Gray (#64748B) handles secondary metadata.
- **Borders:** A thin, Silver (#E2E8F0) stroke defines the architecture without adding visual weight.

## Typography

This design system uses a tri-font hierarchy to balance character with utility. 

- **Headlines:** Manrope provides a modern, refined, and slightly geometric feel. Tighten letter-spacing on larger displays to maintain a "locked-in" editorial look.
- **Body:** Inter is used for all long-form text and interface elements due to its systematic neutrality and exceptional legibility at small scales.
- **Labels:** JetBrains Mono is utilized for metadata, tags, and technical values, reinforcing the "precision tool" aspect of the brand.

All typography should adhere to a strict vertical rhythm based on a 4px baseline grid. Use Deep Charcoal for all primary headlines and Inter Medium for interactive labels.

## Layout & Spacing

The design system employs a **Fluid Grid** model with generous outer margins to simulate an expansive, open-air feeling. 

- **Grid:** A 12-column system for desktop, 8-column for tablet, and 4-column for mobile.
- **Rhythm:** Spacing follows a linear 4px scale. Components should primarily use `md` (16px) for internal padding and `lg` (24px) for vertical separation between sections.
- **Adaptation:** On mobile, margins shrink to 16px to maximize screen real estate, while desktop layouts use 64px margins to create a focused "stage" for the content.

## Elevation & Depth

Depth in this design system is achieved through **Glassmorphism** and **Tonal Layers** rather than traditional shadows.

1.  **Level 0 (Floor):** The Background (#F8FAFC).
2.  **Level 1 (Card/Surface):** Pure white with 75% opacity and a `backdrop-filter: blur(12px)`. This creates the "frosted" effect. Use a 1px border (#E2E8F0) to define the edge.
3.  **Level 2 (Floating/Modals):** Pure white (100% opaque) with a very soft, diffused ambient shadow (color: #0F172A, opacity: 4%, blur: 20px).

Avoid using inner shadows or heavy drop shadows. The goal is to make elements feel as though they are carved from or floating on sheets of ice.

## Shapes

The shape language is "Rounded," striking a balance between the precision of sharp corners and the friendliness of full circles. 

- **Standard Elements:** Buttons, input fields, and small cards use a 0.5rem (8px) radius.
- **Large Containers:** Section containers and large cards use `rounded-lg` (16px).
- **Special Elements:** Search bars and tags may use `rounded-xl` (24px) to distinguish them from structural layout elements.

## Components

- **Buttons:** 
    - *Primary:* Ice Blue (#7dd3fc) background with Charcoal (#0F172A) text for maximum contrast. 
    - *Secondary:* Transparent background with a 1px Silver (#E2E8F0) border and Charcoal text.
- **Input Fields:** 
    - Use the Surface style (white with 75% opacity). On focus, the border should transition to Ice Blue (#7dd3fc) with a subtle 2px outer glow of the same color at 20% opacity.
- **Chips/Tags:** 
    - Use JetBrains Mono for the text. Backgrounds should be a very pale tint of the accent color or a simple silver stroke.
- **Cards:** 
    - Must feature the `backdrop-filter: blur`. Content inside cards should follow the 16px (`md`) padding rule. 
- **Lists:** 
    - Use subtle horizontal dividers (#E2E8F0). Hover states should trigger a slight increase in surface opacity (from 75% to 90%) rather than a color change.
- **Progress Bars:** 
    - Background track should be Silver (#E2E8F0), with the active indicator in Ice Blue (#7dd3fc).