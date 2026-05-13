export const CATEGORIES = {
  'sécurité':     { short: 'SEC',   color: '#C8312D' },
  'mécanique':    { short: 'MEC',   color: '#56524A' },
  'électrique':   { short: 'ELEC',  color: '#2E5C9E' },
  'hydraulique':  { short: 'HYD',   color: '#1F5F5B' },
  'test':         { short: 'TEST',  color: '#7A4F1D' },
  'vérification': { short: 'VERIF', color: '#3D3936' },
}

export const TECHS = [
  { name: 'Marie Tissier',  role: 'Technicienne hydraulique', initials: 'MT', color: '#C8312D' },
  { name: 'Jean Mercier',   role: "Chef d'équipe",            initials: 'JM', color: '#1F5F5B' },
  { name: 'Karim Belkacem', role: 'Mécanicien',               initials: 'KB', color: '#2E5C9E' },
  { name: 'M. Dubois',      role: 'Superviseur sécurité',     initials: 'MD', color: '#56524A' },
]

export const MANUAL = {
  id: 1,
  name: 'Presse hydraulique HP-450',
  ref: 'HP-450 / Rev. 03',
  pdf_filename: 'HP450_manuel_installation_v3.pdf',
  pages: 24,
  total_steps: 20,
  completed_steps: 9,
  created_at: '2026-05-09 08:14:00',
}

export const STEPS = [
  { id: 1,  step_number: 1,  title: "Vérifier l'intégrité de l'emballage",       description: "Inspecter visuellement la caisse de transport. Photographier tout dommage avant déballage. Refuser la livraison si la caisse est éventrée ou si les indicateurs de choc sont rouges.", category: 'vérification', is_critical: false, page_ref: 3,  duration: '5 min',  requires_witness: false },
  { id: 2,  step_number: 2,  title: "Couper l'alimentation générale du site",     description: "Mettre l'armoire principale en position OFF, consigner avec cadenas personnel et placarder le panneau « Travaux en cours — Ne pas réenclencher ».", category: 'sécurité',     is_critical: true,  page_ref: 4,  duration: '3 min',  requires_witness: true  },
  { id: 3,  step_number: 3,  title: 'Délimiter le périmètre de sécurité',         description: 'Installer les barrières amovibles à 2,5 m minimum autour de la zone d\'installation. Fixer les pictogrammes A1 et A3.', category: 'sécurité',     is_critical: true,  page_ref: 4,  duration: '10 min', requires_witness: false },
  { id: 4,  step_number: 4,  title: 'Positionner la presse sur les plots anti-vibratiles', description: 'Utiliser le pont 2 t. Aligner les 4 plots PV-80 selon le gabarit fourni (annexe A). Tolérance de planéité : 0,5 mm/m.', category: 'mécanique',    is_critical: false, page_ref: 6,  duration: '25 min', requires_witness: false },
  { id: 5,  step_number: 5,  title: 'Sceller les plots au sol',                   description: 'Couler la résine époxy bicomposante dans les puits de scellement. Respecter la prise de 4 h avant mise en charge.', category: 'mécanique',    is_critical: false, page_ref: 7,  duration: '4 h',    requires_witness: false },
  { id: 6,  step_number: 6,  title: 'Vérifier la planéité du bâti',               description: 'Niveau de précision sur la table supérieure dans les deux axes. Recalibrer via vis V1–V4 si écart > 0,2 mm/m.', category: 'vérification', is_critical: false, page_ref: 8,  duration: '15 min', requires_witness: false },
  { id: 7,  step_number: 7,  title: 'Raccorder le circuit hydraulique haute pression', description: 'Brancher les flexibles HP1 et HP2 sur les piquages M2 et M3. Couple de serrage : 85 N·m. Utiliser des joints neufs (réf. JT-22).', category: 'hydraulique',  is_critical: false, page_ref: 10, duration: '20 min', requires_witness: false },
  { id: 8,  step_number: 8,  title: "Remplir le réservoir d'huile",               description: "Huile ISO VG 46 uniquement. Quantité : 42 L jusqu'au repère MAX. Filtrer à l'introduction (filtre 10 µm).", category: 'hydraulique',  is_critical: false, page_ref: 11, duration: '15 min', requires_witness: false },
  { id: 9,  step_number: 9,  title: 'Purger le circuit hydraulique',              description: 'Ouvrir la vanne V3 en position basse pression. Laisser le fluide s\'écouler 5 min puis fermer progressivement. Vérifier l\'absence de bulles au regard R1.', category: 'hydraulique',  is_critical: true,  page_ref: 12, duration: '10 min', requires_witness: false },
  { id: 10, step_number: 10, title: "Raccorder l'alimentation triphasée 400V",    description: 'Câble 4G6 minimum. Respecter l\'ordre des phases (L1-L2-L3-N-PE). Couple sur bornier : 2,5 N·m. Vérifier la continuité de terre < 0,1 Ω.', category: 'électrique',   is_critical: true,  page_ref: 14, duration: '30 min', requires_witness: true  },
  { id: 11, step_number: 11, title: "Câbler les arrêts d'urgence",               description: "AU1 (façade), AU2 (arrière), AU3 (déporté). Boucle NC en série. Tester la continuité avant mise sous tension.", category: 'électrique',   is_critical: true,  page_ref: 15, duration: '15 min', requires_witness: false },
  { id: 12, step_number: 12, title: 'Connecter le bus de communication CANopen',  description: 'Câble blindé 2 paires torsadées. Résistance de terminaison 120 Ω aux deux extrémités. Adresse nœud : 0x21.', category: 'électrique',   is_critical: false, page_ref: 16, duration: '10 min', requires_witness: false },
  { id: 13, step_number: 13, title: 'Mettre sous tension',                        description: "Réenclencher l'armoire principale. Vérifier l'allumage du voyant V-MAIN. Aucune alarme ne doit apparaître sur l'IHM.", category: 'électrique',   is_critical: false, page_ref: 17, duration: '2 min',  requires_witness: false },
  { id: 14, step_number: 14, title: "Tester les arrêts d'urgence",               description: 'Activer chaque AU successivement. La pompe doit s\'arrêter en moins de 0,5 s. Réarmer après chaque test.', category: 'test',         is_critical: true,  page_ref: 18, duration: '8 min',  requires_witness: true  },
  { id: 15, step_number: 15, title: "Test d'étanchéité à 50 bar",                description: 'Monter progressivement à 50 bar (pas de 10 bar). Maintenir 10 min. Aucune chute de pression > 1 bar tolérée. Inspecter tous les raccords.', category: 'test',         is_critical: false, page_ref: 19, duration: '20 min', requires_witness: false },
  { id: 16, step_number: 16, title: "Test d'étanchéité à pression nominale 250 bar", description: 'Monter à 250 bar par paliers de 50 bar. Maintenir 30 min. Tolérance : 2 bar max. Documenter les valeurs au manomètre M-PRINC.', category: 'test',         is_critical: true,  page_ref: 20, duration: '45 min', requires_witness: false },
  { id: 17, step_number: 17, title: 'Calibrer la course du vérin',               description: "Lancer le cycle d'auto-calibration depuis l'IHM (menu Maintenance > Calibration). Course attendue : 320 mm ± 0,2 mm.", category: 'test',         is_critical: false, page_ref: 21, duration: '10 min', requires_witness: false },
  { id: 18, step_number: 18, title: "Vérifier l'évacuation des fumées",          description: "Hotte H-1 raccordée et tirage > 200 m³/h mesuré à l'anémomètre. Capteur fumée actif.", category: 'vérification', is_critical: false, page_ref: 22, duration: '5 min',  requires_witness: false },
  { id: 19, step_number: 19, title: 'Renseigner le carnet de mise en service',   description: 'Numéro de série, date, opérateurs, valeurs des tests d\'étanchéité. Coller l\'étiquette CE-MS sur la face avant.', category: 'vérification', is_critical: false, page_ref: 23, duration: '10 min', requires_witness: false },
  { id: 20, step_number: 20, title: 'Briefing utilisateur final',                description: "Présenter à l'opérateur référent : démarrage, AU, recharge huile, alarmes principales. Faire signer le PV de réception.", category: 'vérification', is_critical: false, page_ref: 24, duration: '20 min', requires_witness: false },
]

export const VALIDATIONS = {
  1:  { status: 'done',   technician_name: 'Jean Mercier',   validated_at: '2026-05-09T09:08:00Z' },
  2:  { status: 'done',   technician_name: 'Jean Mercier',   witness_name: 'M. Dubois', validated_at: '2026-05-09T09:14:00Z' },
  3:  { status: 'done',   technician_name: 'Jean Mercier',   validated_at: '2026-05-09T09:26:00Z' },
  4:  { status: 'done',   technician_name: 'Karim Belkacem', validated_at: '2026-05-09T09:58:00Z' },
  5:  { status: 'done',   technician_name: 'Karim Belkacem', note: 'Résine lot R2-3409, prise OK à T+4h10', validated_at: '2026-05-09T14:11:00Z' },
  6:  { status: 'done',   technician_name: 'Karim Belkacem', validated_at: '2026-05-09T14:34:00Z' },
  7:  { status: 'done',   technician_name: 'Marie Tissier',  validated_at: '2026-05-09T15:02:00Z' },
  8:  { status: 'done',   technician_name: 'Marie Tissier',  validated_at: '2026-05-09T15:21:00Z' },
  9:  { status: 'issue',  technician_name: 'Marie Tissier',  note: 'Bulles persistantes au regard R1 après 8 min. Suspicion de fuite d\'air sur joint flexible HP2. Joint à remplacer (réf. JT-22) avant validation.', validated_at: '2026-05-09T15:38:00Z' },
  10: { status: 'active', technician_name: 'Marie Tissier',  started_at: '2026-05-09T15:42:00Z' },
}

export const OTHER_PROJECTS = [
  { id: 9,  name: 'Compresseur Atlas GA-22',    ref: 'GA-22 / Rev. 02', total_steps: 14, completed_steps: 14, created_at: '2026-05-06' },
  { id: 10, name: 'Convoyeur de palettes CP-3', ref: 'CP-3 / Rev. 01',  total_steps: 9,  completed_steps: 9,  created_at: '2026-05-04' },
  { id: 11, name: 'Refroidisseur RC-12',        ref: 'RC-12 / Rev. 04', total_steps: 22, completed_steps: 6,  created_at: '2026-05-02' },
]
