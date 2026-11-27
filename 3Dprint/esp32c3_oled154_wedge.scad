// =====================================================================
//  ESP32-C3 Super Mini + 1.54" 7-pin SPI OLED (SSD1309) desk case, wedge
//
//  Same design as the Pi Zero case (pizero_oled154_case.scad), sized for
//  the ESP32-C3 Super Mini: the display sits in the slanted front face,
//  which leans back like a monitor (face_angle = angle between table and
//  screen). The ESP32 lies flat on the bottom plate behind the display,
//  USB-C port through the back wall. Wired with Dupont jumper wires on
//  pin headers; the room they need is set by esp_plug_h and disp_plug_h.
//
//  Two parts:
//    BODY  - shell with the display mount and window (print upside down,
//            flat top on the bed; the window top edge is a ~40 mm bridge)
//    PLATE - bottom plate with the ESP32 holder, press-fits into the body
//
//  Two snap clips on the plate (left and right) click into grooves on the
//  inside of the body walls; to open the case, pull the plate off firmly
//  (the hooks are angled so they let go).
//
//  The Super Mini has no mounting holes: it drops into a holder that
//  grips its edges and rests on small corner ledges. The back wall keeps
//  it from moving when you plug in the cable; add a drop of hot glue if
//  it sits loose.
//
//  part = "print"    -> both parts laid out for printing
//  part = "assembly" -> assembled, with ghosted boards and plug space
//  part = "section"  -> assembly cut in half, to check the room inside
// =====================================================================

/* [Part to render] */
part = "print"; // [print, body, plate, assembly, section]

/* [Shape] */
face_angle = 125;   // angle between table and screen, 90 = upright, 125 = leaning back 35°
cable_gap  = 3;     // extra free space between display back and the ESP32 plugs

/* [General] */
wall      = 2.0;   // wall thickness (also the thickness in front of the display)
floor_t   = 2.0;   // bottom plate thickness
cl        = 1.2;   // clearance between display frame and inner walls
fit       = 0.1;   // plate-lip fit tolerance per side (increase if too tight)
lip_h     = 3.0;   // how high the plate lip reaches into the body
lip_t     = 1.2;   // lip thickness

/* [Snap clips] */
clips    = true;   // snap clips left and right that hold the plate in the body
clip_w   = 8;      // clip width (front to back)
clip_h   = 8;      // clip height above the plate
clip_t   = 1.2;    // clip thickness (thinner = easier to snap)
clip_nub = 0.6;    // how far the hook sticks out (more = holds tighter)
clip_pos = 0.55;   // clip position from the front, as a share of the inner depth

/* [ESP32-C3 Super Mini] */
esp_l = 22.6;      // PCB length (USB-C edge to antenna edge)
esp_w = 18.0;      // PCB width
esp_t = 1.0;       // PCB thickness
// true:  header pins point out of the chip side -> board lies chip side up
// false: header pins point out of the bottom (soldered for a breadboard)
//        -> board lies chip side down, so the pins still point up
chip_up = true;
esp_plug_h = 17;   // pin header spacer + Dupont plug, measured from the PCB
usb_h = 3.3;       // USB-C connector height
usb_overhang = 1.2;    // how far the USB-C connector sticks out past the PCB
usb_cut = [12.5, 7.5]; // opening in the back wall (sized for the plug overmold)
esp_fit  = 0.2;    // gap around the PCB in the holder
holder_t = 1.2;    // holder wall thickness
ledge    = 1.5;    // size of the corner ledges the PCB rests on

/* [Display] */
disp_w = 42.5;    // display PCB width  (horizontal)
disp_d = 37.3;    // display PCB height (along the slant)
disp_t = 1.6;     // display PCB thickness
disp_total_t = 5.4;   // whole module incl. glass and parts on the back
disp_plug_h = 16.5;   // pin header spacer + Dupont plug on the display back
disp_hdr_y  = 2.5;    // display pin header distance from the top PCB edge
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
frame_h = glass_h + disp_t;
frame_d = disp_d + 2*(disp_fit + frame_t);      // frame size along the slant
frame_w = disp_w + 2*(disp_fit + frame_t);

IL = max(esp_w + 2*(esp_fit + holder_t), frame_w) + 2*cl;   // inner width (x)

s0  = lip_h / cos(t) + 3;                        // slant position of frame bottom
s_c = s0 + frame_d / 2;                          // display centre along the slant
L   = s0 + frame_d + frame_h + cl;               // inner slant length (incl. rib chamfer)
IH  = L * cos(t);                                // inner height

// ESP32: the PCB rests on ledges above the parts on its underside
under_h = chip_up ? 3.0 : usb_h + 0.3;           // pin stubs or chip side below the PCB
pcb_bot = under_h;
pcb_top = pcb_bot + esp_t;
plug_top = pcb_top + esp_plug_h;                 // top of the Dupont plugs
usb_z = chip_up ? pcb_top + usb_h/2 : pcb_bot - usb_h/2;

// ESP32 front edge kept behind the display back (at plug height) + cable gap,
// USB-C edge at the back wall
y_ef  = plug_top * tan(t) + disp_total_t / cos(t) + cable_gap;
D_bot = y_ef + esp_l + usb_overhang - 0.9;       // connector reaches 0.9 mm into the wall
D_top = D_bot - IH * tan(t);                     // inner depth at the top
esp_x = (IL - esp_w) / 2;                        // PCB left edge (x)
clip_y  = D_bot * clip_pos;                      // clip centre (y)
nub_z0  = clip_h - 3;                            // the hook starts here

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

// End of the display plugs (they point back and down, perpendicular to the face)
hdr_s = dy0 + disp_d - disp_hdr_y;
hdr_d = frame_h + disp_plug_h;
hdr_end = [hdr_s * sin(t) + hdr_d * cos(t), hdr_s * cos(t) - hdr_d * sin(t)];   // [y, z]

assert(t >= 0 && t <= 40, "face_angle should be between 90 and 130");
assert(standoff_d > disp_screw_d + 1, "glass_off leaves too little board for the screw posts");
assert(D_top > 5, "top of the case would be too shallow - increase cable_gap");
assert(hdr_end[0] < D_bot - 1, "display plugs hit the back wall - increase cable_gap");

echo(str("Outer size: ", IL + 2*wall, " wide x ", D_bot + 2*wall, " deep x ",
         floor_t + IH + wall, " high (mm)"));
echo(str("Room between display plugs and ESP32 plugs: ", hdr_end[1] - plug_top, " mm"));

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

// local frame of the ESP32: x = along the board (USB-C at x = esp_l),
// y = across, z = up; PCB corner at the origin, z = 0 is the plate top
module esp_frame() {
    translate([esp_x + esp_w, D_bot + 0.9 - usb_overhang - esp_l, 0]) rotate(90) children();
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

// ---------------- ESP32 holder (ESP32 coordinates) ----------------
module esp_holder() {
    h = pcb_top + 0.8;
    difference() {
        translate([-esp_fit - holder_t, -esp_fit - holder_t, -eps])
            cube([esp_l + 2*(esp_fit + holder_t), esp_w + 2*(esp_fit + holder_t), h + eps]);
        translate([-esp_fit, -esp_fit, -1]) cube([esp_l + 2*esp_fit, esp_w + 2*esp_fit, h + 2]);
        // open towards the back wall
        translate([esp_l - 1, -esp_fit - holder_t - 1, -1]) cube([10, esp_w + 2*(esp_fit + holder_t) + 2, h + 2]);
    }
    // corner ledges at the antenna end
    for (y = [-esp_fit, esp_w - ledge])
        translate([-esp_fit, y, -eps]) cube([ledge + esp_fit, ledge + esp_fit, pcb_bot + eps]);
    if (chip_up) {
        // corner ledges at the USB-C end (only the pin stubs are on this side)
        for (y = [-esp_fit, esp_w - ledge])
            translate([esp_l - ledge, y, -eps]) cube([ledge, ledge + esp_fit, pcb_bot + eps]);
    } else {
        // chip side down: the reset and boot buttons sit next to the USB-C
        // connector, so this end rests on the connector instead
        translate([esp_l - 6, esp_w/2 - 3, -eps]) cube([6, 6, usb_z - usb_h/2 + eps]);
    }
}

// ---------------- snap clips (world coordinates) ----------------
// mirror the left side to the right side
module both_sides() {
    children();
    translate([IL, 0, 0]) mirror([1, 0, 0]) children();
}

// extrude a 2D (x,z) profile along y
module yextrude(y0, len) {
    multmatrix([[1, 0, 0, 0], [0, 0, 1, y0], [0, 1, 0, 0]]) linear_extrude(len) children();
}

module clip_arm() {   // left side, on the plate
    translate([fit, clip_y - clip_w/2, -eps]) cube([clip_t, clip_w, clip_h + eps]);
    // hook: steep catch below, gentle lead-in above
    yextrude(clip_y - clip_w/2, clip_w)
        polygon([[fit + clip_t/2, nub_z0], [fit, nub_z0], [fit - clip_nub, nub_z0 + 1],
                 [fit - clip_nub, nub_z0 + 1.5], [fit, clip_h], [fit + clip_t/2, clip_h]]);
}

module clip_gap() {   // left side, frees the clip from the lip
    translate([fit - 1, clip_y - clip_w/2 - 0.6, -eps]) cube([lip_t + 2, clip_w + 1.2, lip_h + 1]);
}

module clip_groove() {   // left side, in the body wall
    translate([-clip_nub - 0.2, clip_y - clip_w/2 - 0.5, nub_z0 - 0.3])
        cube([clip_nub + 0.2 + eps, clip_w + 1, clip_h - nub_z0 + 0.6]);
}

// ---------------- port cutout (world coordinates) ----------------
module port_cuts() {
    translate([esp_x + esp_w/2, D_bot - 1.5, usb_z]) slot_y(usb_cut[0], usb_cut[1], wall + 2.5);
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
        if (clips) both_sides() clip_groove();
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
                if (clips) both_sides() clip_gap();
            }
            if (clips) both_sides() clip_arm();
            esp_frame() esp_holder();
        }
        port_cuts();   // keeps the lip out of the plug opening
    }
}

// ---------------- ghost parts for assembly view ----------------
module ghosts() {
    // ESP32 with the space its plugs take
    %esp_frame() {
        translate([0, 0, pcb_bot]) cube([esp_l, esp_w, esp_t]);
        translate([esp_l - 7.5, esp_w/2 - 4.5, chip_up ? pcb_top : pcb_bot - usb_h])
            cube([7.5 + usb_overhang, 9, usb_h]);
        for (y = [0, esp_w - 2.6])
            translate([1.1, y, pcb_top]) cube([esp_l - 2.2, 2.6, esp_plug_h]);
    }
    %face_frame() {
        translate([dx0, dy0, -frame_h]) cube([disp_w, disp_d, disp_t]);
        translate([dcx + glass_off[0] - glass_w/2, s_c + glass_off[1] - glass_d/2, -glass_h])
            cube([glass_w, glass_d, glass_h]);
        // display plugs
        translate([dcx - 9, dy0 + disp_d - disp_hdr_y - 1.3, -hdr_d]) cube([18, 2.6, disp_plug_h]);
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
} else if (part == "section") {
    difference() {
        union() { color("SteelBlue") plate(); color("LightGray") body(); }
        translate([IL/2, -50, -50]) cube(200);
    }
    ghosts();
} else {
    plate_print();
    translate([IL + 2*wall + 10, 0, 0]) body_print();
}
