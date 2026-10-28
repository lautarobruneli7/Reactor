import * as THREE from 'three';
import type { FaseCompuesto, Resultado } from '../../types';

// Escena 3D del reactor, migrada de prototipos/simulador-quimico-3d.html (three@0.149.0).
// No conoce React ni el backend: recibe un EstadoEscena y lo dibuja.

/** Un compuesto presente en el reactor, con lo que la escena necesita para dibujarlo. */
export interface ItemEscena {
  id: string;
  gramos: number;
  pm: number;
  fase: FaseCompuesto;
  /** Color de las partículas / gotas. */
  color: number;
  /** Color del líquido (0 si no es líquido). */
  liquido: number;
}

export interface EstadoEscena {
  items: ItemEscena[];
  resultado: Resultado | null;
}

export interface EscenaApi {
  sync: (estado: EstadoEscena) => void;
  /** Lanza las gotas de un compuesto que se acaba de agregar. */
  verter: (item: Pick<ItemEscena, 'color' | 'fase'>) => void;
  setAuto: (v: boolean) => void;
  resetVista: () => void;
  dispose: () => void;
}

const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
const colorPuntaje = (v: number) => new THREE.Color(v >= 75 ? 0x4ade80 : v >= 50 ? 0xfbbf24 : 0xfb7185);

function texPunto(tipo: 'glow' | 'burbuja'): THREE.CanvasTexture {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d')!;
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  if (tipo === 'burbuja') {
    gr.addColorStop(0, 'rgba(255,255,255,.04)');
    gr.addColorStop(0.62, 'rgba(255,255,255,.18)');
    gr.addColorStop(0.88, 'rgba(255,255,255,.95)');
    gr.addColorStop(1, 'rgba(255,255,255,0)');
  } else {
    gr.addColorStop(0, 'rgba(255,255,255,1)');
    gr.addColorStop(0.3, 'rgba(255,255,255,.6)');
    gr.addColorStop(1, 'rgba(255,255,255,0)');
  }
  g.fillStyle = gr;
  g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

function spriteTexto() {
  const cv = document.createElement('canvas');
  cv.width = 320;
  cv.height = 80;
  const g = cv.getContext('2d')!;
  const tex = new THREE.CanvasTexture(cv);
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, depthTest: false });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(2.1, 0.525, 1);
  sprite.renderOrder = 20;
  let last = '';
  const set = (txt: string, col: string) => {
    const k = `${txt}|${col}`;
    if (k === last) return;
    last = k;
    g.clearRect(0, 0, 320, 80);
    g.font = '600 34px system-ui, "Segoe UI", Roboto, sans-serif';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.shadowColor = col;
    g.shadowBlur = 12;
    g.fillStyle = col;
    g.fillText(txt, 160, 40);
    tex.needsUpdate = true;
  };
  return { sprite, set };
}

/** Devuelve null si el navegador no tiene WebGL. */
export function crearEscena(cont: HTMLElement): EscenaApi | null {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  } catch {
    return null;
  }
  if (!renderer.getContext()) return null;

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.92;
  cont.insertBefore(renderer.domElement, cont.firstChild);
  const cv = renderer.domElement;
  cv.style.cursor = 'grab';

  const scene = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(40, 1, 0.1, 120);

  // ---- Entorno para reflejos (vidrio y metal)
  try {
    const gc = document.createElement('canvas');
    gc.width = 8;
    gc.height = 256;
    const gg = gc.getContext('2d')!;
    const grd = gg.createLinearGradient(0, 0, 0, 256);
    grd.addColorStop(0, '#6fa4ff');
    grd.addColorStop(0.5, '#1b2f5c');
    grd.addColorStop(1, '#05080f');
    gg.fillStyle = grd;
    gg.fillRect(0, 0, 8, 256);
    const envScene = new THREE.Scene();
    envScene.add(
      new THREE.Mesh(
        new THREE.SphereGeometry(30, 32, 16),
        new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(gc), side: THREE.BackSide, toneMapped: false }),
      ),
    );
    const luces: Array<[number, number, number[], number[]]> = [
      [0xffffff, 4, [8, 10, 6], [7, 0.3, 4]],
      [0x4dd0ff, 5, [-10, 4, -2], [0.4, 7, 5]],
      [0xff5ec8, 4, [9, 2, -8], [0.4, 6, 4]],
      [0xffffff, 3, [-3, 6, 9], [6, 0.3, 1]],
    ];
    luces.forEach(([color, k, pos, size]) => {
      const m = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(k), toneMapped: false });
      const box = new THREE.Mesh(new THREE.BoxGeometry(size[0], size[1], size[2]), m);
      box.position.set(pos[0], pos[1], pos[2]);
      envScene.add(box);
    });
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(envScene, 0.03).texture;
    pmrem.dispose();
  } catch {
    /* sin entorno: se ve más plano pero funciona */
  }

  // ---- Luces
  scene.add(new THREE.HemisphereLight(0x9fc4ff, 0x0a1020, 0.7));
  const key = new THREE.DirectionalLight(0xffffff, 1.0);
  key.position.set(5, 9, 6);
  scene.add(key);
  const rimA = new THREE.PointLight(0x4dd0ff, 0.9, 24);
  rimA.position.set(-6, 4, -3);
  scene.add(rimA);
  const rimB = new THREE.PointLight(0xff5ec8, 0.6, 24);
  rimB.position.set(7, 3, -4);
  scene.add(rimB);

  // ---- Piso
  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(10, 72),
    new THREE.MeshStandardMaterial({ color: 0x07101f, roughness: 0.7, metalness: 0.25, envMapIntensity: 0.35 }),
  );
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);
  const grid = new THREE.PolarGridHelper(10, 20, 10, 72, 0x2a5aa8, 0x16294d);
  grid.position.y = 0.012;
  (grid.material as THREE.Material).transparent = true;
  (grid.material as THREE.Material).opacity = 0.38;
  scene.add(grid);

  const texGlow = texPunto('glow');
  const texBurbuja = texPunto('burbuja');
  const RX = -1.9;
  const BASE_Y = 0.4;
  const LH = 3.0;

  const piso = new THREE.Mesh(
    new THREE.PlaneGeometry(8, 8),
    new THREE.MeshBasicMaterial({ map: texGlow, color: 0x35507a, transparent: true, opacity: 0.55, depthWrite: false, blending: THREE.AdditiveBlending }),
  );
  piso.rotation.x = -Math.PI / 2;
  piso.position.set(RX, 0.02, 0);
  scene.add(piso);

  // =====================  REACTOR  =====================
  const reactorG = new THREE.Group();
  reactorG.position.set(RX, 0, 0);
  scene.add(reactorG);
  const metal = new THREE.MeshStandardMaterial({ color: 0x9fb2d0, metalness: 1, roughness: 0.28 });
  const metalOsc = new THREE.MeshStandardMaterial({ color: 0x22304d, metalness: 0.9, roughness: 0.4 });

  const base = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.78, 0.36, 64), metalOsc);
  base.position.y = 0.18;
  reactorG.add(base);
  const aro = new THREE.Mesh(new THREE.TorusGeometry(1.62, 0.04, 12, 72), metal);
  aro.rotation.x = Math.PI / 2;
  aro.position.y = 0.37;
  reactorG.add(aro);
  const aroTop = new THREE.Mesh(new THREE.TorusGeometry(1.26, 0.06, 16, 72), metal);
  aroTop.rotation.x = Math.PI / 2;
  aroTop.position.y = 3.96;
  reactorG.add(aroTop);
  for (let s = 0; s < 3; s++) {
    const an = (s * Math.PI * 2) / 3 + 0.5;
    const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 3.6, 10), metal);
    rod.position.set(1.42 * Math.cos(an), 2.15, 1.42 * Math.sin(an));
    reactorG.add(rod);
  }

  // Vidrio
  const glass = new THREE.Mesh(
    new THREE.CylinderGeometry(1.25, 1.25, 3.6, 72, 1, true),
    new THREE.MeshPhysicalMaterial({ color: 0xcfeaff, transparent: true, opacity: 0.17, roughness: 0.04, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.05, envMapIntensity: 1.6, side: THREE.DoubleSide, depthWrite: false }),
  );
  glass.position.y = 2.15;
  glass.renderOrder = 4;
  reactorG.add(glass);

  // Líquido
  const liqMat = new THREE.MeshPhysicalMaterial({ color: 0xf59a14, transparent: true, opacity: 0.82, roughness: 0.2, metalness: 0, clearcoat: 0.4, envMapIntensity: 0.35, emissive: 0xf2b84b, emissiveIntensity: 0.1, depthWrite: false });
  const liqGeo = new THREE.CylinderGeometry(1.17, 1.17, 1, 64, 1, false);
  liqGeo.translate(0, 0.5, 0);
  const liq = new THREE.Mesh(liqGeo, liqMat);
  liq.position.y = BASE_Y;
  liq.renderOrder = 1;
  liq.visible = false;
  reactorG.add(liq);

  const surfGeo = new THREE.RingGeometry(0.001, 1.17, 56, 12);
  surfGeo.rotateX(-Math.PI / 2);
  const surfMat = liqMat.clone();
  surfMat.opacity = 0.9;
  surfMat.side = THREE.DoubleSide;
  surfMat.depthWrite = false;
  const surf = new THREE.Mesh(surfGeo, surfMat);
  surf.renderOrder = 2;
  surf.visible = false;
  reactorG.add(surf);
  const surfPos = surfGeo.attributes.position as THREE.BufferAttribute as THREE.BufferAttribute;
  const surfBase = new Float32Array(surfPos.array.length);
  surfBase.set(surfPos.array);

  // Sedimentos (sólidos)
  const solCat = new THREE.Mesh(new THREE.CylinderGeometry(1.12, 1.12, 1, 48), new THREE.MeshStandardMaterial({ color: 0x8b78c9, roughness: 0.95, metalness: 0 }));
  solCat.geometry.translate(0, 0.5, 0);
  solCat.visible = false;
  reactorG.add(solCat);
  const solExc = new THREE.Mesh(new THREE.CylinderGeometry(1.12, 1.12, 1, 48), new THREE.MeshStandardMaterial({ color: 0xe9dcc0, roughness: 0.95, metalness: 0 }));
  solExc.geometry.translate(0, 0.5, 0);
  solExc.visible = false;
  reactorG.add(solExc);

  // Agitador + motor
  const agit = new THREE.Group();
  reactorG.add(agit);
  const vara = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 4.3, 12), metal);
  vara.position.y = 2.7;
  agit.add(vara);
  [0.95, 1.55].forEach((yy, k) => {
    const pala = new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.07, 0.2), metal);
    pala.position.y = yy;
    pala.rotation.y = (k * Math.PI) / 2;
    agit.add(pala);
  });
  const motor = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.5, 32), metalOsc);
  motor.position.y = 5.0;
  reactorG.add(motor);
  const led = new THREE.Mesh(new THREE.SphereGeometry(0.07, 16, 16), new THREE.MeshBasicMaterial({ color: 0x35507a }));
  led.position.set(0.0, 5.0, 0.43);
  reactorG.add(led);
  const tapa = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.7, 0.18, 32), metalOsc);
  tapa.position.y = 4.55;
  reactorG.add(tapa);

  // Partículas de mezcla (≈ moles de cada compuesto)
  const NP = 300;
  const pPos = new Float32Array(NP * 3);
  const pCol = new Float32Array(NP * 3);
  const P = Array.from({ length: NP }, () => ({
    a: Math.random() * 6.283,
    r: 0.08 + Math.sqrt(Math.random()) * 1.02,
    u: Math.random(),
    f: 0.6 + Math.random() * 1.6,
    p: Math.random() * 6.283,
    gas: 0,
  }));
  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
  pGeo.setAttribute('color', new THREE.BufferAttribute(pCol, 3));
  pGeo.setDrawRange(0, 0);
  const pts = new THREE.Points(pGeo, new THREE.PointsMaterial({ size: 0.1, map: texGlow, vertexColors: true, transparent: true, opacity: 0.8, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true }));
  pts.frustumCulled = false;
  pts.renderOrder = 5;
  reactorG.add(pts);

  // Burbujas
  const NB = 130;
  const bPos = new Float32Array(NB * 3);
  const B = Array.from({ length: NB }, () => ({ x: 0, z: 0, y: Math.random() * 3, v: 0.5 + Math.random() * 0.9, w: Math.random() * 6.28 }));
  const bGeo = new THREE.BufferGeometry();
  bGeo.setAttribute('position', new THREE.BufferAttribute(bPos, 3));
  bGeo.setDrawRange(0, 0);
  const bub = new THREE.Points(bGeo, new THREE.PointsMaterial({ size: 0.1, map: texBurbuja, color: 0xbfe6ff, transparent: true, opacity: 0.75, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true }));
  bub.frustumCulled = false;
  bub.renderOrder = 6;
  reactorG.add(bub);
  const resetBurbuja = (b: (typeof B)[number], anywhere: boolean) => {
    const rr = Math.sqrt(Math.random()) * 1.05;
    const aa = Math.random() * 6.283;
    b.x = rr * Math.cos(aa);
    b.z = rr * Math.sin(aa);
    b.y = anywhere ? BASE_Y + Math.random() * LH : BASE_Y + 0.05;
  };
  B.forEach((b) => resetBurbuja(b, true));

  // Anillo de calidad en el piso
  const NS = 72;
  const segs: THREE.Mesh<THREE.BoxGeometry, THREE.MeshBasicMaterial>[] = [];
  for (let i = 0; i < NS; i++) {
    const ang = (i / NS) * Math.PI * 2;
    const sg = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.05, 0.13), new THREE.MeshBasicMaterial({ color: 0x15233f }));
    sg.position.set(2.5 * Math.cos(ang), 0.045, 2.5 * Math.sin(ang));
    sg.rotation.y = -ang;
    reactorG.add(sg);
    segs.push(sg);
  }

  // Gotas al verter + ondas
  type Gota = { m: THREE.Mesh<THREE.SphereGeometry, THREE.MeshBasicMaterial>; vy: number; g: number };
  type Onda = { m: THREE.Mesh<THREE.RingGeometry, THREE.MeshBasicMaterial>; t: number };
  const gotas: Gota[] = [];
  const ondas: Onda[] = [];
  const gotaGeo = new THREE.SphereGeometry(0.075, 12, 12);
  const verter: EscenaApi['verter'] = (c) => {
    const col = new THREE.Color(c.color);
    const gas = c.fase === 'gas';
    for (let k = 0; k < 16; k++) {
      const m = new THREE.Mesh(gotaGeo, new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 1 }));
      m.position.set((Math.random() - 0.5) * 0.7, 6.6 + Math.random() * 1.2, (Math.random() - 0.5) * 0.7);
      m.scale.setScalar(gas ? 1.5 : 1);
      reactorG.add(m);
      gotas.push({ m, vy: -2 - Math.random() * 2, g: gas ? 6 : 15 });
    }
  };
  const onda = (color: THREE.Color) => {
    const m = new THREE.Mesh(
      new THREE.RingGeometry(0.12, 0.17, 40),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending }),
    );
    m.rotation.x = -Math.PI / 2;
    m.position.y = surf.position.y + 0.02;
    m.renderOrder = 7;
    reactorG.add(m);
    ondas.push({ m, t: 0 });
  };

  // =====================  COLUMNAS 3D  =====================
  const barG = new THREE.Group();
  scene.add(barG);
  const BX = [1.55, 2.65, 3.75];
  const BH = 2.4;
  const BN = ['Rendimiento', 'Pureza', 'Balance'];
  const cols = BX.map((x, i) => {
    const gb = new THREE.Group();
    gb.position.set(x, 0, 0.3);
    barG.add(gb);
    const plate = new THREE.Mesh(new THREE.CylinderGeometry(0.46, 0.5, 0.07, 32), metalOsc);
    plate.position.y = 0.035;
    gb.add(plate);
    const gcil = new THREE.CylinderGeometry(0.3, 0.3, 1, 28);
    gcil.translate(0, 0.5, 0);
    const cm = new THREE.MeshPhysicalMaterial({ color: 0x35507a, transparent: true, opacity: 0.88, roughness: 0.3, metalness: 0.1, clearcoat: 0.3, envMapIntensity: 0.4, emissive: 0x35507a, emissiveIntensity: 0.3 });
    const cil = new THREE.Mesh(gcil, cm);
    cil.position.y = 0.07;
    cil.scale.y = 0.001;
    gb.add(cil);
    const edge = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.CylinderGeometry(0.35, 0.35, BH, 16)),
      new THREE.LineBasicMaterial({ color: 0x4d78c9, transparent: true, opacity: 0.4 }),
    );
    edge.position.y = 0.07 + BH / 2;
    gb.add(edge);
    const nombre = spriteTexto();
    nombre.sprite.scale.set(1.9, 0.475, 1);
    nombre.sprite.position.set(0, 0.16, 0.8);
    gb.add(nombre.sprite);
    nombre.set(BN[i], '#c9d7f2');
    const valor = spriteTexto();
    valor.sprite.position.set(0, 0.5, 0);
    gb.add(valor.sprite);
    return { cil, cm, valor };
  });

  // =====================  MOLÉCULA  =====================
  const molG = new THREE.Group();
  molG.position.set(2.65, 4.85, 0);
  scene.add(molG);
  const rot = new THREE.Group();
  molG.add(rot);
  const inner = new THREE.Group();
  rot.add(inner);
  const atoms: Array<{ el: 'C' | 'O'; p: THREE.Vector3 }> = [];
  const addA = (el: 'C' | 'O', x: number, y: number, z: number) => atoms.push({ el, p: new THREE.Vector3(x, y, z) });
  for (let k2 = 0; k2 < 6; k2++) {
    const a2 = (k2 * Math.PI) / 3;
    addA('C', 1.4 * Math.cos(a2), 1.4 * Math.sin(a2), 0);
  }
  addA('C', 2.5, 0.8, 0.4);
  addA('C', 3.9, 0.3, -0.2);
  addA('C', 4.8, 1.3, 0.5);
  addA('C', 4.4, -1.0, 0.4);
  addA('C', -2.5, -0.9, 0.4);
  addA('C', -2.4, -2.3, -0.2);
  addA('C', -3.8, -0.2, 0.1);
  addA('O', -4.0, 1.0, 0.4);
  addA('O', -4.8, -0.9, -0.4);
  const cen = new THREE.Vector3();
  atoms.forEach((a) => cen.add(a.p));
  cen.multiplyScalar(1 / atoms.length);
  atoms.forEach((a) => a.p.sub(cen));
  const molMats: THREE.MeshStandardMaterial[] = [];
  const matMol = (color: number, metalness: number, rough: number) => {
    const m = new THREE.MeshStandardMaterial({ color, metalness, roughness: rough, transparent: true, opacity: 0.25 });
    molMats.push(m);
    return m;
  };
  const mC = matMol(0x7d8ca8, 0.3, 0.3);
  const mO = matMol(0xff4d4d, 0.2, 0.25);
  const mB = matMol(0xd5deef, 0.4, 0.3);
  const sphC = new THREE.SphereGeometry(0.4, 28, 20);
  const sphO = new THREE.SphereGeometry(0.36, 28, 20);
  atoms.forEach((a) => {
    const m = new THREE.Mesh(a.el === 'O' ? sphO : sphC, a.el === 'O' ? mO : mC);
    m.position.copy(a.p);
    inner.add(m);
  });
  const up = new THREE.Vector3(0, 1, 0);
  for (let ia = 0; ia < atoms.length; ia++) {
    for (let ib = ia + 1; ib < atoms.length; ib++) {
      const d = atoms[ia].p.distanceTo(atoms[ib].p);
      if (d < 1.75) {
        const dir = new THREE.Vector3().subVectors(atoms[ib].p, atoms[ia].p).normalize();
        const bond = new THREE.Mesh(new THREE.CylinderGeometry(0.095, 0.095, d, 10), mB);
        bond.position.addVectors(atoms[ia].p, atoms[ib].p).multiplyScalar(0.5);
        bond.quaternion.setFromUnitVectors(up, dir);
        inner.add(bond);
      }
    }
  }
  const arom = new THREE.Mesh(new THREE.TorusGeometry(0.95, 0.05, 10, 48), mB);
  arom.position.copy(new THREE.Vector3(0, 0, 0).sub(cen));
  inner.add(arom);
  inner.scale.setScalar(0.37);

  const glowMol = new THREE.Sprite(new THREE.SpriteMaterial({ map: texGlow, color: 0x35507a, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false }));
  glowMol.scale.set(6.2, 6.2, 1);
  glowMol.position.z = -0.6;
  molG.add(glowMol);

  const NI = 70;
  const iPos = new Float32Array(NI * 3);
  const I = Array.from({ length: NI }, () => ({
    r: 1.9 + Math.random() * 0.8,
    a: Math.random() * 6.283,
    s: 0.35 + Math.random() * 0.7,
    tilt: Math.random() * 3.1416,
    y: (Math.random() - 0.5) * 0.5,
  }));
  const iGeo = new THREE.BufferGeometry();
  iGeo.setAttribute('position', new THREE.BufferAttribute(iPos, 3));
  iGeo.setDrawRange(0, 0);
  const impur = new THREE.Points(iGeo, new THREE.PointsMaterial({ size: 0.16, map: texGlow, color: 0xff9a3c, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true }));
  impur.frustumCulled = false;
  molG.add(impur);

  // =====================  CÁMARA  =====================
  const orb = { theta: 0.5, phi: 1.3, r: 13, tgt: new THREE.Vector3(0.7, 2.35, 0) };
  let auto = true;
  let drag: { x: number; y: number } | null = null;
  let fitR = 13;
  const posCam = () => {
    cam.position.set(
      orb.tgt.x + orb.r * Math.sin(orb.phi) * Math.sin(orb.theta),
      orb.tgt.y + orb.r * Math.cos(orb.phi),
      orb.tgt.z + orb.r * Math.sin(orb.phi) * Math.cos(orb.theta),
    );
    cam.lookAt(orb.tgt);
  };
  const onDown = (e: PointerEvent) => {
    drag = { x: e.clientX, y: e.clientY };
    try {
      cv.setPointerCapture(e.pointerId);
    } catch {
      /* ignorar */
    }
    cv.style.cursor = 'grabbing';
  };
  const onMove = (e: PointerEvent) => {
    if (!drag) return;
    orb.theta -= (e.clientX - drag.x) * 0.0065;
    orb.phi = clamp(orb.phi - (e.clientY - drag.y) * 0.005, 0.45, 1.52);
    drag.x = e.clientX;
    drag.y = e.clientY;
  };
  const onUp = () => {
    drag = null;
    cv.style.cursor = 'grab';
  };
  const onWheel = (e: WheelEvent) => {
    e.preventDefault();
    orb.r = clamp(orb.r * (1 + (e.deltaY > 0 ? 0.08 : -0.08)), 7, 26);
  };
  cv.addEventListener('pointerdown', onDown);
  cv.addEventListener('pointermove', onMove);
  cv.addEventListener('pointerup', onUp);
  cv.addEventListener('pointercancel', onUp);
  cv.addEventListener('wheel', onWheel, { passive: false });

  const resize = () => {
    const w = Math.max(2, cont.clientWidth);
    const h = Math.max(2, cont.clientHeight);
    renderer.setSize(w, h, false);
    cam.aspect = w / h;
    fitR = Math.max(11.6, 13.2 / cam.aspect);
    cam.updateProjectionMatrix();
    orb.r = fitR;
  };
  const ro = new ResizeObserver(resize);
  ro.observe(cont);
  resize();

  // =====================  OBJETIVOS Y ANIMACIÓN  =====================
  const NEUTRO = new THREE.Color(0x35507a);
  const PRODUCTO = new THREE.Color(0x12c98e);
  const S = { level: 0, color: new THREE.Color(0xf2b84b), score: 0, bars: [0, 0, 0], sol: [0, 0], gas: 0, mol: 0.25, imp: 0, nVis: 0, glow: new THREE.Color(0x35507a) };
  const T = { level: 0, color: new THREE.Color(0xf2b84b), score: 0, bars: [0, 0, 0], sol: [0, 0], gas: 0, mol: 0.25, imp: 0, hasRes: false };
  const clock = new THREE.Clock();
  let tNow = 0;

  const asignarParticulas = (lista: Array<{ c: THREE.Color; gas: boolean; w: number }>) => {
    const tot = lista.reduce((s, x) => s + x.w, 0);
    if (tot <= 0) {
      S.nVis = 0;
      pGeo.setDrawRange(0, 0);
      return;
    }
    const nVis = Math.min(NP, Math.round(70 + 55 * tot));
    let idx = 0;
    lista.forEach((x) => {
      const n = Math.max(6, Math.round((nVis * x.w) / tot));
      for (let j = 0; j < n && idx < NP; j++, idx++) {
        pCol[3 * idx] = x.c.r;
        pCol[3 * idx + 1] = x.c.g;
        pCol[3 * idx + 2] = x.c.b;
        P[idx].gas = x.gas ? 1 : 0;
      }
    });
    S.nVis = idx;
    pGeo.setDrawRange(0, idx);
    (pGeo.attributes.color as THREE.BufferAttribute).needsUpdate = true;
  };

  const sync: EscenaApi['sync'] = ({ items, resultado: res }) => {
    const liqs = items.filter((x) => x.fase === 'líquido' && x.gramos > 0);
    const mLiq = liqs.reduce((s, x) => s + x.gramos, 0);
    T.level = mLiq > 0 ? 0.1 + 0.8 * Math.min(1, mLiq / 320) : 0;
    if (mLiq > 0) {
      let cr = 0;
      let cg = 0;
      let cb = 0;
      liqs.forEach((x) => {
        const cc = new THREE.Color(x.liquido);
        const w = x.gramos / mLiq;
        cr += cc.r * w;
        cg += cc.g * w;
        cb += cc.b * w;
      });
      const baseC = new THREE.Color(cr, cg, cb);
      const conv = res ? clamp(res.rendimiento_pct / 95, 0, 1) : 0;
      baseC.lerp(PRODUCTO, conv * 0.9);
      T.color.copy(baseC);
    }
    let gCat = 0;
    let gExc = 0;
    let wGas = 0;
    items.forEach((x) => {
      if (x.id === 'cat') gCat = x.gramos;
      if (x.id === 'exc') gExc = x.gramos;
      if (x.fase === 'gas') wGas += x.gramos / x.pm;
    });
    T.sol[0] = Math.min(0.55, 0.4 * Math.sqrt(gCat / 150));
    T.sol[1] = Math.min(0.55, 0.4 * Math.sqrt(gExc / 150));
    T.gas = clamp(wGas / 2.2, 0, 1);
    T.hasRes = !!res;
    T.score = res ? res.puntaje : 0;
    T.bars = res
      ? [clamp(res.rendimiento_pct / 100, 0, 1), clamp((res.pureza_producto_pct - 80) / 20, 0, 1), clamp(res.balance_pct / 100, 0, 1)]
      : [0, 0, 0];
    T.mol = res ? 1 : 0.25;
    T.imp = res ? Math.round(Math.min(NI, (100 - res.pureza_producto_pct) * 5)) : 0;
    asignarParticulas(
      items
        .filter((x) => x.gramos > 0)
        .map((x) => ({ c: new THREE.Color(x.color), gas: x.fase === 'gas', w: x.pm > 0 ? x.gramos / x.pm : x.gramos / 150 })),
    );
  };

  let raf = 0;
  const frame = () => {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.05, clock.getDelta());
    tNow += dt;
    const k = 1 - Math.exp(-dt * 3.2);

    if (auto && !drag) orb.theta += dt * 0.1;
    posCam();

    S.level = lerp(S.level, T.level, k);
    S.color.lerp(T.color, k);
    S.score = lerp(S.score, T.score, 1 - Math.exp(-dt * 2.2));
    S.gas = lerp(S.gas, T.gas, k);
    S.mol = lerp(S.mol, T.mol, k);
    S.imp = lerp(S.imp, T.imp, k);
    for (let i = 0; i < 3; i++) S.bars[i] = lerp(S.bars[i], T.bars[i], 1 - Math.exp(-dt * 2.4));
    for (let i = 0; i < 2; i++) S.sol[i] = lerp(S.sol[i], T.sol[i], k);

    const hLiq = S.level * LH;
    const surfY = BASE_Y + hLiq;

    // líquido
    const hayLiq = S.level > 0.006;
    liq.visible = hayLiq;
    surf.visible = hayLiq;
    liq.scale.y = Math.max(0.0001, hLiq);
    surf.position.y = surfY + 0.004;
    liqMat.color.copy(S.color).multiplyScalar(0.72);
    liqMat.emissive.copy(S.color);
    surfMat.color.copy(S.color).multiplyScalar(0.72);
    surfMat.emissive.copy(S.color);
    const brillo = 0.1 + 0.18 * (S.score / 100) * (T.hasRes ? 1 : 0);
    liqMat.emissiveIntensity = brillo;
    surfMat.emissiveIntensity = brillo;
    // olas
    if (hayLiq) {
      const amp = 0.025 + 0.05 * S.gas;
      const arr = surfPos.array as Float32Array;
      for (let v = 0; v < arr.length; v += 3) {
        const bx = surfBase[v];
        const bz = surfBase[v + 2];
        const rr = Math.sqrt(bx * bx + bz * bz) / 1.17;
        arr[v + 1] = amp * (Math.sin(bx * 3.1 + tNow * 2.3) + Math.cos(bz * 3.5 + tNow * 1.9)) * (0.35 + 0.65 * rr);
      }
      surfPos.needsUpdate = true;
      surfGeo.computeVertexNormals();
    }

    // sólidos
    solCat.visible = S.sol[0] > 0.01;
    solCat.scale.y = Math.max(0.001, S.sol[0]);
    solCat.position.y = BASE_Y;
    solExc.visible = S.sol[1] > 0.01;
    solExc.scale.y = Math.max(0.001, S.sol[1]);
    solExc.position.y = BASE_Y + S.sol[0];

    // agitador
    agit.rotation.y += dt * (hayLiq ? 3.4 : 0.9);

    // partículas de mezcla
    const top = hayLiq ? surfY - 0.1 : BASE_Y + 0.4;
    const bot = BASE_Y + 0.12 + S.sol[0] + S.sol[1];
    for (let i = 0; i < S.nVis; i++) {
      const q = P[i];
      const r = q.r;
      const sw = q.gas ? 0.35 : (0.5 + 1.5 * (1 - r / 1.1)) * (hayLiq ? 1 : 0.4);
      q.a += sw * dt;
      const ytop = q.gas ? 3.75 : top;
      const ybot = q.gas ? BASE_Y + 0.3 : bot;
      const uu = clamp(q.u + 0.1 * Math.sin(tNow * q.f + q.p), 0, 1);
      pPos[3 * i] = r * Math.cos(q.a);
      pPos[3 * i + 1] = ybot + uu * Math.max(0.05, ytop - ybot);
      pPos[3 * i + 2] = r * Math.sin(q.a);
    }
    pGeo.attributes.position.needsUpdate = true;

    // burbujas
    const nb = hayLiq ? Math.round(8 + 120 * S.gas) : 0;
    bGeo.setDrawRange(0, nb);
    for (let i = 0; i < nb; i++) {
      const b = B[i];
      b.y += b.v * dt * (0.7 + S.gas);
      if (b.y > surfY - 0.02) resetBurbuja(b, false);
      bPos[3 * i] = b.x + 0.04 * Math.sin(tNow * 3 + b.w);
      bPos[3 * i + 1] = b.y;
      bPos[3 * i + 2] = b.z + 0.04 * Math.cos(tNow * 2.6 + b.w);
    }
    bGeo.attributes.position.needsUpdate = true;

    // gotas y ondas
    for (let i = gotas.length - 1; i >= 0; i--) {
      const gt = gotas[i];
      gt.vy -= gt.g * dt;
      gt.m.position.y += gt.vy * dt;
      const piso0 = hayLiq ? surfY : BASE_Y + S.sol[0] + S.sol[1] + 0.05;
      if (gt.m.position.y <= piso0) {
        if (Math.random() < 0.22 && ondas.length < 14) onda(gt.m.material.color);
        reactorG.remove(gt.m);
        gt.m.material.dispose();
        gotas.splice(i, 1);
      }
    }
    for (let i = ondas.length - 1; i >= 0; i--) {
      const on = ondas[i];
      on.t += dt;
      on.m.scale.setScalar(1 + on.t * 7);
      on.m.material.opacity = Math.max(0, 0.75 * (1 - on.t / 0.9));
      if (on.t > 0.9) {
        reactorG.remove(on.m);
        on.m.geometry.dispose();
        on.m.material.dispose();
        ondas.splice(i, 1);
      }
    }

    // color por puntaje
    const cPuntaje = T.hasRes ? colorPuntaje(T.score) : NEUTRO;
    S.glow.lerp(cPuntaje, k);

    // anillo del piso
    const lit = (S.score / 100) * NS;
    for (let i = 0; i < NS; i++) {
      const sg = segs[i];
      if (i < lit) {
        const pulso = 0.72 + 0.28 * Math.sin(tNow * 3.2 - i * 0.28);
        sg.material.color.copy(S.glow).multiplyScalar(pulso);
        sg.scale.y = 1 + 0.6 * pulso;
      } else {
        sg.material.color.setHex(0x15233f);
        sg.scale.y = 1;
      }
    }
    piso.material.color.copy(S.glow);
    piso.material.opacity = 0.35 + 0.3 * (S.score / 100);
    led.material.color.copy(S.glow);

    // columnas
    for (let i = 0; i < 3; i++) {
      const cc2 = cols[i];
      const val = S.bars[i];
      const h = val * BH;
      cc2.cil.scale.y = Math.max(0.001, h);
      const cb2 = T.hasRes ? colorPuntaje(val * 100).multiplyScalar(0.8) : NEUTRO;
      cc2.cm.color.lerp(cb2, k);
      cc2.cm.emissive.copy(cc2.cm.color);
      cc2.valor.sprite.position.y = 0.07 + h + 0.38;
      cc2.valor.sprite.visible = T.hasRes;
      cc2.valor.set(`${Math.round(val * 100)}%`, `#${cc2.cm.color.getHexString()}`);
    }

    // molécula
    rot.rotation.y += dt * 0.55;
    rot.rotation.x = 0.25 * Math.sin(tNow * 0.4);
    molG.position.y = 4.85 + 0.12 * Math.sin(tNow * 0.9);
    molMats.forEach((m) => {
      m.opacity = 0.2 + 0.8 * ((S.mol - 0.25) / 0.75);
    });
    glowMol.material.color.copy(S.glow);
    glowMol.material.opacity = 0.22 + 0.4 * (S.score / 100) * (T.hasRes ? 1 : 0) + 0.04 * Math.sin(tNow * 2);
    const ni = Math.round(S.imp);
    iGeo.setDrawRange(0, ni);
    for (let i = 0; i < ni; i++) {
      const im = I[i];
      const an3 = im.a + tNow * im.s;
      iPos[3 * i] = im.r * Math.cos(an3);
      iPos[3 * i + 1] = im.r * Math.sin(an3) * Math.sin(im.tilt) + im.y;
      iPos[3 * i + 2] = im.r * Math.sin(an3) * Math.cos(im.tilt);
    }
    iGeo.attributes.position.needsUpdate = true;

    renderer.render(scene, cam);
  };
  frame();

  const dispose = () => {
    cancelAnimationFrame(raf);
    ro.disconnect();
    cv.removeEventListener('pointerdown', onDown);
    cv.removeEventListener('pointermove', onMove);
    cv.removeEventListener('pointerup', onUp);
    cv.removeEventListener('pointercancel', onUp);
    cv.removeEventListener('wheel', onWheel);
    scene.traverse((o) => {
      const obj = o as THREE.Mesh;
      obj.geometry?.dispose();
      const mats = Array.isArray(obj.material) ? obj.material : obj.material ? [obj.material] : [];
      mats.forEach((m) => {
        (m as THREE.MeshBasicMaterial).map?.dispose();
        m.dispose();
      });
    });
    scene.environment?.dispose();
    renderer.dispose();
    renderer.forceContextLoss();
    cv.remove();
  };

  return {
    sync,
    verter,
    dispose,
    setAuto: (v) => {
      auto = v;
    },
    resetVista: () => {
      orb.theta = 0.5;
      orb.phi = 1.3;
      orb.r = fitR;
    },
  };
}
