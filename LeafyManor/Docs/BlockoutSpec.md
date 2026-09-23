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

### Where the references disagree (decisions I made; each is easy to change)
1. **Front doors on the north wall.** Both hero views look at open exterior doors across the room. The player spawns in the **sunken south vestibule facing north**, so the first thing they see is the hero composition. The floor plan's "player spawn" arrow in the north corridor contradicts its own "ENTRANCE" arrow at the south. Moving the spawn means moving one actor (`PlayerStart_LM_Vestibule`).
2. **Stairs are straight flights along the side walls**, rising north to the galleries, as in both hero views. The floor plan draws them diagonally in the NW/NE corners. Straight flights are more reliable for the collision ramp and easier to model.
3. **Two fireplaces (W and E)** for the requested symmetry. The east lounge gets the chess table and the orb desk from the pixel-art view.
4. **U-shaped gallery** (west + north + east) at 392 cm, connecting both staircases above the front doors.
5. **Sunken vestibule** (−65 cm, 6 steps) from the pixel-art view, with stone cheek walls, balustrade and crowned dog statues on the pillars.

## 2. Scale: fitting the hall to your character

| Item | Value |
|---|---|
| Character mesh (both FBX variants) | **97.8 cm** tall, T-pose span 89–96 cm, depth about 41 cm; UE5 Mannequin bone names; exported from Blender (FBX Units Scale) |
| Assumed capsule | radius 28, half-height 50 (edit `PLAYER` in the layout file if yours differs) |
| `LM_SCALE` | 97.8 / 180 × 1.25 (grandeur) = **0.68** |
| Stair riser / tread | 10.9 / 20.4 cm (28°); entry steps 10.9 / 27.2 cm (22°) |
| Railing height | 61 cm (about chest height; the character sees over it) |
| Doors | grand 272 × 354, side 136 × 245 |
| Clear widths | stairs 224, galleries 224, lounge aisles ≥ 88 cm (≥ 3× the capsule diameter; still passes with the UE template capsule r42/hh96) |
| Headroom | under the galleries 364 cm, ceiling 1088 cm |

## 3. Plan

```
                           N (+X)
                   ┌──── PORCH (x 1265..1768) ────┐   exterior night garden beyond, visual only
                   │   leaves open ║   ║          │   invisible walls around the porch
  x 1224 ┌─────────┴─────────── FRONT DOORS 272 ──┴────────────┐
         │ bookcase   N GALLERY z392 (x 986..1224) over doors   │ clock/desk
         │ door  W GALLERY z392      knights       E GALLERY    │ door
  x  544 │ bookcase  (y ±714..±952)  runner                     │
         │ ▲ W STAIR                 GRAND RUG                ▲ │ E STAIR
         │ ▲ (x -170..544)          (x -41..707)              ▲ │ (36 × 10.9 cm)
  x -170 │ ▲                                                  ▲ │
         │ FIREPLACE W ─ lounge   lion ◯ FOUNTAIN ◯ lion  lounge ─ FIREPLACE E
         │ (x -714..-374)         planters (x -340)             │
  x -952 └────────── balustrade ═ STEPS ═ balustrade ──────────┘
                     │  VESTIBULE z -65  (x -1496..-952)   │
                     │  ★ PlayerStart facing north         │
  x -1496            └──────── inner grand doors (closed) ─┘
                               S
```

Hall interior 2176 (N–S) × 1904 (E–W) × 1088 cm. Vestibule 544 × 816. Porch 503 × 680.

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

* Level: `/Game/LeafyManor/Maps/LVL_LM_EntranceHall_Blockout`
* Blockout meshes: `/Game/LeafyManor/Architecture/Blockout/SM_LM_BO_{Cube,Cylinder,Cone,Sphere}`
* Materials: `/Game/LeafyManor/Materials/Blockout/M_LM_Blockout` (1 m world-space checker, tinted per material) + `MI_LM_BO_*`, and `M_LM_BO_Collision`
* Outliner folders: `LeafyManor_Blockout/{Architecture/*, Collision/Blockers, Props/*, Furniture/*, Exterior, Lighting, Gameplay}`
* Every generated actor is tagged `LM_Blockout` + `LM_Kind_<Kind>`. `LM_Kind_*` is what the later "swap proxy → Blender mesh" step keys on.
