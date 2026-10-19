// v2: v1 plus a small coaxial modulation pair for lock-in detection.
//
// The modulation pair (2 x 16 turns of 0.5 mm, 0.68 mT/A, f_3dB ~1.3 kHz) is wound on
// an insert that slides into the Z bore from the back. A lip stops it against the Z
// former's collar and two radial M3 nylon thumbscrews in the collar lock it. Free bore
// through the insert: 36 mm (the N40X-PF is 30 mm). The Z former, base and sample arm
// are the v1 parts, so going from v1 to v2 means printing one extra part.

include <coil_lib.scad>

part = "assembly";   // assembly | z_former | base | sample_arm | mod_insert | collide
a = ""; b = "";

module base_v1() {
    difference() {
        translate([-50, -25, -BEAM_H]) cube([100, 50, BASE_T]);
        for (sx = [-1, 1]) translate([sx * SLOT_X, 0, -BEAM_H]) m6_slot();
    }
    z_pedestal();
}

module placed(name) {
    if (name == "base") base_v1();
    else if (name == "z_former") z_former();
    else if (name == "mod_insert") mod_insert();
    else if (name == "sample_arm") sample_arm();
    else if (name == "objective") ghost_objective();
}

module printable(name) {
    if (name == "z_former") translate([0, 0, half_len(ZD)]) rotate([0, 90, 0]) z_former();
    else if (name == "base") translate([0, 0, BEAM_H]) base_v1();
    else if (name == "sample_arm") translate([0, 0, BEAM_H - STAGE_TOP]) sample_arm();
    else if (name == "mod_insert")
        translate([0, 0, half_len(ZD) + COLLAR_L + 2]) rotate([0, -90, 0]) mod_insert();
}

module assembly() {
    color("lightgray") placed("base");
    color("steelblue", 0.45) placed("z_former");
    color("chocolate") ghost_winding(ZD, "x");
    color("seagreen", 0.8) placed("mod_insert");
    color("gold") ghost_winding(MD, "x");
    color("orange") placed("sample_arm");
    color("magenta") ghost_diamond();
    color("dimgray", 0.35) placed("objective");
}

if (part == "assembly") assembly();
else if (part == "collide") intersection() { placed(a); placed(b); }
else printable(part);
