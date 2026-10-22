// v3: three axes. Z (scan) is the v1 former, coaxial with the optical axis.
// X (horizontal, across the beam) and Y (vertical) are pairs of separate hoops that
// are joined into cages by M4 brass/nylon threaded rod and printed spacers. The
// modulation insert from v2 fits unchanged.
//
//   X pair: axis along y, 2 x 64 turns of 0.8 mm, r_in 50 mm. The two lower rods run
//           through the legs printed on the base (the legs set the spacing), and the
//           two upper rods carry x_spacer tubes.
//   Y pair: axis vertical, 2 x 100 turns of 0.8 mm, r_in 70 mm. Four rods go up from
//           the base (nuts sunk in its underside), through the base posts, the lower
//           hoop, a y_spacer, and the upper hoop.
// The Z former, sample arm and mod insert are the v1/v2 parts. The base keeps the v1
// M6 slots, so it bolts to the same table holes.
// Bed: the Y hoop is ~190 mm across and the base 142 mm square.

include <coil_lib.scad>

part = "assembly";   // assembly | base | x_hoop | y_hoop | x_spacer | y_spacer | collide
a = ""; b = "";

RX = tab_r45(XD);
RY = tab_r45(YD);

module base_v3() {
    B = RY + 8;
    zt = -BEAM_H + BASE_T;
    difference() {
        union() {
            translate([-B, -B, -BEAM_H]) cube([2 * B, 2 * B, BASE_T]);
            z_pedestal();
            // X lower legs: a spacer tube along y (sets the X spacing) on a web
            for (sx = [-1, 1]) translate([sx * RX, 0, 0]) {
                translate([0, -spacer_len(XD) / 2, -RX]) rotate([-90, 0, 0])
                    cylinder(d = SPACER_D, h = spacer_len(XD), $fn = 48);
                translate([-4, -spacer_len(XD) / 2, zt - 0.01]) cube([8, spacer_len(XD), -RX - zt + 0.01]);
            }
            // Y posts up to the lower hoop's tabs
            for (sx = [-1, 1], sy = [-1, 1]) translate([sx * RY, sy * RY, zt - 0.01])
                cylinder(d = 12, h = -tab_face(YD) - zt + 0.01, $fn = 48);
        }
        m6_slots();
        for (sx = [-1, 1]) translate([sx * RX, -60, -RX]) rotate([-90, 0, 0]) cylinder(d = M4_D, h = 120, $fn = 24);
        for (sx = [-1, 1], sy = [-1, 1]) translate([sx * RY, sy * RY, -BEAM_H - 1]) {
            cylinder(d = M4_D, h = 200, $fn = 24);
            hex_pocket(M4_NUT_D, M4_NUT_T + 1);
        }
    }
}

// hoops in the assembly frame; inner flange towards the sample, leads on top / at the back
module x_hoop_p() translate([0, XD[3] / 2, 0]) rotate([-90, 0, 0]) hoop(XD, lead_ang = 270);
module y_hoop_t() translate([0, 0, YD[3] / 2]) hoop(YD, lead_ang = 180);

module placed(name) {
    if (name == "base") base_v3();
    else if (name == "z_former") z_former();
    else if (name == "mod_insert") mod_insert();
    else if (name == "x_hoop_p") x_hoop_p();
    else if (name == "x_hoop_n") mirror([0, 1, 0]) x_hoop_p();
    else if (name == "y_hoop_t") y_hoop_t();
    else if (name == "y_hoop_b") mirror([0, 0, 1]) y_hoop_t();
    else if (name == "x_spacers") for (sx = [-1, 1])
        translate([sx * RX, -spacer_len(XD) / 2, RX]) rotate([-90, 0, 0]) spacer(spacer_len(XD));
    else if (name == "y_spacers") for (sx = [-1, 1], sy = [-1, 1])
        translate([sx * RY, sy * RY, -spacer_len(YD) / 2]) spacer(spacer_len(YD));
    else if (name == "sample_arm") sample_arm();
    else if (name == "objective") ghost_objective();
}

module printable(name) {
    if (name == "base") translate([0, 0, BEAM_H]) base_v3();
    else if (name == "x_hoop") translate([0, 0, wc(XD) / 2 + FLANGE]) hoop(XD, lead_ang = 270);
    else if (name == "y_hoop") translate([0, 0, wc(YD) / 2 + FLANGE]) hoop(YD, lead_ang = 180);
    else if (name == "x_spacer") spacer(spacer_len(XD));
    else if (name == "y_spacer") spacer(spacer_len(YD));
}

module assembly() {
    color("lightgray") placed("base");
    color("steelblue", 0.5) placed("z_former");
    color("chocolate") ghost_winding(ZD, "x");
    color("seagreen", 0.8) placed("mod_insert");
    color("gold") ghost_winding(MD, "x");
    color("tomato", 0.55) { placed("x_hoop_p"); placed("x_hoop_n"); }
    color("chocolate") ghost_winding(XD, "y");
    color("mediumpurple", 0.5) { placed("y_hoop_t"); placed("y_hoop_b"); }
    color("chocolate") ghost_winding(YD, "z");
    color("khaki") { placed("x_spacers"); placed("y_spacers"); }
    color("orange") placed("sample_arm");
    color("magenta") ghost_diamond();
    color("dimgray", 0.35) placed("objective");
}

if (part == "assembly") assembly();
else if (part == "collide") intersection() { placed(a); placed(b); }
else printable(part);
