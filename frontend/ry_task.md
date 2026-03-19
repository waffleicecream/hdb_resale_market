We want to add a new page to the app called **Flat Amenities Comparison**.

First, study the current codebase and understand:
- the existing React app structure
- routing conventions
- shared layout/components
- styling system and design tokens
- how existing pages are organized

Use the app’s current design system first. Do not introduce a completely different visual style. The page should structurally resemble a side-by-side comparison table like the provided reference image, but adapted to the current app styling.

## Goal
Build a **frontend-only** page for comparing nearby amenities across up to **3 flats**, using **mock data for now**.

## Main behavior
The page should let users input a **Singapore 6-digit postal code**. When a valid postal code is entered:
- add that flat as a new comparison column
- retrieve mock flat metadata from a mock dataset
- display the flat’s:
  - block + street name
  - postal code

The comparison should support a **maximum of 3 flats**.
- Once 3 flats are added, disable the input box
- Keep the input visible, but show a clear message such as “Maximum of 3 flats compared”
- Each compared flat should have a **remove button**
- Removing a flat should free up a slot and re-enable input if below 3

If the postal code is not found in the mock dataset:
- show an inline validation/error message: **“Postal code not found”**

## UI structure
Build the page as a **side-by-side comparison table** similar to the reference screenshot:
- first column = metric labels
- next columns = compared flats
- maximum 3 flat columns

Add a top input area with:
- postal code input
- add button
- clear feedback/error state
- selected compared flats represented clearly in the table itself

Page title:
- **Flat Amenities Comparison**

No need to optimize for mobile. Desktop-first is fine.

## Metrics to compare

### A. Nearest amenity categories
For each flat, show the following nearest amenity categories:
- MRT station
- Mall
- Sports hall
- Polyclinic/Hospital
- Hawker centre

For each of the above, display:
- first line: distance and walking time in the format  
  `0.5 km | 10 mins`
- second line: amenity name

Assume walking speed is:
- **1 km = 20 minutes**

Walking time should be:
- computed from distance
- rounded to the nearest whole minute

If no amenity exists for that category in the mock data, show:
- **No amenity found**

### B. Amenities within 1 km
For each flat, also show:

- Primary schools within 1 km
- Parks within 1 km

Display:
- count first
- then the names

Since names are important, include them in the cell.
If there are more than 5 entries:
- truncate the visible list
- reveal the full list via a **tooltip**

## Ranking and highlighting logic
For nearest-amenity rows:
- the flat with the **smallest distance** is the best

For “within 1 km” rows:
- the flat with the **largest count** is the best

If there is a tie:
- highlight all tied best values

Use the same logic as the reference image:
- highlight the best cell in green
- also show a small green **“Best”** pill/badge inside that cell

There is **no overall score** on this page.

## Mock data requirements
Since the real data does not exist yet, create a mock dataset file for this page.

The mock dataset should include:
- a small set of valid Singapore-style 6-digit postal codes
- each postal code maps to:
  - block number
  - street name
  - postal code
  - nearest MRT station name + distance
  - nearest mall name + distance
  - nearest sports hall name + distance
  - nearest polyclinic/hospital name + distance
  - nearest hawker centre name + distance
  - list of primary schools within 1 km
  - list of parks within 1 km

Use realistic-looking Singapore examples where possible, but keep it obviously mock/demo data in code comments or naming.

## Engineering constraints
- Frontend UI first only
- No backend integration yet
- Use mock dataset and local state
- Follow existing project patterns and naming conventions
- Reuse existing shared components if appropriate
- Keep code modular and readable
- Avoid unnecessary abstraction
- Do not add reordering functionality
- Do not add mobile-specific work unless it is already easy within the current layout system

## Expected UX flow
1. User lands on Flat Amenities Comparison page
2. User enters a valid 6-digit postal code
3. Matching flat is added as a comparison column
4. User can add up to 3 flats
5. Best values are highlighted row by row
6. User can remove a flat column
7. Invalid postal codes show “Postal code not found”

## Implementation expectations
Before writing code:
1. inspect the existing codebase
2. identify the best route/page location for this new page
3. identify reusable UI patterns/components already present
4. propose a short implementation plan

Then implement:
- the page
- the mock dataset
- any helper functions needed, such as:
  - walking time formatter
  - best-value detection
  - tooltip truncation logic

## Deliverables
Please provide:
1. a short implementation plan
2. the files you will add or modify
3. the actual code
4. a brief explanation of how the mock dataset is structured
5. any assumptions made

Use the current app’s design system first, but make the layout clearly resemble a clean side-by-side comparison table like the reference image.

Do not start coding immediately.
First give:
1. the route/page you plan to create
2. the component structure
3. the mock data shape
4. the table row definitions
Wait for approval before implementing.

Read CLAUDE.md and PROGRESS.md.
Then read TASK.md and propose a plan before coding.

create a PROGRESS.md in frontend folder to track progress, start by looking at the current existing code and adding the detail inside, then write in the new additions.