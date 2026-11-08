import { useEffect, useRef } from "react";

/** Pixel-art port of the "Market Voyage" scene: the game's background.
 * mode "voyage": sea surface on the chart's sea-level line and mast tip on the chart's top line,
 *   both read from `.chart-plot[data-sea-y][data-top-y]` (set by Chart); the ship sails left → right with progress.
 * mode "start" / "end": zoomed in on the ship moored at the departure / finishing dock.
 * mood: -1 (stormy loss) … 0 (calm) … +1 (sunny gain). */
export type SeaMode = "voyage" | "start" | "end";

const ZOOM: Record<SeaMode, number> = { voyage: 4, start: 7, end: 7 }; // CSS px per scene pixel

// Pirate ship facing right. Each character is one sprite pixel; "." is transparent. The bottom 3 rows sit under water.
const SHIP = [
  "...............M.FFFF",
  "...............M.FwFF",
  "...............M.FFFF",
  "...............M",
  "..........SSSSSSSSSSS",
  ".........SSSSSSSSSSSSS",
  ".........SSSSwwwwwSSSS",
  ".........SSSwwwwwwwSSS",
  ".........SSSwSwwwSwSSS",
  ".........SSSwwwwwwwSSS",
  ".........SSSSwSwSwSSSS",
  ".........SSwSSSSSSSwSS",
  "..........SSSwwSwwSSS",
  "...........SSSSwSSSS",
  "BBBB...........M",
  "BbbB...........M..........ll",
  "BbbBBBBBBBBBBBBBBBBBBBBBBlll",
  "BbbbbbbbbbbbbbbbbbbbbbbbbbB",
  "BbYbbbYbbbYbbbYbbbYbbbYbbB",
  ".BbbbbbbbbbbbbbbbbbbbbbbB",
  "..RRRRRRRRRRRRRRRRRRRRRR",
  "...BBBBBBBBBBBBBBBBBBBB",
].map(row => row.padEnd(30, "."));
const SHIP_W = SHIP[0].length;
const ABOVE_WATER = SHIP.length - 3; // sprite rows from mast tip to waterline
const SHIP_COLORS: Record<string, string> = {
  M: "#3b2a1a", F: "#111111", w: "#f1ede4", S: "#262626", B: "#4a2c17",
  b: "#7a4520", Y: "#d4a24c", R: "#8b1e1e", l: "#3b2a1a",
};

/** "#rrggbb" or a previous mix()'s "rgb(r,g,b)" → [r, g, b], so mixes can be chained. */
const hex = (c: string) => c.startsWith("#") ? [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16)) : c.slice(4, -1).split(",").map(Number);
function mix(a: string, b: string, t: number) {
  const [x, y] = [hex(a), hex(b)];
  return `rgb(${x.map((v, i) => Math.round(v + (y[i] - v) * t)).join(",")})`;
}
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
/** Same three-sine swell as the original, in CSS pixels. */
const wave = (x: number, t: number, amp: number, spd: number) =>
  amp * (Math.sin(x * 0.011 + t * 1.1 * spd) * 0.6 + Math.sin(x * 0.026 - t * 1.6 * spd) * 0.3 + Math.sin(x * 0.004 + t * 0.6) * 0.5);

export function PixelSea({ mode, mood, progress, reducedMotion }: { mode: SeaMode; mood: number; progress: number; reducedMotion: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const live = useRef({ mode, mood, progress, reducedMotion });
  live.current = { mode, mood, progress, reducedMotion };

  useEffect(() => {
    const cv = ref.current!;
    const g = cv.getContext("2d")!;
    let W = 0, H = 0, PX = 4, T = 0, prev = performance.now(), last = 0, frame = 0, flash = 0;
    const s = { mood: live.current.mood, pos: live.current.progress };
    const rain: { x: number; y: number; v: number }[] = [];
    let splash: { x: number; y: number; vx: number; vy: number; l: number }[] = [];
    const clouds = Array.from({ length: 6 }, () => ({ x: Math.random(), y: 0.1 + Math.random() * 0.35, s: 0.6 + Math.random() * 0.8, v: 0.004 + Math.random() * 0.01 }));

    const fit = () => { // canvas resolution follows the box and the mode's zoom
      PX = ZOOM[live.current.mode];
      const w = Math.ceil(cv.clientWidth / PX), h = Math.ceil(cv.clientHeight / PX);
      if (w !== W || h !== H) { W = w; H = h; cv.width = W; cv.height = H; }
    };

    const rect = (x: number, y: number, w: number, h: number, color: string) => {
      g.fillStyle = color;
      g.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
    };
    const disc = (cx: number, cy: number, r: number, color: string) => {
      g.fillStyle = color;
      r = Math.round(r);
      for (let dy = -r; dy <= r; dy++) {
        const w = Math.floor(Math.sqrt(r * r - dy * dy));
        g.fillRect(Math.round(cx) - w, Math.round(cy) + dy, 2 * w + 1, 1);
      }
    };
    /** Sea line and chart-top line in scene pixels (voyage), or fixed framing for the dock close-ups. */
    const frameLines = () => {
      const plot = document.querySelector<HTMLElement>(".chart-plot[data-sea-y]");
      if (live.current.mode !== "voyage" || !plot) return { sea: H * 0.62, top: H * 0.12 };
      const offset = plot.getBoundingClientRect().top - cv.getBoundingClientRect().top;
      return { sea: (offset + Number(plot.dataset.seaY)) / PX, top: (offset + Number(plot.dataset.topY)) / PX };
    };

    const draw = (still: boolean) => {
      const mode = live.current.mode;
      const m = s.mood, k = (m + 1) / 2, storm = clamp(-m, 0, 1), sun = clamp(m, 0, 1);
      const lines = frameLines();
      const wy = Math.round(lines.sea);
      // Storms: taller swells that roll slower and heavier (calm 1.0 → full storm 0.55 speed).
      const amp = 8 + storm * 84 + sun * 3, spd = 1 - storm * 0.45;
      const surface = (x: number, layer = 0) => wy + layer * 5 + wave(x * PX + layer * 90, T - layer * 0.35, amp * (1 - layer * 0.2), spd) / PX;

      // Sky: eight flat bands, the pixel-art stand-in for a gradient.
      const top = mix("#232b36", "#2c6cb0", k), horizon = mix("#5b6674", "#7cc4ea", k);
      rect(0, 0, W, H, horizon); // repaint everything: wave troughs dip below the sky bands
      for (let i = 0; i < 8; i++) rect(0, (wy * i) / 8, W, wy / 8 + 1, mix(top, horizon, i / 7));

      if (sun > 0.02) {
        const sx = W * 0.82, sy = wy * 0.3 + (1 - sun) * 10, r = Math.max(7, Math.round(W / 50));
        disc(sx, sy, r * 2, `rgba(255,240,170,${0.12 * sun})`);
        disc(sx, sy, r * 1.6, `rgba(255,240,170,${0.22 * sun})`);
        disc(sx, sy, r, `rgba(255,226,120,${sun})`);
      }

      for (const c of clouds) {
        if (!still) { c.x += c.v * (1 + storm * 3) * 0.016; if (c.x > 1.2) c.x = -0.2; }
        const cx = c.x * W, cy = c.y * wy + storm * 5, r = 8 * c.s * (1 + storm * 0.6);
        g.globalAlpha = 0.55 + storm * 0.4;
        const color = mix("#4b5563", "#ffffff", clamp(k * 1.1 - 0.05, 0, 1));
        for (const [dx, dy, f] of [[0, 0, 1], [0.9, 0.15, 0.85], [-0.9, 0.2, 0.8], [0.4, -0.3, 0.8]]) disc(cx + r * dx, cy + r * dy, r * f, color);
        g.globalAlpha = 1;
      }

      const want = Math.floor(storm * 160 * (W / 360));
      while (rain.length < want) rain.push({ x: Math.random() * W, y: Math.random() * wy, v: 120 + Math.random() * 100 });
      rain.length = Math.min(rain.length, want);
      for (const r of rain) {
        if (!still) { r.y += r.v * 0.016; r.x -= 30 * 0.016; if (r.y > wy + 10) { r.y = -3; r.x = Math.random() * W + 25; } }
        rect(r.x, r.y, 1, 3, "rgba(200,220,240,0.6)");
      }

      // Lightning, softened (max 25% white) and never under reduced motion.
      if (!still && storm > 0.55 && Math.random() < 0.004 * storm) flash = 1;
      if (flash > 0) {
        rect(0, 0, W, H, `rgba(255,255,255,${flash * 0.25})`);
        if (flash > 0.7) {
          let lx = W * (0.2 + Math.random() * 0.6);
          for (let ly = 0; ly < wy - 8; ly += 2) { lx += Math.round((Math.random() - 0.5) * 3); rect(lx, ly, 1, 2, "rgba(255,255,230,0.9)"); }
        }
        flash -= 0.06;
      }

      // Sea: two thin back swells, then the front layer banded darker with depth so text below stays legible.
      const front = mix("#0e1e2c", "#2a8fcc", k), abyss = "#06121c";
      const column = (x: number) => {
        const y0 = Math.round(surface(x));
        for (let band = 0; y0 + band * 6 < H; band++) rect(x, y0 + band * 6, 1, 6, mix(front, abyss, Math.min(band / 7, 1)));
        if (storm > 0.25 && wave(x * PX, T, amp, spd) < -amp * 0.45) rect(x, y0, 1, 1, `rgba(255,255,255,${storm * 0.8})`);
      };
      for (const [layer, color] of [[2, mix("#0b1823", "#0b5288", k)], [1, mix("#0c1a27", "#1c76b0", k)]] as const) {
        for (let x = 0; x < W; x++) rect(x, surface(x, layer), 1, 14, color);
      }
      for (let x = 0; x < W; x++) column(x);

      // Docks (z = detail scale): a house on the departure dock, a lighthouse on the finishing dock.
      const z = mode === "voyage" ? 1 : 2;
      const dock = (x0: number, x1: number) => {
        rect(x0, wy - 2 * z, x1 - x0, 3 * z, "#6b4a2b");
        rect(x0, wy - 2 * z, x1 - x0, z, "#8a6440");
        for (let p = x0 + 2 * z; p < x1; p += 9 * z) rect(p, wy + z, 2 * z, 30 * z, "#4a321c");
      };
      const house = (hx: number) => {
        rect(hx, wy - 11 * z, 9 * z, 9 * z, mix("#2d3540", "#c94f3d", k));
        rect(hx + 3 * z, wy - 6 * z, 3 * z, 4 * z, "#3b2a1a");
        for (let i = 0; i < 5; i++) rect(hx - z + i * z, wy - 12 * z - i * z, (11 - 2 * i) * z, z, mix("#1e242c", "#8d2f22", k));
      };
      const lighthouse = (lx: number) => {
        rect(lx, wy - 18 * z, 3 * z, 16 * z, mix("#2d3540", "#f1c40f", k));
        rect(lx, wy - 12 * z, 3 * z, 2 * z, "#c0392b");
        rect(lx - z, wy - 20 * z, 5 * z, 2 * z, "#ffffff");
      };

      // Ship scale: voyage fits mast tip → chart top; close-ups fill most of the sky.
      const scale = Math.max(1, (wy - lines.top) / ABOVE_WATER);
      const shipW = SHIP_W * scale;
      let shipX: number;
      if (mode === "voyage") {
        dock(0, W * 0.11); house(Math.round(W * 0.02));
        dock(W * 0.89, W); lighthouse(Math.round(W * 0.935));
        shipX = W * (0.15 + s.pos * 0.68);
      } else if (mode === "start") {
        dock(0, W * 0.16); house(Math.round(W * 0.03));
        shipX = W * 0.16 + shipW / 2 + 2;
      } else {
        dock(W * 0.84, W); lighthouse(Math.round(W * 0.92));
        shipX = W * 0.84 - shipW / 2 - 2;
      }

      // Pirate ship: rides the swell, tilts by shearing columns (rotation would blur the pixels).
      const slope = clamp(((wave((shipX + 4) * PX, T, amp, spd) - wave((shipX - 4) * PX, T, amp, spd)) / PX / 8) * 0.9
        + (storm > 0.2 && !still ? Math.sin(T * 3) * 0.05 * storm : 0), -0.4, 0.4); // steeper shear shreds the sprite
      const left = Math.round(shipX - shipW / 2);
      const mastTip = surface(shipX) - ABOVE_WATER * scale;
      SHIP.forEach((row, r) => [...row].forEach((ch, c) => {
        if (ch === ".") return;
        const x0 = Math.floor(c * scale), x1 = Math.floor((c + 1) * scale);
        const shear = Math.round(slope * (c - SHIP_W / 2) * scale);
        const y0 = Math.floor(mastTip + r * scale) + shear, y1 = Math.floor(mastTip + (r + 1) * scale) + shear;
        rect(left + x0, y0, Math.max(x1 - x0, 1), Math.max(y1 - y0, 1), SHIP_COLORS[ch]);
      }));
      // Water in front of the hull, so its bottom rows sit below the waterline.
      for (let x = left - 1; x <= left + shipW + 1; x++) column(x);

      if (!still && storm > 0.3 && Math.random() < storm * 0.7) {
        splash.push({ x: shipX + (Math.random() - 0.5) * shipW * 0.7, y: surface(shipX), vx: (Math.random() - 0.5) * 15, vy: -30 - Math.random() * 30, l: 1 });
      }
      splash = splash.filter(p => (p.l -= 0.03) > 0);
      for (const p of splash) { p.x += p.vx * 0.016; p.y += p.vy * 0.016; p.vy += 125 * 0.016; rect(p.x, p.y, 1, 1, "rgba(255,255,255,0.8)"); }

      rect(0, 0, W, H, `rgba(10,15,25,${0.12 + storm * 0.22})`); // dim: storms darker, UI text always readable
    };

    const tick = (now: number) => {
      frame = requestAnimationFrame(tick);
      const still = live.current.reducedMotion;
      if (still && now - last < 250) return; // reduced motion: a static frame, refreshed for layout and mood changes
      last = now;
      const dt = still ? 0 : Math.min(0.05, (now - prev) / 1000);
      prev = now;
      T += dt;
      s.mood += (live.current.mood - s.mood) * (still ? 1 : dt * 1.2);
      s.pos += (live.current.progress - s.pos) * (still ? 1 : dt * 0.8);
      fit();
      draw(still);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, []);

  return <canvas ref={ref} className="pixel-sea" aria-hidden="true" />;
}
