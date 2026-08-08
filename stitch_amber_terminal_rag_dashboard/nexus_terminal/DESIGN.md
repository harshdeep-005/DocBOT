---
name: Nexus Terminal
colors:
  surface: '#18120c'
  surface-dim: '#18120c'
  surface-bright: '#3f3830'
  surface-container-lowest: '#130d07'
  surface-container-low: '#211b13'
  surface-container: '#251f17'
  surface-container-high: '#302921'
  surface-container-highest: '#3b342c'
  on-surface: '#ede0d5'
  on-surface-variant: '#d6c4b0'
  inverse-surface: '#ede0d5'
  inverse-on-surface: '#362f27'
  outline: '#9e8e7c'
  outline-variant: '#514536'
  surface-tint: '#ffb956'
  primary: '#ffc16c'
  on-primary: '#462b00'
  primary-container: '#e8a33d'
  on-primary-container: '#5f3c00'
  inverse-primary: '#835400'
  secondary: '#44e2cd'
  on-secondary: '#003731'
  secondary-container: '#03c6b2'
  on-secondary-container: '#004d44'
  tertiary: '#99d3ff'
  on-tertiary: '#00344e'
  tertiary-container: '#63b9f3'
  on-tertiary-container: '#00486a'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffddb5'
  primary-fixed-dim: '#ffb956'
  on-primary-fixed: '#2a1800'
  on-primary-fixed-variant: '#643f00'
  secondary-fixed: '#62fae3'
  secondary-fixed-dim: '#3cddc7'
  on-secondary-fixed: '#00201c'
  on-secondary-fixed-variant: '#005047'
  tertiary-fixed: '#c9e6ff'
  tertiary-fixed-dim: '#8bceff'
  on-tertiary-fixed: '#001e2f'
  on-tertiary-fixed-variant: '#004b6f'
  background: '#18120c'
  on-background: '#ede0d5'
  surface-variant: '#3b342c'
typography:
  display-lg:
    fontFamily: IBM Plex Mono
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: IBM Plex Mono
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-base:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: IBM Plex Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  utility-data:
    fontFamily: IBM Plex Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  citation-link:
    fontFamily: IBM Plex Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
spacing:
  unit: 4px
  gutter: 16px
  margin-mobile: 12px
  margin-desktop: 24px
  panel-sidebar: 280px
  panel-inspector: 320px
---

## Brand & Style
The design system is engineered for high-utility, technical environments where information density and precision are paramount. The brand personality is "Advanced Industrial"—a blend of modern cloud infrastructure aesthetics and classic terminal interfaces.

The design style follows a **Technical Minimalism** approach: 
- **High Density:** Information is packed tightly to minimize scrolling and maximize context for RAG workflows.
- **Data-Centric:** Visual flourish is sacrificed for clarity; UI chrome is secondary to the source documents and model outputs.
- **Sharp Geometry:** No rounded corners are used, reinforcing a precise, engineered feel.
- **Monospaced Accents:** Used strategically to signal "system" data, citations, and terminal-like interactions.

## Colors
The palette is rooted in a deep, blue-tinted obsidian to reduce eye strain during long research sessions. 

- **Primary Amber (#E8A33D):** Reserved for primary actions, focus states, and the system "intelligence" indicator. It evokes a legacy terminal warmth updated for high-resolution displays.
- **Citation Teal (#2DD4BF):** Specifically used for source grounding, document references, and RAG verification links. It provides a cool, trustworthy contrast to the amber system color.
- **Functional Grays:** The interface uses three distinct levels of darkness to establish hierarchy without relying on shadows. Borders are tight and high-contrast relative to the backgrounds.

## Typography
This design system employs a dual-font strategy to separate content from container.

- **IBM Plex Mono** is used for the "System UI": navigation, labels, citations, and metadata. It creates a structured, grid-aligned feel.
- **Inter** is used for the "Content UI": the actual chatbot responses and document text. This ensures maximum readability for long-form prose and complex technical explanations.
- **Hierarchy:** Use `label-caps` for section headers in sidebars. Use `utility-data` for timestamps, file sizes, and token counts.

## Layout & Spacing
The layout follows a multi-pane "Integrated Development Environment" (IDE) model.

- **Panel System:** A 3-column architecture is preferred. Left for document library, center for the chat/PDF viewer, and right for citations/metadata.
- **Grid:** Use a strict 4px baseline grid. All padding and margins should be multiples of 4.
- **Density:** Maintain tight internal padding (e.g., 8px or 12px) within cards and list items to support the "data-heavy" requirement.
- **Hairline Dividers:** Use 1px solid borders (`#232A38`) to separate panels. Avoid using negative space alone to define boundaries.

## Elevation & Depth
In this design system, depth is communicated through **Tonal Layering** rather than shadows. 

- **Level 0 (Base):** `#0B0E14` - The main canvas/background.
- **Level 1 (Sidebar):** `#12161F` - Fixed navigation or secondary panels.
- **Level 2 (Raised):** `#171C27` - Active cards, modals, or hovered items.

**Focus State:** Instead of a shadow, an active or focused element should receive a 1px or 2px solid border of `Accent Amber (#E8A33D)`.

## Shapes
The design system uses a **Zero-Radius (Sharp)** philosophy. 

All buttons, input fields, panels, and dropdowns must have 0px corner radius. This creates a rigid, grid-based aesthetic that aligns with monospaced typography. The only exception is for circular avatars or status indicators (e.g., online/offline dots).

## Components
- **Buttons:** Sharp corners. Primary buttons use `Accent Amber` with black text. Ghost buttons use a 1px border of `#232A38` and `Text Muted`.
- **Inputs:** Solid background of `#0B0E14` with a 1px border. On focus, the border changes to `Accent Amber`.
- **Citations:** Inline chips with `utility-data` styling. Background: `rgba(45, 212, 191, 0.1)`, Text: `Citation Teal`. On click, highlight the corresponding text in the PDF viewer.
- **Chat Bubbles:** No rounded corners. User messages are right-aligned with a subtle border. Assistant messages have a distinct background (`#12161F`) to differentiate from the base canvas.
- **Scrollbars:** Custom thin bars using `#232A38` for the track and `#8B93A7` for the thumb. No rounded ends.
- **Checkboxes:** Square, sharp-edged. When checked, fill with `Accent Amber`.