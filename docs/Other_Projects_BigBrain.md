Dharani/docs/Other Projects::BigBrain

[Back] to `docs`

[Back]:README.md

## The BigBrain Dataset

The BigBrain dataset is a groundbreaking resource in the field of neuroanatomy, representing an ultra-high-resolution (20 μm isotropic) three-dimensional (3D) model of an entire human brain, offering a level of detail approaching that of individual neurons. This remarkable model was constructed through the meticulous process of reconstructing 7404 histological sections, each a mere 20 microns in thickness, obtained from the brain of a 65-year-old male that had been embedded in paraffin. The creation of BigBrain involved a decade-long effort encompassing scanning, staining, both manual and automated correction of histological defects, and extensive digital processing to assemble the contiguous 3D volume. The dataset is made available to the research community in several formats to cater to diverse analytical needs. These include the original microscopy stains as high-resolution and color.tiff files, accompanied by transformation maps to the 3D blockface space, allowing researchers to access the raw data. Additionally, 3D reconstructions of the stains and MRI data are provided at a resolution of approximately 200 μm, offering a volumetric representation of the brain. For integration with standard neuroimaging pipelines, the dataset includes MNI coregistrations, where the stains, blockface, and MRI data are aligned to the MNI2009B space at a resolution of 0.5 mm. Finally, automated parcellations of the whole brain, cortical surface, and subcortical structures are also available. The BigBrain dataset is shared under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International Public License.

BigBrain holds immense significance for neuroanatomical research as it enables the extraction of microscopic-level data that is crucial for the modeling and simulation of neural circuits and brain function at an unprecedented spatial resolution. Unlike existing brain atlases that are limited to macroscopic scales, BigBrain allows for investigations at the level of cortical layers, columns, microcircuits, and even individual neurons, which is essential for understanding the neurobiological basis of complex cognitive processes. Furthermore, BigBrain is integrated within the EBRAINS infrastructure, a major European initiative dedicated to advancing brain research. This integration provides researchers with access to online viewers such as siibra-explorer, which allows for interactive visualization and exploration of the BigBrain data at its full 20 μm resolution, as well as the ability to link this structural information with other multimodal data available through EBRAINS. For researchers aiming to integrate BigBrain's detailed histology with other neuroimaging modalities, particularly MRI, the BigBrainWarp toolbox is a valuable resource. This toolbox simplifies the complex procedures required to transform data between BigBrain's histological space and standard MRI coordinate systems, facilitating multimodal analyses.

## Links
- https://www.ebrains.eu/tools/human-brain-atlas
- https://bigbrainproject.org/
- https://ftp.bigbrainproject.org/bigbrain-ftp/Welcome.txt
- https://siibra-python.readthedocs.io/en/latest/examples/01_atlases_and_parcellations/index.html
- https://www.science.org/doi/10.1126/science.1235381
- https://github.com/FZJ-INM1-BDA/siibra-tutorials
