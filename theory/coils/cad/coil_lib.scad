// Shared parts for the zero-field coil formers (v1 / v2 / v3).
//
// Assembly frame (all versions): the diamond's front face is at the origin, the
// optical axis is +x (the N40X-PF objective comes in from +x, the sample arm from
// -x), z is up and the table top is at z = -BEAM_H. The scan (Z) pair is coaxial
// with the optical axis, so its field is normal to the [100] diamond face.
//
// Winding geometry comes from coil_dims.scad, which helmholtz_designer.py writes.
// Hardware: everything near the sample is non-magnetic. Use nylon or brass M3/M4
// screws, nuts and threaded rod; the M6 table screws are far enough away to be steel.

include <coil_dims.scad>

$fn = 120;

// --- the rig ------------------------------------------------------------------
BEAM_H    = 75;     // optical axis above the table (mm)
STAGE_TOP = 40;     // top face of the sample translation stage above the table
ARM_REACH = 120;    // sample-arm riser centre, behind the sample (-x)

// --- printing / fit -------------------------------------------------------------
WALL    = 2.5;      // former tube wall under the winding
FLANGE  = 2.5;      // flange thickness
LIP     = 2.0;      // flange beyond the finished winding
CH_CLR  = 0.6;      // extra channel width over m x enamelled wire (hand winding)
TAB_OUT = 4.5;      // hoop tabs stand this far proud of the outer flange
TAB_GAP = 8;        // rod axis this far outside the flange rim
TAB_W   = 12;
PAD_T   = 3;        // Z former mounting pad below the winding radius
PAD_W   = 26;
COLLAR_L = 8;       // Z former back collar (locks the modulation insert)
COLLAR_T = 7;
BASE_T  = 12;
SLOT_X  = 37.5;     // M6 table slots at x = +-SLOT_X, y in +-SLOT_HALF (25 mm grid)
SLOT_HALF = 12.5;
MOD_WALL = 2; MOD_FLANGE = 1.5; MOD_LIP = 1.5;

M3_D = 3.4;  M3_NUT_W = 5.8; M3_NUT_T = 2.8;  M3_CSK_D = 6.6;
M4_D = 4.5;  M4_NUT_D = 8.4; M4_NUT_T = 3.6;  // M4_NUT_D: across corners (+clearance)
M6_D = 6.6;  M6_HEAD_D = 11; M6_HEAD_H = 6.5;
SPACER_D = 10;

// --- derived ---------------------------------------------------------------------
function wc(D) = D[2] + CH_CLR;                         // channel width
function rf(D, lip = LIP) = D[1] + lip;                 // flange outer radius
function half_len(D, fl = FLANGE) = D[3] / 2 + wc(D) / 2 + fl;
function tab_r(D) = rf(D) + TAB_GAP;                    // hoop rod radius
function tab_r45(D) = tab_r(D) / sqrt(2);
function tab_face(D) = D[3] / 2 + wc(D) / 2 + FLANGE + TAB_OUT;  // outer face of a pair's tabs
function spacer_len(D) = D[3] + wc(D);                  // between a pair's tab inner faces
function z_gap(D) = D[3] / 2 - wc(D) / 2 - FLANGE;      // half clear gap between inner flanges

ZD = zf_scan_Z;  XD = zf_transverse_X;  YD = zf_transverse_Y;  MD = zf_modulation;

// --- primitives --------------------------------------------------------------------
module ring(r1, r2, z0, z1) {
    translate([0, 0, z0]) difference() {
        cylinder(r = r2, h = z1 - z0);
        translate([0, 0, -1]) cylinder(r = r1, h = z1 - z0 + 2);
    }
}

module hex_pocket(d, h) cylinder(d = d, h = h, $fn = 6);

module m6_slot(len = 2 * SLOT_HALF, t = BASE_T) {      // slot along y, counterbored from the top
    hull() for (s = [-1, 1]) translate([0, s * len / 2, -1]) cylinder(d = M6_D, h = t + 2, $fn = 32);
    hull() for (s = [-1, 1]) translate([0, s * len / 2, t - M6_HEAD_H]) cylinder(d = M6_HEAD_D, h = t, $fn = 48);
}

// two flanges of one winding channel centred at zc (local z = coil axis)
module channel_flanges(D, zc, fl, lip) {
    w = wc(D);
    for (e = [-1, 1]) let(z0 = zc + e * w / 2)
        ring(D[0] - 0.5, D[1] + lip, min(z0, z0 + e * fl), max(z0, z0 + e * fl));
}

// start-lead hole at the channel floor + finish-lead notch in the rim, both flanges
module lead_cuts(D, zc, fl, lip, ang) {
    w = wc(D);
    rotate([0, 0, ang]) for (e = [-1, 1]) let(z0 = zc + e * w / 2, za = min(z0, z0 + e * fl) - 0.5) {
        translate([D[0] + 0.9, 0, za]) cylinder(d = 1.8, h = fl + 1, $fn = 16);
        translate([D[1] - 0.5, -1, za]) cube([lip + 1, 2, fl + 1]);
    }
}

// a Helmholtz pair on one tube, axis = local z, centred at the origin
module spool_pair(D, wall = WALL, fl = FLANGE, lip = LIP, lead_ang = 0) {
    L = half_len(D, fl);
    difference() {
        union() {
            ring(D[0] - wall, D[0], -L, L);
            for (s = [-1, 1]) channel_flanges(D, s * D[3] / 2, fl, lip);
        }
        for (s = [-1, 1]) lead_cuts(D, s * D[3] / 2, fl, lip, lead_ang);
    }
}

// one coil of a pair as a separate ring ("hoop"): channel centred at local z = 0,
// inner flange (sample side) at -z, outer flange + 4 rod tabs at +z
module hoop(D, lead_ang = 0) {
    w = wc(D);
    R = tab_r(D);
    difference() {
        union() {
            ring(D[0] - WALL, D[0], -w / 2 - FLANGE, w / 2 + FLANGE);
            channel_flanges(D, 0, FLANGE, LIP);
            for (k = [0:3]) rotate([0, 0, 45 + 90 * k]) translate([0, 0, w / 2])
                linear_extrude(FLANGE + TAB_OUT) hull() {
                    translate([R, 0]) circle(d = TAB_W);
                    translate([rf(D) - 4, -TAB_W / 2]) square([1, TAB_W]);
                }
        }
        for (k = [0:3]) rotate([0, 0, 45 + 90 * k]) translate([R, 0, -50]) cylinder(d = M4_D, h = 100, $fn = 24);
        lead_cuts(D, 0, FLANGE, LIP, lead_ang);
        translate([0, 0, -50]) cylinder(r = D[0] - WALL, h = 100);
    }
}

module spacer(len) difference() {
    cylinder(d = SPACER_D, h = len, $fn = 48);
    translate([0, 0, -1]) cylinder(d = M4_D, h = len + 2, $fn = 24);
}

// --- Z (scan) former: assembly frame, axis = x ------------------------------------
module z_former() {
    D = ZD; w = wc(D); L = half_len(D); r_b = D[0] - WALL;
    xn = -L - COLLAR_L / 2;                     // thumbscrew plane in the collar
    difference() {
        union() {
            rotate([0, 90, 0]) spool_pair(D, lead_ang = 180);   // leads come out on top
            // flat mounting pad under the gap between the windings
            translate([-(D[3] / 2 - w / 2), -PAD_W / 2, -(D[0] + PAD_T)])
                cube([D[3] - w, PAD_W, PAD_T + WALL]);
            // back collar for the modulation insert's thumbscrews
            translate([-L - COLLAR_L, 0, 0]) rotate([0, 90, 0]) cylinder(r = r_b + COLLAR_T, h = COLLAR_L + 0.01);
        }
        rotate([0, 90, 0]) cylinder(r = r_b, h = 4 * L, center = true);
        // 2 x M3 countersunk, driven from inside the bore into the pedestal
        for (y = [-7, 7]) let(zb = -sqrt(r_b * r_b - y * y)) {
            translate([0, y, zb - 20]) cylinder(d = M3_D, h = 25, $fn = 24);
            translate([0, y, zb - 1.9]) cylinder(d1 = M3_D, d2 = M3_CSK_D, h = 1.91, $fn = 32);
            translate([0, y, zb]) cylinder(d = M3_CSK_D, h = 5, $fn = 32);
        }
        // 2 x radial M3 thumbscrews (+-45 deg from the top), nuts slid in from the back face
        for (a = [-45, 45]) rotate([a, 0, 0]) {
            translate([xn, 0, r_b - 1]) cylinder(d = M3_D, h = COLLAR_T + 2, $fn = 24);
            translate([-L - COLLAR_L - 1, -M3_NUT_W / 2, r_b + 2])
                cube([xn + M3_NUT_W / 2 + L + COLLAR_L + 1, M3_NUT_W, M3_NUT_T]);
        }
    }
}

// pedestal under the Z former's pad (part of every base)
module z_pedestal() {
    D = ZD;
    g = z_gap(D) - 0.4;
    ztop = -(D[0] + PAD_T);
    zneck = -(rf(D) + 1.5);
    zb = -BEAM_H + BASE_T - 0.01;
    difference() {
        union() {
            translate([-g, -PAD_W / 2, zneck]) cube([2 * g, PAD_W, ztop - zneck]);
            hull() {
                translate([-g, -PAD_W / 2, zneck]) cube([2 * g, PAD_W, 0.01]);
                translate([-24, -PAD_W / 2, zb]) cube([48, PAD_W, 0.01]);
            }
        }
        for (y = [-7, 7]) {
            translate([0, y, ztop - 16]) cylinder(d = M3_D, h = 17, $fn = 24);
            // nut slot from the +-y face, 6 mm below the top
            translate([-M3_NUT_W / 2, y > 0 ? y - M3_NUT_W / 2 : -PAD_W / 2 - 1, ztop - 6 - M3_NUT_T / 2])
                cube([M3_NUT_W, PAD_W / 2 + 1 - (abs(y) - M3_NUT_W / 2), M3_NUT_T]);
        }
    }
}

// --- modulation insert: slides into the Z bore from the back ------------------------
module mod_insert() {
    D = MD; Lz = half_len(ZD); r_zb = ZD[0] - WALL;
    r_i = D[0] - MOD_WALL;
    x_back = -Lz - COLLAR_L;
    r_ring = r_zb - 0.25;
    difference() {
        union() {
            rotate([0, 90, 0]) spool_pair(D, wall = MOD_WALL, fl = MOD_FLANGE, lip = MOD_LIP, lead_ang = 180);
            // tube the full length of the Z former
            translate([x_back, 0, 0]) rotate([0, 90, 0]) ring(r_i, D[0], 0, Lz - x_back);
            // centring rings: front, and back (under the collar thumbscrews)
            translate([Lz - 6, 0, 0]) rotate([0, 90, 0]) ring(r_i, r_ring, 0, 6);
            translate([x_back, 0, 0]) rotate([0, 90, 0]) ring(r_i, r_ring, 0, COLLAR_L + 4);
            // stop lip against the collar's back face
            translate([x_back - 2, 0, 0]) rotate([0, 90, 0]) ring(r_i, r_zb + COLLAR_T - 1, 0, 2);
        }
        // lead groove along the top, through the rings and the lip
        translate([x_back - 3, -1.5, D[0] - 0.5]) cube([Lz - x_back + 4, 3, 20]);
    }
}

// --- sample arm: bolts to the translation stage, enters the bore from -x -----------
AW = 18; AH = 20;               // beam cross-section (y, z)
DIA = 3.0; DIA_T = 0.5;         // DNVB14: 3 x 3 x 0.5 mm
module sample_arm() {
    zf = STAGE_TOP - BEAM_H;    // stage top in the assembly frame
    FT = 8;
    x0 = -ARM_REACH;
    tip = -DIA_T - 2.0;         // beam end face: the diamond stands 2 mm proud of it
    difference() {
        union() {
            translate([x0, -AW / 2, -AH / 2]) cube([tip - x0, AW, AH]);
            // pedestal smaller than the diamond: the diamond overhangs it, so the
            // objective (0.66 mm WD) only ever meets the diamond
            translate([tip - 0.01, -1.2, -1.2]) cube([2.01, 2.4, 2.4]);
            translate([x0 - 10, -AW / 2, zf]) cube([20, AW, AH / 2 - zf]);
            translate([x0 - 37.5, -25, zf]) cube([75, 50, FT]);
            for (s = [-1, 1]) hull() {           // gussets under the beam and to the foot
                translate([x0 + s * 10, -AW / 2, zf + FT - 0.01]) cube([0.01, AW, AH / 2 - zf - FT]);
                translate([x0 + s * 18, -AW / 2, zf + FT - 0.01]) cube([0.01, AW, 0.01]);
            }
            for (s = [-1, 1]) hull() {
                translate([x0 - 10, s > 0 ? AW / 2 - 0.01 : -AW / 2, zf + FT - 0.01]) cube([20, 0.01, 18]);
                translate([x0 - 10, s > 0 ? 24 : -24.01, zf + FT - 0.01]) cube([20, 0.01, 0.01]);
            }
        }
        for (sx = [-1, 1], sy = [-1, 1]) translate([x0 + sx * 25, sy * 12.5, zf - 1])
            cylinder(d = M6_D, h = FT + 2, $fn = 32);
    }
}

// --- ghosts for previews and collision checks ---------------------------------------
module ghost_diamond() translate([-DIA_T, -DIA / 2, -DIA / 2]) cube([DIA_T, DIA, DIA]);

// N40X-PF: Ø30 mm, parfocal 60 mm, WD 0.66 mm; 30 mm cage plate (41 mm square) behind it
module ghost_objective() {
    translate([0.66, 0, 0]) rotate([0, 90, 0]) {
        cylinder(d1 = 8, d2 = 30, h = 8);
        translate([0, 0, 8]) cylinder(d = 30, h = 60 - 0.66 - 8);
    }
    translate([60, -20.5, -20.5]) cube([12, 41, 41]);
    for (y = [-15, 15], z = [-15, 15]) translate([72, y, z]) rotate([0, 90, 0]) cylinder(d = 6, h = 40);
}

module ghost_winding(D, axis = "x") {     // copper volume of a pair, for previews
    rot = axis == "x" ? [0, 90, 0] : axis == "y" ? [-90, 0, 0] : [0, 0, 0];
    rotate(rot) for (s = [-1, 1]) ring(D[0], D[1], s * D[3] / 2 - D[2] / 2, s * D[3] / 2 + D[2] / 2);
}
