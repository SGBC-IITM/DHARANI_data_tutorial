
# Image analysis for fetal brain anomalies

There are multiple AI-based image analysis models and methods that can be used to study fetal brain pathologies from histology slides. These include both general-purpose histopathology analysis techniques and some specialized methods for neurodevelopmental pathology. Below is a breakdown of approaches and tools that are most relevant:

| Applications | Task | Methods | 
|:-- | :-- | :-- |
| * Delineating disrupted cortical lamination (e.g., in lissencephaly).<br> *  Identifying germinal matrix or periventricular regions (e.g., for GMH). <br> * Mapping white vs. gray matter in myelination studies. | Tissue & region segmentation <br> (Useful for localizing anatomical structures, lesions, and abnormal regions) | * **U-Net variants**: For fine-grained segmentation of cortical layers, ventricles, germinal matrix. <br> * **Vision Transformers** (e.g., Mask2Former, Segment Anything variants): For high-resolution and hierarchical region segmentation. <br> * **HoVer-Net / Cellpose**: For nuclei and cell boundary segmentation. |
| *Neuronal depletion in hypoxic-ischemic encephalopathy (HIE).<br> * Proliferation deficits in microcephaly (with Ki-67 labeling). <br> * Increased gliosis in PVL (astrocytes, microglia). | Cell counting & density estimation <br> (Quantifies changes in cell populations and cytoarchitecture) | * **StarDist / Cellpose / QuPath**: For automatic nuclear segmentation and counting.<br> * **Patch-based CNNs or ViTs**: For estimating cell density in tiles. <br> * Density heatmaps: Using **kernel density estimation** or deep regression models. |
| * Detecting disrupted layering in polymicrogyria or lissencephaly.<br> * Identifying ectopic neurons in heterotopias. <br> * Characterizing cortical plate vs. subplate. | Cortical Layering & Cytoarchitecture Analysis <br> (Detects abnormalities in cortical development, lamination, and migration) | * Delineation of layers using CNN-based **boundary detectors** or ViTs with positional encoding. <br> * Self-supervised models (e.g., DINO, MAE) for **feature learning from unlabeled slides**. <br> * **Graph-based methods**: Mapping neuronal positions and connectivity.|
| * Germinal matrix hemorrhage detection.<br> * Hypoxic injury in white matter or cortex.<br> * Periventricular leukomalacia. | Vascular & Hemorrhage Detection <br> (Detects hemorrhage, vessel malformations, and hypoxia-related damage) | * Color deconvolution + rule-based **segmentation** (e.g., for hemorrhage in HE-stained sections).<br> * Deep CNN classifiers or segmenters trained on annotated vascular lesions. <br> * **Tissue classification** pipelines (e.g., in Slideflow or PathML).|
| * Detecting delayed myelination in microcephaly. <br> * Characterizing white matter injury in PVL or HIE.<br> * Studying corpus callosum formation. | Myelination & White Matter Analysis <br> (Assesses white matter integrity and myelin development) | * **Color-based segmentation** of Luxol Fast Blue (LFB) or MBP IHC. <br> * CNNs trained to classify degree of myelination by region. <br> * **Texture-based features** or self-supervised representations for tissue characterization.|
| * CMV: Periventricular inclusions.<br> * Toxoplasma: Cyst detection.<br> * Zika: Calcifications, neuron loss.| Detection of Pathological Cell Types or Inclusions <br> (Identifies abnormal cells or infectious agents) | * **Object detection** models (e.g., Faster R-CNN, RetinaNet) for detecting CMV-infected cells, multinucleated cells. <br> * Custom-trained classifiers for giant cells in tuberous sclerosis or microglial nodules. <br> * Tile-level **anomaly detection using autoencoders** or weak supervision. |
| * Analyzing cortical folding in polymicrogyria.<br> * Detecting midline fusion defects.<br> * Quantifying ventricular or sulcal expansion. |  Morphometric & Shape Analysis <br> (Quantifies gyrification, structural dimensions, and malformations) |* **Image registration & morphometry**: Measuring structural symmetry/asymmetry.<br> * **Graph-based cortex unfolding**: For assessing gyri/sulci development.<br> * **Shape modeling**: For clefts (schizencephaly) or fused hemispheres (holoprosencephaly).|


## 🔧 Available Tools & Platforms
**QuPath** – Manual/semi-automated histology analysis with scripting.
- https://qupath.readthedocs.io/en/stable/docs/intro/about.html

- Bankhead, P., Loughrey, M.B., Fernández, J.A. et al. *QuPath: Open source software for digital pathology image analysis*. Sci Rep 7, 16878 (2017). https://doi.org/10.1038/s41598-017-17204-5

**PathML** / **Slideflow** – Python frameworks for WSI analysis with deep learning.
- https://pathml.readthedocs.io/en/latest/
- Rosenthal, J., Carelli, R., Omar, M., et al. *Building Tools for Machine Learning and Artificial Intelligence in Cancer Research: Best Practices and a Case Study with the PathML Toolkit for Computational Pathology*. Mol Cancer Res 1 February 2022; 20 (2): 202–206. https://doi.org/10.1158/1541-7786.MCR-21-0665
- https://github.com/slideflow/slideflow?tab=readme-ov-file
- Dolezal, J.M., Kochanny, S., Dyer, E. et al. Slideflow: deep learning for digital histopathology with real-time whole-slide visualization. BMC Bioinformatics 25, 134 (2024). https://doi.org/10.1186/s12859-024-05758-x

**MONAI** – Medical imaging deep learning framework (3D+2D).
- https://developer.nvidia.com/blog/whole-slide-image-analysis-in-real-time-with-monai-and-rapids/
- https://monai.medium.com/pathology-image-labeling-comes-to-monai-a033e200e587
- https://docs.monai.io/en/stable/whatsnew_1_1.html
- https://docs.monai.io/en/latest/applications.html#nuclick-modules-for-interactive-nuclei-segmentation

**TIA Toolbox** - computational pathology toolbox, with graph neural network support (*slidegraph*)
- https://tia-toolbox.readthedocs.io/en/latest/
- https://github.com/TissueImageAnalytics/tiatoolbox/tree/master
- Pocock, J., Graham, S., Vu, Q.D. et al. TIAToolbox as an end-to-end library for advanced tissue image analytics. Commun Med 2, 120 (2022). https://doi.org/10.1038/s43856-022-00186-5

**The Digital Slide Archive**, **HistomicsTK**
- https://digitalslidearchive.github.io/digital_slide_archive/#About
- https://github.com/DigitalSlideArchive/HistomicsTK?tab=readme-ov-file
- Gutman, D.A., Khalilia, M., Lee, S., et al. *The Digital Slide Archive: A Software Platform for Management, Integration, and Analysis of Histology for Cancer Research*. Cancer Res 1 November 2017; 77 (21): e75–e78. https://doi.org/10.1158/0008-5472.CAN-17-0629

Other software tools for pathology image analysis (Fiji, CellProfiler, Ilastik, Icy) https://digitalpathologyplace.com/8-free-open-source-software-programs-for-image-analysis-of-pathology-slides/

## Foundation models

Refer Mahmood Lab (Harvard) for several foundation models such as UNI, CONCH, HIPT
https://github.com/mahmoodlab

A table of foundation models in computational pathology
https://github.com/georg-wolflein/pathology-foundation-models

GigaPath
- https://www.microsoft.com/en-us/research/blog/gigapath-whole-slide-foundation-model-for-digital-pathology/
- Xu, H., Usuyama, N., Bagga, J. et al. A whole-slide foundation model for digital pathology from real-world data. Nature 630, 181–188 (2024). https://doi.org/10.1038/s41586-024-07441-w

Virchow
- https://www.microsoft.com/en-us/research/blog/large-scale-pathology-foundation-models-show-promise-on-a-variety-of-cancer-related-tasks/
- Vorontsov, E., Bozkurt, A., Casson, A. et al. A foundation model for clinical-grade computational pathology and rare cancers detection. Nat Med 30, 2924–2935 (2024). https://doi.org/10.1038/s41591-024-03141-0

Path Foundation
- https://developers.google.com/health-ai-developer-foundations/path-foundation/model-card
- https://arxiv.org/abs/2310.13259

HistoEncoder
- https://github.com/jopo666/HistoEncoder
- https://docs.pytorch.org/tutorials/intermediate/tiatoolbox_tutorial.html


## Evaluation studies, benchmarkss
- Tawsifur Rahman, Alexander S. Baras, Rama Chellappa, *Evaluation of a Task-Specific Self-Supervised Learning Framework in Digital Pathology Relative to Transfer Learning Approaches and Existing Foundation Models*, Modern Pathology,Volume 38, Issue 1,2025, https://doi.org/10.1016/j.modpat.2024.100636.
- Zheng, S., Cui, X., Sun, Y. et al. *Benchmarking PathCLIP for Pathology Image Analysi*s. J Digit Imaging. Inform. med. 38, 422–438 (2025). https://doi.org/10.1007/s10278-024-01128-4
- Narmin Ghaffari Laleh, Hannah Sophie Muti, Chiara Maria Lavinia Loeffler, et al,
*Benchmarking weakly-supervised deep learning pipelines for whole slide classification in computational pathology,* Medical Image Analysis, Volume 79, 2022, https://doi.org/10.1016/j.media.2022.102474.
- Wölflein, Georg, et al. *Benchmarking pathology feature extractors for whole slide image classification*. arXiv preprint arXiv:2311.11772 (2023). https://arxiv.org/abs/2311.11772