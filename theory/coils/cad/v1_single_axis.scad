// v1: single scan axis (Z pair, coaxial with the optical axis) for the first
// zero-field PL-dip test. Bench supply in CC mode, polarity by hand.
//
// Parts: z_former (wind 2 x 81 turns of 1.0 mm), base (table plate + pedestal),
// sample_arm (bolts to the translation stage, carries the diamond into the bore).
// Render one part:  openscad -D 'part="z_former"' -o z_former.stl v1_single_axis.scad
// or run export_stl.py, which renders every part of every version.

include <coil_lib.scad>

part = "assembly";   // assembly | z_former | base | sample_arm | collide (with a, b)
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
    else if (name == "sample_arm") sample_arm();
    else if (name == "objective") ghost_objective();
}

module printable(name) {
    if (name == "z_former") translate([0, 0, half_len(ZD)]) rotate([0, 90, 0]) z_former();
    else if (name == "base") translate([0, 0, BEAM_H]) base_v1();
    else if (name == "sample_arm") translate([0, 0, BEAM_H - STAGE_TOP]) sample_arm();
}

module assembly() {
    color("lightgray") placed("base");
    color("steelblue", 0.6) placed("z_former");
    color("chocolate") ghost_winding(ZD, "x");
    color("orange") placed("sample_arm");
    color("magenta") ghost_diamond();
    color("dimgray", 0.35) placed("objective");
}

if (part == "assembly") assembly();
else if (part == "collide") intersection() { placed(a); placed(b); }
else printable(part);
