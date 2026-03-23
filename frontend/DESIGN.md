# Design System Specification: High-End Real Estate Editorial

## 1. Overview & Creative North Star
**Creative North Star: "The Architectural Ledger"**

This design system moves away from the generic "dashboard" look of property tech. Instead, it adopts the persona of a high-end architectural journal—precise, data-rich, but undeniably premium. We prioritize **Intentional Asymmetry** and **Tonal Depth** over standard grids and borders. 

By utilizing a "Digital Curatorial" approach, we treat every property transaction not as a row in a database, but as a significant entry in a ledger. The aesthetic is defined by vast amounts of breathing room, sophisticated layering of blues, and typography that commands authority. We break the "template" feel by overlapping elements and using background shifts to define space, creating an interface that feels built, not just programmed.

---

## 2. Colors & Surface Logic

The palette is anchored in deep oceanic blues (`primary: #00145d`) and sterile, crisp whites (`surface: #fbf8ff`). We avoid "pure black" to maintain a sophisticated, high-contrast editorial feel.

### The "No-Line" Rule
**Explicit Instruction:** 1px solid borders for sectioning are strictly prohibited. 
Structural boundaries must be defined solely through background color shifts. To separate a sidebar from a main content area, transition from `surface-container-low` to `surface`. This creates a seamless, modern "wash" of color rather than a boxed-in feel.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers—stacked sheets of frosted glass or fine paper.
- **Base Layer:** `surface` (#fbf8ff)
- **Secondary Sections:** `surface-container-low` (#f4f2ff)
- **Interactive/Floating Cards:** `surface-container-lowest` (#ffffff)
- **High-Emphasis Callouts:** `surface-container-high` (#e5e6ff)

### Glass & Gradient Soul
To move beyond a flat, out-of-the-box appearance:
- **Glassmorphism:** Use `surface-container-lowest` at 70% opacity with a `20px` backdrop-blur for floating navigation or property filters.
- **Signature Gradients:** Main CTAs and Hero backgrounds should utilize a subtle linear gradient from `primary` (#00145d) to `primary_container` (#0f2885) at a 135-degree angle. This adds "visual soul" and depth that flat hex codes cannot achieve.

---

## 3. Typography: The Editorial Voice

We utilize a dual-typeface system to balance technical precision with premium branding.

*   **Display & Headlines (Manrope):** Chosen for its geometric modernism. Use `display-lg` (3.5rem) with tighter letter-spacing (-0.02em) for property prices and hero headlines to convey high-value authority.
*   **Body & Labels (Inter):** Inter provides exceptional readability for complex real estate data. 
*   **The Hierarchy of Trust:** Large headlines should always be `on_surface` (#08154d), while secondary metadata uses `on_surface_variant` (#454652). This contrast ensures the user's eye gravitates toward the "Financial Truths" first.

---

## 4. Elevation & Depth

### The Layering Principle
Hierarchy is achieved through **Tonal Layering**. Instead of applying a shadow to a card, place a `surface-container-lowest` card on a `surface-container-low` background. The slight shift in brightness creates a soft, natural lift.

### Ambient Shadows
When an element must "float" (e.g., a modal or a primary property action button):
- **Shadow Specs:** Blur: `40px`, Spread: `-10px`, Opacity: `6%`.
- **Shadow Tint:** Use a tinted version of `on_surface` (#08154d) rather than grey. This mimics natural light passing through blue-toned glass.

### The "Ghost Border" Fallback
If accessibility requires a container boundary, use a **Ghost Border**: `outline-variant` (#c5c5d4) at **15% opacity**. Never use 100% opaque borders.

---

## 5. Signature Components

### Cards & Property Lists
*   **The Rule:** Forbid the use of divider lines. 
*   **Implementation:** Use the Spacing Scale `8` (2rem) or `10` (2.5rem) to separate list items. Use a subtle background shift to `surface-container-low` on hover to indicate interactivity.

### Buttons (The "Precision" Variant)
*   **Primary:** Gradient fill (`primary` to `primary_container`), `roundness-md` (0.375rem), white text.
*   **Secondary:** `surface-container-highest` background with `on_primary_container` text. No border.
*   **Tertiary/Ghost:** Text-only with an icon. On hover, apply a `surface-variant` background at 10% opacity.

### Data Inputs & Fields
*   **Style:** Minimalist. No border. Use `surface-container-highest` as the input background. 
*   **Focus State:** Transition the background to `surface-container-lowest` and apply a 1px "Ghost Border" at 40% opacity.

### High-Context Components (Real Estate Specific)
*   **Transaction Timeline:** Use a vertical "Thread" layout. Instead of a line, use a sequence of `surface-container-high` nodes.
*   **Property Tags (Chips):** Use `secondary_container` with `on_secondary_container` text. Roundness should be `full` for a modern, tech-forward feel.

---

## 6. Do’s and Don'ts

### Do:
*   **Embrace Whitespace:** Use the `24` (6rem) spacing token between major sections to let the data breathe.
*   **Use Intentional Asymmetry:** Offset images from their text containers by `2rem` to create a custom, high-end editorial layout.
*   **Layer Surfaces:** Always ask, "Can I define this area with a background color shift instead of a line?"

### Don’t:
*   **Don't use "Card Fatigue":** Avoid putting everything in a white box with a shadow. Use the background tiers to create zones of information.
*   **Don't use Default Shadows:** Never use the standard CSS `0 2px 4px rgba(0,0,0,0.5)`. It feels cheap and dated.
*   **Don't use High-Contrast Dividers:** 1px grey lines (`#D1D5DB`) disrupt the flow of a premium experience. Use negative space instead.