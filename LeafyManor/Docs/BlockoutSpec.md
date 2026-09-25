# Leafy Manor Entrance Hall: Blockout Spec

Source of truth: `Unreal/Python/leafy_manor_layout.py`. Numbers here are **final cm** (design units × `LM_SCALE` 0.68) unless marked *du*.
Axes: **+X = North** (exterior front doors), **+Y = East**, **+Z = Up**. Origin = hall centre line at main-floor level.

## 1. Reference analysis

| Reference | What it establishes |
|---|---|
| Master sheet, *Main View* | Symmetric hall, central crowned fountain with blue glow, lions on pedestals either side, blue/gold runner to open doors with a night garden, **stairs on both sides rising to a back balcony**, lounges with fireplaces on both side walls, banners, candle sconces, chandeliers. |
| Master sheet, *Floor Plan* | Cross-shaped plan with W/E lounge wings (fireplace + sofas), big leaf rug north of the fountain, main path on the N–S axis, entrance at the south, stairs toward the north corners. |
| Master sheet, *Elevations* | Front wall: tall arched double doors + banners. Left wall: bookshelves, sofa, fireplace, painting. Right wall: staircase, knight, doorway. Back wall: upper balcony, knights beside a door. |
| Master sheet, *Details / Materials* | Fountain, door, banner, lion, chandelier and fireplace close-ups. Materials: black and cream marble with gold veins, gold inlay, dark stone walls, dark wood, gold trim, royal-blue fabric, purple velvet, foliage, glowing water, candle flame. |
| Pixel-art hero view | Camera from the south looking north: open doors to the night garden at the far end; fireplace lounge NW with the *Sticky* portrait; grand staircase NE along the east wall; chess / armchairs / orb desk to the east; big leaf rug; fountain flanked by crowned dog statues and planters; **the hall floor is a raised platform with balustrades, and central steps lead down to a lower entry landing** ("SAME SPOT. DIFFERENT WORLD." rug). |

### Layout decisions (v2, after your floor-plan diorama)
Your diorama (`Reference/FloorPlan_Diorama_TopView.png`, turned 45° square) is the plan of record:
1. **Fountain in the centre.** It's ringed by planters and two crowned lions, with the carpet runner on the north–south axis.
2. **Two 45° grand staircases** rise from beside the fountain to landings in the NW / NE corners of a U-shaped balcony (west, north and east sides).
3. **Lounges in the middle of the west and east walls.** Each has a fireplace, sofas, table, chair and rug.
4. **Props in the south corners:** globe and chest on one side, chess table and chairs on the other. The vestibule and spawn are to the south.
5. **Front arch in the middle of the north wall.** It opens onto a porch and the night garden (castle backdrop, moon, exterior fountain).
6. **One story = 514 cm**, the height of one of your wall kit sections. The balcony floor is at 514 cm and the ceiling at 1074 cm (two stories + cornice). Steps are 12.2 cm high × 20.4 cm deep (31°).
7. The sunken entry of the first blockout was dropped because the diorama shows a level entrance.

## 2. Scale

| Item | Value |
|---|---|
| Character mesh | **97.8 cm** tall (both FBX variants), UE5 Mannequin bone names |
| Assumed capsule | radius 28, half-height 50 (edit `PLAYER` in `leafy_manor_layout.py`) |
| `LM_SCALE` | 97.8 / 180 × 1.25 = **0.68** (design units → cm) |
| Hall | 24.5 × 24.5 m (9 × 9 wall sections of 272 cm), 10.7 m to the ceiling |
| Stairs | 41 treads, 12.2 cm risers, 20.4 cm treads, 238 cm wide, 31° |
| Balcony | 514 cm up, 238 cm deep, railing 61 cm |
| Front arch | 141 cm wide × 355 cm to the spring of the arch |

## 3. Plan

See `Validation/walkability_map.png` (north up; left = ground level, right = balcony level) and
`Preview/room_high.png`.

## 4. Collision rules used

| Element | Collision |
|---|---|
| Floors, walls, stairs, galleries, columns, rails, doors | `BlockAll` (simple box / k-DOP collision on the blockout meshes) |
| Stairs (both grand flights + entry steps) | Step boxes **plus** an invisible sloped ramp over the nosings (the character and camera glide instead of bumping) |
| Gallery edges, stair open side | Balustrade (61 cm) **plus** an invisible wall up to the ceiling (can't jump off) |
| Porch | Balustrade + 476 cm invisible walls (can't leave the map) |
| Fountain | Walkable 11 cm plinth, solid basin, invisible no-jump cylinder over the water |
| Furniture, statues, planters, armour | `BlockAll` + **CanCharacterStepUpOn = No** (never climbed onto by accident) |
| Rugs, banners, windows, portraits, chandeliers, water, fire, exterior | `NoCollision` (nothing to snag on) |
| Invisible walls | Profile `InvisibleWall` with **Camera = Ignore** (no camera popping), hidden in game, translucent red in the editor |

## 5. Blockout lighting (work lights; the full lighting pass is step 11)

All movable, so Lumen needs no lighting build. Warm chandelier lights ×3, fireplace glow ×2, blue fountain light, blue exterior fountain light, cool moon directional light coming through the front doors, low sky light, and an unbound post-process volume clamping auto-exposure (EV100 0–8).

## 6. Outliner / content organisation

* Level: `/Game/LeafyManor/Maps/LVL_LM_EntranceHall`
* Blockout meshes: `/Game/LeafyManor/Architecture/Blockout/SM_LM_BO_{Cube,Cylinder,Cone,Sphere}`
* Materials: `/Game/LeafyManor/Materials/Blockout/M_LM_Blockout` (1 m world-space checker, tinted per material) + `MI_LM_BO_*`, and `M_LM_BO_Collision`
* Outliner folders: `LeafyManor/{Architecture/*, Collision/*, Props/*, Furniture/*, Exterior, Lighting, Gameplay}`
* Every generated actor is tagged `LM_Blockout` + `LM_Kind_<Kind>`. `LM_Kind_*` is what the later "swap proxy → Blender mesh" step keys on.
