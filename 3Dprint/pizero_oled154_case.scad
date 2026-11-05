// =====================================================================
//  Raspberry Pi Zero + 1.54" 7-pin SPI OLED (SSD1309) desk case
//
//  Wedge-shaped case: the display sits in the slanted front face, which
//  leans back like a monitor (face_angle = angle between table and screen).
//  The Pi lies flat on the bottom plate behind the display, power port
//  facing the back. Open space between display and Pi for the wiring.
//
//  Two parts:
//    BODY  - shell with the display mount and window (print upside down,
//            flat top on the bed; the window top edge is a ~40 mm bridge)
//    PLATE - bottom plate with the Pi standoffs, press-fits into the body
//
//  part = "print"    -> both parts laid out for printing
//  part = "assembly" -> assembled, with ghosted Pi + display
// =====================================================================

/* [Part to render] */
part = "print"; // [print, body, plate, assembly]

/* [Shape] */
face_angle = 125;   // angle between table and screen, 90 = upright, 125 = leaning back 35°
cable_gap  = 10;    // extra free space between display back and Pi, for wiring
pi_parts_h = 12;    // height of Pi header + wire stubs (used to keep clear of the display)

/* [General] */
wall      = 2.0;   // wall thickness (also the thickness in front of the display)
floor_t   = 2.0;   // bottom plate thickness
cl        = 1.2;   // clearance between boards and inner walls
fit       = 0.1;  // plate-lip fit tolerance per side (increase if too tight)
lip_h     = 3.0;   // how high the plate lip reaches into the body
lip_t     = 1.2;   // lip thickness
vents     = true;  // ventilation slots in the plate

/* [Raspberry Pi Zero] */
pi_w   = 65;
pi_d   = 30;
pi_t   = 1.4;
pi_standoff_h = 3.0;   // space under the Pi
pi_standoff_d = 5.5;
pi_screw_d    = 2.2;   // pilot hole for M2.5 self-tapping screws
// Connector positions measured from the Pi's corner with the ports edge at y = 0
hdmi_x = 12.4;
usb_x  = 41.4;   // micro-USB data (OTG)
pwr_x  = 54.0;   // micro-USB power
sd_y   = 16.9;   // SD card centre on the short edge
conn_z = 1.6;    // connector centre height above PCB top
hdmi_cut = [15, 8];    // cutout w x h (sized for cable overmold)
usb_cut  = [11, 7.5];
sd_cut   = [14, 4];
sd_overhang = 3;       // how far an inserted card sticks out past the PCB
// Which openings to cut (power input is always open, in the back wall)
hdmi_port = false;     // mini-HDMI
usb_port  = false;     // micro-USB data (OTG)
sd_port   = false;     // SD card slot (card must be inserted before closing)
cam_slot  = false;     // slot for camera ribbon
cam_y    = 15;
cam_cut  = [18, 3];

/* [Display] */
disp_w = 42.5;    // display PCB width  (horizontal)
disp_d = 37.3;    // display PCB height (along the slant)
disp_t = 1.6;     // display PCB thickness
disp_total_t = 5.4;   // whole module incl. glass and parts on the back
glass_w = 42.5;   // OLED glass panel size
glass_d = 27.3;
glass_h = 1.7;    // glass thickness (glass rests against the front wall)
glass_off  = [0, 0];  // glass centre offset from PCB centre (+y = towards top of PCB)
active_w = 36;        // visible area width
active_d = 18;        // visible area height
active_left = 3.0;    // visible area distance from the left glass edge
active_top  = 2.5;    // visible area distance from the top glass edge
// visible area centre offset from glass centre
active_off = [active_left + active_w/2 - glass_w/2,
              glass_d/2 - active_top - active_d/2];
window_margin = 0.0;  // extra window size around the visible area
// Display mounting holes: centre-to-centre spacing, centred on the board
disp_hole_spacing = [37.5, 33.1];   // left-right, top-bottom
disp_standoff_d = 4.0;     // shrunk automatically if it would touch the glass
disp_screw_d    = 1.7;     // pilot for M2 self-tapping screws
disp_fit = 0.3;            // gap around display PCB in the locating frame
frame_t  = 1.2;            // locating frame wall

/* [Print tuning] */
ef   = 0.4;    // bottom-edge chamfer on the plate (elephant's foot)
lead = 0.6;    // lead-in chamfer on top of the plate lip

/* [Hidden] */
$fn = 48;
eps = 0.01;
t = face_angle - 90;       // lean-back angle from vertical

// ---------------- derived dimensions ----------------
sd_room = sd_port ? 0 : sd_overhang;
frame_h = glass_h + disp_t;
frame_d = disp_d + 2*(disp_fit + frame_t);      // frame size along the slant
frame_w = disp_w + 2*(disp_fit + frame_t);

IL = max(pi_w + sd_room, frame_w) + 2*cl;       // inner width (x)

s0  = lip_h / cos(t) + 3;                        // slant position of frame bottom
s_c = s0 + frame_d / 2;                          // display centre along the slant
L   = s0 + frame_d + frame_h + cl;               // inner slant length (incl. rib chamfer)
IH  = L * cos(t);                                // inner height

// Pi: front edge (GPIO side) kept behind the display back + cable gap
y_pf  = pi_parts_h * tan(t) + disp_total_t / cos(t) + cable_gap;
D_bot = y_pf + pi_d + cl;                        // inner depth at the floor
D_top = D_bot - IH * tan(t);                     // inner depth at the top

pi_x = (IL - pi_w - sd_room) / 2;                // card room on the right
pcb_bot = pi_standoff_h;
pcb_top = pcb_bot + pi_t;

dcx = IL / 2;                                    // display centre (x)
dx0 = dcx - disp_w / 2;                          // display PCB corner (face coords)
dy0 = s_c - disp_d / 2;

hx0 = (disp_w - disp_hole_spacing[0]) / 2;
hy0 = (disp_d - disp_hole_spacing[1]) / 2;
disp_holes = [[hx0, hy0], [disp_w - hx0, hy0],
              [hx0, disp_d - hy0], [disp_w - hx0, disp_d - hy0]];
glass_bot_y = (disp_d - glass_d) / 2 + glass_off[1];
glass_top_y = glass_bot_y + glass_d;
standoff_d = min(disp_standoff_d,
                 2 * (glass_bot_y - hy0 - 0.3),
                 2 * ((disp_d - hy0) - glass_top_y - 0.3));

assert(t >= 0 && t <= 40, "face_angle should be between 90 and 130");
assert(standoff_d > disp_screw_d + 1, "glass_off leaves too little board for the screw posts");
assert(D_top > 5, "top of the case would be too shallow - increase cable_gap");

echo(str("Outer size: ", IL + 2*wall, " wide x ", D_bot + 2*wall, " deep x ",
         floor_t + IH + wall, " high (mm)"));

// Pi coordinates (ports edge = y 0) -> world, Pi rotated 180° so ports face back
function pw(p) = [pi_x + pi_w - p[0], D_bot - cl - p[1]];
pi_holes = [[3.5, 3.5], [61.5, 3.5], [3.5, 26.5], [61.5, 26.5]];

// ---------------- helpers ----------------
// extrude a 2D (y,z) profile along x
module xextrude(x0, len) {
    multmatrix([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]]) linear_extrude(len) children();
}

// local frame of the slanted face: x = across, y = up the slant,
// z = outward normal; z = 0 is the inner surface of the front wall
module face_frame() {
    multmatrix([[1, 0, 0, 0],
                [0, sin(t), -cos(t), 0],
                [0, cos(t),  sin(t), 0]]) children();
}

module inner_profile(ext = 0) {
    polygon([[-ext*tan(t), -ext], [IH*tan(t), IH], [D_bot, IH], [D_bot, -ext]]);
}

module slot_y(w, h, len, r = 1.5) {   // rounded slot along +y, centred in x/z
    rr = min(r, h/2 - eps, w/2 - eps);
    hull() for (sx = [-1, 1], sz = [-1, 1])
        translate([sx*(w/2 - rr), 0, sz*(h/2 - rr)])
            rotate([-90, 0, 0]) cylinder(r = rr, h = len);
}

module slot_x(w, h, len, r = 1.5) {   // rounded slot along +x, centred in y/z
    rr = min(r, h/2 - eps, w/2 - eps);
    hull() for (sy = [-1, 1], sz = [-1, 1])
        translate([0, sy*(w/2 - rr), sz*(h/2 - rr)])
            rotate([0, 90, 0]) cylinder(r = rr, h = len);
}

// ---------------- display mount (face coordinates) ----------------
module display_adds() {
    fw = disp_w + 2*disp_fit;
    fd = disp_d + 2*disp_fit;
    // locating frame with wire / clip gaps in the middle of each side
    s_out = s_c + fd/2 + frame_t;   // outer face of the top rib
    translate([0, 0, -frame_h])
        difference() {
            union() {
                translate([dcx - fw/2 - frame_t, s_c - fd/2 - frame_t, 0])
                    cube([fw + 2*frame_t, fd + 2*frame_t, frame_h + eps]);
                // 45° chamfer under the top rib: it faces down when the body is
                // printed upside down, so it must not be a flat ledge
                xextrude(dcx - fw/2 - frame_t, fw + 2*frame_t)
                    polygon([[s_out - eps, 0], [s_out - eps, frame_h + eps],
                             [s_out + frame_h, frame_h + eps]]);
            }
            translate([dcx - fw/2, s_c - fd/2, -1]) cube([fw, fd, frame_h + 2]);
            translate([dcx - 6, s_c - 50, -1]) cube([12, 100, frame_h + 1]);
            translate([dcx - 60, s_c - 6, -1]) cube([120, 12, frame_h + 1]);
        }
    // screw posts, the glass rests against the wall between them
    for (h = disp_holes)
        translate([dx0 + h[0], dy0 + h[1], -glass_h])
            cylinder(d = standoff_d, h = glass_h + eps);
}

module display_cuts() {
    aw = active_w + 2*window_margin;
    ad = active_d + 2*window_margin;
    acx = dcx + glass_off[0] + active_off[0];
    acy = s_c + glass_off[1] + active_off[1];
    for (h = disp_holes)
        translate([dx0 + h[0], dy0 + h[1], -glass_h - 1])
            cylinder(d = disp_screw_d, h = glass_h + wall - 0.6 + 1);
    // chamfered viewing window
    hull() {
        translate([acx - aw/2, acy - ad/2, -eps]) cube([aw, ad, eps]);
        translate([acx - aw/2 - wall, acy - ad/2 - wall, wall]) cube([aw + 2*wall, ad + 2*wall, eps]);
    }
}

// ---------------- port cutouts (world coordinates) ----------------
module port_cuts() {
    z = pcb_top + conn_z;
    yb = D_bot - cl - 0.5;          // from inside, through the back wall
    len = cl + wall + 1;
    translate([pw([pwr_x, 0])[0], yb, z]) slot_y(usb_cut[0], usb_cut[1], len);
    if (usb_port)
        translate([pw([usb_x, 0])[0], yb, z]) slot_y(usb_cut[0], usb_cut[1], len);
    if (hdmi_port)
        translate([pw([hdmi_x, 0])[0], yb, z]) slot_y(hdmi_cut[0], hdmi_cut[1], len);
    if (sd_port)    // right wall
        translate([pi_x + pi_w - 1, pw([0, sd_y])[1], pcb_top + 0.8])
            slot_x(sd_cut[0], sd_cut[1], IL - pi_x - pi_w + wall + 2);
    if (cam_slot)   // left wall
        translate([-wall - 0.5, pw([0, cam_y])[1], pcb_top + 1])
            slot_x(cam_cut[0], cam_cut[1], wall + pi_x + 1.5, 1);
}

// ---------------- BODY ----------------
module body() {
    difference() {
        union() {
            difference() {
                intersection() {
                    xextrude(-wall, IL + 2*wall) offset(r = wall) inner_profile(0);
                    translate([-500, -500, 0]) cube(1000);
                }
                xextrude(0, IL) inner_profile(1);
            }
            face_frame() display_adds();
        }
        face_frame() display_cuts();
        port_cuts();
    }
}

// ---------------- PLATE ----------------
module plate() {
    difference() {
        union() {
            // floor, with a small bottom chamfer against elephant's foot
            hull() {
                translate([-wall + ef, -wall + ef, -floor_t])
                    cube([IL + 2*wall - 2*ef, D_bot + 2*wall - 2*ef, eps]);
                translate([-wall, -wall, -floor_t + ef])
                    cube([IL + 2*wall, D_bot + 2*wall, floor_t - ef]);
            }
            // lip, front side follows the slant of the face, chamfered top edge
            // as a lead-in so the body slides on easily
            difference() {
                hull() {
                    xextrude(fit, IL - 2*fit)
                        polygon([[fit, 0], [fit + (lip_h - lead)*tan(t), lip_h - lead],
                                 [D_bot - fit, lip_h - lead], [D_bot - fit, 0]]);
                    xextrude(fit + lead, IL - 2*fit - 2*lead)
                        polygon([[fit + lip_h*tan(t) + lead, lip_h - eps], [fit + lip_h*tan(t) + lead, lip_h],
                                 [D_bot - fit - lead, lip_h], [D_bot - fit - lead, lip_h - eps]]);
                }
                xextrude(fit + lip_t, IL - 2*fit - 2*lip_t)
                    polygon([[fit + lip_t - tan(t), -1], [fit + lip_t + (lip_h + 1)*tan(t), lip_h + 1],
                             [D_bot - fit - lip_t, lip_h + 1], [D_bot - fit - lip_t, -1]]);
            }
            for (h = pi_holes)
                translate([pw(h)[0], pw(h)[1], -eps])
                    cylinder(d = pi_standoff_d, h = pi_standoff_h + eps);
        }
        for (h = pi_holes)
            translate([pw(h)[0], pw(h)[1], -floor_t + 0.6])
                cylinder(d = pi_screw_d, h = floor_t + pi_standoff_h);
        if (vents)
            for (x = [14 : 7 : 49])
                hull() for (y = [7, 23])
                    translate([pw([x, y])[0], pw([x, y])[1], -floor_t - 1]) cylinder(d = 2, h = floor_t + 2);
        port_cuts();   // keeps the lip out of the plug openings
    }
}

// ---------------- ghost parts for assembly view ----------------
module ghosts() {
    %translate([pi_x, D_bot - cl - pi_d, pcb_bot]) cube([pi_w, pi_d, pi_t]);
    %face_frame() {
        translate([dx0, dy0, -frame_h]) cube([disp_w, disp_d, disp_t]);
        translate([dcx + glass_off[0] - glass_w/2, s_c + glass_off[1] - glass_d/2, -glass_h])
            cube([glass_w, glass_d, glass_h]);
    }
}

// ---------------- output ----------------
module body_print() { translate([0, D_bot, IH + wall]) rotate([180, 0, 0]) body(); }
module plate_print() { translate([0, 0, floor_t]) plate(); }

if (part == "body") {
    body_print();
} else if (part == "plate") {
    plate_print();
} else if (part == "assembly") {
    color("SteelBlue") plate();
    color("LightGray", 0.6) body();
    ghosts();
} else {
    plate_print();
    translate([IL + 2*wall + 10, 0, 0]) body_print();
}
