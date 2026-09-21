# Optical table enclosure frame — design and cut list

Table 2.00 × 1.50 m · shelf at ~2.0 m · 7 kg now, 20 kg design load.
Prices ex-VAT, checked 15 Sep 2026.

## Geometry

Frame **stands on the floor and straddles the table — it never touches it.**

**Clearance: 50 mm per side** (decided).

| | |
|---|---|
| Frame outer footprint | **2180 × 1680 mm** |
| Inner clear opening | 2100 × 1600 mm |
| Upright profile length | **2050 mm** (unchanged — castors add height below) |
| Castors | 6 levelling castors, ~80–110 mm each |
| **Overall height** | **~2140–2160 mm**, shelf surface ~2090–2110 mm |
| Uprights | 6 — four corners + two mid-span on the long sides, at 1090 mm centres |
| Enclosed volume above table | ~4.4 m³ |

**Check ceiling clearance** — you need ≥2.25 m, and more to work comfortably at the top.
Confirm the castor's exact overall height before ordering, since that sets the final number.

**The frame will not fit through a doorway** at 2180 × 1680 mm. The castors are for
repositioning within the room — rolling it back to reach the table, say. To move it out,
it has to be unbolted, which is fine since it's a bolted structure throughout.

50 mm covers non-contact on a floated table (~30 mm, since the top moves as it floats and
as load changes) with enough margin to assemble without banging the table.

> **One check before ordering.** The binding constraint is the table's support structure at
> **floor level**, not the top. Measure the widest point of the base including levelling
> feet and any pneumatic isolators. The frame's 2100 × 1600 mm inner opening must exceed
> that, plus ~40 mm for the frame's own feet to land beside it. If the base protrudes past
> the 2.0 × 1.5 m top, widen the frame to suit — it costs ~€22 per 100 mm, so err wide
> rather than rebuild.

## Load check — 40×40 is comfortable

With mid-span uprights the longest shelf span is 1150 mm. 20 kg shared over two
longitudinal beams, so 5 kg per span:

δ = 5wL⁴/384EI, w = 42.7 N/m, L = 1.15 m, E = 70 GPa, I ≈ 9 cm⁴ → **δ ≈ 0.15 mm**

Negligible. 40×40 slot 8 is chosen for the *uprights* (2.05 m tall, freestanding, sway and
buckling matter) rather than for the shelf. Don't drop to 30×30 for the verticals.

## Cut list — 40×40, ranura 8

Frame 2180 × 1680 × 2050 mm. **35 m of 40×40 ranura 8, cut to these lengths.**

| # | Member | Length | Qty | Total |
|---|---|---|---|---|
| 1 | Uprights | 2050 mm | 6 | 12,30 m |
| 2 | Top perimeter, long | 2180 mm | 2 | 4,36 m |
| 3 | Top perimeter, short | 1600 mm | 2 | 3,20 m |
| 4 | Mid rail, long (between uprights) | 1050 mm | 4 | 4,20 m |
| 5 | Mid rail, short | 1600 mm | 2 | 3,20 m |
| 6 | Shelf longitudinal (600 mm in from back) | 2100 mm | 1 | 2,10 m |
| 7 | Shelf cross-members | 600 mm | 4 | 2,40 m |
| | | | **Subtotal** | **31,76 m** |
| | +10 % waste / spares | | | **≈ 35 m** |

| 8 | 45° diagonal braces (if using struts) | ~300 mm | 8 | 2,40 m |

Short members are 1680 − 2×40 = 1600 mm, i.e. they fit *between* the full-length long
rails. Mid rails sit at ~1100 mm. Diagonals are cut 45° at **both** ends.

### Ordering checklist

1. **Measure the table base at floor level** — the one thing that can invalidate the cut list.
2. Send the table above to a specialist as a cut list; ask for **cut to length, square ends**.
3. Compare silver vs black anodised on 35 m before choosing (see below).
4. Order ~46 corner brackets, 8 diagonal braces + their 45° connectors, and ~300
   T-nuts/bolts.
5. **6 levelling castors** from the same supplier; confirm overall height and check it
   against ceiling clearance.
6. Sheet material, matte black paint and foam tape locally; don't buy these from Thorlabs.
7. One `AEPU1/M` for the cable feedthrough.

## The Motedis custom-frame configurator

Verified Motedis per-metre prices (ex-IVA, three quantity tiers):

| Profile | €/m |
|---|---|
| [40x40L Tipo-I ranura 8](https://www.motedis.es/es/Perfil-40x40L-Tipo-I-ran-8) | 15,92 / 14,86 / 14,43 |
| [40x80 Ligero Tipo-I ranura 8](https://www.motedis.es/es/Perfil-40x80-Ligero-tipo-I-ran-8) | 28,89 / 26,97 / 26,18 |
| [80x80L Tipo-I ranura 8](https://www.motedis.es/es/Perfil-80x80L-Tipo-I-ranura-8mm) | 47,91 / 44,72 / 43,42 |

**Motedis 40×40 at €15.92/m vs RS at €42.44/m** — 2.7× cheaper. Order the profile here
regardless of which route you take.

### What the configurator actually gives you

The diagram is a **table base**: four uprights, a top ring and one lower ring at *Höhe 2*.
It is not an enclosure frame. It has no mid-span uprights, no shelf, no diagonals, and only
two horizontal levels.

**The gap that matters:** with four uprights your panels would span **2180 mm unsupported**.
No sheet material does that. You must add mid-uprights whatever else you decide.

### Is 80×80 justified?

It's forced by the product, not chosen — and it exists because the frame has only four
legs. Uprights carry trivial axial load here (170 kg / 4 = 43 kg each); their job is sway
resistance. 80×80 has ~10× the second moment of 40×40, which is machine-base grade for a
20 kg shelf.

| | 4 × 80×80 uprights | 6 × 40×40 uprights |
|---|---|---|
| Profile cost | 8.2 m × 47,91 € = **393 €** | 12.3 m × 15,92 € = **196 €** |
| Added mass | ~43 kg | ~20 kg |

Adding two more cheap legs removes the need for the expensive ones.

### Horizontals: pick 40×80

With only four uprights the top rail spans 2180 mm. Shelf load 20 kg over two beams:

| Profile | I (typical) | Deflection |
|---|---|---|
| 40×40 | 9.3 cm⁴ | **2.0 mm** |
| 40×80 (80 mm vertical) | ~70 cm⁴ | **0.27 mm** |
| 80×80 | ~90 cm⁴ | 0.21 mm |

**40×80** is the sweet spot — 40×40 sags visibly over that span, 80×80 costs 66 % more for
no useful gain. Two rings = 15.12 m × 28,89 € = **437 €**.

### Values to enter

**The dimension depends on the upright width.** What is fixed is the *inner clear opening*,
which must be table + 2 × clearance:

| | |
|---|---|
| Inner clear, length | 2000 + 2×50 = **2100 mm** |
| Inner clear, width | 1500 + 2×50 = **1600 mm** |

Then, for 80×80 uprights:

| Convention | Length | Width |
|---|---|---|
| **Outer** (2100 + 2×80) | **2260 mm** | **1760 mm** |
| **Centre-to-centre** (2100 + 2×40) | **2180 mm** | **1680 mm** |

The 2180 × 1680 figures elsewhere in this document are **outer** dimensions for a
**40×40** frame. They coincide with the *centre-to-centre* figures for an 80×80 frame,
which is a trap — do not reuse them without checking which convention applies.

| Field | Value |
|---|---|
| Länge / length | **2260 mm** if outer · 2180 mm if centre-to-centre |
| Breite / width | **1760 mm** if outer · 1680 mm if centre-to-centre |
| Höhe 1 / height 1 | **2050 mm + castor height** (see below) |
| Höhe 2 / height 2 | **~810 mm** — puts the top of the lower rail at ~850 mm, the bottom edge of your panels |
| Horizontal profile | **40×80** |

Note the 80×80 uprights also grow the **room footprint** to 2260 × 1760 mm — 80 mm more in
each direction than the 40×40 design, before walking space.

### Ask Motedis three things before ordering

1. **Are Länge/Breite outer or centre-to-centre?** This decides 2260 vs 2180. Getting it
   wrong either loses your clearance or wastes 80 mm of room.
2. **Does Höhe 1 include the feet?** The diagram measures from the floor, which suggests it
   does. You want 2050 mm of *profile*, so the number you enter depends on the answer.
3. **What's included** — connectors, feet, cutting, assembly? This decides whether the
   configurator is good value or just expensive profile.

### Cost comparison

| | Profile |
|---|---|
| Configurator (4 × 80×80 = 8.2 m, + 2 rings of 40×80 = 15.44 m) | **839 €** |
| Loose cut list, 6 × 40×40 uprights, all 40×40, 35 m | **557 €** |

Plus, in either case, the things the configurator omits: 2 mid-uprights (~65 €), shelf
members (~72 €), diagonals (~38 €), and a second panel rail (~120 €).

**Take the configurator only if its all-in price (connectors + feet + cutting) lands near
€900.** Above ~€1200, order loose cut profile against the cut list below — you're paying
~€270 extra for 80×80 uprights the design doesn't need.

### Castor warning for the 4-leg version

Four legs instead of six means **170 kg / 4 = 43 kg per castor**, against the SM-40's 50 kg
rating. That's only 1.2× margin. Either add mid-uprights with their own castors (back to
six) or specify castors rated ≥100 kg.

## Profile cost — go to a specialist, not RS

| Source | €/m | 36 m |
|---|---|---|
| RS Componentes [187-3275](https://es.rs-online.com/web/p/tubos-y-perfiles/1873275), black, 3 m | 42,44 € | **1 527,96 €** |
| Spanish specialist (cut to length) | ~18–22 € | **~720 €** |

An €800 difference on one line item. Specialists that cut to size:
[perfilalu10](https://www.perfilalu10.com/en/17-serie-4080-slot-8),
[perfilaluminioextruido.com](https://www.perfilaluminioextruido.com/perfil-de-aluminio-40x40-ranura-8),
[tiendaperfilaluminioyaccesorios.com](https://www.tiendaperfilaluminioyaccesorios.com/perfil-aluminio-40x40-ranura-8).

**Cut-to-length is worth more than the price gap.** A frame is only as square as its worst
cut — out-of-square ends make the corner brackets fight each other and the whole structure
racks. Order it cut and assemble in an afternoon.

### Silver vs black — revised

I said "buy black" before knowing the quantity. At 36 m the 15–25 % anodising premium is
€100–250, so it's worth thinking about. **Mount the hardboard on the *inside* face of the
frame** and the extrusion sits outside the light volume entirely — then silver is fine and
the panels form a continuous black inner surface. Compare both prices before deciding;
black is the lower-risk option if you'd rather not think about it.

## Hardware

| Item | Qty | Unit | Total |
|---|---|---|---|
| Corner brackets (escuadras) 40×40 slot 8 | ~46 | 3–6 € | 140–280 € |
| **45° diagonal braces** (see below) | 8 | ~10–15 € | 80–120 € |
| T-nuts M8 slot 8 (tuercas martillo) + bolts | ~300 | 0,30–0,50 € | 90–150 € |
| **Levelling castors** (see below) | 6 | ~8–15 € | 50–90 € |
| End caps | ~12 | 1–2 € | 15–25 € |

## Bracing — use diagonals, not more brackets

A bolted rectangle with only corner brackets resists racking through the **moment
capacity of each bracket** — a small L-plate with two bolts per leg, relying on bolt
preload and slot friction. It's a semi-rigid joint at best, and it creeps.

A diagonal converts the corner into a **triangle**, so the load runs axially in
tension/compression along the strut. That is far stiffer for the same money. One diagonal
beats four extra corner brackets. This is why every frame in the reference photos has
45°-cut struts at the top corners.

**This matters more now that the frame is on castors.** Pushing a 2.15 m frame applies a
lateral load at the top — which is precisely the racking load case. Unbraced, that load is
carried entirely by bracket friction.

### Revised bracket count

| Joint type | Joints | Brackets |
|---|---|---|
| Upright → top rail (highest moment) | 6 | 2 each = 12 |
| Top perimeter corners | 4 | 2 each = 8 |
| Mid rails → uprights | 12 | 1 each = 12 |
| Shelf members | 10 | 1 each = 10 |
| Spares | | 4 |
| | | **~46** |

Down from ~70. **One bracket per joint is enough once diagonals and panels carry the
shear** — double up only at the six upright-to-top junctions and the four top corners.

### Two ways to brace

| | Pros | Cons |
|---|---|---|
| **45° strut** — 40×40 or lighter 40×20 cut 45°/45°, fixed with **45° angle connectors** (*conector angular 45°*) | strongest, what's in your photos, looks right | needs the special connector and two extra cuts |
| **Triangular gusset plate** — flat plate bolted across the corner, 2 bolts per member | cheapest, no cutting, no special parts | intrudes into the corner, slightly less stiff |

Either works. **Eight braces** — two per vertical plane at the top corners — is the
standard arrangement and what the photos show. Add the diagonals to the profile cut list
if you go the strut route (~0.3 m each, ~2.5 m total).

**The panels are still structural.** A continuous sheet screwed to the frame is actually a
better shear web than a corner diagonal, because it resists over the whole panel area
rather than at one point. The diagonals matter most (a) during assembly before panels go
on, and (b) at the top, where the shelf and the push-load live.

## Castors

**Use levelling castors, not braked castors.** This is not a preference. A braked castor
still rolls if the brake is knocked off, and with 50 mm clearance a 50 mm nudge puts the
frame against the table — destroying the whole no-contact premise. A levelling castor has
an integrated screw foot: wind it down and the **wheel lifts clear of the floor**, so the
frame sits on rigid feet and physically cannot roll. It also replaces the separate
levelling feet, so the cost is a wash.

Benchmark part, stocked in Spain (Motedis SL, Vilafamés, Castellón):

| | |
|---|---|
| Part | [Rueda niveladora SM-40](https://www.motedis.es/es/Rueda-niveladora-SM-40) (ref. LC-SM40) |
| Price | **8,38 € ex-IVA** each (33,53 € per pack of 4) |
| Load capacity | 50 kg each |
| Swing radius | 42 mm · swing interference 85 mm |
| Mounting | supplied with mounting plate for 40-series profile |

### Load check

| | |
|---|---|
| Profile, 35 m × ~1.6 kg/m | ~56 kg |
| Panels, ~13 m² | ~45 kg |
| Brackets and fasteners | ~10 kg |
| Shelf load (design) | 20 kg |
| **Total** | **~140 kg** |

Over 6 castors that's **23 kg each** against a 50 kg rating — 2.2× margin. Even with the
load thrown onto four of six it's 35 kg each, still inside spec. Adequate.

**Move the frame empty.** Roll it before loading the shelf and the margin question never
arises. When parked the load sits on the levelling feet anyway, so the wheel rating only
governs while rolling.

### Buy them with the profile

Stock on the SM-40 was showing as limited and it's overstock pricing, so treat €8.38 as a
benchmark rather than a guarantee. Every 40-series specialist stocks an equivalent —
order them from whoever cuts your profile. Same shipment, guaranteed compatibility.

Two things to specify: **non-marking grey rubber or TPE** wheels (hard nylon marks lab
floors and transmits vibration), and a total-swivel lock if the model offers one.

**Two brackets per joint, not one** — a single bracket lets the joint rotate. This is the
count people underestimate by about half.

**Leroy Merlin is genuinely useful here**: they stock slot-8
[T-nuts in 50-packs online](https://www.leroymerlin.es/productos/tuerca-de-cabeza-de-martillo-con-ranura-en-t-fijacion-de-acero-al-carbono-niquelado-para-perfil-de-aluminio-eu40-m8-19-5-10-93836865.html)
(EU40 M8) even though they don't carry the profile.

## Panels

Only the volume **above the table** has to be light-tight. Panel from ~850 mm (just below
the table surface) to 2050 mm, plus a lid:

- Sides: 8.2 m perimeter × 1.2 m = 9.84 m²
- Lid: 2.30 × 1.80 = 4.14 m²
- **≈ 14 m²**

| Source | Coverage | Cost |
|---|---|---|
| Thorlabs `TB4` black hardboard (610×610, ×3) | 1.12 m² per pack, €73,95 | **~1 100 €** for 14 m² |
| Leroy Merlin MDF/hardboard 2440×1220 + matte black paint | 2.98 m²/sheet, ~5 sheets | **~100–150 €** |

Don't buy Thorlabs hardboard by the square metre. This is the other thing Leroy Merlin is
for: sheet material, matte black paint, and black foam gasket tape.

**The panels are structural.** A rectangular frame with only corner brackets racks into a
parallelogram; sheet material screwed to the frame resists shear the way plywood sheathing
does in a timber wall. Plan on the panels doing that job — and add two temporary diagonal
braces during assembly, because the bare frame will be floppy until they're on.

Seal with black foam tape between panel and profile, and **overlap panel joints rather than
butting them**.

## Cable feedthrough — the part that fixes your actual problem

Your leak is cables through holes. The fix is not a better hole, it's **no hole**:
terminate cables at bulkhead connectors so there is no optical path at all.

[`AEPU1/M`](https://www.thorlabs.com/thorproduct.cfm?partnumber=AEPU1/M) — 375 × 300 mm
anodised aluminium utility panel, 3.2 mm thick, with **four RBX-BLK1F blank connection
panels** and one SM1-threaded through hole. **178,63 €** (`AEPU2/M`, 225 × 300 mm, is
176,73 € — barely cheaper, so take the larger one).

It's sized for Thorlabs XE25 enclosures, but it's just a plate — cut a 375 × 300 aperture
in one hardboard panel and mount it there. Its value is the four pre-made cutouts that
accept standard connector panels; if you're not buying those, a DIY aluminium plate or a
19" rack blanking panel does the same for ~€30.

Route by cable type:

- **SMA (microwave)** — bulkhead SMA. You already have `Cinch SMA ×8` on your list.
- **BNC (signals)** — bulkhead BNC.
- **USB / Ethernet / mains** — no cheap bulkhead option. These need a **labyrinth**: a
  small black box where the cable enters, turns a corner, and exits. Never a straight
  through-hole. The mouldable matte black foil already in your list seals the rest.

## Ventilation

A sealed box with anything warm inside will drift, and dD/dT = −74 kHz/K makes your
diamond a thermometer. Vents must be **baffled** — a labyrinth or foam filter media
painted matte black, never a straight path.

## Reconsider what goes on the shelf

20 kg is structurally trivial, so the constraint isn't strength. It's that fan-cooled,
heat-producing kit directly above a sealed enclosure gives you a thermal load, acoustic
coupling, and more cables entering the box — which is your current failure mode. Put the
SMCV100B, the ZHL amplifier and the PC on a trolley beside the table; keep the shelf for
light, fanless things and cable management.

## Budget summary

| | Low (specialist + local panels) | High (RS + Thorlabs) |
|---|---|---|
| Profile, 36 m | 720 € | 1 528 € |
| Brackets, T-nuts, feet, caps | 395 € | 735 € |
| Panels, 14 m² | 125 € | 1 100 € |
| AEPU1/M utility panel | 179 € | 179 € |
| Foam tape, paint, fixings | 60 € | 60 € |
| **Total** | **≈ 1 480 €** | **≈ 3 600 €** |

The low column is achievable and is what I'd budget. Note that even €1,480 is ~30 % of the
€5,000 — this is a major line item, not an accessory, and it competes directly with the
fibre-coupling stage and the detector upgrade. Worth deciding explicitly where it ranks.
