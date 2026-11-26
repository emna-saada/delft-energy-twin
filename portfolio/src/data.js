// All facts come from Emna's CV (Nov 2026) and the delft-energy-twin README.
// Reference "role": used = cited / used in the work; background = further reading for the topic.

export const links = {
  email: 'emnasaada171@gmail.com',
  linkedin: 'https://www.linkedin.com/in/emnasaada',
  github: 'https://github.com/emna-saada',
  cv: './Emna_Saada_CV.pdf'
};

export const nav = [
  { id: 'build', label: 'What I build' },
  { id: 'quest', label: 'Main quest' },
  { id: 'projects', label: 'Projects' },
  { id: 'experience', label: 'Experience' },
  { id: 'skills', label: 'Skills' },
  { id: 'contact', label: 'Contact' }
];

export const heroStats = [
  { to: 178, label: 'wetland videos analysed' },
  { to: 442, suffix: 'M', label: 'LiDAR points processed' },
  { to: 2239, separator: ',', label: 'papers in my RAG agent' },
  { to: 6, label: 'research-grade projects' }
];

export const domains = [
  {
    key: 'cv',
    title: 'Computer vision',
    kicker: 'Seeing wildlife',
    text: 'Detectors and classifiers that find birds in wetland videos, recognise their species and read their behaviour, evaluated without leakage.',
    tags: ['YOLOv9', 'Faster R-CNN', 'EfficientNet', 'PyTorch'],
    stat: { value: '+12.6%', label: 'mAP50-95 over the published baseline (first fold)' }
  },
  {
    key: 'eo',
    title: 'Earth observation',
    kicker: 'Reading the planet',
    text: 'Ten years of a UNESCO wetland mapped from Sentinel-2 and Landsat time series, with trend tests that turn pixels into findings.',
    tags: ['Sentinel-2', 'Landsat', 'Earth Engine', 'U-Net'],
    stat: { value: '−18%', label: 'summer marsh lost in Ichkeul, detected with Mann-Kendall' }
  },
  {
    key: 'lidar',
    title: '3D & LiDAR',
    kicker: 'Rebuilding cities',
    text: 'Hundreds of millions of airborne laser points turned into a validated 3D city model with rooftop solar potential.',
    tags: ['AHN6', 'Numba', 'CityJSON', 'CesiumJS'],
    stat: { value: '5.2 cm', label: 'median roof-height error on 30,598 buildings' }
  },
  {
    key: 'ai',
    title: 'AI agents & data',
    kicker: 'Making research faster',
    text: 'A local agent that reads 2,239 papers, then writes, runs and repairs its own satellite workflows, plus a climate-risk model for banks.',
    tags: ['RAG', 'Local LLMs', 'FastAPI', 'CMIP6'],
    stat: { value: '30/30', label: 'benchmark tasks solved by the GeoRAG agent' }
  }
];

export const wetland = {
  setting: [
    { to: 178, label: 'videos' },
    { to: 13, label: 'bird species' },
    { to: 7, label: 'behaviours' },
    { to: 2, label: 'wetlands · Alicante, Spain' }
  ],
  behaviours: ['alert', 'preening', 'resting', 'flying', 'swimming', 'feeding', 'walking'],
  metrics: [
    { name: 'Precision', ours: 0.872, paper: 0.835 },
    { name: 'Recall', ours: 0.776, paper: 0.759 },
    { name: 'mAP50', ours: 0.833, paper: 0.801 },
    { name: 'mAP50-95', ours: 0.626, paper: 0.556 }
  ],
  protocol: [
    { t: 'Video-grouped cross-validation', d: 'All frames of a video stay on the same side of every split.' },
    { t: 'Locked test fold', d: 'Held-out videos are protected by an assertion: the code refuses to run if they leak.' },
    { t: 'Two-phase protocol', d: 'Tune on train/validation videos, then evaluate once per seed on the held-out videos.' },
    { t: 'McNemar + Holm-Bonferroni', d: 'Paired tests with multiple-comparison correction behind every "best model" claim.' }
  ],
  classification: [
    { label: 'Species · EfficientNet-B0 + logistic regression', value: 96.95, note: 'macro-F1 0.960', tone: 'lagoon' },
    { label: 'Behaviour · paper video models', value: 56, from: 49, note: '49–56%', tone: 'muted' },
    { label: 'Behaviour · ours, 4-frame pooling', value: 43.4, note: '7 classes', tone: 'coral' },
    { label: 'Behaviour · paper S3D baseline', value: 29, note: 'baseline', tone: 'muted' }
  ],
  engineering: [
    'Configuration-driven, resumable pipeline',
    'Cached frozen embeddings',
    'Warm-up + cosine learning rate',
    'Letterbox resizing',
    'CSV result tables',
    'Faster R-CNN also tested',
    'Dataset issues documented'
  ]
};

export const projects = [
  {
    id: 'wetlandbirds',
    num: '01',
    kicker: 'Research internship · MSE × Efrei · Jul – Aug 2026',
    title: 'Visual WetlandBirds',
    subtitle: 'Bird detection, species and behaviour recognition in wetland videos',
    challenge:
      'Reproduce, then beat, the baselines of a 2025 Scientific Data benchmark: 178 videos from La Mata and El Hondo, 13 species, 7 behaviours.',
    solution:
      'YOLOv9 detection with the paper’s frame sampling, EfficientNet-B0 embeddings for species, 4-frame pooling for behaviour, inside a leakage-free, statistically tested protocol.',
    pipeline: ['Video', 'Frame sampling', 'YOLOv9', 'Crops', 'EfficientNet-B0', 'Species / behaviour', 'McNemar tests'],
    stack: ['Python', 'PyTorch', 'Ultralytics', 'scikit-learn', 'RTX 4060'],
    team: 'Supervisors: Dr. Ali Ben Abbes (MSE), Dr. Faten Chakchouk (Efrei Research Lab) · team of two, with Souha Hamdani',
    deep: {
      how: [
        'Detection: yolov9c, COCO-pretrained (Ultralytics), trained with the paper’s frame sampling. About 31 h per fold on an RTX 4060 laptop GPU.',
        'Result on the first completed tuning fold: precision 0.872, recall 0.776, mAP50 0.833, mAP50-95 0.626, against 0.835 / 0.759 / 0.801 / 0.556 for the paper. Multi-seed evaluation on the official test videos is the next step.',
        'I first compared 4 CNNs with stratified 5-fold cross-validation. Auditing my own pipeline revealed crop-level leakage between frames of the same video, so I rebuilt it around video-grouped folds and a locked test fold.',
        'Species: 96.95% accuracy (macro-F1 0.960) with frozen EfficientNet-B0 embeddings and logistic regression. Behaviour: 43.4% over 7 classes, above the S3D baseline (29%), below the paper’s video models (49–56%), which points to temporal models and tracking.'
      ],
      links: [
        { label: 'Code on GitHub', href: 'https://github.com/emna-saada/wetlandbirds-internship', kind: 'code' }
      ],
      refs: [
        { t: 'Rodriguez-Juan et al. (2025). Visual WetlandBirds. Scientific Data 12:1200', href: 'https://www.nature.com/search?q=Visual%20WetlandBirds&journal=sdata', role: 'benchmark followed' },
        { t: 'Wang, Yeh & Liao (2024). YOLOv9: Learning What You Want to Learn Using Programmable Gradient Information', href: 'https://arxiv.org/abs/2402.13616', role: 'used' },
        { t: 'Ultralytics YOLO documentation', href: 'https://docs.ultralytics.com', role: 'used' },
        { t: 'Tan & Le (2019). EfficientNet: Rethinking Model Scaling for CNNs', href: 'https://arxiv.org/abs/1905.11946', role: 'used' },
        { t: 'Ren et al. (2015). Faster R-CNN', href: 'https://arxiv.org/abs/1506.01497', role: 'used' },
        { t: 'Xie et al. (2018). Rethinking Spatiotemporal Feature Learning (S3D)', href: 'https://arxiv.org/abs/1712.04851', role: 'paper baseline' },
        { t: 'scikit-learn GroupKFold', href: 'https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html', role: 'used' },
        { t: 'McNemar’s test', href: 'https://en.wikipedia.org/wiki/McNemar%27s_test', role: 'used' },
        { t: 'Holm–Bonferroni method', href: 'https://en.wikipedia.org/wiki/Holm%E2%80%93Bonferroni_method', role: 'used' }
      ]
    }
  },
  {
    id: 'ichkeul',
    num: '02',
    kicker: 'Personal project · 2026',
    title: 'Ichkeul Habitat Time Machine',
    subtitle: 'Ten years of a UNESCO wetland, seen from orbit',
    challenge:
      'Ichkeul is a UNESCO wetland and a key stop for migratory waterbirds. How have its habitats changed, and what drives the water?',
    solution:
      '20 seasonal Sentinel-2 composites with 8-class weak labels; Random Forest, U-Net and AlphaEarth embeddings compared on a spatial-block split; trend tests and a Landsat cross-check back to 1984.',
    pipeline: ['Sentinel-2', 'Seasonal composites', 'Weak labels', 'RF / U-Net / AlphaEarth', 'Trend tests', 'Web atlas'],
    stack: ['Google Earth Engine', 'PyTorch', 'Sentinel-2', 'Landsat', 'rasterio'],
    results: [
      { v: '0.605', l: 'mIoU, AlphaEarth embeddings' },
      { v: '−18%', l: 'summer marsh (Mann-Kendall, Sen)' },
      { v: 'R² 0.91', l: 'open water explained by season + rainfall' },
      { v: 'r = 0.99', l: 'agreement with Landsat 1984–2021' }
    ],
    deep: {
      how: [
        '20 seasonal Sentinel-2 composites over ten years, labelled with 8 weak habitat classes.',
        'Models compared on a spatial-block split (no neighbouring pixels across train and test): Random Forest 0.514, U-Net ResNet-34 0.573, AlphaEarth embeddings 0.605 mIoU.',
        'Mann-Kendall test and Sen’s slope reveal an 18% loss of summer marsh; season and rainfall explain R² 0.91 of open-water area.',
        'The series is validated against Landsat 1984–2021 (r = 0.99) and published as an interactive web atlas.'
      ],
      links: [
        { label: 'Interactive atlas', href: 'https://emna-saada.github.io/ichkeul-habitat-time-machine', kind: 'live' },
        { label: 'Code on GitHub', href: 'https://github.com/emna-saada/ichkeul-habitat-time-machine', kind: 'code' }
      ],
      refs: [
        { t: 'UNESCO World Heritage: Ichkeul National Park', href: 'https://whc.unesco.org/en/list/8', role: 'site' },
        { t: 'Copernicus Sentinel-2 mission (ESA)', href: 'https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2', role: 'data' },
        { t: 'Google Satellite Embedding (AlphaEarth) dataset', href: 'https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL', role: 'used' },
        { t: 'Ronneberger et al. (2015). U-Net', href: 'https://arxiv.org/abs/1505.04597', role: 'used' },
        { t: 'He et al. (2015). Deep Residual Learning (ResNet)', href: 'https://arxiv.org/abs/1512.03385', role: 'used' },
        { t: 'Mann–Kendall trend test', href: 'https://en.wikipedia.org/wiki/Kendall_rank_correlation_coefficient#Mann%E2%80%93Kendall_test', role: 'used' },
        { t: 'Theil–Sen (Sen’s slope) estimator', href: 'https://en.wikipedia.org/wiki/Theil%E2%80%93Sen_estimator', role: 'used' }
      ]
    }
  },
  {
    id: 'delft',
    num: '03',
    kicker: 'Personal project · 2026',
    title: 'LiDAR Energy Twin of Delft',
    subtitle: 'From point cloud to prosumer',
    challenge:
      'How much solar power could Delft’s roofs produce, what do heritage rules allow, and what happens when Dutch net metering ends on 1 January 2027?',
    solution:
      '442 million AHN6 points reconstructed into roof planes per building, a shadow-aware solar model per 0.5 m roof cell, heritage filters and household economics, published as a 3D web twin.',
    pipeline: ['AHN6 LiDAR', 'DSM / DTM', 'Roof planes (Numba)', 'Shadow + sun model', 'PV economics', 'CesiumJS twin'],
    stack: ['Python', 'Numba', 'CityJSON', 'CesiumJS', 'MapLibre'],
    results: [
      { v: '31,400', l: 'buildings reconstructed' },
      { v: '99.3%', l: 'roof planes matched to national 3D data' },
      { v: '18.5 GWh', l: 'solar potential, historic centre' },
      { v: '94%', l: 'recall, change detection AHN5 → AHN6' }
    ],
    deep: {
      how: [
        '442 million AHN6 points over 14 tiles → DSM, DTM and vegetation rasters → roof planes per BAG building with Numba region growing (31,400 buildings).',
        'Per 0.5 m roof cell: a 72-direction horizon scan over 200 m, a sun map from the PVGIS-SARAH3 typical year, Hay–Davies sky model, trees with seasonal transmissivity.',
        'Validation: 99.3% of roof planes ≥ 10 m² matched, 5.2 cm median height error, irradiance bias −1.2% against PVGIS.',
        'The historic centre could produce 18.5 GWh a year; when net metering ends, panels on its homes lose 34% of their annual value, 15% with a 5 kWh battery.'
      ],
      links: [
        { label: '3D web twin', href: 'https://emna-saada.github.io/delft-energy-twin/', kind: 'live' },
        { label: 'Code on GitHub', href: 'https://github.com/emna-saada/delft-energy-twin', kind: 'code' }
      ],
      refs: [
        { t: 'AHN: Actueel Hoogtebestand Nederland (Dutch national LiDAR)', href: 'https://www.ahn.nl', role: 'data' },
        { t: 'PVGIS (EU Joint Research Centre)', href: 'https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en', role: 'validation' },
        { t: 'Zhou et al. (2022). Solar RRL 6, 2100478', href: 'https://onlinelibrary.wiley.com/action/doSearch?AllField=Zhou+2022+Solar+RRL+2100478', role: 'validation' },
        { t: 'CityJSON 2.0 specification', href: 'https://www.cityjson.org', role: 'used' },
        { t: 'CesiumJS', href: 'https://cesium.com/platform/cesiumjs/', role: 'used' },
        { t: 'Numba', href: 'https://numba.pydata.org', role: 'used' }
      ]
    }
  },
  {
    id: 'georag',
    num: '04',
    kicker: 'Personal project · 2026',
    title: 'GeoRAG Copilot',
    subtitle: 'A local AI agent for geospatial research',
    challenge:
      'Research questions in remote sensing need both the literature and working code. Could a fully local agent do both, and prove its answers?',
    solution:
      'Hybrid retrieval (BM25 + Qwen3 embeddings) over 2,239 papers with a 181-term knowledge graph; an agent that writes, runs and self-repairs Sentinel-2 workflows in a sandbox.',
    pipeline: ['Question', 'BM25 + Qwen3', 'Knowledge graph', 'Agent writes code', 'Sandbox run', 'Self-repair', 'Answer'],
    stack: ['Python', 'Local LLMs', 'RAG', 'FastAPI', 'CI'],
    results: [
      { v: '2,239', l: 'papers indexed' },
      { v: '181', l: 'knowledge-graph terms' },
      { v: '30/30', l: 'benchmark tasks' },
      { v: 'IoU 0.966', l: 'vs JRC Global Surface Water' }
    ],
    deep: {
      how: [
        'Hybrid retrieval combines keyword search (BM25) and dense Qwen3 embeddings over 2,239 papers, linked by a 181-term knowledge graph.',
        'The agent writes Sentinel-2 workflows, runs them in a sandbox, reads the errors and repairs its own code.',
        'It solves 30/30 benchmark tasks; its water maps reach IoU 0.966 against the JRC Global Surface Water reference. Tests and CI included.'
      ],
      links: [
        { label: 'Project site', href: 'https://emna-saada.github.io/GeoRAG', kind: 'live' },
        { label: 'Code on GitHub', href: 'https://github.com/emna-saada/GeoRAG', kind: 'code' }
      ],
      refs: [
        { t: 'Lewis et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP', href: 'https://arxiv.org/abs/2005.11401', role: 'background' },
        { t: 'Okapi BM25', href: 'https://en.wikipedia.org/wiki/Okapi_BM25', role: 'used' },
        { t: 'Qwen models on Hugging Face', href: 'https://huggingface.co/Qwen', role: 'used' },
        { t: 'JRC Global Surface Water', href: 'https://global-surface-water.appspot.com', role: 'validation' },
        { t: 'FastAPI', href: 'https://fastapi.tiangolo.com', role: 'used' }
      ]
    }
  }
];

export const moreProjects = [
  {
    id: 'climarisk',
    cat: 'data',
    tag: 'Climate · Finance',
    title: 'ClimaRisk Tunisia',
    text: 'Heat, drought, flood and wildfire scores for 2,000 synthetic loans in 24 governorates from 5 CMIP6 models, translated into PD, LGD and expected-loss adjustments.',
    bullets: ['Tested Python package', 'Results website'],
    stack: 'Python · CMIP6 · NGFS · WRI Aqueduct · Streamlit',
    links: [
      { label: 'Site', href: 'https://emna-saada.github.io/climarisk-tunisia' },
      { label: 'Code', href: 'https://github.com/emna-saada/climarisk-tunisia' }
    ],
    refs: [
      { t: 'CMIP6', href: 'https://pcmdi.llnl.gov/CMIP6/' },
      { t: 'NGFS scenarios', href: 'https://www.ngfs.net/ngfs-scenarios-portal/' },
      { t: 'WRI Aqueduct', href: 'https://www.wri.org/aqueduct' }
    ]
  },
  {
    id: 'federated',
    cat: 'ai',
    tag: 'Capstone · MSE',
    title: 'Federated learning at the edge',
    text: 'Raised global accuracy from 49.0% to 80.1% (macro-F1 72.9%) across distributed clients, without centralising their data.',
    bullets: ['49.0% → 80.1% accuracy', 'macro-F1 72.9%'],
    stack: 'Academic project · 2025 – 2026',
    links: [],
    refs: [{ t: 'McMahan et al. (2017), FedAvg (background)', href: 'https://arxiv.org/abs/1602.05629' }]
  },
  {
    id: 'pwn',
    cat: 'data',
    tag: 'Internship · 2025',
    title: '44 million health records',
    text: 'Cleaned and matched 44 million records (2.8 GB) with regex and Levenshtein distance, then built Kibana (ELK) dashboards for a Ministry of Health programme.',
    bullets: ['Fuzzy record linkage', 'ELK dashboards'],
    stack: 'Python · regex · Levenshtein · Elasticsearch · Kibana',
    links: [],
    refs: [{ t: 'Levenshtein distance', href: 'https://en.wikipedia.org/wiki/Levenshtein_distance' }]
  },
  {
    id: 'species',
    cat: 'cv',
    tag: 'Internship module',
    title: 'Species recognition',
    text: 'Frozen EfficientNet-B0 embeddings plus logistic regression on annotated crops: 96.95% accuracy and macro-F1 0.960 over 13 wetland bird species.',
    bullets: ['Cached embeddings', 'Grouped evaluation'],
    stack: 'PyTorch · EfficientNet · scikit-learn',
    links: [{ label: 'Code', href: 'https://github.com/emna-saada/wetlandbirds-internship' }],
    refs: [{ t: 'EfficientNet (Tan & Le, 2019)', href: 'https://arxiv.org/abs/1905.11946' }]
  },
  {
    id: 'change',
    cat: 'eo',
    tag: '3D change detection',
    title: 'Delft, 2023 → 2026',
    text: 'Compared two LiDAR epochs (AHN5 → AHN6) to find new, raised, lowered and demolished buildings and rooftop PV installed since 2023: 94% recall on new buildings.',
    bullets: ['96.5% of new buildings confirmed by BAG year', 'Rooftop PV detection'],
    stack: 'AHN5 · AHN6 · Python',
    links: [{ label: 'Code', href: 'https://github.com/emna-saada/delft-energy-twin' }],
    refs: [{ t: 'AHN', href: 'https://www.ahn.nl' }]
  },
  {
    id: 'cnn',
    cat: 'cv',
    tag: 'Evaluation study',
    title: 'Four CNNs, one honest test',
    text: 'Compared four CNN backbones with stratified 5-fold cross-validation, then caught my own crop-level leakage and rebuilt the study with video-grouped folds.',
    bullets: ['Leakage audit', 'Paired statistical tests'],
    stack: 'PyTorch · scikit-learn · statsmodels-style tests',
    links: [{ label: 'Code', href: 'https://github.com/emna-saada/wetlandbirds-internship' }],
    refs: [{ t: 'Data leakage in ML', href: 'https://en.wikipedia.org/wiki/Leakage_(machine_learning)' }]
  }
];

export const filters = [
  { id: 'all', label: 'All' },
  { id: 'cv', label: 'Computer vision' },
  { id: 'eo', label: 'Earth observation' },
  { id: 'data', label: 'Data & climate' },
  { id: 'ai', label: 'Distributed AI' }
];

export const experience = [
  {
    when: 'Jul — Aug 2026',
    where: 'Manouba · with Efrei, Paris',
    role: 'Research Intern',
    org: 'Wildlife Monitoring & Computer Vision, MSE × Efrei',
    text: 'Reproduced and beat the Visual WetlandBirds baselines; redesigned the evaluation after finding leakage in my own pipeline.',
    tags: ['YOLOv9', 'Grouped CV', 'McNemar', 'PyTorch']
  },
  {
    when: 'Jul — Aug 2025',
    where: 'Tunisia',
    role: 'Data Analysis Intern',
    org: 'Pwn & Patch',
    text: 'Cleaned and matched 44 million records (2.8 GB); Kibana dashboards for a Ministry of Health programme.',
    tags: ['Regex', 'Levenshtein', 'ELK']
  },
  {
    when: '2023 — 2025',
    where: 'Manouba',
    role: 'Founder & Chairwoman',
    org: 'IEEE MSE Student Branch',
    text: 'Founded the branch and led it for two years; in 2025 also founded Blue MSE, a UN SDG initiative.',
    tags: ['Leadership', 'Community']
  }
];

export const skills = [
  { group: 'Computer vision', items: ['YOLOv9 (Ultralytics)', 'Faster R-CNN', 'EfficientNet', 'ResNet', 'U-Net', 'Transfer learning', 'Video frame sampling', 'mAP50 / mAP50-95'] },
  { group: 'Evaluation & statistics', items: ['Grouped k-fold', 'Locked test sets', 'McNemar', 'Holm-Bonferroni', 'Macro-F1', 'Spatial-block validation', 'Mann-Kendall · Sen'] },
  { group: 'Programming', items: ['Python', 'PyTorch', 'scikit-learn', 'NumPy', 'pandas', 'SHAP', 'Git', 'Unit tests + CI', 'FastAPI', 'SQL'] },
  { group: 'Earth observation', items: ['Sentinel-2', 'Landsat', 'Google Earth Engine', 'AlphaEarth', 'Airborne LiDAR', 'rasterio', 'GeoPandas', 'QGIS'] }
];

export const method = [
  { n: '01', t: 'Reproduce', d: 'Rebuild the published baseline before claiming anything.' },
  { n: '02', t: 'Audit', d: 'Hunt for leakage in my own pipeline, not just others’.' },
  { n: '03', t: 'Improve', d: 'Change one thing at a time, with configs and cached runs.' },
  { n: '04', t: 'Prove', d: 'Locked test sets and paired statistical tests.' }
];

export const education = [
  {
    when: '2022 — 2027',
    title: 'Engineering Degree in Geoinformatics',
    org: 'Manouba School of Engineering (MSE), University of Manouba',
    note: 'Final year · taught in English · GPA 15/20 (Bien)'
  }
];

export const coursework = ['Machine learning', 'Image processing', 'Remote sensing', '3D imagery', 'Geostatistics', 'Spatio-temporal analytics', 'Big data & cloud'];

export const awards = [
  { t: 'Winner, TCB SCALE', d: '1 of 6 winning teams among 200 · 10,000 TND funding · 2025' },
  { t: 'Founder & Chairwoman', d: 'IEEE MSE Student Branch · 2023 – 2025' },
  { t: 'Founder, Blue MSE', d: 'UN Sustainable Development Goals initiative · 2025' },
  { t: 'Freelance translator', d: 'English · Arabic · French' }
];

export const languages = [
  { l: 'Arabic', lv: 'Native', p: 100 },
  { l: 'English', lv: 'C1', p: 85 },
  { l: 'French', lv: 'B2', p: 70 }
];

export const achievements = {
  start: { t: 'New game', d: 'You started Emna’s story' },
  build: { t: 'Four worlds unlocked', d: 'Vision, orbit, cities, agents' },
  baseline: { t: 'Baseline beaten', d: '+12.6% mAP50-95 on the first fold' },
  leak: { t: 'Boss defeated: data leakage', d: 'Video-grouped split engaged' },
  orbit: { t: 'Ten years from orbit', d: '20 seasonal composites scanned' },
  city: { t: '442 million points tamed', d: 'Delft rebuilt in 3D' },
  curious: { t: 'Curious mind', d: 'You opened a deep dive' },
  final: { t: 'Final level reached', d: 'Next quest: PFE, Feb 2027' }
};
