
import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import '../styles/simulation.css'

type MaterialType =
  | 'No reciclable'
  | 'Vidrio'
  | 'Papel y cartón'
  | 'PET'
  | 'Otros plásticos'
  | 'Aluminio'

type MaterialConfig = {
  name: MaterialType
  points: number
  color: string
  binIndex: number
}

const materials: MaterialConfig[] = [
  { name: 'No reciclable', points: 0, color: '#737B80', binIndex: 0 },
  { name: 'Vidrio', points: 2.5, color: '#258B51', binIndex: 1 },
  { name: 'Papel y cartón', points: 1.5, color: '#E78B32', binIndex: 2 },
  { name: 'PET', points: 3.75, color: '#277BC1', binIndex: 3 },
  { name: 'Otros plásticos', points: 2, color: '#E9C52C', binIndex: 4 },
  { name: 'Aluminio', points: 2.5, color: '#F0F0ED', binIndex: 5 },
]

const binDefinitions = [
  { name: 'NO RECICLABLE', color: '#737B80', icon: '?' },
  { name: 'VIDRIO', color: '#258B51', icon: 'bottle' },
  { name: 'PAPEL Y CARTÓN', color: '#E78B32', icon: 'box' },
  { name: 'PET', color: '#277BC1', icon: 'pet' },
  { name: 'OTROS PLÁSTICOS', color: '#E9C52C', icon: 'recycle' },
  { name: 'ALUMINIO', color: '#F0F0ED', icon: 'can' },
]

function createLabel(text: string, color: string) {
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = 128

  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = color
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  ctx.fillStyle = text === 'ALUMINIO' ? '#34443a' : '#ffffff'
  ctx.font = `bold ${text.length > 12 ? 28 : 42}px Arial`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, 256, 64)

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace

  return new THREE.MeshBasicMaterial({
    map: texture,
    side: THREE.DoubleSide,
  })
}

function createBinIcon(type: string) {
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 256

  const ctx = canvas.getContext('2d')!
  const iconColor = type === 'ALUMINIO' ? '#34443a' : '#ffffff'

  ctx.strokeStyle = iconColor
  ctx.fillStyle = iconColor
  ctx.lineWidth = 13
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'

  if (type === 'NO RECICLABLE') {
    ctx.font = 'bold 180px Arial'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('?', 128, 128)
  }

  if (type === 'VIDRIO') {
    // Botella de vidrio
    ctx.beginPath()
    ctx.moveTo(105, 38)
    ctx.lineTo(151, 38)
    ctx.lineTo(151, 75)
    ctx.lineTo(174, 99)
    ctx.lineTo(174, 205)
    ctx.quadraticCurveTo(128, 226, 82, 205)
    ctx.lineTo(82, 99)
    ctx.lineTo(105, 75)
    ctx.closePath()
    ctx.stroke()

    ctx.beginPath()
    ctx.moveTo(84, 112)
    ctx.lineTo(172, 112)
    ctx.stroke()
  }

  if (type === 'PAPEL Y CARTÓN') {
    // Caja de cartón
    ctx.beginPath()
    ctx.moveTo(48, 91)
    ctx.lineTo(128, 48)
    ctx.lineTo(208, 91)
    ctx.lineTo(208, 185)
    ctx.lineTo(128, 224)
    ctx.lineTo(48, 185)
    ctx.closePath()
    ctx.stroke()

    ctx.beginPath()
    ctx.moveTo(48, 91)
    ctx.lineTo(128, 135)
    ctx.lineTo(208, 91)
    ctx.moveTo(128, 135)
    ctx.lineTo(128, 224)
    ctx.stroke()
  }

  if (type === 'PET') {
    // Botella plástica
    ctx.beginPath()
    ctx.moveTo(108, 38)
    ctx.lineTo(148, 38)
    ctx.lineTo(148, 70)
    ctx.lineTo(171, 94)
    ctx.lineTo(171, 204)
    ctx.quadraticCurveTo(128, 222, 85, 204)
    ctx.lineTo(85, 94)
    ctx.lineTo(108, 70)
    ctx.closePath()
    ctx.stroke()

    ctx.strokeRect(110, 23, 36, 16)
    ctx.beginPath()
    ctx.moveTo(88, 125)
    ctx.lineTo(168, 125)
    ctx.stroke()
  }

  if (type === 'OTROS PLÁSTICOS') {
    // Símbolo de reciclaje con tres flechas
    ctx.beginPath()
    ctx.moveTo(128, 38)
    ctx.lineTo(178, 69)
    ctx.lineTo(158, 73)
    ctx.moveTo(178, 69)
    ctx.lineTo(174, 48)
    ctx.stroke()

    ctx.beginPath()
    ctx.moveTo(190, 112)
    ctx.lineTo(190, 169)
    ctx.lineTo(171, 157)
    ctx.moveTo(190, 169)
    ctx.lineTo(209, 157)
    ctx.stroke()

    ctx.beginPath()
    ctx.moveTo(67, 174)
    ctx.lineTo(48, 122)
    ctx.lineTo(69, 126)
    ctx.moveTo(48, 122)
    ctx.lineTo(43, 145)
    ctx.stroke()

    ctx.beginPath()
    ctx.moveTo(128, 38)
    ctx.lineTo(98, 91)
    ctx.lineTo(67, 174)
    ctx.moveTo(190, 169)
    ctx.lineTo(128, 215)
    ctx.stroke()
  }

  if (type === 'ALUMINIO') {
    // Lata metálica
    ctx.beginPath()
    ctx.roundRect(78, 55, 100, 150, 16)
    ctx.stroke()

    ctx.beginPath()
    ctx.ellipse(128, 58, 49, 12, 0, 0, Math.PI * 2)
    ctx.ellipse(128, 202, 49, 12, 0, 0, Math.PI * 2)
    ctx.stroke()

    ctx.beginPath()
    ctx.ellipse(128, 58, 16, 5, 0, 0, Math.PI * 2)
    ctx.stroke()
  }

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace

  return new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    side: THREE.DoubleSide,
  })
}

function createRecycleLogoMaterial() {
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = 512

  const ctx = canvas.getContext('2d')!
  ctx.strokeStyle = '#28794b'
  ctx.fillStyle = '#28794b'
  ctx.lineWidth = 34
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'

  // Tres flechas formando un ciclo
  const drawArrow = (
    startX: number,
    startY: number,
    endX: number,
    endY: number,
    angle: number,
  ) => {
    ctx.beginPath()
    ctx.moveTo(startX, startY)
    ctx.lineTo(endX, endY)
    ctx.stroke()

    ctx.save()
    ctx.translate(endX, endY)
    ctx.rotate(angle)
    ctx.beginPath()
    ctx.moveTo(0, 0)
    ctx.lineTo(-34, -17)
    ctx.lineTo(-34, 17)
    ctx.closePath()
    ctx.fill()
    ctx.restore()
  }

  drawArrow(150, 100, 300, 100, Math.PI / 2)
  drawArrow(350, 150, 275, 310, Math.PI * 0.85)
  drawArrow(225, 360, 125, 195, -Math.PI * 0.45)

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace

  return new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    side: THREE.DoubleSide,
  })
}

function createWaste(type: MaterialType) {
  const group = new THREE.Group()

  if (type === 'PET') {
    const plastic = new THREE.MeshPhysicalMaterial({
      color: '#62c5e8',
      transparent: true,
      opacity: 0.85,
      roughness: 0.15,
      transmission: 0.12,
    })

    const body = new THREE.Mesh(
      new THREE.CylinderGeometry(0.14, 0.17, 0.55, 24),
      plastic,
    )
    group.add(body)

    const shoulder = new THREE.Mesh(
      new THREE.CylinderGeometry(0.07, 0.14, 0.13, 24),
      plastic,
    )
    shoulder.position.y = 0.34
    group.add(shoulder)

    const neck = new THREE.Mesh(
      new THREE.CylinderGeometry(0.055, 0.07, 0.12, 20),
      plastic,
    )
    neck.position.y = 0.46
    group.add(neck)

    const cap = new THREE.Mesh(
      new THREE.CylinderGeometry(0.06, 0.06, 0.07, 20),
      new THREE.MeshStandardMaterial({ color: '#25834c' }),
    )
    cap.position.y = 0.55
    group.add(cap)
  }

  if (type === 'Vidrio') {
    const glassMaterial = new THREE.MeshPhysicalMaterial({
      color: '#279653',
      transparent: true,
      opacity: 0.82,
      roughness: 0.12,
      transmission: 0.18,
    })

    const body = new THREE.Mesh(
      new THREE.CylinderGeometry(0.16, 0.18, 0.52, 24),
      glassMaterial,
    )
    group.add(body)

    const neck = new THREE.Mesh(
      new THREE.CylinderGeometry(0.07, 0.12, 0.2, 24),
      glassMaterial,
    )
    neck.position.y = 0.35
    group.add(neck)
  }

  if (type === 'Aluminio') {
    const metalMaterial = new THREE.MeshStandardMaterial({
      color: '#bdc8ce',
      metalness: 0.82,
      roughness: 0.24,
    })

    const can = new THREE.Mesh(
      new THREE.CylinderGeometry(0.16, 0.16, 0.48, 32),
      metalMaterial,
    )
    group.add(can)

    const top = new THREE.Mesh(
      new THREE.CylinderGeometry(0.15, 0.15, 0.018, 32),
      metalMaterial,
    )
    top.position.y = 0.25
    group.add(top)
  }

  if (type === 'Papel y cartón') {
    const cardboard = new THREE.MeshStandardMaterial({
      color: '#d4b887',
      roughness: 0.95,
    })

    const box = new THREE.Mesh(
      new THREE.BoxGeometry(0.4, 0.24, 0.32),
      cardboard,
    )
    group.add(box)

    const top = new THREE.Mesh(
      new THREE.BoxGeometry(0.4, 0.025, 0.32),
      new THREE.MeshStandardMaterial({ color: '#e4c99e' }),
    )
    top.position.y = 0.13
    group.add(top)
  }

  if (type === 'Otros plásticos') {
    const plasticMaterial = new THREE.MeshStandardMaterial({
      color: '#e5c52e',
      roughness: 0.35,
    })

    const container = new THREE.Mesh(
      new THREE.BoxGeometry(0.32, 0.42, 0.22),
      plasticMaterial,
    )
    group.add(container)

    const lid = new THREE.Mesh(
      new THREE.BoxGeometry(0.34, 0.045, 0.24),
      plasticMaterial,
    )
    lid.position.y = 0.23
    group.add(lid)
  }

  if (type === 'No reciclable') {
    const wasteMaterial = new THREE.MeshStandardMaterial({
      color: '#737B80',
      roughness: 0.8,
    })

    const object = new THREE.Mesh(
      new THREE.DodecahedronGeometry(0.23, 0),
      wasteMaterial,
    )
    group.add(object)
  }

  group.traverse((object) => {
    if (object instanceof THREE.Mesh) {
      object.castShadow = true
      object.receiveShadow = true
    }
  })

  return group
}

export function SimulationPage() {
  const containerRef = useRef<HTMLDivElement>(null)
  const wasteGroupsRef = useRef<Record<MaterialType, THREE.Group> | null>(null)

  const animationRef = useRef({
    active: false,
    start: 0,
    selected: 'PET' as MaterialType,
    binIndex: 3,
  })

  const timersRef = useRef<number[]>([])

  const [selected, setSelected] = useState<MaterialType>('PET')
  const [status, setStatus] = useState('Máquina lista para recibir residuos')
  const [reward, setReward] = useState<number | null>(null)
  const [total, setTotal] = useState(0)
  const [count, setCount] = useState(0)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#eaf0e9')

    const camera = new THREE.PerspectiveCamera(
      38,
      container.clientWidth / container.clientHeight,
      0.1,
      100,
    )
    camera.position.set(6.5, 4.2, 8.5)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.15
    container.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.target.set(0, 0.1, 0)
    controls.minDistance = 5
    controls.maxDistance = 13
    controls.maxPolarAngle = Math.PI * 0.84

    scene.add(new THREE.HemisphereLight('#ffffff', '#a5b4a4', 2.2))

    const keyLight = new THREE.DirectionalLight('#ffffff', 3.2)
    keyLight.position.set(5, 9, 7)
    keyLight.castShadow = true
    keyLight.shadow.mapSize.set(2048, 2048)
    scene.add(keyLight)

    const fillLight = new THREE.DirectionalLight('#d9f4e0', 1.4)
    fillLight.position.set(-5, 4, -4)
    scene.add(fillLight)

    const green = new THREE.MeshStandardMaterial({
      color: '#28794b',
      roughness: 0.42,
    })

    const darkGreen = new THREE.MeshStandardMaterial({
      color: '#174d31',
      roughness: 0.5,
    })

    const white = new THREE.MeshStandardMaterial({
      color: '#f5f7f3',
      roughness: 0.5,
    })

    const dark = new THREE.MeshStandardMaterial({
      color: '#202c27',
      roughness: 0.5,
    })

    const glass = new THREE.MeshPhysicalMaterial({
      color: '#c8e5d6',
      transparent: true,
      opacity: 0.16,
      roughness: 0.08,
      metalness: 0.05,
      transmission: 0.2,
      side: THREE.DoubleSide,
      depthWrite: false,
    })

    const metal = new THREE.MeshStandardMaterial({
      color: '#9da9a3',
      metalness: 0.72,
      roughness: 0.28,
    })

    const machine = new THREE.Group()
    scene.add(machine)

    const addBox = (
      parent: THREE.Object3D,
      size: [number, number, number],
      position: [number, number, number],
      material: THREE.Material,
    ) => {
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(...size),
        material,
      )
      mesh.position.set(...position)
      mesh.castShadow = true
      mesh.receiveShadow = true
      parent.add(mesh)
      return mesh
    }

    // Estructura principal
    addBox(machine, [4.2, 5.0, 1.55], [0, 0, -0.15], white)
    addBox(machine, [4.28, 0.22, 1.62], [0, -2.48, -0.15], darkGreen)
    addBox(machine, [4.28, 0.2, 1.62], [0, 2.48, -0.15], green)

    // Marco frontal verde
    addBox(machine, [0.16, 4.85, 0.16], [-2.08, 0, 0.68], green)
    addBox(machine, [0.16, 4.85, 0.16], [2.08, 0, 0.68], green)
    addBox(machine, [4.2, 0.14, 0.16], [0, 2.4, 0.68], green)

    // Cámara transparente de procesamiento
    addBox(machine, [2.0, 2.0, 0.035], [0.95, 0.55, 0.55], glass)
    addBox(machine, [0.035, 2.0, 0.9], [1.95, 0.55, 0.1], glass)
    addBox(machine, [0.035, 2.0, 0.9], [-0.05, 0.55, 0.1], glass)
    addBox(machine, [2.0, 0.035, 0.9], [0.95, -0.45, 0.1], darkGreen)
    addBox(machine, [2.0, 0.035, 0.9], [0.95, 1.55, 0.1], green)

    // Pantalla frontal
    addBox(machine, [1.45, 1.8, 0.12], [-1.15, 0.75, 0.72], darkGreen)
    addBox(machine, [1.3, 1.64, 0.045], [-1.15, 0.75, 0.8], dark)

    const screenCanvas = document.createElement('canvas')
    screenCanvas.width = 512
    screenCanvas.height = 640

    const screenContext = screenCanvas.getContext('2d')!
    screenContext.fillStyle = '#102d20'
    screenContext.fillRect(0, 0, 512, 640)

    screenContext.fillStyle = '#9be2ad'
    screenContext.font = 'bold 36px Arial'
    screenContext.textAlign = 'center'
    screenContext.fillText('ECO PUNTO', 256, 85)

    screenContext.fillStyle = '#ffffff'
    screenContext.font = '24px Arial'
    screenContext.fillText('Bienvenido', 256, 155)
    screenContext.fillStyle = '#b9d7c2'
    screenContext.fillText('Escanea tu código QR', 256, 205)

    screenContext.strokeStyle = '#ffffff'
    screenContext.lineWidth = 8
    screenContext.strokeRect(176, 250, 160, 160)

    screenContext.fillStyle = '#ffffff'
    screenContext.font = 'bold 25px Arial'
    screenContext.fillText('RECICLA', 256, 475)
    screenContext.fillText('Y GANA', 256, 515)

    screenContext.fillStyle = '#9be2ad'
    screenContext.font = 'bold 32px Arial'
    screenContext.fillText('EcoPuntos', 256, 570)

    const screenTexture = new THREE.CanvasTexture(screenCanvas)
    screenTexture.colorSpace = THREE.SRGBColorSpace

    const screenDisplay = new THREE.Mesh(
      new THREE.PlaneGeometry(1.18, 1.48),
      new THREE.MeshBasicMaterial({ map: screenTexture }),
    )
    screenDisplay.position.set(-1.15, 0.75, 0.835)
    machine.add(screenDisplay)

    // Abertura circular de ingreso
    const intakeRing = new THREE.Mesh(
      new THREE.TorusGeometry(0.43, 0.075, 16, 64),
      green,
    )
    intakeRing.position.set(1.0, 1.48, 0.76)
    machine.add(intakeRing)

    const intakeHole = new THREE.Mesh(
      new THREE.CircleGeometry(0.37, 48),
      dark,
    )
    intakeHole.position.set(1.0, 1.48, 0.72)
    machine.add(intakeHole)

    const ledMaterial = new THREE.MeshStandardMaterial({
      color: '#a9f5bb',
      emissive: '#50d878',
      emissiveIntensity: 1.5,
    })

    for (let i = 0; i < 8; i++) {
      const angle = (i / 8) * Math.PI * 2
      const led = new THREE.Mesh(
        new THREE.SphereGeometry(0.035, 12, 12),
        ledMaterial,
      )
      led.position.set(
        1.0 + Math.cos(angle) * 0.53,
        1.48 + Math.sin(angle) * 0.53,
        0.82,
      )
      machine.add(led)
    }

    // Plataforma de pesaje y cinta transportadora
    addBox(machine, [1.6, 0.12, 0.72], [0.95, -0.05, 0.05], dark)
    addBox(machine, [1.5, 0.045, 0.66], [0.95, 0.025, 0.08], metal)

    for (let i = 0; i < 7; i++) {
      addBox(
        machine,
        [0.035, 0.025, 0.62],
        [0.3 + i * 0.21, 0.055, 0.09],
        darkGreen,
      )
    }

    for (const x of [0.18, 1.72]) {
      const roller = new THREE.Mesh(
        new THREE.CylinderGeometry(0.075, 0.075, 0.7, 24),
        metal,
      )
      roller.rotation.x = Math.PI / 2
      roller.position.set(x, -0.02, 0.08)
      machine.add(roller)
    }

    // Seis compartimientos inferiores: orden exacto de izquierda a derecha
    const binStartX = -1.7
    const binSpacing = 0.68

    binDefinitions.forEach((bin, index) => {
      const x = binStartX + index * binSpacing

      const binMaterial = new THREE.MeshStandardMaterial({
        color: bin.color,
        roughness: 0.6,
      })

      // Marco del compartimiento
      addBox(
        machine,
        [0.64, 1.35, 0.12],
        [x, -1.72, 0.69],
        darkGreen,
      )

      // Panel frontal de color
      addBox(
        machine,
        [0.58, 1.15, 0.08],
        [x, -1.72, 0.78],
        binMaterial,
      )

      // Icono
      const icon = new THREE.Mesh(
        new THREE.PlaneGeometry(0.34, 0.34),
        createBinIcon(bin.name),
      )
      icon.position.set(x, -1.48, 0.83)
      machine.add(icon)

      // Nombre del material
      const label = new THREE.Mesh(
        new THREE.PlaneGeometry(0.57, 0.18),
        createLabel(bin.name, bin.color),
      )
      label.position.set(x, -1.78, 0.835)
      machine.add(label)

      // Ventana inferior
      addBox(
        machine,
        [0.45, 0.28, 0.025],
        [x, -2.02, 0.84],
        glass,
      )

      // Indicador de llenado
      addBox(
        machine,
        [0.42, 0.045, 0.035],
        [x, -2.28, 0.85],
        dark,
      )

      addBox(
        machine,
        [0.25, 0.035, 0.045],
        [x, -2.28, 0.88],
        binMaterial,
      )
    })

    // Logo de reciclaje en ambos costados
    const recycleMaterial = createRecycleLogoMaterial()

    const recycleLogoRight = new THREE.Mesh(
      new THREE.PlaneGeometry(0.95, 0.95),
      recycleMaterial,
    )
    recycleLogoRight.position.set(2.16, -1.65, -0.15)
    recycleLogoRight.rotation.y = Math.PI / 2
    machine.add(recycleLogoRight)

    const recycleLogoLeft = new THREE.Mesh(
      new THREE.PlaneGeometry(0.95, 0.95),
      recycleMaterial,
    )
    recycleLogoLeft.position.set(-2.16, -1.65, -0.15)
    recycleLogoLeft.rotation.y = -Math.PI / 2
    machine.add(recycleLogoLeft)

    // Tornillos frontales
    for (const x of [-1.9, 1.9]) {
      for (const y of [-2.3, 2.25]) {
        const screw = new THREE.Mesh(
          new THREE.CylinderGeometry(0.045, 0.045, 0.025, 16),
          metal,
        )
        screw.rotation.x = Math.PI / 2
        screw.position.set(x, y, 0.79)
        machine.add(screw)
      }
    }

    // Residuos disponibles para la animación
    const wasteGroups = {
      'No reciclable': createWaste('No reciclable'),
      Vidrio: createWaste('Vidrio'),
      'Papel y cartón': createWaste('Papel y cartón'),
      PET: createWaste('PET'),
      'Otros plásticos': createWaste('Otros plásticos'),
      Aluminio: createWaste('Aluminio'),
    }

    Object.values(wasteGroups).forEach((group) => {
      group.visible = false
      scene.add(group)
    })

    wasteGroupsRef.current = wasteGroups

    // Piso y base de presentación
    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(200, 200),
      new THREE.MeshStandardMaterial({
        color: '#dfe8df',
        roughness: 0.9,
      }),
    )
    floor.rotation.x = -Math.PI / 2
    floor.position.y = -2.56
    floor.receiveShadow = true
    scene.add(floor)

    const base = new THREE.Mesh(
      new THREE.CylinderGeometry(2.65, 2.8, 0.12, 64),
      white,
    )
    base.position.y = -2.5
    base.receiveShadow = true
    base.castShadow = true
    scene.add(base)

    // Animación de ingreso y clasificación
    let animationId = 0

    const animate = () => {
      animationId = requestAnimationFrame(animate)
      controls.update()

      const animation = animationRef.current

      if (animation.active) {
        const elapsed = (performance.now() - animation.start) / 1000
        const waste = wasteGroupsRef.current?.[animation.selected]

        if (waste) {
          waste.visible = true

          // 0 a 1.5 s: acercamiento e ingreso
          if (elapsed < 1.5) {
            const progress = elapsed / 1.5
            waste.position.set(
              1.0,
              1.48 - progress * 0.25,
              1.7 - progress * 0.9,
            )
            waste.rotation.set(progress * 0.3, 0, -progress * 0.5)
          }

          // 1.5 a 3.5 s: pesaje y desplazamiento
          else if (elapsed < 3.5) {
            const progress = (elapsed - 1.5) / 2
            waste.position.set(
              1.0 - progress * 0.55,
              1.15 - progress * 0.8,
              0.8 - progress * 0.35,
            )
            waste.rotation.z = progress * 0.5
          }

          // 3.5 a 5.2 s: traslado al compartimiento correspondiente
          else if (elapsed < 5.2) {
            const progress = (elapsed - 3.5) / 1.7
            const targetX = binStartX + animation.binIndex * binSpacing

            waste.position.set(
              0.45 + (targetX - 0.45) * progress,
              0.35 - progress * 1.85,
              0.4 + progress * 0.45,
            )
            waste.rotation.z = progress * Math.PI
          } else {
            waste.visible = false
            animation.active = false
          }
        }
      }

      renderer.render(scene, camera)
    }

    animate()

    const resizeObserver = new ResizeObserver(() => {
      const width = container.clientWidth
      const height = container.clientHeight

      if (!width || !height) return

      camera.aspect = width / height
      camera.updateProjectionMatrix()
      renderer.setSize(width, height)
    })

    resizeObserver.observe(container)

    return () => {
      cancelAnimationFrame(animationId)
      resizeObserver.disconnect()
      controls.dispose()
      wasteGroupsRef.current = null

      timersRef.current.forEach((timer) => window.clearTimeout(timer))
      timersRef.current = []

      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose()

          const meshMaterials = Array.isArray(object.material)
            ? object.material
            : [object.material]

          meshMaterials.forEach((material) => {
            if ('map' in material && material.map instanceof THREE.Texture) {
              material.map.dispose()
            }
            material.dispose()
          })
        }
      })

      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [])

  const startSimulation = () => {
    if (running) return

    const wasteGroups = wasteGroupsRef.current
    if (!wasteGroups) return

    Object.values(wasteGroups).forEach((group) => {
      group.visible = false
      group.position.set(0, 0, 0)
      group.rotation.set(0, 0, 0)
    })

    const selectedMaterial = materials.find(
      (material) => material.name === selected,
    )

    if (!selectedMaterial) return

    animationRef.current = {
      active: true,
      start: performance.now(),
      selected,
      binIndex: selectedMaterial.binIndex,
    }

    setRunning(true)
    setReward(null)
    setStatus('Identificando material y realizando pesaje...')

    const identificationTimer = window.setTimeout(() => {
      setStatus('Material identificado. Trasladando al compartimiento...')
    }, 1800)

    const completionTimer = window.setTimeout(() => {
      if (selectedMaterial.points > 0) {
        setStatus(
          `¡Depósito exitoso! Ganaste ${selectedMaterial.points} EcoPuntos.`,
        )
        setReward(selectedMaterial.points)
        setTotal((previous) => previous + selectedMaterial.points)
      } else {
        setStatus('Residuo no reciclable. No genera EcoPuntos.')
        setReward(0)
      }

      setCount((previous) => previous + 1)
      setRunning(false)
    }, 5400)

    timersRef.current.push(identificationTimer, completionTimer)
  }

  return (
    <section className="simulation-page">
      <div className="simulation-intro">
        <span className="simulation-eyebrow">
          SIMULACIÓN INTERACTIVA 3D
        </span>

        <h2>Conoce cómo funciona EcoPunto</h2>

        <p>
          Explora la máquina, deposita un material y observa el proceso
          de identificación, pesaje, clasificación y recompensa.
        </p>
      </div>

      <div className="simulation-layout">
        <div className="simulation-viewer">
          <div className="viewer-label">
            MODELO 3D · MÁQUINA ECO PUNTO
          </div>

          <div ref={containerRef} className="simulation-canvas" />

          <div className="viewer-help">
            Arrastra para rotar · Desplaza para acercar o alejar
          </div>
        </div>

        <aside className="simulation-info">
          <span className="simulation-eyebrow">
            SIMULADOR DE RECICLAJE
          </span>

          <h3>Deposita tu residuo</h3>

          <label
            className="simulation-field-label"
            htmlFor="material-select"
          >
            Selecciona el material
          </label>

          <select
            id="material-select"
            className="simulation-select"
            value={selected}
            onChange={(event) =>
              setSelected(event.target.value as MaterialType)
            }
            disabled={running}
          >
            {materials.map((material) => (
              <option key={material.name} value={material.name}>
                {material.name}
              </option>
            ))}
          </select>

          <div className="simulation-reward-preview">
            <span>Recompensa estimada</span>
            <strong>
              {materials.find((item) => item.name === selected)?.points}{' '}
              EcoPuntos
            </strong>
          </div>

          <button
            className="simulation-start-button"
            onClick={startSimulation}
            disabled={running}
          >
            {running ? 'Procesando residuo...' : 'Iniciar depósito'}
          </button>

          <div className="simulation-status" aria-live="polite">
            <span
              className={running ? 'status-dot active' : 'status-dot'}
            />
            {status}
          </div>

          {reward !== null && (
            <div className="simulation-success">
              <strong>
                {reward > 0 ? '¡Excelente, reciclaste!' : 'Residuo no reciclable'}
              </strong>
              <span>
                {reward > 0 ? `+${reward} EcoPuntos` : '0 EcoPuntos'}
              </span>
            </div>
          )}

          <div className="simulation-session">
            <div>
              <span>EcoPuntos acumulados</span>
              <strong>{total.toFixed(2)}</strong>
            </div>

            <div>
              <span>Residuos depositados</span>
              <strong>{count}</strong>
            </div>
          </div>

          <div className="simulation-notice">
            Esta experiencia es una simulación digital. La identificación,
            el pesaje y la clasificación representan procesos ilustrativos,
            no lecturas de sensores físicos.
          </div>
        </aside>
      </div>

      <section className="simulation-video-section">
        <span className="simulation-eyebrow">DEMO DEL PROTOTIPO</span>

        <h3>Funcionamiento de la máquina EcoPunto</h3>

        <p>
          Observa el recorrido del residuo y el funcionamiento general
          del prototipo.
        </p>

        <video
          className="simulation-video"
          controls
          preload="metadata"
          playsInline
        >
          <source
            src="/videos/ecopunto-funcionamiento.mp4"
            type="video/mp4"
          />
          Tu navegador no puede reproducir este video.
        </video>
      </section>
    </section>
  )
}
