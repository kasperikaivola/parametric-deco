# Optional concealed lighting — removable edge clamps

These cuts add plywood carriers, end pads and jaws without changing or drilling
any base plywood. Match every part ID and host to `lighting-routing.json`.
Front and oblique CAD views show geometry and purchased-strip dimensional proxies;
they are NOT simulated illumination. `views/lighting-section.png` shows an actual
local cross section and cut contour for the first clamp.
`views/lighting-input-section.png` shows the exposed bottom tie/cable path.

## Mechanical installation

Disconnect all power. Place the tray two stock thicknesses behind the host.
Place the two end pads between tray and host, and the two jaws on the front
face. Each outside-edge M3 bolt passes through jaw, pad and tray WITHOUT drilling
the host. Insert bolts from REAR to FRONT; fit washers and locking nuts on the front. Tighten gently against plywood bearing;
check for crushing, loosening, sliding and damage. Do not suspend the sculpture
from these clamps. See the BOM for minimum bolt length, then round UP to available
stock and verify actual nut engagement and protrusion. Use washers no larger than
7 mm OD. Nominal bolt holes are 3.4 mm; laser kerf compensation belongs in CAM.

Lay the strip flat on the rear tray, emitters facing the host underside (+Z).
Use reusable ties with body <=2.5 x 1 mm and locking head <=5 x 5 x 3 mm.
Length must meet the BOM minimum (100 mm for defaults). Two ties thread through the
paired 3 x 2 mm tray slots and wrap OVER the strip at its ends. Move ties onto
non-emitting cut-pad areas, place locking heads BEHIND the tray at the first
slot row, and solder leads without covering emitters or shorting
pads. LED pitch alone cannot describe real component footprints: check the actual
strip and its marked cut intervals before cutting. No adhesive is required for
retention. Replace ties or alter purchased strip if component positions obstruct
them; do not claim fit without checking. Cable ties through jaw anchor holes can
secure short service loops; disconnect leads before removing a sculptural module.

Mount the input clamp on the bottom backplate edge: rear tray and front jaws
bear directly on the board (no spacer pads). The paired 2 x 3 mm slots are
OUTSIDE the board at local Y=-8/-3 mm and X=-5/+5 mm. Two ties wrap a cable up
to 5 mm diameter along Y, with heads behind the tray. Both slot exits and the
front cable loop/rear tie return are exposed, not trapped against the board.
Route leads around the board edge with a service loop before dressing inward.
No extra stock thickness is added behind the board, preserving 10 mm rear defaults. Fit a purchased inline connector/cable; no PCB/connector is
manufactured by this generator. All power, data and ground enter here.

## Wiring and electrical selection

Use ONLY the voltage specified by the purchased strip (5, 12 or 24 V in config).
`current_per_led_ma` is a user supplied worst-case estimate; the default 60 mA
is conservative for traditional 5 V RGB pixels and is not a universal rating.
For grouped 12/24 V pixels, configure pitch, count and current per ADDRESSABLE
CUT UNIT, not per individual LED package. Configured segment length must match
the purchased strip's cut interval. Supply, wire, fuse and connector continuous
ratings must be verified against actual data sheets, duty cycle and installation.
The manifest's 25% connector headroom is a sizing target, not a connector rating.
The single input carries the TOTAL estimated load; never assume a generic
three-pin connector can carry it. Supply electronics externally.

Connect controller DATA OUT to the bottom DATA input, then DIN of each segment
in `data_route` order; each DOUT feeds the next DIN. Never join two DOUTs. This is
a pixel-data input, NOT a firmware programming port. Configure the external
controller for the purchased strip protocol, addressable unit count, color order,
voltage-compatible data signal and brightness/current limit. Use an appropriate
logic level shifter where needed. Connect controller ground and supply ground to
strip ground before data. Never power strips from a controller GPIO pin.

Power branches internally from this SAME bottom input. Omit V+ on data jumpers
that cross injection groups (the manifest marks these DATA/GND only), so separate
branch fuses are not bypassed by a parallel V+ connection. The manifest lists
injection groups with estimated current <= `injection_limit_a`; run separately
fused V+/GND pairs from a suitable internal distribution point to each group's
first segment and share ground. Jumper waypoints and lengths are straight-line
minimums plus configured slack, NOT obstacle-free harness paths. Dress around
joints and withdrawal paths, secure at clamp holes and add length as necessary.
Use actual wire resistance and load to assess voltage drop; add injection from
the same input if needed. Group limits do not prove voltage-drop/thermal safety.

Adafruit's NeoPixel guidance recommends a 300–500 ohm resistor at the first
pixel's data input and a 500–1000 uF capacitor across strip power input (voltage
rating suitable for your supply). These are external purchased components.
Follow the specific strip/controller manufacturer's requirements, especially for
12/24 V products, rather than assuming 5 V NeoPixel details apply universally.
References:
- https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels
- https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices

## Validation limits

The full strip footprint is checked against intact host plywood with a positive
front shield margin. Solid clamp collisions, envelope and root hardware proxies
are checked digitally. Fixed maximum tie bodies/heads, rear returns and the
input cable envelope are also checked against board, artwork and total envelope.
Strip thickness + 1 mm tie body + requested clearance must fit the stock:
with 6 mm stock and 0.5 mm clearance, maximum strip thickness is 4.5 mm.
Emission aims at the host UNDERSIDE, not the wall or
backplate. Direct front-face lighting is not guaranteed; front faces may stay
dark, and oblique observers may see LEDs through open carrier ends. This design
needs optical prototyping; it is not a photometric or thermal simulation.
Physical fit/retention, optical performance, electrical/thermal tests and
Wire/Arena runtime checks: **NOT RUN**. Inspect one prototype before a full cut.

Saved lit inventories replay their exact supplementary parts. Config or host
placement changes are rejected; generate a new explicit supplemental design
rather than silently changing manufactured parts. Turning lighting off removes
carriers from the arrangement but preserves them in the saved physical inventory.

## Density and symmetry

`max_segments` requests additional separated carriers in repeated module passes.
Check requested/achieved and per-module counts in the routing manifest: geometry
or complete symmetry orbits may limit capacity. Short single-unit strips can
thus be distributed around fins instead of requiring a long colliding strip.
Laminar and creature carrier geometry follows complete physical symmetry groups;
the single bottom cable input is intentionally exempt. This is mechanical coverage,
not a prediction of uniform illumination or brightness.

Inventories predating verified tie paths are rejected when relighting; generate
explicit supplemental new cuts. Disabling still preserves their physical inventory.
