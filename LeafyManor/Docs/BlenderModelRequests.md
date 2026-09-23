# Leafy Manor – Blender Model Requests (Entrance Hall)

All sizes are **final in-game centimetres**, matching the blockout at `LM_SCALE = 0.68`, which fits your 97.8 cm character.
If you change `LM_SCALE`, multiply every size here by `new_scale / 0.68`.

## Rules for every model

| Topic | Rule |
|---|---|
| Units | Work the way your character was exported: Blender in metres, FBX **Apply Scalings = "FBX Units Scale"** (so 272 cm = 2.72 m in Blender). |
| Orientation | Z up. The model's **front** (the side the player sees or approaches) faces **Blender −Y** (numpad-1 Front view). |
| Transforms | Apply all transforms (Ctrl+A → All Transforms). Put the object origin at the listed pivot. |
| Names | Mesh object = the `SM_LM_…` name. Collision objects = `UCX_<MeshName>_01`, `_02`… (convex shapes only). |
| Materials | Use the slot names listed (`M_LM_…`). I'll create matching Unreal materials. Keep slots per model to 5 or fewer. |
| UVs | UV0 unwrapped, no overlaps on unique parts. Architecture can use tiling UVs at about 512 px/m. No lightmap UVs needed (Lumen + movable lights). |
| LODs | Where it says "No", I'll enable **Nanite** on import. Where it says "Yes", export LOD0 only and I'll use Unreal's auto-LOD. |
| Export | FBX, selected objects only, Apply Modifiers on, Smoothing = Face, no armature, no "Add Leaf Bones". |
| Budgets | The triangle counts in *Extra Notes* are targets for LOD0. |

Import targets in Unreal: architecture → `/Game/LeafyManor/Architecture`, props → `/Game/LeafyManor/Props`, furniture → `/Game/LeafyManor/Furniture`.

### Things you do NOT need to model (I'll do these in Unreal)
Floors and ceiling (modular boxes + tiled marble/stone materials) · rugs and runners (planes + textures) · water surfaces, fire, sparks and fountain spray (materials + Niagara) · the night view through windows and doors (material + sky) · invisible collision · plants, trees and hedges (use free Quixel Megascans / Fab foliage unless you want custom ones) · banner text and portrait artwork (2D textures).

### Priority order
1. **Priority 1 (architecture + hero pieces).** These replace the blockout geometry. Start with #1 Wall Kit, #5 Grand Staircase, #6 Balustrade Kit and #8 Fountain.
2. **Priority 2.** Furniture, statues, chandelier, banners.
3. **Priority 3.** Small detail props.

---

## PRIORITY 1

MODEL NEEDED:
Name: Wall Kit (SM_LM_Wall_*)

Purpose:
Modular dark-stone walls for the whole hall, vestibule and galleries. Replaces every `LM_BO_Wall_*` blockout bay.

Description:
Dark stone ashlar wall bay with a slim flat pilaster on both vertical edges. Lower bays: 20 cm stone plinth at the bottom, recessed wainscot panels, a thin gold trim line at about 100 cm. Upper bays: plain dark stone between the pilasters, a moulded cornice at the top that meets the ceiling. Door and window variants have arched openings with a stone surround.

Approximate Size:
Width: 272 cm (one bay)
Depth: 41 cm
Height: 392 cm (lower bay) / 696 cm (upper bay) → stacked = 1088 cm floor to ceiling

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Wall_Lower_01 – plain lower bay 272 × 41 × 392
- SM_LM_Wall_Lower_Door_01 – lower bay with a centred arched opening 136 W × 245 H starting at floor level
- SM_LM_Wall_Upper_01 – plain upper bay 272 × 41 × 696 with the cornice at the top
- SM_LM_Wall_Upper_Window_01 – upper bay with a centred arched opening 136 W × 408 H, bottom of the opening 125 cm above the bay's bottom edge
- SM_LM_Wall_Upper_Door_01 – upper bay with a centred opening 136 W × 245 H starting at the bay's bottom edge (gallery doors)
- SM_LM_Wall_Lintel_Grand_01 – 272 × 41 × 38 lintel that sits above the 354 cm tall grand-door openings (bottom at 354, top at 392)
- SM_LM_Wall_Corner_01 – corner pillar 41 × 41 × 1088

Material Slots Needed:
- M_LM_StoneDark
- M_LM_StoneLight (plinth, cornice, opening surrounds)
- M_LM_Gold (trim line)

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre of the front (room-facing) face.

Collision Type:
Simple custom collision. Plain bays get one UCX box. Bays with openings get UCX boxes around the opening (left jamb, right jamb, header, and sill for windows) so the opening stays open.

LOD Needed:
No (Nanite)

Modular:
Yes – snaps on a 272 cm grid. Upper bays sit directly on lower bays.

Recommended Export:
FBX

Extra Notes:
Keep the back face flat, since it is never seen. The gallery floor meets the wall at the 392 cm seam, so hide the seam behind the cornice or trim of the lower bay. Target about 1–3k triangles per bay. Window sills must not stick out more than 5 cm, so the player can't perch on them from the gallery.

---

MODEL NEEDED:
Name: Grand Double Door (SM_LM_Door_Grand_01)

Purpose:
Main exterior entrance (opened outward so the night garden shows through), plus the closed inner doors at the back of the vestibule. The same model is used in both places.

Description:
Tall arched double door in dark carved wood with gold studs, hinges, ring handles and a gold crown-and-leaf emblem on each leaf (see "Door Detail" on the master sheet). Stone arched surround with a keystone that carries a small gold crown.

Approximate Size:
Width: 340 cm (surround outer) – opening 272 cm
Depth: 30 cm (surround sticks out 15 cm from the wall face)
Height: 400 cm (surround) – opening 354 cm (arch springs at about 300 cm)

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Door_Grand_Frame_01 (stone surround + keystone crown)
- SM_LM_Door_Grand_LeafL_01 (136 × 10 × 354, arched top)
- SM_LM_Door_Grand_LeafR_01 (mirror of the left leaf)

Material Slots Needed:
- M_LM_WoodDark
- M_LM_Gold
- M_LM_StoneLight

UVs Needed:
Yes

Moving Parts:
Yes – leaves rotate about their hinges.

Pivot Location:
Frame: bottom centre of the opening, on the wall's front face. Leaves: bottom of the hinge edge.

Collision Type:
Simple custom collision. Frame: UCX boxes for the jambs and header only (the 272 cm opening stays clear). Each leaf: one UCX box.

LOD Needed:
No (Nanite)

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 15–25k triangles total. The front leaves are placed swung outward 90°, so detail both sides of each leaf.

---

MODEL NEEDED:
Name: Side Door (SM_LM_Door_Side_01)

Purpose:
Closed doors to side rooms: 2 on the ground floor under the galleries and 2 on the gallery level.

Description:
Smaller arched double door matching the grand door style: dark wood, gold hinges and handles, stone surround.

Approximate Size:
Width: 176 cm (surround) – opening 136 cm
Depth: 20 cm
Height: 265 cm (surround) – opening 245 cm

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Door_Side_Frame_01
- SM_LM_Door_Side_LeafL_01 (68 × 8 × 245)
- SM_LM_Door_Side_LeafR_01

Material Slots Needed:
- M_LM_WoodDark
- M_LM_Gold
- M_LM_StoneLight

UVs Needed:
Yes

Moving Parts:
Yes (for future interaction; placed closed for now)

Pivot Location:
Frame: bottom centre of the opening, on the wall's front face. Leaves: bottom of the hinge edge.

Collision Type:
Simple custom collision – one UCX box per leaf, UCX boxes for the frame.

LOD Needed:
No (Nanite)

Modular:
Yes (fits SM_LM_Wall_Lower_Door_01 and SM_LM_Wall_Upper_Door_01)

Recommended Export:
FBX

Extra Notes:
About 8–12k triangles.

---

MODEL NEEDED:
Name: Arched Window (SM_LM_Window_Arched_01)

Purpose:
Tall upper-wall windows: 3 per side wall and 2 on the north wall, all above the galleries. The night sky shows through them.

Description:
Tall round-arched window with a stone or gold frame, thin mullions and a small sill. The glass is a separate piece so it can get the emissive night-sky material.

Approximate Size:
Width: 170 cm (frame) – opening 136 cm
Depth: 41 cm (fills the wall thickness)
Height: 435 cm (frame) – opening 408 cm

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Window_Arched_Frame_01 (frame + mullions + sill)
- SM_LM_Window_Arched_Glass_01 (single flat pane following the arch)

Material Slots Needed:
- M_LM_StoneLight
- M_LM_Gold
- M_LM_WindowGlass

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre of the opening, on the room-facing face.

Collision Type:
None (the wall behind provides collision).

LOD Needed:
No (Nanite for the frame)

Modular:
Yes (fits SM_LM_Wall_Upper_Window_01)

Recommended Export:
FBX

Extra Notes:
The sill must stick out 5 cm or less. About 3–6k triangles.

---

MODEL NEEDED:
Name: Grand Staircase (SM_LM_Staircase_Grand_01)

Purpose:
The two grand staircases along the west and east walls, rising north to the galleries. Model one flight; I'll mirror it in Unreal for the other side.

Description:
Marble treads with dark stone risers, a blue carpet runner with gold stair rods down the middle, and a solid stone stringer on the open side. The flight is solid underneath all the way to the floor (not walk-under). A sloped balustrade runs along the open side, with a newel post at the bottom.

Approximate Size:
Width: 238 cm (walkable stair width)
Depth: 734 cm (run from the first step's front edge to the gallery edge = 714 cm, plus a 20 cm newel overhang)
Height: 392 cm (36 risers of 10.9 cm; treads 20.4 cm deep; the last riser is the gallery floor edge, so the model has 35 steps)

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Staircase_Grand_Flight_01 (steps + runner + solid body)
- SM_LM_Staircase_Grand_Balustrade_01 (sloped handrail + balusters: 61 cm tall measured vertically above the step nosings, 14 cm wide, full flight length)
- SM_LM_Staircase_Grand_Newel_01 (27 × 27 × 88 with a finial)

Material Slots Needed:
- M_LM_Marble
- M_LM_StoneDark
- M_LM_Carpet
- M_LM_Gold

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Floor level, at the front edge of the first step, centred on the stair width. The flight rises toward Blender +Y (the first step faces −Y).

Collision Type:
Simple custom collision: one convex UCX wedge for the whole flight (floor → sloped plane through the step nosings → vertical back face), and one UCX box for the balustrade. The invisible ramp and side blockers already in the level stay.

LOD Needed:
No (Nanite)

Modular:
No (mirrored for the second side)

Recommended Export:
FBX

Extra Notes:
Rise and run must stay exact: 10.88 cm × 36 and 20.4 cm × 35, or the stairs won't line up with the gallery and the collision ramp. Model the **west** flight: walking up it, the wall is on your left and the open (balustrade) side is on your right. About 15–30k triangles.

---

MODEL NEEDED:
Name: Balustrade Kit (SM_LM_Balustrade_*)

Purpose:
Railings along the gallery edges (U-shape, about 22 m total), the vestibule edge on both sides of the entry steps, and the porch.

Description:
Classic stone balustrade: base rail, turned balusters, top rail with a thin gold cap. Square posts with caps. A larger pedestal post carries the crowned dog statues at the top of the entry steps.

Approximate Size:
Width: 136 cm (straight section)
Depth: 14 cm
Height: 61 cm

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Balustrade_Straight_01 – 136 × 14 × 61
- SM_LM_Balustrade_Post_01 – 27 × 27 × 70
- SM_LM_Balustrade_PedestalPost_01 – 41 × 41 × 102 (top must be flat for a statue)

Material Slots Needed:
- M_LM_StoneLight
- M_LM_Gold

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre (the straight section's pivot is the centre of its length, on the bottom).

Collision Type:
Simple custom collision – one UCX box per piece. The invisible blockers above the rails stay.

LOD Needed:
No (Nanite)

Modular:
Yes – 136 cm is half a wall bay.

Recommended Export:
FBX

Extra Notes:
About 2–4k triangles per straight section (balusters are where the triangles go).

---

MODEL NEEDED:
Name: Gallery Column + Gallery Fascia (SM_LM_Column_Gallery_01, SM_LM_GalleryFascia_01)

Purpose:
Columns holding up the gallery edges (6 instances) and the decorative front edge of the gallery floor slab.

Description:
Column: square stone column with a moulded base, a gold ring below a simple capital, and a small corbel on top. Fascia: 27 cm tall moulded edge band with small corbels hanging 20 cm below it every 68 cm.

Approximate Size:
Width: 41 cm (column) / 136 cm (fascia section)
Depth: 41 cm (column) / 12 cm (fascia)
Height: 364 cm (column, floor to underside of the gallery) / 47 cm (fascia incl. corbels)

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Column_Gallery_01
- SM_LM_GalleryFascia_01 (straight 136 cm)
- SM_LM_GalleryFascia_Corner_01

Material Slots Needed:
- M_LM_StoneLight
- M_LM_StoneDark
- M_LM_Gold

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Column: bottom centre. Fascia: top centre of the back face (it hangs on the slab edge).

Collision Type:
Column: one UCX box. Fascia: none.

LOD Needed:
No (Nanite)

Modular:
Yes

Recommended Export:
FBX

Extra Notes:
About 2–5k triangles each.

---

MODEL NEEDED:
Name: Central Fountain (SM_LM_Fountain_01)

Purpose:
The hero fountain in the middle of the hall, south of the grand rug. It is also reused (scaled about 1.15×) as the exterior garden fountain.

Description:
Round luxury fountain: a low walkable marble plinth step, a dark stone lower basin with gold rim trim and gold leaf-emblem plaques on 4 sides, a centre column, a smaller upper bowl, and a gold crown on top with blue gem inlays (emissive). The water surfaces are separate flat discs.

Approximate Size:
Width: 517 cm (plinth)
Depth: 517 cm
Height: 218 cm (top of crown)

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- Plinth step: Ø 517 × 11 cm (walkable)
- Lower basin: outer Ø 354, rim top 58 cm above the floor, inner floor about 30 cm below the rim
- Centre column: Ø 75 up to 177 cm
- Upper bowl: Ø 177, from 122 to 139 cm
- Crown: Ø 84, from 177 to 218 cm (gems as their own material slot)
- Gold trims and emblem plaques (can be part of the basin)
- SM_LM_Fountain_WaterLower_01: flat disc Ø 326 at 50 cm (separate mesh)
- SM_LM_Fountain_WaterUpper_01: flat disc Ø 160 at 137 cm (separate mesh)

Material Slots Needed:
- M_LM_Marble
- M_LM_StoneDark
- M_LM_Gold
- M_LM_GemBlue (emissive)
- M_LM_Water (water discs only)

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre

Collision Type:
Simple custom collision: UCX convex 16-sided cylinder for the plinth (11 cm, walkable step), a UCX convex cylinder for the basin up to the rim, and a UCX for the centre column. The water discs have no collision. An invisible no-jump cylinder already sits over the water.

LOD Needed:
No (Nanite for the stone/gold; the water discs are simple planes)

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 25–40k triangles. The crown silhouette is important from the entry view, so give it clear points. Spray and falling water will be Niagara, attached at the upper bowl rim and the crown.

---

MODEL NEEDED:
Name: Fireplace (SM_LM_Fireplace_01)

Purpose:
The two fireplaces in the west and east lounges. The west one has the "Sticky the Watchdog Merchant" portrait above it.

Description:
Lower section of a stone chimney breast with a recessed firebox, a carved light-stone surround (jambs, lintel, deep mantel shelf with gold trim), a marble hearth slab, and an iron grate with a log pile. Above 400 cm the chimney breast continues as a plain box in Unreal.

Approximate Size:
Width: 381 cm (mantel) – chimney breast 340 cm
Depth: 76 cm (breast 54 + mantel 22)
Height: 400 cm (mantel top at 178 cm, firebox opening 163 W × 120 H × 35 deep)

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Fireplace_Breast_01 (340 × 54 × 400 with the firebox recess)
- SM_LM_Fireplace_Surround_01 (jambs + lintel + mantel)
- SM_LM_Fireplace_Hearth_01 (272 × 54 × 8)
- SM_LM_Fireplace_Grate_01 (grate + logs)

Material Slots Needed:
- M_LM_StoneDark
- M_LM_StoneLight
- M_LM_Marble
- M_LM_Gold
- M_LM_IronWood (grate + logs)

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre of the back face (the face against the wall).

Collision Type:
Simple custom collision: one UCX box for the breast that also closes the firebox front (so the player can't walk into the fire), and one thin UCX box for the hearth (8 cm, walkable).

LOD Needed:
No (Nanite)

Modular:
No

Recommended Export:
FBX

Extra Notes:
Fire, embers and glow will be Niagara plus a light. About 15–25k triangles.

---

## PRIORITY 2

MODEL NEEDED:
Name: Sofa (SM_LM_Sofa_01)

Purpose:
Lounge sofas facing the fireplaces (west and east).

Description:
Chesterfield-style tufted purple velvet sofa, rolled arms, short dark wood legs, gold piping, 2–3 cushions.

Approximate Size:
Width: 156 cm
Depth: 65 cm
Height: 58 cm (seat at 31 cm)

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- Sofa body
- SM_LM_Cushion_01 (reusable loose cushion)

Material Slots Needed:
- M_LM_FabricPurple
- M_LM_WoodDark
- M_LM_Gold

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre

Collision Type:
Simple custom collision – UCX box for the seat and one for the back.

LOD Needed:
Yes

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 8–12k triangles.

---

MODEL NEEDED:
Name: Armchair (SM_LM_Armchair_01)

Purpose:
Two armchairs per lounge.

Description:
Tufted wingback armchair matching the sofa (purple or royal-blue velvet, dark wood legs, gold trim).

Approximate Size:
Width: 61 cm
Depth: 61 cm
Height: 58 cm (a wingback may go up to 75 cm)

Units:
Centimeters

Separate Pieces Needed:
No

List Separate Pieces:
- None

Material Slots Needed:
- M_LM_FabricPurple
- M_LM_WoodDark
- M_LM_Gold

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre

Collision Type:
Simple custom collision – UCX box for the seat and one for the back.

LOD Needed:
Yes

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 5–8k triangles.

---

MODEL NEEDED:
Name: Coffee Table + Chess Table (SM_LM_CoffeeTable_01, SM_LM_ChessTable_01)

Purpose:
Coffee table in the west lounge and chess table in the east lounge (the east seating in the pixel-art reference).

Description:
Dark wood with gold edge trim and carved legs. The chess table has an inlaid board. The chess set is a separate small mesh.

Approximate Size:
Width: 88 cm (coffee) / 54 cm (chess)
Depth: 48 cm (coffee) / 54 cm (chess)
Height: 31 cm (coffee) / 48 cm (chess)

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_CoffeeTable_01
- SM_LM_ChessTable_01
- SM_LM_ChessSet_01 (32 pieces merged into one mesh)

Material Slots Needed:
- M_LM_WoodDark
- M_LM_Gold
- M_LM_Marble (chessboard)

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre

Collision Type:
Simple (one UCX box each); the chess set has none.

LOD Needed:
Yes

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 2–5k triangles each.

---

MODEL NEEDED:
Name: Bookshelf (SM_LM_Bookshelf_01)

Purpose:
Tall bookshelves under the galleries.

Description:
Dark wood bookcase with an arched top, gold trim, 5 shelves. The books are separate so they can vary.

Approximate Size:
Width: 163 cm
Depth: 34 cm
Height: 218 cm

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Bookshelf_01 (empty case)
- SM_LM_BookRow_01, SM_LM_BookRow_02 (about 40 cm rows of books, 2 variations)

Material Slots Needed:
- M_LM_WoodDark
- M_LM_Gold
- M_LM_Books (atlas)

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre of the back face.

Collision Type:
Simple – one UCX box for the case; the book rows have none.

LOD Needed:
Yes

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 3k (case) + 2k per book row.

---

MODEL NEEDED:
Name: Knight Armor (SM_LM_KnightArmor_01)

Purpose:
Suits of armour flanking the front doors and the gallery doors (6 instances).

Description:
Standing full plate armour on a low square base, holding a halberd (separate), with a small gold crest on the breastplate.

Approximate Size:
Width: 41 cm
Depth: 48 cm
Height: 129 cm (including a 10 cm base; the halberd reaches 165 cm)

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- Armour + base
- SM_LM_Halberd_01

Material Slots Needed:
- M_LM_Steel
- M_LM_Gold
- M_LM_StoneDark (base)

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre

Collision Type:
Simple custom collision – one UCX box (base to shoulders).

LOD Needed:
No (Nanite)

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 15–25k triangles.

---

MODEL NEEDED:
Name: Crowned Lion Statue + Pedestal (SM_LM_LionStatue_01, SM_LM_Pedestal_01)

Purpose:
The two stone lions flanking the fountain (east and west), facing the entrance.

Description:
Seated stone lion wearing a small gold crown, on a square stone pedestal with a gold leaf-emblem plaque.

Approximate Size:
Width: 75 cm (pedestal) / 61 cm (lion)
Depth: 75 cm (pedestal) / 41 cm (lion)
Height: 68 cm (pedestal) + 75 cm (lion) = 143 cm

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_LionStatue_01
- SM_LM_Pedestal_01 (reusable)

Material Slots Needed:
- M_LM_StoneLight
- M_LM_Gold

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre (the lion's pivot is at the bottom of its own base, so it sits on top of the pedestal).

Collision Type:
Pedestal: one UCX box. Lion: none (out of reach on top of the pedestal).

LOD Needed:
No (Nanite)

Modular:
No

Recommended Export:
FBX

Extra Notes:
This is a sculpt-level asset, so a high triangle count is fine with Nanite. Bake to a decimated mesh if Nanite is off in your project.

---

MODEL NEEDED:
Name: Crowned Dog Statue (SM_LM_DogStatue_01)

Purpose:
Two statues on the pedestal posts at the top of the entry steps (the "watchdog" motif from the pixel-art reference).

Description:
Sitting stone dog wearing a gold crown and a chain collar, looking toward the vestibule.

Approximate Size:
Width: 34 cm
Depth: 27 cm
Height: 51 cm

Units:
Centimeters

Separate Pieces Needed:
No

List Separate Pieces:
- None (stands on SM_LM_Balustrade_PedestalPost_01)

Material Slots Needed:
- M_LM_StoneLight
- M_LM_Gold

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre

Collision Type:
None (out of reach on top of the post)

LOD Needed:
No (Nanite)

Modular:
No

Recommended Export:
FBX

Extra Notes:
Sculpt-level asset, same notes as the lion.

---

MODEL NEEDED:
Name: Grand Chandelier (SM_LM_Chandelier_01)

Purpose:
Three chandeliers: over the fountain, over the grand rug, and a smaller copy (scaled 0.62) in the vestibule. They are the main warm light sources.

Description:
Two-tier gold candle chandelier (about 16 candles on the lower ring, 8 on the upper), with crystal drops optional. Candles are opaque; flames are a separate small mesh so they can use an emissive material.

Approximate Size:
Width: 218 cm
Depth: 218 cm
Height: 136 cm (body) + chain

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Chandelier_01 (body + candles)
- SM_LM_Chandelier_Flames_01 (flame cards/meshes, same pivot)
- SM_LM_ChandelierChain_01 (50 cm tileable chain segment, pivot at top)

Material Slots Needed:
- M_LM_Gold
- M_LM_Candle
- M_LM_Flame (emissive)

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Top centre (the hanging point)

Collision Type:
None

LOD Needed:
Yes (the flames can't be Nanite; the body can)

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 20–35k triangles. The hanging point sits 340 cm below the ceiling in the level; the chain is tiled.

---

MODEL NEEDED:
Name: Banner (SM_LM_Banner_Tall_01, SM_LM_Banner_Wide_01)

Purpose:
Blue-and-gold hanging banners on the walls ("GOOD PLANTS BETTER PEOPLE", "HIGHER TOGETHER", crown banners).

Description:
Cloth banner with gentle vertical folds, gold fringe along a pointed bottom edge, and a horizontal rod with gold finials at the top. The front face is UV'd flat (0–1) so emblem and text textures map cleanly.

Approximate Size:
Width: 136 cm (tall) / 354 cm (wide)
Depth: 10 cm (folds + rod)
Height: 394 cm (tall) / 476 cm (wide)

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Banner_Tall_01
- SM_LM_Banner_Wide_01

Material Slots Needed:
- M_LM_BannerCloth (textured)
- M_LM_Gold (rod, finials, fringe)

UVs Needed:
Yes

Moving Parts:
No (optional cloth or wind later)

Pivot Location:
Top centre, on the back (wall) side of the rod.

Collision Type:
None

LOD Needed:
Yes

Modular:
Yes – I'll scale the tall one for the 177 × 408 side-wall and 95–136 cm vestibule versions.

Recommended Export:
FBX

Extra Notes:
About 2–4k triangles each.

---

MODEL NEEDED:
Name: Planter (SM_LM_Planter_01)

Purpose:
Square planters around the fountain and throughout the hall (plants come from Megascans/Fab).

Description:
Square light-stone planter with a gold rim band and a leaf emblem on each side. The soil surface is at 36 cm.

Approximate Size:
Width: 54 cm
Depth: 54 cm
Height: 41 cm

Units:
Centimeters

Separate Pieces Needed:
No

List Separate Pieces:
- None

Material Slots Needed:
- M_LM_StoneLight
- M_LM_Gold
- M_LM_Soil

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre

Collision Type:
Simple – one UCX box (it is flagged "can't step up on" in Unreal).

LOD Needed:
No (Nanite)

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 1–2k triangles.

---

## PRIORITY 3

MODEL NEEDED:
Name: Grandfather Clock (SM_LM_GrandfatherClock_01)

Purpose:
Tall clock under the east gallery near the front doors (pixel-art reference).

Description:
Dark wood long-case clock, gold face and trim, glass door showing the pendulum.

Approximate Size:
Width: 41 cm
Depth: 37 cm
Height: 156 cm

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- Case
- SM_LM_ClockPendulum_01
- SM_LM_ClockHandHour_01, SM_LM_ClockHandMinute_01

Material Slots Needed:
- M_LM_WoodDark
- M_LM_Gold
- M_LM_Glass

UVs Needed:
Yes

Moving Parts:
Yes – the pendulum swings (pivot at its top) and the hands rotate (pivots at the dial centre).

Pivot Location:
Case: bottom centre of the back face. Moving parts: at their rotation points.

Collision Type:
Simple – one UCX box.

LOD Needed:
Yes

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 5–8k triangles.

---

MODEL NEEDED:
Name: Desk + Glowing Orb (SM_LM_Desk_01, SM_LM_Orb_01)

Purpose:
Writing desk with a glowing blue orb under the east gallery (pixel-art reference).

Description:
Small dark-wood writing desk with gold handles. The orb is a glass sphere on a gold tripod stand.

Approximate Size:
Width: 82 cm (desk) / 22 cm (orb)
Depth: 54 cm (desk) / 22 cm (orb)
Height: 53 cm (desk) / 30 cm (orb + stand)

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Desk_01
- SM_LM_Orb_01 (stand + sphere; sphere in its own material slot)

Material Slots Needed:
- M_LM_WoodDark
- M_LM_Gold
- M_LM_OrbGlow (emissive)

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre

Collision Type:
Desk: one UCX box. Orb: none.

LOD Needed:
Yes

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 3–5k triangles.

---

MODEL NEEDED:
Name: Bust on Pedestal (SM_LM_Bust_01, SM_LM_BustPedestal_01)

Purpose:
Decorative busts at both ends of the north gallery.

Description:
Classical marble bust on a slim fluted pedestal with a gold ring.

Approximate Size:
Width: 34 cm (pedestal) / 27 cm (bust)
Depth: 34 cm (pedestal) / 27 cm (bust)
Height: 75 cm (pedestal) + 34 cm (bust)

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_Bust_01
- SM_LM_BustPedestal_01

Material Slots Needed:
- M_LM_Marble
- M_LM_Gold

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre

Collision Type:
Pedestal: one UCX box. Bust: none.

LOD Needed:
No (Nanite)

Modular:
No

Recommended Export:
FBX

Extra Notes:
Sculpt-level asset.

---

MODEL NEEDED:
Name: Wall Sconce (SM_LM_WallSconce_01)

Purpose:
Candle sconces on the walls and pilasters (about 24 instances) – warm light points.

Description:
Gold three-arm candle sconce with a leaf-shaped back plate. The flames are a separate mesh.

Approximate Size:
Width: 30 cm
Depth: 20 cm
Height: 45 cm

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- SM_LM_WallSconce_01 (body + candles)
- SM_LM_WallSconce_Flames_01

Material Slots Needed:
- M_LM_Gold
- M_LM_Candle
- M_LM_Flame (emissive)

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Centre of the back plate (the wall contact point).

Collision Type:
None

LOD Needed:
Yes

Modular:
No

Recommended Export:
FBX

Extra Notes:
Keep it light (about 1–2k triangles) because there are many instances.

---

MODEL NEEDED:
Name: Floor Candelabra (SM_LM_Candelabra_Floor_01)

Purpose:
Standing candelabras around the fountain and beside the doors (pixel-art reference).

Description:
Tall gold floor candelabra with a tripod base and 5–7 candles.

Approximate Size:
Width: 34 cm
Depth: 34 cm
Height: 120 cm

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- Body + candles
- Flames (separate mesh)

Material Slots Needed:
- M_LM_Gold
- M_LM_Candle
- M_LM_Flame (emissive)

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre

Collision Type:
Simple – one UCX box or capsule around the stem and base, so the player slides around it instead of snagging.

LOD Needed:
Yes

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 2–4k triangles.

---

MODEL NEEDED:
Name: Candle Cluster (SM_LM_CandleCluster_01)

Purpose:
Small candle groups on mantels, tables, the fountain plinth and window sills.

Description:
3–5 pillar candles of different heights, with drips, on a small gold tray. The flames are a separate mesh.

Approximate Size:
Width: 20 cm
Depth: 20 cm
Height: 25 cm

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- Candles + tray
- Flames

Material Slots Needed:
- M_LM_Candle
- M_LM_Gold
- M_LM_Flame (emissive)

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre

Collision Type:
None

LOD Needed:
Yes

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 500–1,500 triangles.

---

MODEL NEEDED:
Name: Portrait Frame (SM_LM_PortraitFrame_01)

Purpose:
Ornate frames above the fireplaces (the west one holds the "Sticky – The Watchdog Merchant" portrait).

Description:
Heavy carved gold frame. The canvas is a separate flat plane UV'd 0–1 for the portrait texture.

Approximate Size:
Width: 156 cm
Depth: 5 cm
Height: 190 cm

Units:
Centimeters

Separate Pieces Needed:
Yes

List Separate Pieces:
- Frame
- SM_LM_PortraitCanvas_01 (plane)

Material Slots Needed:
- M_LM_Gold
- M_LM_Portrait

UVs Needed:
Yes

Moving Parts:
No

Pivot Location:
Bottom centre of the back face

Collision Type:
None

LOD Needed:
Yes

Modular:
No

Recommended Export:
FBX

Extra Notes:
About 3–6k triangles.
