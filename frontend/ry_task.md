Start by reading `progress.md` and `claude.md` carefully to understand project context, previous implementation progress, design intentions, constraints, pending tasks, and any repo-specific instructions. Then inspect the existing codebase structure in detail before making changes. You must build on top of the current code structure, reuse existing components/routes/styles/utilities where sensible, and avoid rewriting from scratch unless something is clearly broken or unusable. If required data is missing, create realistic mock data and wire the UI cleanly so it can be swapped with real data sources later.

Your task is to build a React web app for a Singapore HDB resale decision-support product using the attached mockups and the design language from `DESIGN.md`.

The visual direction is a premium editorial property intelligence product, not a generic dashboard. The design system is “The Architectural Ledger”: deep oceanic blue primary (`#00145d`), crisp soft-white and pale-lavender surfaces, strong editorial typography, tonal layering instead of visible borders, subtle gradients for key CTAs, lots of breathing room, intentional asymmetry, and a calm high-trust aesthetic. Avoid default dashboard patterns, divider-heavy layouts, harsh boxes, cheap shadows, and generic UI kits. Follow these design rules closely:
- no 1px section borders for layout separation
- define structure mainly through background tone shifts
- use layered surfaces instead of card-overload
- use large, authoritative typography for hero titles, values, and price signals
- keep metadata quieter and highly readable
- inputs should be minimalist with soft filled backgrounds, not bordered form controls
- primary CTAs should use a subtle blue gradient
- use shadows only when something genuinely floats
- preserve a spacious, premium layout throughout

Build the app as if it were a polished front-end prototype ready for a real product team to continue.

## High-level objective
Create a navigable React app with a coherent design system and these main product surfaces:
1. Landing / User Guide
2. Market Analysis
3. Flat Amenities
4. Flat Valuation

## Working process requirements
Before coding:
1. Read `progress.md`
2. Read `claude.md`
3. Inspect the current repo structure
4. Identify reusable existing code
5. Decide what should be extended vs newly created
6. Create a short implementation plan
7. Then begin building

While building:
- prefer incremental changes over wholesale rewrites
- preserve existing architecture where possible
- create reusable components instead of page-specific duplication
- use mock data only where real data is unavailable
- keep the codebase easy to extend for future APIs and map integrations

## Technical requirements
- Use React
- Use the repo’s existing stack, conventions, and component patterns where possible
- Keep the app modular and production-oriented
- Use clean routing for major pages
- Organize code clearly across pages, shared components, mock data, utils, and styles
- Do not hardcode everything directly into page files
- If there is an existing design token/theme layer, integrate with it
- If there is no clear design system in code yet, establish one lightly and consistently

## Pages and expected UX

### 1. Landing / User Guide page
Build a premium landing page that introduces the product clearly.

Include:
- top navigation bar
- brand identity aligned with the mockups
- strong hero section with headline, subheadline, and CTA
- supporting visual or image treatment
- feature overview for:
  - Market Analysis
  - Flat Amenities
  - Flat Valuation
- polished footer or lower informational section

Design goals:
- immediate trust and clarity
- editorial, clean, premium
- not crowded
- strong first impression

### 2. Market Analysis page
Build a town-level market exploration page inspired by the mockups.

Include:
- town search input
- main visual area for a stylized map / heatmap / region selection interface
- a selected-town panel that shows:
  - selected region/town name
  - broad descriptor such as region / estate type
  - median price
  - recent transaction count
  - price by flat type
  - 12-month trend
  - optional development notes or area facts
- CTA to drill deeper, such as “View Listed Properties” or similar placeholder

Behavior:
- selecting a town updates the side panel
- use believable mock market data
- maintain a spacious visual layout, not a cramped analytics page

### 3. Flat Amenities page
Build a comparison tool for shortlisted flats.

Include:
- postal code input
- “Add Flat” interaction
- support for comparing multiple flats
- a premium comparison matrix showing amenity access for each flat
- rows such as:
  - MRT Station
  - Shopping Mall
  - Sports Hall
  - Medical Facility
  - Hawker Centre
- each cell should show nearest amenity name plus distance/travel time
- clearly label the best flat for each row where applicable
- “View on Map” affordances
- lower sections for category-specific nearby amenities, for example:
  - Primary Schools within 1KM
  - Parks & Recreation within 1KM
- elegant comparison layout with strong readability

Behavior:
- user can add comparison flats from mock data by postal code
- comparison table updates based on selected flats
- lower amenity sections update accordingly

### 4. Flat Valuation page
Build a valuation workflow page with an input panel and comparables.

Include:
- left-side valuation input panel
- fields for:
  - flat type
  - postal code
  - flat size (sqm)
  - lease left (years)
  - floor level
  - optional listed price
- primary action button such as “Search & Calculate”
- result card showing:
  - estimated current value
  - recent growth or directional signal
  - valuation confidence
- right-side comparables list showing:
  - block / comparable name
  - transacted price
  - floor area
  - transaction date
  - floor range
  - lease left
  - relative difference vs estimate
- supporting summary such as area median price
- optional center canvas for reserved map or geographic/price visualization

Behavior:
- form submission populates valuation output and comparable transactions from mock data
- valuation result should feel believable and coherent with comparable records
- design should match the premium system, not default form-plus-cards UI

## Reusable components to create or refine
Create reusable components wherever appropriate, such as:
- AppShell / top navigation
- page header / section header
- premium button variants
- search field
- soft filled form input
- select dropdown
- metric display block
- comparison matrix row
- amenity card/list group
- comparable transaction card
- selected area side panel
- chart wrapper
- floating utility button
- chip / tag
- empty state / loading skeleton
- map placeholder container

## Mock data requirements
If real data is unavailable, create realistic Singapore HDB-themed mock data in separate files.

Include mock datasets for:
- towns and market summaries
- area price trends
- flat-type price breakdowns
- amenity proximity data by postal code / flat
- nearby schools, parks, recreation, malls, MRTs, etc.
- valuation outputs
- comparable transactions
- area-level price summaries

The mock data should be:
- structured
- reusable
- believable
- easy to replace later

## Styling requirements
Translate `DESIGN.md` into actual UI decisions.

Specifically:
- use tonal surfaces to separate sections instead of visible borders
- avoid generic white cards everywhere
- keep list separation mostly through spacing and hover tone shifts
- use soft pale backgrounds for sidebars, panels, and grouped sections
- use deep blue for major emphasis and trust anchors
- use gradient fills sparingly on primary CTAs or premium callouts
- use ghost-border treatment only if needed for accessibility or focus state
- ensure typography hierarchy is strong and intentional
- keep spacing generous between major sections

## Code quality requirements
- read the existing repo before implementing
- do not duplicate logic unnecessarily
- name components clearly
- keep page composition understandable
- separate layout, presentation, and data concerns sensibly
- leave comments only where helpful, not everywhere
- make future API replacement straightforward
- do not leave the app in a hacked-together prototype state

## Execution sequence
Follow this sequence:
1. Read `progress.md`
2. Read `claude.md`
3. Inspect repo structure and current implementation
4. Summarize current state briefly
5. Create implementation plan
6. Build shared design primitives if needed
7. Build or refine navigation and app shell
8. Build Landing / User Guide page
9. Build Market Analysis page
10. Build Flat Amenities page
11. Build Flat Valuation page
12. Add mock data and connect interactions
13. Polish spacing, typography, and consistency
14. Check responsiveness for desktop-first behavior
15. Review for visual consistency against mockups and `DESIGN.md`

## Definition of done
The task is complete only when:
- all four key pages exist and are navigable
- the app matches the premium editorial design language
- the pages resemble the supplied mockups in structure and feel
- the app builds on the existing repo rather than replacing it blindly
- mock data is added where necessary
- the core interactions work with local state
- components are reusable and code is organized cleanly
- the result feels like a serious product prototype, not a rough student front end

## Final output requirements
When finished, provide:
1. a concise summary of what was built
2. key files created or modified
3. assumptions made
4. where mock data was introduced
5. anything left as a placeholder for future real backend / map integration

Important:
Do not drift into a generic admin dashboard look. Keep pushing the implementation toward a premium, editorial, architectural-property aesthetic with strong hierarchy, tonal depth, clean layering, and elegant restraint.