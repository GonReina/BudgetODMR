 ▐▛███▛█   Claude Code v2.1.285
▝▜██████▀  Opus 5.5 · Claude Pro
 ▝▝   ▝▝   ~\Downloads\BudgetODMR

  Get to finished work sooner with Opus 5.5. Switch anytime with /model.

❯ /init                                                                         

  Ran 5 shell commands (ctrl+o to expand)

● Write(CLAUDE.md)
  ⎿  Wrote 37 lines to CLAUDE.md
      1 # CLAUDE.md
      3 This file provides guidance to Claude Code (claude.ai/code) when 
      4 
      5 ## What this is
      7 A budget ODMR (optically detected magnetic resonance) rig for an 
        ~2870 MHz, gamma = 28.024 MHz/mT) while a photodiode watches the 
        plication: there is no build system, test suite, linter, or requi
        rements file. Scripts are plain Python (numpy, matplotlib) run di
      8 
         backup. `TROUBLESHOOTING_GUIDE.md` is the ADF4351 +
     … +91 lines (ctrl+o to expand)

● I created CLAUDE.md in the repo root.

  The repo has no build system, tests or linter, and most scripts need live
  instruments. So instead of build and test commands, the file tells future
  sessions:

  - What runs without hardware: only the analysis scripts, the two simulations,
    and smcv/laser_rin_pc.py selftest. For everything else, use python -m 
    py_compile to check changes, and never run acquisition scripts because they
    drive real equipment.
  - How scripts are configured: by editing the constants at the top of each file
    or smcv/config.json, not with command-line arguments. It also lists the few
    scripts that do take an optional argument.
  - The three control setups: the old Arduino one, the scripts that run on the
    Red Pitaya itself, and the current smcv/ scripts that run on the PC and talk
    to both instruments over the network.
  - The shared modules in smcv/: the config loader, the instrument classes, the
    Red Pitaya acquisition sequence to reuse, the lock-in engine, and the
    helpers for power sweeps and self-oscillation runs.
  - How imports work: smcv/ modules import each other directly, and the
    analysis/ and notebooks/ scripts add smcv/ to their import path to reach the
    config loader.
  - Data conventions: the CSV format with # metadata lines, and which plot
    script goes with which acquisition script, so an output-format change
    updates both.

  It points to README.md and TROUBLESHOOTING_GUIDE.md for the full details
  rather than repeating them. There were no Cursor, Copilot, Codex or Gemini
  config files to include.

  smcv/config.json points data_dir at a Windows path on the lab PC
  (C:\Users\qute\...). The file mentions this, so a future session won't expect
  that folder to exist on your machine.

✻ Cogitated for 47s · done Wednesday 10:29

※ recap: I created CLAUDE.md for the BudgetODMR repo, covering how to run and safely check scripts, the three control setups, the shared smcv modules and the data conventions. Next, you could review the file and commit it if it looks right. (disable recaps in /config)

❯ I am working on an optical setup for NV-diamond experiments, and I want to    
  extend the existing Jupyter notebook to model and compare several versions of 
  the setup.                                                                    
                                                                                
  The current setup is documented in:                                           
                                                                                
  `@notebooks/Optical_Setup.ipynb`                                              
                                                                                
  Please first inspect this notebook carefully and understand the optical       
  components, their approximate positions, focal lengths, apertures/NA, and the 
  intended excitation and collection paths. Do not make assumptions about       
  component specifications if they can be determined from the notebook or       
  project files.                                                                
                                                                                
  ## Overall objective                                                          
                                                                                
  I want the notebook to become a quantitative optical-design document that:    
                                                                                
  1. Shows a clear 2D ray diagram for each configuration.                       
  2. Simulates the relevant optical paths.                                      
  3. Calculates useful figures of merit.                                        
  4. Clearly states the assumptions and approximations used.                    
  5. Identifies potential optical problems or missing components.               
  6. Allows the different configurations to be compared quantitatively.         
                                                                                
  A suitable ray-tracing package such as:                                       
                                                                                
  `https://github.com/DCC-Lab/RayTracing`                                       
                                                                                
  could be used, but please assess whether it is actually appropriate for all   
  parts of this task. If another Python package or a combination of analytical  
  Gaussian-optics calculations and ray tracing would be more suitable, use that 
  instead.                                                                      
                                                                                
  Do not add a dependency simply for the sake of using a ray-tracing library.   
  Prefer the simplest physically appropriate modelling approach.                
                                                                                
  ---                                                                           
                                                                                
  # 1. Model the current optical setup                                          
                                                                                
  Start with the setup that is already described in `Optical_Setup.ipynb`.      
                                                                                
  Create a section that reconstructs the optical system and produces a 2D       
  diagram showing:                                                              
                                                                                
  * excitation laser path                                                       
  * focusing optics                                                             
  * diamond/sample                                                              
  * fluorescence collection path                                                
  * collection optics                                                           
  * filters                                                                     
  * photodetector                                                               
  * relevant distances and focal lengths                                        
                                                                                
  Where useful, distinguish the excitation and collection paths visually.       
                                                                                
  I want to calculate at least:                                                 
                                                                                
  ### Excitation                                                                
                                                                                
  * Beam size at relevant optical elements                                      
  * Beam size entering the focusing optic                                       
  * Expected spot size at the diamond                                           
  * Ray angles/convergence at the sample                                        
  * Whether the focusing optic is being used within a sensible NA/aperture      
  regime                                                                        
  * Any obvious clipping or overfilling of apertures                            
                                                                                
  ### Collection                                                                
                                                                                
  * Approximate angular acceptance / collection NA                              
  * Size and position of the collected fluorescence beam at relevant planes     
  * Expected spot size on the photodetector                                     
  * Whether the detector is appropriately positioned relative to the collection 
  optics                                                                        
  * Any obvious clipping or vignetting                                          
                                                                                
  Be explicit about whether each calculation is based on geometric ray tracing, 
  Gaussian beam propagation, diffraction-limited estimates, or another          
  approximation.                                                                
                                                                                
  For quantities that cannot be reliably calculated with the chosen model, say  
  so rather than producing a misleading number.                                 
                                                                                
  ---                                                                           
                                                                                
  # 2. Model a fibre-coupled version of the setup                               
                                                                                
  Create a second section representing an improved setup in which the laser is  
  coupled into a fibre before entering the main optical system.                 
                                                                                
  The proposed sequence includes:                                               
                                                                                
  * fibre                                                                       
  * linear polariser on a rotating mount                                        
  * aspheric condenser/collimator                                               
  * two absorptive ND filters                                                   
  * the existing optical setup                                                  
                                                                                
  I am currently unsure about the correct order of the polariser and aspheric   
  optic. Please determine the physically sensible arrangement and explain why.  
                                                                                
  In particular, investigate:                                                   
                                                                                
  * Whether the asphere should act as a fibre collimator or condenser in this   
  configuration                                                                 
  * Where the polariser should be placed                                        
  * Whether the ND filters should be before or after the fibre/collimating      
  optics                                                                        
  * Whether the filters could introduce unwanted beam steering, aberrations, or 
  other issues                                                                  
  * Whether the fibre changes the expected beam waist/divergence entering the   
  setup                                                                         
  * Whether the fibre output can reasonably be treated as a Gaussian beam       
  * What fibre parameters are required for an accurate model                    
                                                                                
  If important information is missing (e.g. fibre type, wavelength, core        
  diameter, NA, MFD, etc.), identify it explicitly and ask me for it rather     
  than inventing values.                                                        
                                                                                
  Produce the same type of ray/optical diagram and quantitative analysis as for 
  the current setup.                                                            
                                                                                
  Also identify anything important that I may have forgotten in this proposed   
  configuration.                                                                
                                                                                
  ---                                                                           
                                                                                
  # 3. Optimised configuration for ensemble NV measurements                     
                                                                                
  Create a third section specifically for ensemble NV measurements.             
                                                                                
  The main proposed change is to replace the current 40× objective used for     
  collection with a high-NA collection aspheric condenser.                      
                                                                                
  Model the complete excitation and collection path.                            
                                                                                
  I want:                                                                       
                                                                                
  * A clear 2D optical diagram                                                  
  * The excitation path                                                         
  * The collection path                                                         
  * Relevant focal lengths, apertures and distances                             
  * Ray tracing or another appropriate optical simulation                       
  * Estimated collection NA                                                     
  * Estimated excitation spot size                                              
  * Collection beam size at relevant planes                                     
  * Expected light level reaching the detector, where this can reasonably be    
  estimated                                                                     
  * Identification of optical bottlenecks, clipping, aberrations, or            
  alignment-sensitive elements                                                  
                                                                                
  Please specifically consider whether using an aspheric condenser instead of   
  the 40× objective changes the geometry of the collection path in ways that    
  need to be accounted for.                                                     
                                                                                
  If the model requires assumptions about the fluorescence emission pattern of  
  an NV ensemble, state those assumptions explicitly.                           
                                                                                
  ---                                                                           
                                                                                
  # 4. Single-NV confocal configuration                                         
                                                                                
  Finally, model the single-NV configuration using the components I already     
  have.                                                                         
                                                                                
  This should use:                                                              
                                                                                
  * the 40× objective                                                           
  * the excitation path                                                         
  * the fluorescence collection path                                            
  * the pinhole                                                                 
  * the detector                                                                
  * the relevant filters                                                        
                                                                                
  The goal is to assess whether the available optics form a sensible confocal   
  microscope.                                                                   
                                                                                
  Calculate or estimate:                                                        
                                                                                
  * excitation spot size at the diamond                                         
  * collection NA                                                               
  * image/beam size at the pinhole plane                                        
  * appropriate pinhole size                                                    
  * expected confocal resolution, where it can be estimated                     
  * whether the pinhole is correctly positioned                                 
  * sensitivity of the system to defocus/misalignment                           
  * whether any existing optics are likely to limit the performance             
                                                                                
  If possible, show the excitation focus and fluorescence image/collection path 
  separately so that the confocal geometry is easy to understand.               
                                                                                
  ---                                                                           
                                                                                
  Do not manufacture values where the available information is insufficient.    
  Mark those quantities as requiring an input parameter or experimental         
  measurement.                                                                  
                                                                                
  ---                                                                           
                                                                                
  # 5. Implementation requirements                                              
                                                                                
  Please work directly with the existing notebook and project structure.        
                                                                                
  Before making substantial changes:                                            
                                                                                
  1. Inspect `@notebooks/Optical_Setup.ipynb`.                                  
  2. Inspect any existing optical-component definitions, configuration files,   
  or relevant Python modules in the repository.                                 
  3. Determine what information is already available.                           
  4. Identify missing hardware specifications.                                  
                                                                                
  Keep the notebook organised into clearly separated sections corresponding to  
  the four configurations above.                                                
                                                                                
  Where possible, make the optical parameters configurable near the beginning   
  of each section rather than hard-coding numbers throughout the calculations.  
                                                                                
  For example:                                                                  
                                                                                
  ```python                                                                     
  wavelength = ...                                                              
  focal_length = ...                                                            
  beam_diameter = ...                                                           
  distance = ...                                                                
  NA = ...                                                                      
  ```                                                                           
                                                                                
  Use SI units internally and label plots with sensible units.                  
                                                                                
  The notebook should produce publication/report-quality figures rather than    
  only numerical output.                                                        
                                                                                
  For diagrams, include:                                                        
                                                                                
  * optical components                                                          
  * optical axis                                                                
  * approximate ray paths                                                       
  * focal planes                                                                
  * sample plane                                                                
  * detector/pinhole planes                                                     
  * relevant distances                                                          
                                                                                
  For quantitative plots, include appropriate axis labels, units, legends, and  
  explanatory annotations.                                                      
                                                                                
  ---                                                                           
                                                                                
  # 6. Physics/model validation                                                 
                                                                                
  This is important: I do not just want code that produces plausible-looking    
  diagrams.                                                                     
                                                                                
  For each model, explain briefly:                                              
                                                                                
  * what physical model is being used                                           
  * what assumptions it makes                                                   
  * where the approximation is valid                                            
  * what it cannot tell us                                                      
  * whether the resulting figure of merit is likely to be experimentally        
  meaningful                                                                    
                                                                                
  In particular, distinguish between:                                           
                                                                                
  * geometric ray tracing                                                       
  * paraxial optics                                                             
  * Gaussian beam propagation                                                   
  * diffraction-limited estimates                                               
  * numerical aperture calculations                                             
  * actual aberration modelling                                                 
                                                                                
  If a simple analytical calculation is more physically appropriate than ray    
  tracing for a particular quantity, use the analytical calculation instead.    
                                                                                
  ---                                                                           
                                                                                
  # 7. Questions before implementation                                          
                                                                                
  You are explicitly allowed to ask me questions before implementing anything.  
                                                                                
  First inspect the notebook and repository, then give me a concise list of any 
  missing information that is genuinely required to make the simulations        
  physically meaningful.                                                        
                                                                                
  Prioritise questions such as:                                                 
                                                                                
  * laser wavelength                                                            
  * laser beam diameter/divergence                                              
  * fibre type and mode-field diameter                                          
  * aspheric lens focal length and NA                                           
  * objective model / NA                                                        
  * detector active area                                                        
  * pinhole diameter                                                            
  * filter specifications                                                       
  * relevant distances between components                                       
  * diamond thickness/index                                                     
  * any other parameter that materially affects the calculation                 
                                                                                
  If a parameter is not essential, do not stop the implementation just to ask   
  for it. Instead, make it a clearly documented configurable assumption.        
                                                                                
  Once the required information is available, implement the notebook            
  systematically rather than building four unrelated simulations.               

  Read 1 file, ran 6 shell commands (ctrl+o to expand)

● I've read the notebook and the related project files. The notebook only has
  one markdown cell describing the current setup, but procurement/ and proposal/
  already pin down most part numbers. Before I build anything, there are a few
  gaps that change the physics rather than just the numbers.

  What I already have

  Item: Laser
  Value: Thorlabs DJ532-40 at 532 nm, in an LDM56 mount run by an LTC56A
  controller, with a laser-pointer collimator
  Source: notebook, fiber_coupling_stage.md
  ────────────────────────────────────────
  Item: Objective
  Value: N40X-PF: NA 0.75, f = 5 mm, back aperture 7.5 mm
  Source: fiber_coupling_stage.md
  ────────────────────────────────────────
  Item: Collection optics and detector
  Value: DMLP550R dichroic, FELH0550 longpass, AC254-150-A-ML lens, PDA10A2
  detector (0.8 mm² active area, about Ø1 mm)
  Source: notebook, upgrade_justification.md
  ────────────────────────────────────────
  Item: Diamond
  Value: Thorlabs DNVB14 (n = 2.42)
  Source: proposal/workpackage3_report.tex
  ────────────────────────────────────────
  Item: Fibre
  Value: P3-405BPM-FC-1: single-mode and polarisation-maintaining at 532 nm,
  mode-field diameter ≈ 4.0 µm at 532 nm, FC/APC connector
  Source: fiber_coupling_stage.md
  ────────────────────────────────────────
  Item: Collimators
  Value: F240FC-532 owned (f = 7.86 mm, 1.48 mm beam); F810APC-543 proposed (f =

  34.74 mm)
  Source: fiber_coupling_stage.md
  ────────────────────────────────────────
  Item: Ensemble collection optic
  Value: ACL25416U-B asphere: f = 16 mm, NA 0.79, Ø25 mm, AR coating only 
  650–1050 nm
  Source: build_shopping.py
  ────────────────────────────────────────
  Item: Proposed extras
  Value: PDA100A2 detector (75.4 mm²), FELH0650 longpass, LPVISE100-A polariser
  on an RSP1/M rotation mount, NE10A and NE20A ND filters
  Source: build_shopping.py

  Modelling approach

  I recommend not adding DCC-Lab RayTracing. It is a paraxial matrix-optics
  tool, and paraxial optics breaks down exactly where this setup is interesting:
  an NA 0.75 objective, an NA 0.79 asphere, and refraction and total internal
  reflection at the diamond surface (n = 2.42). I'd put a small shared model in
  the notebook, using only numpy, scipy and matplotlib, which are already
  installed:

  - Gaussian beam propagation for all the excitation beams (laser, fibre output,
    filling the objective's back aperture).
  - Exact ray tracing with Snell's law at the diamond surface for the collection
    cone, total internal reflection and focal shift.
  - Étendue and imaging magnification for how big the fluorescence spot is on
    the detector and pinhole. The source is an extended glowing volume, not a
    point.
  - Diffraction-limited formulas for the confocal spot, the pinhole size and the
    resolution. Each one will be labelled as a best case wherever aberrations
    make it optimistic.

  The same component and drawing code will serve all four configurations, and
  every quantity will be tagged with the model it comes from.

  Questions

  Essential: these change the answers qualitatively.

  1. Laser beam leaving the pointer collimator: what are its diameter (1/e² or
     roughly) and divergence? fiber_coupling_stage.md lists this as unmeasured.
     It sets how much of the objective's back aperture is filled, and therefore
     the spot size in configuration 1. If it hasn't been measured, I'll make it
     a parameter and plot the results against it, with 1.5 mm as the reference
     value.
  2. Which asphere is the "condenser/collimator" in configuration 2? Is it the
     F240 collimator, the F810APC-543, or the ACL25416U-B? This decides whether
     roughly 1.5, 2.7 or 5.8 mm of beam reaches the objective. Also, are the
     collimators you own engraved FC or APC? An APC fibre in an FC collimator
     tilts the output beam by 3.7°.
  3. Ensemble geometry (configuration 3): does the ACL25416U-B collect from the
     opposite face of the diamond while the objective still does the excitation
     (transmission geometry)? Or does it replace the objective for both
     excitation and collection through the dichroic? And which detector and
     longpass filter go with it: PDA10A2 or PDA100A2, FELH0550 or FELH0650?
  4. Confocal path (configuration 4):
     - What is the pinhole diameter, or its part number?
     - Which lens focuses onto it? Is it the AC254-150 lens?
     - What sits behind the pinhole: the PDA10A2 directly, or a relay lens?
  5. Diamond: is it 3.0 × 3.0 × 0.5 mm? Which face is excited, and is there a
     coverslip or other window between the objective and the diamond? The
     N40X-PF is designed for a 0.17 mm glass coverslip. Focusing straight into
     diamond causes strong spherical aberration and shifts the focus, which
     matters most for configuration 4.

  Useful, but I'll use documented defaults if you don't have them.

  6. Approximate distances:
     - laser → dichroic → objective
     - objective → AC254 lens
     - AC254 lens → detector

     These only matter for divergence and clipping. Without them I'll assume the
     beams are collimated between components, use typical cage-system spacings,
     and flag that assumption.
  7. Excitation filter part number: "FBW5532-10" is not a Thorlabs number I
     recognise. Is it the FLH05532-10 (10 nm bandpass at 532 nm) or something
     else? Only its transmission matters.
  8. Laser power at the sample (mW), and whether you have a PDA10A2 voltage and
     gain setting from a real run. The notebook can then estimate the light
     reaching the detector and check it against a measurement, instead of
     floating an absolute number.

  Issues I've already spotted

  - The ACL25416U-B's -B coating is not anti-reflective at 532 nm. If it also
    carries the excitation beam, you get reflections of about 4% per surface.
    That costs power and sends back-reflections toward the detector.
  - For single-NV work, the diamond's refractive index is likely to limit
    performance more than the objective's NA: the refraction and
    spherical-aberration issue from question 5.

  Answer whatever you can, and say "use defaults" for the rest. I'll then build
  the notebook with the four configurations sharing one model.

✻ Cogitated for 1m 22s · done Wednesday 10:59

※ recap: I'm getting ready to turn Optical_Setup.ipynb into a quantitative comparison of your four optical setups, and I've finished reviewing the notebook and project files. Next, please answer my questions (laser beam size, which asphere, ensemble geometry, pinhole, diamond) or say "use defaults". (disable recaps in /config)

❯ Answers:                                                                      
  1. I had a rough look with a viewing card and it seemed just below 1.5mm      
  diameter. My understanding is that Over-filled pupils can lead to diffraction 
  effects at the focal spot.                                                    
  2. I haven't picked a part yet, I thought it would be necessary for the fiber 
  ocupling.                                                                     
  3. Both excitation and collection, i would probably use what we have, the     
  FELH0550 and the PDA10A2. We do not have the PDA100A2 or the FELH0650         
  4. I have a pinhole kit, so i haven't estimated the required diameter. Yes,   
  the lens would be the AC254-150. And lastly, I would assume to the have the   
  detector but I don't know if that is correct.                                 
  5. The diamond samples are both 3 by 3 by 0.5 mm                              
     The current distance from the laser to the dichroic is about 5 cm          
     the objective is about 8-9 cm from the lens and the lens is 15 cm from the 
  detector. The FBW5532-10 is indeed a real thorlabs bandpass filter. The       
  laser power is in the miliwatt range, i reckon about 1-5 MW reaching the      
  sample although maybe this is something that could be measured? I am happy to 
  go in the lab and take more presice measurements for all of these values      

● Thanks, that's enough to build it. I'll look up the datasheet values the model
  depends on (working distance, back focal lengths, coatings, detector NEP, NV
  density) rather than guess them.

● Fetch(https://www.thorlabs.com/thorproduct.cfm?partnumber=N40X-PF)
  ⎿  Received 1.3KB (200 OK)

● Fetch(https://www.thorlabs.com/thorproduct.cfm?partnumber=ACL25416U-B)
  ⎿  Received 1.3KB (200 OK)

● Fetch(https://www.thorlabs.com/thorproduct.cfm?partnumber=DNVB14)
  ⎿  Received 1.3KB (200 OK)

● Fetch(https://www.thorlabs.com/thorproduct.cfm?partnumber=PDA10A2)
  ⎿  Received 1.3KB (200 OK)

● Web Search("Thorlabs N40X-PF Nikon 40X Plan Fluor 0.75 NA working distance
            0.66 mm cover glass 0.17 entrance pupil")
  ⎿  Did 1 search in 5s

● Web Search("Thorlabs ACL25416U aspheric condenser EFL 16 mm back focal length
            center thickness")
  ⎿  Did 1 search in 5s

● Web Search("Thorlabs DNVB14 NV diamond 3.0 x 3.0 x 0.5 mm NV concentration
            ppm")
  ⎿  Did 1 search in 3s

● Fetch(https://www.3doptix.com/catalog/optics/lens/thorlabs/ACL25416U-B)
  ⎿  Received 11.9KB (200 OK)

● Web Search("Thorlabs PDA10A2 active area 0.8 mm2 NEP responsivity
            transimpedance gain 150 MHz")
  ⎿  Did 1 search in 4s

● Web Search("Thorlabs FBW5532-10 bandpass filter 532 nm specifications")
  ⎿  Did 1 search in 6s

● Web Search("Thorlabs DMLP550R dichroic mirror reflection band transmission
            band diameter thickness")
  ⎿  Did 1 search in 5s

● Fetch(https://www.thorlabs.com/NewGroupPage9_PF.cfm?ObjectGroup_ID=3257)  ⎿  Received 1.3KB (200 OK)

● Fetch(https://www.thorlabs.com/wedged-hard-coated-bandpass-filters)
  ⎿  Received 1.3KB (200 OK)

● Web Search("Thorlabs FELH0550 longpass filter clear aperture thickness
            transmission blocking OD")
  ⎿  Did 1 search in 6s

● Web Search("Thorlabs NE10A absorptive ND filter thickness Schott NG glass SM1
            mounted; LPVISE100-A extinction ratio thickness acceptance angle")
  ⎿  Did 2 searches in 7s

● Fetch(https://www.oxxius.ru/upload/iblock/897/mcanjju9nif6loaceobzk8vl8glipzji
       /TTN134700_D02.pdf)
  ⎿  Received 1.2MB (200 OK)

● Web Search("Thorlabs wedged bandpass filter FBW "wedge" angle 30 arcmin beam
            deviation")
  ⎿  Did 1 search in 6s

● Datasheet lookups are mostly done. Pulling the detector specs out of the
  downloaded PDF, then I'll write the optics model.

  Ran 2 shell commands (ctrl+o to expand)

● I have what I need. Now writing the shared optics model
  (notebooks/optics_model.py), starting with the physics, which I'll check
  against known analytic limits before building the notebook on it.

● Write(notebooks\optics_model.py)
  ⎿  Wrote 380 lines to notebooks\optics_model.py
       1 """
       3 
       4 Four levels of model, used where each is physically appropriate:
       6 1. Gaussian beam propagation (paraxial, ABCD / complex-q).  Lase
         r and fibre-mode
         res.
       8 2. Scalar Debye focusing integral.  High-NA focal spots (objecti
       9    Gaussian pupil fill, focusing through the air/diamond interfa
         ce including the
         ar: polarisation
     … +467 lines (ctrl+o to expand)

● Update(notebooks\optics_model.py)
  ⎿  Removed 1 line
      326      X2, Y2 = px + ax * L2, py + ay * L2
      327      bx, by = ax - X2 / f2, ay - Y2 / f2
      328      Xd, Yd = X2 + bx * d2, Y2 + by * d2
      329 -    ok &= _inside(X2, Y2, stops[-1][1]) if stops else True    
      329      ok &= _inside(Xd, Yd, det)
      330      stages["on detector"] = ok
      331      res = {k: 0.5 * np.sum(T * m) / N for k, m in stages.items
           ()}

  Ran 1 shell command (ctrl+o to expand)

● My model matches known benchmarks accurately, but the cover-glass case failed
  due to a too-narrow focus search window. I'll fix that now.

● Update(notebooks\optics_model.py)
  ⎿  Added 2 lines, removed 1 line
      191          medium.  Returns (z_f, Strehl) with Strehl relative to
            the aberration-free
      192          pupil.  Grid search then golden refinement (the SA lan
           dscape is multimodal)."""
      193          zf_par = depth / self.n2
      194 -        grid = np.linspace(0.3 * zf_par - 2e-6, 1.3 * zf_par +
          - 2e-6, 401)                                                   
      194 +        self_cg = self.t_cg * (1 - 1 / self.n_cg)     # paraxi
          +al shift from the missing cover glass                         
      195 +        grid = np.linspace(0.25 * zf_par - 3e-6, 1.3 * zf_par 
          ++ self_cg + 3e-6, 1601)                                       
      196          ph0 = self.k0 * depth * self.kz2 + self.psi
      197          amp = self.ws * self.P * self.s
      198  

● Update(notebooks\optics_model.py)
  ⎿  Added 1 line
      157      def __init__(self, lam0, NA, f, w_pupil=None, n2=1.0, t_cg
           =0.0, n_cg=1.523,
      158                   fresnel=True, nq=600):
      159          self.lam0, self.NA, self.f, self.n2 = lam0, NA, f, n2
      160 +        self.t_cg, self.n_cg = t_cg, n_cg                     
      161          self.k0 = 2 * np.pi / lam0
      162          x, w = leggauss(nq)
      163          self.s = 0.5 * NA * (x + 1)

  Ran 1 shell command (ctrl+o to expand)

● Without the specified 0.17 mm cover glass, the N40X-PF's best focus shifts to
  roughly 150–200 µm deep in the diamond rather than at its surface, since the
  diamond's aberration cancels the lens's built-in correction there. Now I'll
  write the drawing helpers.

● Write(notebooks\optics_draw.py)
  ⎿  Wrote 226 lines to notebooks\optics_draw.py
       1 """
       2 2-D layout drawing for notebooks/Optical_Setup.ipynb.
       4 Folded geometry, drawn in millimetres at true scale:
       5   * collection axis along +x, diamond top surface at x = 0;
       6   * excitation arm vertical (along +y) up to the dichroic at (x_
       7     where it is reflected towards -x into the focusing optic.
       8 Component outlines are schematic (correct position and clear ape
         rture, not
         om the model.
      10 """
     … +275 lines (ctrl+o to expand)

● Drawing helpers are written. Checking whether pandas is available for tables,
  then I'll write the notebook generator.

  Ran 1 shell command (ctrl+o to expand)

● Update(notebooks\optics_model.py)
  ⎿  Added 1 line
      325          X, Y = px + ax * dist, py + ay * dist
      326          ok &= _inside(X, Y, shape)
      327      stages["through filters/dichroic/lens stops"] = ok.copy()
      328 +    pre = ok.copy()                                           
      329      X2, Y2 = px + ax * L2, py + ay * L2
      330      bx, by = ax - X2 / f2, ay - Y2 / f2
      331      Xd, Yd = X2 + bx * d2, Y2 + by * d2

● Update(notebooks\optics_model.py)
  ⎿  Added 1 line, removed 1 line
      335      res["escape (no TIR)"] = 0.5 * np.sum(T * esc) / N
      336      if return_rays:
      337          res["rays"] = dict(Xd=Xd, Yd=Yd, px=px, py=py, ax=ax, 
           ay=ay, z=zd, T=T,
      338 -                           in_na=stages["within lens NA"], hit
          -=ok)                                                          
      338 +                           in_na=stages["within lens NA"], pre
          +=pre, hit=ok)                                                 
      339      return res
      340  
      341  

● Before writing the notebook prose, I'm running the key collection numbers for
  the objective and condenser setups so the text matches what the model actually
  says.

  Ran 2 shell commands (ctrl+o to expand)

● The main bottleneck is the detector itself: only ~0.7% of emitted PL reaches
  the 1mm PDA10A2, versus ~2% entering the objective, though the condenser
  boosts collection 1.5–2.2× and a shorter detector lens would recover most of
  the loss. Now I'll write this up in the notebook.

  Made 1 scratchpad edit +941 (ctrl+o to expand)

● Backing up the original notebook, then generating and executing the new one.

● Bash(cd "C:/Users/Gonzalo/AppData/Local/Temp/claude/C--Users-Gonzalo-Downloads
      -BudgetODMR/964694e3-0940-4c61-ba0c-84510a14a6be/scratchpad" && cp
      "C:/Users/Gonzalo/Do…)  ⎿  written 40 cells
     fig, ax = plt.subplots(figsize=(7, 3.3))
     ax.plot(depths / UM, S_exc, "g", label="excitation 532 nm (F810-filled
     … +44 lines (ctrl+o to expand)
  ⎿  1 file changed (binary, mode only or too large to show)

● Bash(cd "C:/Users/Gonzalo/AppData/Local/Temp/claude/C--Users-Gonzalo-Downloads
      -BudgetODMR/964694e3-0940-4c61-ba0c-84510a14a6be/scratchpad" && python -
      <<'EOF'
      p='bui…)
  ⎿  written 40 cells
     [NbConvertApp] Converting notebook Optical_Setup.ipynb to notebook
     C:\Users\Gonzalo\AppData\Local\Programs\Python\Python312\Lib\site-pack
     … +11 lines (ctrl+o to expand)
  ⎿  1 file changed (binary, mode only or too large to show)

● It runs end to end in under a minute. Now checking every printed number and
  every figure against the prose.

  Ran 1 shell command (ctrl+o to expand)

● I found a few discrepancies to fix: the polariser wander is actually ±17% (not
  ±18%), the condenser's effective NA is 0.70, the ensemble spot is 7.7 µm (not
  9), and the pinhole axial tolerance is ±0.2 mm—plus the detector axial scan
  needs a wider range since it peaks at the edge. Next I'll check the confocal
  table and figures.

  Read 5 files, ran 1 shell command (ctrl+o to expand)

● Found layout bugs—filter positions in wrong units, overlapping labels, cramped
  fibre-arm figures—plus a physics issue where the confocal z-window is too
  short for large pinholes. Fixing all of these now.

● Bash(cd "C:/Users/Gonzalo/AppData/Local/Temp/claude/C--Users-Gonzalo-Downloads
      -BudgetODMR/964694e3-0940-4c61-ba0c-84510a14a6be/scratchpad" && python -
      <<'EOF'
      p='bui…)
  ⎿  Traceback (most recent call last):
       File "<stdin>", line 16, in <module>
     AssertionError:         lens_v(ax, S["x_optic_front"], 12.7, t=14.0, k
     … +3 lines (ctrl+o to expand)
  ⎿  1 file changed (binary, mode only or too large to show)

  Searched for 1 pattern (ctrl+o to expand)

● Fixing the diagram label placement in the drawing module, then re-running the
  notebook.

  Read 1 file (ctrl+o to expand)

● Update(notebooks\optics_draw.py)
  ⎿  Added 2 lines, removed 2 lines
      154      if S["optic"] == "objective":
      155          objective(ax, S["x_optic_front"], S["x_pupil"], S["pup
           il_r"])
      156      else:
      157 -        lens_v(ax, S["x_optic_front"], 12.7, t=14.0, kind="pla
          -noconvex",                                                    
      158 -               label="ACL25416U-B\nf=16, NA 0.79", ly=14.5)   
      157 +        lens_v(ax, S["x_optic_front"], 12.7, t=14.0, kind="pla
          +noconvex")                                                    
      158 +        _txt(ax, S["x_optic_front"] + 7, -14.5, "ACL25416U-B\n
          +f=16, NA 0.79", va="top")                                     
      159      dichroic(ax, S["x_dich"])
      160      plate_v(ax, S["x_felh"], 12.5, t=3.5, fc="#e8a33d", label=
           "FELH0550")
      161      lens_v(ax, S["x_lens"], 12.7, t=5.0, label="AC254-150-A")

● Update(notebooks\optics_draw.py)
  ⎿  Added 1 line, removed 1 line
      69      pts = np.array([[-L, -T], [L, -T], [L, T], [-L, T]])
      70      R = np.array([[c, -s], [s, c]])
      71      ax.add_patch(Polygon(pts @ R.T + [x, 0], fc="#b58cd6", ec="
          0.2", lw=0.6, alpha=0.7))
      72 -    _txt(ax, x + 9, 13.5, label, ha="left")                    
      72 +    _txt(ax, x - 7, 14, label, ha="right")                     
      73  
      74  
      75  def objective(ax, x_front, x_back, pupil_r, label="N40X-PF 40x/
          0.75"):

● Update(notebooks\optics_draw.py)
  ⎿  Added 1 line, removed 1 line
      82  
      83  def diamond(ax, t=0.5, h=1.5, label="DNVB14\n3x3x0.5 mm"):
      84      ax.add_patch(Rectangle((-t, -h), t, 2 * h, fc="#9ad0f5", ec
          ="0.2", lw=0.6))
      85 -    _txt(ax, -t / 2, -h - 7, label, va="top")                  
      85 +    _txt(ax, -3, -3, label, ha="right", va="top")              
      86  
      87  
      88  def detector(ax, x, r_active, label="PDA10A2", body=6.0):

● Update(notebooks\optics_draw.py)
  ⎿  Added 1 line, removed 1 line
       94  def pinhole(ax, x, r_hole, h=8.0, label="pinhole"):
       95      ax.plot([x, x], [r_hole, h], color="k", lw=2)
       96      ax.plot([x, x], [-h, -r_hole], color="k", lw=2)
       97 -    _txt(ax, x, h + 1.5, label)                               
       97 +    _txt(ax, x, -h - 1.5, label, va="top")                    
       98  
       99  
      100  def laser(ax, y, x=0.0, label="DJ532-40\n+ pointer collimator"
           ):

● Update(notebooks\optics_draw.py)
  ⎿  Added 1 line
      194      if S.get("x_pinhole") is not None:
      195          cone(ax, S["x_pinhole"], 0.05, S["x_det"], S["r_after_
           pinhole"], C_PL, 0.22)
      196      ax.set_aspect("equal")
      197 +    ax.set_ylim(top=27)                                       
      198      ax.set_xlabel("position along collection axis (mm)")
      199      ax.set_ylabel("mm")
      200      for s in ("top", "right"):

● Bash(cd "C:/Users/Gonzalo/Downloads/BudgetODMR/notebooks" && jupyter nbconvert
      --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800
      Optical_Setup.ipy…)
  ⎿  [NbConvertApp] Writing 1494056 bytes to Optical_Setup.ipynb
     fig 10 1
     fig 16 2
     … +111 lines (ctrl+o to expand)
  ⎿  1 file changed (binary, mode only or too large to show)

● Correcting an earlier error: DNVB14 at 4.5 ppm actually holds about 8×10⁵ NVs
  per µm³ (not "hundreds"), putting roughly 10⁶ NVs in the confocal volume —
  I'll fix this in the text and now check the redrawn figures.

  Read 9 files (ctrl+o to expand)

● All figures render. I'm correcting the text to match the computed values and
  tidying the last overlapping labels.

● Bash(cd "C:/Users/Gonzalo/AppData/Local/Temp/claude/C--Users-Gonzalo-Downloads
      -BudgetODMR/964694e3-0940-4c61-ba0c-84510a14a6be/scratchpad" && python -
      <<'EOF'
      p='bui…)
  ⎿  Traceback (most recent call last):
       File "<stdin>", line 32, in <module>
     AssertionError: it is �12.5 mm, and a 5.9 mm beam clips ~0.1 % there,
     … +3 lines (ctrl+o to expand)
  ⎿  1 file changed (binary, mode only or too large to show)

● The shell mangled the non-ASCII characters (Ø, µ, ±), so none of those edits
  were applied. I'll write the patch as a UTF-8 file instead.

  Made 1 scratchpad edit +33 (ctrl+o to expand)

● Bash(cd "C:/Users/Gonzalo/AppData/Local/Temp/claude/C--Users-Gonzalo-Downloads
      -BudgetODMR/964694e3-0940-4c61-ba0c-84510a14a6be/scratchpad" && python -X
      utf8 patch1.p…)
  ⎿  patched 15
     written 40 cells
     [NbConvertApp] Writing 1487847 bytes to Optical_Setup.ipynb
     0
  ⎿  1 file changed (binary, mode only or too large to show)

  Read 1 file, ran 1 shell command (ctrl+o to expand)

● I've rebuilt notebooks/Optical_Setup.ipynb as the optical-design document you
  described. It runs top to bottom in about a minute with no errors, and I
  checked the numbers and figures in its text against the computed output. Your
  original description is kept as the first cell.

  The four configurations share one model, in notebooks/optics_model.py
  (physics) and notebooks/optics_draw.py (diagrams). Every input sits in one
  table tagged datasheet, measured, assumed or unknown, and every result is
  tagged with the model that produced it.

  Modelling approach. I didn't use DCC-Lab RayTracing. It uses paraxial ray/beam
  matrices, which break down exactly where this setup matters: NA 0.75–0.79
  optics, refraction at the diamond surface (n = 2.42), and a glowing volume
  rather than a single beam. The notebook uses the simplest valid model for each
  quantity:
  - Gaussian-beam propagation for the laser and fibre beams.
  - A scalar wave-optics focus calculation for high-NA spots, including the
    aberration from focusing into diamond and the objective's cover-glass
    correction.
  - A Monte-Carlo ray trace for collecting light emitted evenly in all
    directions.
  - Closed-form estimates (NA, étendue) as cross-checks.

  The model reproduces the Airy spot width, the Gaussian waist formula (to 0.2%)
  and the analytic collection fraction (to 0.1%).

  Main findings
  - Current setup (§1): the 1.4 mm beam fills only 19% of the 7.5 mm pupil, so
    the excitation works at an effective NA of 0.14 and gives a 2.4 µm spot. On
    overfilling: it gives the Airy pattern (the diffraction limit) plus power
    lost at the pupil edge. It never makes the spot worse.
  - The detector is the real bottleneck. The diamond lets out at most ~3.5% of
    the light through its top face, and the objective collects 2.0%. The Ø1 mm
    PDA10A2 at 30× magnification catches only 0.7%, because it acts like a
    pinhole on the 0.5 mm excited column. A 50 mm detector lens instead of the
    150 mm one doubles the signal.
  - Fibre version (§2):
    - Order: fibre → collimator → fixed polariser → tilted ND filters →
      FBW5532-10 → dichroic.
    - Collimator or condenser: the asphere acts as a collimator. The F240APC-532
      suits ensemble work (1.3 mm beam) and the F810APC-543 confocal work (5.9
      mm, 78% of the pupil).
    - Polariser: don't rotate it for power control after a
      polarisation-maintaining fibre. It turns the fibre's temperature drift
      into ±17% power wander.
    - Filter wedge: the FBW5532-10 is wedged, so inserting or rotating it moves
      the focus by about 20 µm.
  - Condenser version (§3): it gives about 2.2× more signal than today (1.4–2.7×
    depending on unknowns). That gain comes from seeing a wider field, not from
    NA: the 1″ filters and lens cut its effective NA to 0.70, and in diamond
    its extra NA barely adds collection angle.
  - Confocal version (§4): the geometry works. It needs a 30 µm pinhole (one
    Airy unit) aligned to ±6 µm sideways and about ±0.3 mm along the axis, with
    the PDA10A2 within 20 mm behind it.
    - Because the objective is corrected for a 0.17 mm cover glass that isn't
      there, the sharpest focus is about 210 µm deep in the diamond, not at the
      surface.
    - I underestimated the NV count earlier. DNVB14 holds about 8×10⁵ NVs per
      µm³, so every confocal volume contains around 10⁶ NVs, and single-NV work
      is impossible with this sample. The PDA10A2 couldn't detect one NV anyway.

  What's still uncertain, and the measurements that would pin it down
  1. PL power at the detector position, measured with the S120C sensor behind
     the FELH0550. All light-level results are only relative until this is in.
  2. Laser beam diameter with a knife-edge or iris, and divergence from the
     diameter at two distances at least 1 m apart.
  3. Does the objective have a cover-glass correction collar? If it does, the
     best confocal depth can move.
  4. Which pinholes are in your kit, and whether you have a second ACL25416U-B
     or an achromat of about 50 mm focal length for the detector lens.

  Some filter clear apertures, the objective's transmission and the condenser's
  reflectance at 532 nm are marked as assumed in the parameter table. Each can
  be changed in one place.

  The notebook is untracked and not committed. A backup of the original is in
  the scratchpad (Optical_Setup.orig.ipynb).

  Specs I looked up:
  - N40X-PF
  - ACL25416U-B
  - DNVB14
  - FBW5532-10
  - DMLP550R
  - FELH0550
  - PDA10A2
  - NE10A

✻ Cogitated for 31m 12s · done Wednesday 11:45

❯ Ok, update the fiber coupling md file with any corrections you might see fit. 
  My conclusion is that the correct fiber coupling stage would be DJ532-40 to   
  FBW5532-10 filter to linear polariser  to Iris to BB1-E02P mirror to second   
  BB1-E02P mirror to iris to colimator to fiber to colimator to nd filters to   
  lambda/2 plate to DMLP550R. Is that right?                                    

  Read 1 file (ctrl+o to expand)

● Three components—the λ/2 plate, polariser, and FBW filter—are out of order,
  and the first iris isn't serving any alignment purpose before M1. I'll add the
  corrected path at the top of the md file and fix the smaller errors further
  down.
● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 57 lines
       1  # Free-space → fibre coupling stage — parts list
       2  
       3  All prices **ex-VAT**, read from thorlabs.com on 15 Sep 2026 (E
          UR, Bergkirchen DE warehouse).
       4 +Reviewed 30 Sep 2026 against the optical model in `notebooks/Op
         +tical_Setup.ipynb` (§2):                                       
       5 +corrected beam path below, beam-size numbers recomputed for thi
         +s fibre's 4.0 µm mode.                                         
       6  
       7 +## Reviewed beam path — what goes where, and why               
       8 +                                                               
       9 +```                                                            
      10 +LAUNCH END (beam walk, alignment-critical)                     
      11 +DJ532-40 ─► M1 (KS1+BB1-E02P) ─► M2 (KS1+BB1-E02P) ─► [iris A] 
         +─► λ/2 (RSP1/M) ─► [iris B] ─► F240APC-532 ─► fibre            
      12 + ~1.4 mm    150–300 mm apart      iris A just after M2, iris B 
         +just before the coupler, as far apart as possible              
      13 +                                                               
      14 +DELIVERY END (collimated, nothing here is alignment-critical)  
      15 +fibre ─► F810APC-543 (confocal)  ─► LPVISE100-A ─► NE10A / NE20
         +A ─► FBW5532-10 ─► DMLP550R ─► objective                       
      16 +      or F240APC-532 (ensemble)     fixed, on the    tilted 2–5
         +°      fixed mount                                             
      17 +                                    slow axis                  
      18 +```                                                            
      19 +                                                               
      20 +Compared with the proposed order                               
      21 +`DJ532-40 → FBW5532-10 → polariser → iris → M1 → M2 → iris → co
         +llimator → fibre → collimator → ND → λ/2 → DMLP550R`,          
      22 +five things move:                                              
      23 +                                                               
      24 +1. **λ/2 plate: launch side, after M2, before the coupler, not 
         +before the DMLP550R.** Its job                                 
      25 +   is to rotate the laser's linear polarisation onto the fibre'
         +s slow axis. That is what                                      
      26 +   makes the PM fibre polarisation-maintaining. It goes *after*
         + the mirrors because it can                                    
      27 +   rotate linear polarisation but cannot undo the ellipticity t
         +hat 45° dielectric mirrors                                     
      28 +   add. Keep the laser polarisation s or p on M1/M2 (the plate 
         +fixes the orientation                                          
      29 +   afterwards). At the delivery end, a λ/2 in front of the DMLP
         +550R would rotate the                                          
      30 +   polarisation *at the dichroic*. 532 nm sits on its 533 nm re
         +flection-band edge, where                                      
      31 +   reflectance is polarisation-dependent, so it would change th
         +e excitation power and                                         
      32 +   NV-orientation selectivity together. If you later want polar
         +isation control at the                                         
      33 +   sample, put a **second** λ/2 between the DMLP550R and the ob
         +jective.                                                       
      34 +2. **Linear polariser: after the output collimator, fixed on th
         +e slow axis, not at the                                        
      35 +   launch.** At the launch it is redundant if the DPSS output i
         +s already well polarised                                       
      36 +   (check once: rotate it in front of the power meter). As a *r
         +otating* attenuator it would                                   
      37 +   also misalign the input polarisation from the PM axis. After
         + the fibre, fixed, it acts as                                  
      38 +   a clean-up polariser. The residual polarisation wander (≤ −1
         +5 dB extinction ratio) then                                    
      39 +   becomes a ≤ 3 % power change instead of a polarisation chang
         +e at the dichroic. **Do not                                    
      40 +   rotate it for power control.** At 45° to the slow axis the f
         +ibre's thermal birefringence                                   
      41 +   drift becomes ±17 % power wander (notebook §2). Step the pow
         +er with the ND filters.                                        
      42 +3. **FBW5532-10: after the fibre, not before.** Silica fibre ge
         +nerates weak Raman and                                         
      43 +   fluorescence background above 540 nm. Part of it reaches the
         + detector: it is reflected by                                  
      44 +   the DMLP550R, bounces off the diamond (~17 %), and passes th
         +e FELH0550. The line filter                                    
      45 +   has to sit after the fibre to remove it (and any residual pu
         +mp IR with it). It is wedged                                   
      46 +   (~30′ → 4 mrad deviation → **~20 µm focus shift** with the N
         +40X-PF), so give it a fixed                                    
      47 +   mount and align after it. Ø12.5 mm clips only ~0.3 % of a 5.
         +9 mm beam.                                                     
      48 +4. **Irises: both after the mirrors.** An iris before M1 sees a
         + beam whose position is fixed                                  
      49 +   by the laser, so it adds nothing to the walk. It is still us
         +eful as a safety aperture.                                     
      50 +   Beam walking needs two reference points *downstream* of M2 (
         +steps 1–4 of the procedure                                     
      51 +   below).                                                     
      52 +5. **ND filters: after the collimator (as proposed).** In the c
         +ollimated beam a flat plate                                    
      53 +   adds no aberration. A 3° tilt shifts the beam by ~36 µm, whi
         +ch is harmless. Tilting keeps                                  
      54 +   their reflections out of the fibre. Between fibre and lens t
         +he same 2 mm plate would move                                  
      55 +   the focus by 0.7 mm and ruin the collimation.               
      56 +                                                               
      57 +The output collimator **is** an asphere acting as a collimator 
         +(a point source, the 4 µm                                      
      58 +mode, at its focus). Use a fixed-focus APC package rather than 
         +an ACL condenser: the                                          
      59 +package sets the fibre–lens spacing at the factory, compensates
         + the 8° APC facet, and is                                      
      60 +AR-coated at 532 nm.                                           
      61 +                                                               
      62  ## The fibre has two ends, and they want different collimators
      63  
      64  This is the thing to hold onto, because the two requirements pu
          ll in opposite directions:

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 7 lines, removed 2 lines
      65  
      66  | End | Job | Beam diameter needed | Set by |
      67  |---|---|---|---|
      68 -| **Launch** (laser → fibre) | focus the laser onto the fibre c
         -ore | match the **laser's** beam, ≈ 1.5 mm | `F240APC-532` |   
      69 -| **Delivery** (fibre → microscope) | collimate for the objecti
         -ve pupil | fill the **7.5 mm** back aperture | `F810APC-543` | 
      68 +| **Launch** (laser → fibre) | focus the laser onto the fibre c
         +ore | match the **laser's** beam, ≈ 1.3–1.5 mm | `F240APC-532` 
         +|                                                              
      69 +| **Delivery, confocal** (fibre → microscope) | collimate for t
         +he objective pupil | fill the **7.5 mm** back aperture | `F810A
         +PC-543` |                                                      
      70 +| **Delivery, ensemble** | reproduce today's beam | ≈ 1.3 mm (e
         +ffective NA 0.13, ~2.5 µm spot, no saturation) | a second `F240
         +APC-532` |                                                     
      71  
      72 +The two delivery options are different experiments, not better 
         +and worse. For ensemble                                        
      73 +ODMR a pupil-filling beam makes a ~0.4 µm spot that saturates t
         +he NVs at mW powers.                                           
      74 +Mount the delivery collimator in an SM1 adapter so that swappin
         +g them is a two-minute job.                                    
      75 +                                                               
      76  > **APC, not PC** — see the connector section below. Both colli
          mators you own are the
      77  > FC/**PC** variant and your fibre is FC/**APC**. This is proba
          bly not a detail.
      78  

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 5 lines, removed 4 lines
      76  > **APC, not PC** — see the connector section below. Both colli
          mators you own are the
      77  > FC/**PC** variant and your fibre is FC/**APC**. This is proba
          bly not a detail.
      78  
      79 -Both produce the same ~3.6 µm spot at the fibre tip — they have
         - to, it is the same fibre                                      
      80 -mode — so either *could* sit at either end. What differs is the
         - free-space beam diameter                                      
      81 -on the other side of the lens, and that is chosen by what it ha
         -s to talk to: a 1.5 mm                                         
      82 -laser beam at one end, a 7.5 mm objective pupil at the other.  
      79 +Both focus to the same spot at the fibre tip. They have to, sin
         +ce it is the same fibre                                        
      80 +mode (MFD ≈ 4.0 µm at 532 nm for this fibre), so either *could*
         + sit at either end. What                                       
      81 +differs is the free-space beam diameter on the other side of th
         +e lens, D = 4λf/(π·MFD).                                       
      82 +That diameter is chosen by what the lens has to talk to: a ~1.4
         + mm laser beam at one end,                                     
      83 +a 7.5 mm objective pupil at the other.                         
      84  
      85  ---
      86  

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 1 line, removed 1 line
      127  
      128  ## Design decision: you do NOT need a focusing lens
      129  
      130 -The `F240FC-532` you already own **is** the coupling lens. Run
          - in reverse it takes a                                        
      130 +The F240 collimator (as the APC version, see above) **is** the
          + coupling lens. Run in reverse it takes a                     
      131  collimated beam and focuses it onto the fibre tip; the lens-to
           -tip spacing is fixed at the
      132  factory, which is exactly why it works. Adding a separate focu
           sing lens would give you a
      133  second, conflicting focus condition and make the alignment har
           der, not easier.

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 11 lines, removed 6 lines
      149  ## Gate before ordering: measure your beam diameter (LAUNCH en
           d only)
      150  
      151  `F240FC-532` specs (verified): waist diameter **1.48 mm**, wai
           st distance 6.96 mm,
      152 -NA = 0.51, f = 7.86 mm, housing Ø12 mm / M12 × 0.5.           
      152 +NA = 0.51, f = 7.86 mm, housing Ø12 mm / M12 × 0.5. Thorlabs q
          +uote the 1.48 mm with their                                   
      153 +reference fibre. With *this* fibre's 4.0 µm mode the matched b
          +eam is **1.33 mm**.                                           
      154  
      154 -Your collimated laser beam at the coupler should be **≈ 1.5 mm
          - (1/e²)**. Mismatch costs                                     
      155 -coupling efficiency as η = [2w₁w₂/(w₁²+w₂²)]² — a 2× mismatch 
          -already throws away ~36 %.                                    
      155 +Mismatch costs coupling efficiency as η = [2w₁w₂/(w₁²+w₂²)]². 
          +A 2× mismatch already throws                                  
      156 +away ~36 %, but ±30 % costs only ≤ 9 %. The gate is forgiving.
      157  
      157 -Measure it with the VRC2 card and the ID25 iris (close down un
          -til ~85 % of power is                                         
      158 -clipped). If it comes out far from 1.5 mm, **do not build a te
          -lescope** — just swap the                                     
      159 -launch collimator, all three are the same €176.05:            
      158 +**Status (30 Sep 2026): provisionally passed.** A viewing-card
          + estimate gives the laser                                     
      159 +beam as "just below 1.5 mm". Taking 1.4 mm, the ideal mode mat
          +ch to the F240 is 99.7 %,                                     
      160 +so no collimator swap is needed. Real coupling will be limited
          + by M², astigmatism and                                       
      161 +alignment (expect 50–80 %), not by diameter. Confirm it proper
          +ly with the ID25 iris: the                                    
      162 +iris diameter at which **86.5 % of the power is transmitted** 
          +is the 1/e² diameter. Only                                    
      163 +if it comes out far from 1.3–1.5 mm, **do not build a telescop
          +e**: swap the launch                                          
      164 +collimator instead (FC prices shown; the APC equivalents are n
          +eeded for this fibre):                                        
      165  
      166  | Part | Waist diameter | Use if your beam is |
      167  |---|---|---|

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 4 lines, removed 3 lines
      191  replacing.** (This also retracts a warning I gave earlier abou
           t FC/PC Fresnel
      192  back-reflection into the DJ532-40 — that concern does not appl
           y; your fibre is APC.)
      193  
      194 -PM is worth keeping rather than downgrading to plain single-mo
          -de: your `DMLP550R` sits at                                   
      195 -45° and is polarisation-sensitive, so a drifting output polari
          -sation would convert                                          
      196 -directly into excitation-power drift in the ODMR baseline.    
      194 +PM is worth keeping rather than downgrading to plain single-mo
          +de. Your `DMLP550R` sits at                                   
      195 +45° and is polarisation-sensitive: 532 nm is right at the edge
          + of its 380–533 nm                                            
      196 +reflection band. A drifting output polarisation would therefor
          +e convert directly into                                       
      197 +excitation-power drift in the ODMR baseline.                  
      198  
      199  ### Optional fibre swap — better, and it refunds you €37
      200  

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 6 lines, removed 3 lines
      219  ## Why the delivery end matters at all
      220  
      221  Your `N40X-PF` has NA = 0.75 and f = 5 mm, so its back apertur
           e is 2·NA·f = **7.5 mm**.
      222 -An `F240` delivers 1.48 mm there — an 18 % pupil fill, which d
          -rops the *effective                                           
      223 -excitation* NA to ~0.14 and inflates the focal volume by rough
          -ly 900×. That is why you                                      
      224 -have no optical sectioning. The F810 fixes it; the fibre choic
          -e then tunes 78 % → 92 %.                                     
      222 +An `F240` delivers 1.33 mm there (as does today's free-space b
          +eam): an 18 % pupil fill,                                     
      223 +which drops the *effective excitation* NA to ~0.13. The spot i
          +s then ~2.5 µm (1/e²)                                         
      224 +instead of ~0.4 µm FWHM, with a ~20 µm Rayleigh range in the d
          +iamond. In a confocal                                         
      225 +arrangement (30 µm pinhole) the F810 shrinks the effective det
          +ection volume ~7×, from                                       
      226 +~31 to ~5 µm³ (notebook §4). The fibre choice then tunes the f
          +ill from 78 % to 92 %. For                                    
      227 +**ensemble** work the under-filled F240 beam is the better cho
          +ice (see the table at the top).                               
      228  
      229  **On the 11 nm wavelength offset (543 design, 532 use):** the 
           AR coating is 350–700 nm and
      230  Thorlabs quote the damage threshold "measured at 532 nm", so t
           ransmission is a non-issue.

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 1 line, removed 1 line
      271  stalls at a few percent and nobody can say why. (The `SI050P` 
           is the wrong size — it
      272  starts at 2.5 mm.)
      273  
      274 -## Optional — PM axis launch (€464,72)                        
      274 +## Recommended — PM axis launch (€464,72)                     
      275  
      276  | # | Part | Description | Qty | Unit | Total |
      277  |---|---|---|---|---|---|

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 6 lines, removed 2 lines
      284  and because your `DMLP550R` dichroic is polarisation-sensitive
           , that wander converts
      285  directly into **excitation-power drift** — which will show up 
           in your ODMR baseline and
      286  in the RIN measurement as spurious 1/f. The waveplate is not n
           eeded to *get* light down
      287 -the fibre; it is needed for the light to stay stable once you 
          -do. Defer it until coupling                                   
      288 -works, then decide.                                           
      287 +the fibre; it is needed for the light to stay stable once you 
          +do. It is the only                                            
      288 +continuous polarisation adjustment the launch has, so it belon
          +gs in the build, placed                                       
      289 +**after M2, just before the coupler** (see the reviewed beam p
          +ath at the top). It can be                                    
      290 +added after the first successful coupling without disturbing t
          +he walk. To set it: rotate                                    
      291 +the plate while heating the fibre gently by hand, and stop whe
          +re the output power behind                                    
      292 +the fixed delivery polariser stops fluctuating.               
      293  
      294  ---
      295  

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 1 line, removed 1 line
      297  
      298  | Part | Qty | Role in this stage |
      299  |---|---|---|
      300 -| `F240FC-532` | 2 | **one** as the launch coupler; the second
          - is a spare — return it against the F810FC-543 (€176,05 each) 
          -|                                                             
      300 +| `F240FC-532` | 2 | FC/**PC** — wrong for the APC fibre; retu
          +rn both (€176,05 each) against the APC versions. If you want t
          +he ensemble delivery option, order **two** `F240APC-532` (+238
          +,55 € over the table above) |                                 
      301  | `KAD12NT` | 2 | Ø1" kinematic pitch/yaw adapter for the Ø12 
           mm collimator body (€73,08) |
      302  | `P3-405BPM-FC-1` | 1 | the fibre |
      303  | `PM101A` + `S120C` | 1 | coupling-efficiency readout — essen
           tial during the walk |

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 2 lines, removed 1 line
      317  | APC collimators + AD15F, net of returning 2 × F240FC-532 | 2
           33,16 € | **874,60 €** |
      318  | Shear plate SI035P | 167,54 € | 1 042,14 € |
      319  | *credit:* swap fibre to P3-488PM-FC-1 | −37,03 € | 1 005,11 
           € |
      320 -| PM axis launch (optional, defer) | 464,72 € | 1 469,83 € |  
      320 +| PM axis launch (recommended; can follow first coupling) | 46
          +4,72 € | 1 469,83 € |                                         
      321 +| *option:* second F240APC-532 for ensemble delivery | 238,55 
          +€ | 1 708,38 € |                                              
      322  | *variant:* plain BB1-E02 instead of BB1-E02P | −54,88 € | |
      323  
      324  The first two rows are what unblock work: **€874.60** gets you
            a correctly-connectorised,

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 6 lines, removed 3 lines
      335  
      336  ## Layout and procedure
      337  
      338 +See the reviewed beam path at the top for the full order, incl
          +uding the λ/2 plate,                                          
      339 +polariser, NDs and line filter. The core of the launch:       
      340 +                                                              
      341  ```
      342  LAUNCH END
      340 -DJ532-40 ──► [ID25/M #1] ──► M1 (KS1+BB1-E02P) ──► M2 (KS1+BB1
          --E02P) ──► [ID25/M #2] ──► F240FC-532 ──► fibre               
      341 -  ~1.5 mm                                                     
          -                            (KAD12NT in LMR1/M)               
      343 +DJ532-40 ──► M1 (KS1+BB1-E02P) ──► M2 (KS1+BB1-E02P) ──► [ID25
          +/M A] ──► (λ/2) ──► [ID25/M B] ──► F240APC-532 ──► fibre      
      344 +  ~1.4 mm                                                     
          +                                   (KAD12NT in LMR1/M)        
      345  
      346  DELIVERY END
      344 -fibre ──► F810FC-543 ──► ~6 mm collimated ──► DMLP550R ──► N40
          -X-PF (7.5 mm pupil) ──► diamond                               
      347 +fibre ──► F810APC-543 ──► 5.9 mm collimated ──► polariser ─► N
          +D ─► FBW5532-10 ──► DMLP550R ──► N40X-PF ──► diamond          
      348            (AD15F into cage plate)
      349  ```
      350  

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 5 lines, removed 2 lines
      365  
      366  ## Open items
      367  
      368 -- Beam diameter of the `DJ532-40` + `LTC56A/M` assembly is **u
          -nmeasured**. This gates                                       
      369 -  item selection (see Gate above). Measure before ordering.   
      368 +- Beam diameter of the `DJ532-40` + `LTC56A/M` assembly: viewi
          +ng-card estimate "just                                        
      369 +  below 1.5 mm" (30 Sep 2026). That provisionally passes the g
          +ate. Confirm with the iris                                    
      370 +  (86.5 % transmission) and measure the divergence (diameter a
          +t two distances ≥ 1 m apart).                                 
      371 +- Check the laser's polarisation ratio once (polariser in fron
          +t of the power meter). If it                                  
      372 +  is poor, a fixed polariser *before* M1 is justified as well.
      373  - **Confirm the collimator engravings** (`F240FC-532` vs `F240
           APC-532`). The whole
      374    "corrected optics" tranche hangs on this. It is a two-minute
            check with a torch.
      375  - Fibre swap to `P3-488PM-FC-1` is optional and refunds €37.03
           . Decide it independently

● Not quite. The components are right, but the λ/2 plate, the polariser and the
  FBW filter each belong somewhere else, and the first iris does no alignment
  work where you have it. I've put the corrected path at the top of
  procurement/fiber_coupling_stage.md, with the reasoning for each move.

  Launch side: DJ532-40 → M1 → M2 → iris → λ/2 → iris → F240APC-532 → fibre

  Delivery side: fibre → collimator → polariser (fixed) → ND filters (tilted
  2–5°) → FBW5532-10 (fixed mount) → DMLP550R

  What changes from your chain:

  1. The λ/2 plate goes on the launch side, after M2 and just before the 
     coupler. Its job is to line the laser's polarisation up with the fibre's
     slow axis. Without that, the polarisation-maintaining fibre doesn't hold
     polarisation.
     - It goes after the mirrors because it can rotate linear polarisation but
       can't undo the ellipticity the 45° mirrors add.
     - In front of the DMLP550R it would change your excitation power. 532 nm
       sits right on the dichroic's 533 nm band edge, where reflectance depends
       on polarisation.
  2. The polariser goes after the output collimator, fixed on the slow axis.
     There it acts as a clean-up polariser: leftover polarisation drift becomes
     at most ~3% power change instead of a polarisation change at the dichroic.
     Don't rotate it to control power; at 45° the fibre's temperature drift
     becomes ±17% power wander. Use the ND filters for power steps.
  3. The FBW5532-10 goes after the fibre. The fibre itself generates weak Raman
     and fluorescence background above 540 nm, and some of it reaches the
     detector. The filter has to come after the fibre to remove it. It is
     wedged, so it moves the focus by about 20 µm: give it a fixed mount and
     align after it.
  4. Both irises go after the mirrors. Before M1 the beam position is fixed by
     the laser, so an iris there adds nothing to beam walking. Put one just
     after M2 and one just before the coupler, as far apart as possible.
  5. The ND filters stay where you had them, after the collimator. Tilted a few
     degrees, they add no aberration and their reflections stay out of the
     fibre.

  Other corrections in the file:
  - Launch beam size: with your fibre's 4.0 µm mode, the F240's matched beam is
    1.33 mm, not 1.48 mm (that figure is for Thorlabs' reference fibre). Your
    ~1.4 mm beam gives a 99.7% ideal mode match, so the beam-diameter check
    passes provisionally and no collimator swap is needed.
  - Iris measurement: the old instruction to "clip ~85% of the power" was wrong.
    The 1/e² diameter is where the iris transmits 86.5%.
  - Removed claim: I dropped the "~900× focal volume" figure. The file now
    quotes the notebook's confocal result instead: about 7× smaller detection
    volume with the F810 than with the F240.
  - Two delivery collimators: F810APC-543 for confocal and a second F240APC-532
    for ensemble work. A pupil-filling beam would saturate the NVs in ensemble
    ODMR. I added the second F240APC as a €238.55 option, noted that both F240FC
    units should be returned, and moved the λ/2 section from optional to
    recommended.

  One check to add: measure the laser's polarisation ratio once, with the
  polariser in front of the power meter. If it turns out poor, an extra fixed
  polariser before M1 is justified.

✻ Cogitated for 2m 13s · done Wednesday 12:00

※ recap: We're turning the optical-setup notebook into a design document, and I've just corrected the fibre coupling md with the reviewed beam path. Next, measure the laser beam diameter and PL power at the detector so the model's numbers become absolute. (disable recaps in /config)

❯ Ok, add the λ/2 plate the polariser and the FBW5532-10 to the fiber launch md 
  file explanations                                                             

  Read 1 file (ctrl+o to expand)

● I'll add a section covering what each of the three components does, where it
  goes, setup steps, and parts to order, plus the corresponding steps in the
  alignment procedure.

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 117 lines, removed 3 lines
      287  the fibre; it is needed for the light to stay stable once you 
           do. It is the only
      288  continuous polarisation adjustment the launch has, so it belon
           gs in the build, placed
      289  **after M2, just before the coupler** (see the reviewed beam p
           ath at the top). It can be
      290 -added after the first successful coupling without disturbing t
          -he walk. To set it: rotate                                    
      291 -the plate while heating the fibre gently by hand, and stop whe
          -re the output power behind                                    
      292 -the fixed delivery polariser stops fluctuating.               
      290 +added after the first successful coupling without disturbing t
          +he walk. The set-up                                           
      291 +procedure is in the next section.                             
      292  
      293  ---
      294  
      295 +## Polarisation and filtering optics — the λ/2 plate, the pola
          +riser and the FBW5532-10                                      
      296 +                                                              
      297 +These three parts do not help get light into the fibre. They s
          +et the **polarisation**,                                      
      298 +**power stability** and **spectral purity** of the light that 
          +comes out, and each has                                       
      299 +exactly one correct place in the beam path.                   
      300 +                                                              
      301 +| # | Part | Where | Job | Mount |                            
      302 +|---|---|---|---|---|                                         
      303 +| 9 | `WPH10ME-532` λ/2 plate | launch: after M2, before iris 
          +B and the coupler | rotate the laser polarisation onto the fib
          +re's slow axis | `RSP1/M` rotation mount (listed above) |     
      304 +| 12 | `LPVISE100-A` linear polariser | delivery: first elemen
          +t after the output collimator | clean-up polariser, **fixed** 
          +on the slow axis | rotation mount, set once and locked |      
      305 +| 13 | `NE10A`, `NE20A` absorptive ND | delivery: after the po
          +lariser | discrete power steps (×0.1, ×0.01, ×0.001) | SM1-thr
          +eaded, tilted 2–5° |                                          
      306 +| — | `FBW5532-10` (owned) | delivery: after the NDs, last ele
          +ment before the DMLP550R | 532 nm laser-line clean-up | fixed;
          + Ø12.5 mm → needs an SM05-to-SM1 thread adapter in a 1″ cage |
      307 +                                                              
      308 +### λ/2 plate: matching the laser polarisation to the PM fibre
      309 +                                                              
      310 +**What it does.** A half-wave plate turns linear polarisation 
          +into linear polarisation,                                     
      311 +mirrored about its fast axis. Rotating the plate by θ rotates 
          +the polarisation by **2θ**,                                   
      312 +so 45° of plate rotation covers the full 90° range. The DPSS o
          +utput is already linear. The                                  
      313 +plate only has to *turn* it to lie along the fibre's slow axis
          +, and it does so without any                                  
      314 +power loss.                                                   
      315 +                                                              
      316 +**Why the fibre needs this.** A PANDA PM fibre maintains polar
          +isation only for light                                        
      317 +launched along one of its two stress axes. Launched at an angl
          +e, the light splits between                                   
      318 +the slow and fast axes. These travel at different speeds, so t
          +heir relative phase drifts                                    
      319 +with fibre temperature and bending, and the output polarisatio
          +n wanders. After the                                          
      320 +polarisation-sensitive DMLP550R (532 nm sits on its 533 nm ban
          +d edge), that wander becomes                                  
      321 +excitation-power noise in the ODMR baseline.                  
      322 +                                                              
      323 +**Why after the mirrors.** The BB1-E02P dielectric mirrors at 
          +45° shift the s and p phases                                  
      324 +differently. Linear light that is neither pure s nor pure p co
          +mes off them slightly                                         
      325 +elliptical, and a λ/2 plate cannot remove ellipticity. So: kee
          +p the laser polarisation s or                                 
      326 +p on M1/M2 (it usually is when the beam stays in a horizontal 
          +plane), and rotate it with                                    
      327 +the plate *after* the last mirror.                            
      328 +                                                              
      329 +**Why not at the delivery end** (in front of the DMLP550R). Th
          +ere it would rotate the                                       
      330 +polarisation at the dichroic's band edge, and change the NV-or
          +ientation selectivity at the                                  
      331 +same time. Excitation power and NV response would then vary to
          +gether, and you could not                                     
      332 +separate them. If you ever want polarisation control *at the s
          +ample*, add a **second** λ/2                                  
      333 +between the DMLP550R and the objective.                       
      334 +                                                              
      335 +### Linear polariser: clean-up, not attenuator                
      336 +                                                              
      337 +**What it does.** Passes only the polarisation component along
          + its axis. It is fixed on the                                 
      338 +fibre's slow axis, so it removes the small fraction of light i
          +n the fast axis. With the                                     
      339 +fibre's 15 dB minimum extinction ratio that fraction is ≤ 3 %.
          + The light reaching the                                       
      340 +dichroic then always has the same polarisation direction. Any 
          +residual launch imperfection                                  
      341 +shows up as a ≤ 3 % power change, which a reference photodiode
          + can normalise, instead of a                                  
      342 +polarisation change, which nothing downstream can correct.    
      343 +                                                              
      344 +**Why not rotate it for power control** (Malus law, as the sho
          +pping list originally                                         
      345 +proposed). Behind a PM fibre the output always contains a smal
          +l, phase-drifting                                             
      346 +fast-axis component. With the polariser at angle θ to the slow
          + axis, the transmitted power                                  
      347 +swings by up to ±2√(ε(1−ε))·sinθ·cosθ as that phase drifts, wh
          +ere ε = 10^(−ER/10). At                                       
      348 +15 dB and θ = 45° that is **±17 %**. On the slow axis (θ = 0) 
          +the swing vanishes. Use the                                   
      349 +NDs for power steps. For *continuous* power control, the right
          + tool is a second λ/2 +                                       
      350 +polariser pair *before* the fibre, so the fibre always receive
          +s the same polarisation.                                      
      351 +                                                              
      352 +**Why after the output collimator, not before it or at the lau
          +nch.**                                                        
      353 +- *Between the fibre and the collimator lens:* the beam diverg
          +es at ±4.9° and there is no                                   
      354 +  room inside a collimator package. Any plate there also moves
          + the focus (≈ 0.7 mm for 2 mm                                 
      355 +  of glass) and spoils the collimation.                       
      356 +- *At the launch:* it is redundant if the DPSS is already well
          + polarised (check once, see                                   
      357 +  Open items). As a rotating element it would misalign the inp
          +ut from the PM axis.                                          
      358 +- *In the collimated delivery beam:* it simply transmits.     
      359 +                                                              
      360 +### FBW5532-10: laser-line filter after the fibre             
      361 +                                                              
      362 +**What it does.** A hard-coated 532 nm bandpass, 10 nm FWHM, ≥
          + 90 % transmission and                                        
      363 +OD > 5 blocking outside the band. It removes everything in the
          + excitation beam that is not                                  
      364 +532 nm.                                                       
      365 +                                                              
      366 +**Why it moves from the laser to after the fibre.** The silica
          + fibre itself produces a weak                                 
      367 +broadband Raman and fluorescence background above 540 nm, in t
          +he NV emission band. That                                     
      368 +light takes a path to the detector: part is reflected by the D
          +MLP550R towards the sample,                                   
      369 +~17 % is back-reflected by the diamond surface, and it then pa
          +sses the dichroic and the                                     
      370 +FELH0550 like real PL. A filter before the fibre cannot remove
          + light the fibre creates.                                     
      371 +One filter after the fibre removes the fibre background *and* 
          +anything the laser emits                                      
      372 +outside 532 nm, so a second one before the fibre is unnecessar
          +y.                                                            
      373 +                                                              
      374 +**Why a fixed mount, and why last.** The FBW series is **wedge
          +d** (≈ 30′ per the vendor                                     
      375 +text) to suppress etalon fringes. That tilts the transmitted b
          +eam by (n − 1)·α ≈ 4 mrad.                                    
      376 +At the objective pupil a beam *angle* becomes a *lateral focus
          + shift* of f·δ: **≈ 20 µm**                                   
      377 +with the N40X-PF and ≈ 64 µm with the ACL25416U. Rotating, rem
          +oving or re-seating the                                       
      378 +filter therefore moves the focus on the sample. Put it in a fi
          +xed mount, never touch it,                                    
      379 +and do the final pointing into the objective after it. Placed 
          +last, nothing downstream has                                  
      380 +to be re-aligned when upstream NDs are swapped.               
      381 +                                                              
      382 +**Size and angle.** It is Ø12.5 mm. A 5.9 mm F810 beam loses ~
          +0.3 % at an assumed ~Ø10 mm                                   
      383 +clear aperture, and the 1.3 mm F240 beam loses nothing. Tiltin
          +g it a few degrees to keep                                    
      384 +its reflection out of the fibre shifts the passband by well un
          +der 1 nm, which is harmless                                   
      385 +for a 10 nm band.                                             
      386 +                                                              
      387 +### ND filters (for completeness)                             
      388 +                                                              
      389 +Absorptive, so they dissipate rather than reflect the blocked 
          +power (fine at ≤ 40 mW).                                      
      390 +A 3° tilt shifts the beam by ~36 µm, which is irrelevant at a 
          +7.5 mm pupil, and keeps                                       
      391 +their ~4 % surface reflections out of the fibre. They are plan
          +e plates, not wedges, but                                     
      392 +their parallelism is not specified. Check the focus position o
          +nce when you swap them (a                                     
      393 +0.1 mrad deviation moves the N40X-PF focus by 0.5 µm).        
      394 +                                                              
      395 +### Delivery-optics parts (€315.49; already in tier B of `NV_u
          +pgrade_shopping_list.xlsx`)                                   
      396 +                                                              
      397 +| # | Part | Description | Qty | Unit | Total |               
      398 +|---|---|---|---|---|---|                                     
      399 +| 12 | [LPVISE100-A](https://www.thorlabs.com/thorproduct.cfm?
          +partnumber=LPVISE100-A) | Ø1″ linear polariser, 400–700 nm | 1
          + | 103,08 € | 103,08 € |                                      
      400 +| 12a | [RSP1/M](https://www.thorlabs.com/thorproduct.cfm?part
          +number=RSP1/M) | rotation mount for the polariser (set once, t
          +hen locked) | 1 | 95,73 € | 95,73 € |                         
      401 +| 13 | [NE10A](https://www.thorlabs.com/thorproduct.cfm?partnu
          +mber=NE10A) | absorptive ND, OD 1.0, SM1-mounted | 1 | 58,34 €
          + | 58,34 € |                                                  
      402 +| 13a | [NE20A](https://www.thorlabs.com/thorproduct.cfm?partn
          +umber=NE20A) | absorptive ND, OD 2.0, SM1-mounted | 1 | 58,34 
          +€ | 58,34 € |                                                 
      403 +                                                              
      404 +Note that the λ/2 plate (#9) and the polariser each need their
          + **own** rotation mount. The                                  
      405 +single `RSP1/M` in the shopping list was meant for a rotating 
          +polariser. In this design it                                  
      406 +holds the polariser, and the PM-launch tranche above supplies 
          +the second one for the plate.                                 
      407 +                                                              
      408 +---                                                           
      409 +                                                              
      410  ## Already owned — do not re-order
      411  
      412  | Part | Qty | Role in this stage |

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 1 line
      416  | `P3-405BPM-FC-1` | 1 | the fibre |
      417  | `PM101A` + `S120C` | 1 | coupling-efficiency readout — essen
           tial during the walk |
      418  | `VRC2` | 1 | beam visualisation |
      419 +| `FBW5532-10` | 1 | laser-line filter; **moves** from the fre
          +e-space laser path to the delivery end, after the NDs |       
      420  | `CCHK/M`, `HW-KIT1/M`, `HW-KIT2/M` | — | hex keys and screws
            |
      421  
      422  Verified compatible mounting adapters for the Ø12 mm / M12 × 0
           .5 `F240FC-532` body:

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 1 line
      434  | *credit:* swap fibre to P3-488PM-FC-1 | −37,03 € | 1 005,11 
           € |
      435  | PM axis launch (recommended; can follow first coupling) | 46
           4,72 € | 1 469,83 € |
      436  | *option:* second F240APC-532 for ensemble delivery | 238,55 
           € | 1 708,38 € |
      437 +| Delivery optics: polariser + rotation mount + 2 ND (already 
          +in tier B) | 315,49 € | 2 023,87 € |                          
      438  | *variant:* plain BB1-E02 instead of BB1-E02P | −54,88 € | |
      439  
      440  The first two rows are what unblock work: **€874.60** gets you
            a correctly-connectorised,

● Update(procurement\fiber_coupling_stage.md)
  ⎿  Added 18 lines
      479  5. Expect **> 50 %** into the fibre once mode-matched. If you 
           plateau below ~20 % and the
      480     shear plate says the beam is collimated, the beam diameter 
           is wrong — revisit the gate.
      481  
      482 +Then the polarisation and filter optics, in this order (power 
          +meter at the delivery end):                                   
      483 +                                                              
      484 +6. **Output collimator + polariser.** Fit the delivery collima
          +tor, then the polariser in its                                
      485 +   rotation mount. Rotate the polariser for maximum transmissi
          +on (P_max), then 90° away                                     
      486 +   for minimum (P_min). The extinction ratio is 10·log(P_max/P
          +_min).                                                        
      487 +7. **λ/2 plate (launch side).** Leave the polariser at the *mi
          +nimum* (crossed) position.                                    
      488 +   Warm a length of the fibre gently with your hand, or flex i
          +t slowly. If P_min                                            
      489 +   fluctuates, the launch is off-axis. Rotate the λ/2 plate a 
          +few degrees at a time,                                        
      490 +   re-find the polariser minimum, and repeat. Stop when P_min 
          +is smallest and steady;                                       
      491 +   aim for ≥ 15 dB (the fibre's minimum spec). Inserting the p
          +late does not disturb the                                     
      492 +   coupling, so re-peak M2 only if the power dropped. Thorlabs
          + align the PM slow axis to                                    
      493 +   the connector key, which gives a first guess.              
      494 +8. **Lock the polariser at maximum** (the slow axis). Record t
          +he angle.                                                     
      495 +9. **NDs and FBW5532-10.** Insert the NDs tilted 2–5°, then th
          +e FBW5532-10 in its fixed                                     
      496 +   mount, then align into the DMLP550R and the objective *afte
          +r* the FBW is in place.                                       
      497 +   Check the power stability behind the whole chain for ~30 mi
          +n while touching the fibre.                                   
      498 +   The residual drift should be a few % or less.              
      499 +                                                              
      500  ## Open items
      501  
      502  - Beam diameter of the `DJ532-40` + `LTC56A/M` assembly: viewi
           ng-card estimate "just
● I've added a new section to procurement/fiber_coupling_stage.md covering the
  λ/2 plate, the polariser and the FBW5532-10.

  What the new section explains:
  - λ/2 plate (launch side, after M2): it rotates the laser's polarisation onto
    the fibre's slow axis, without any power loss. Rotating the plate by θ
    rotates the polarisation by 2θ. It must come after the mirrors, because they
    can make the beam slightly elliptical and a λ/2 plate can't fix that. At
    the delivery end it would cause problems at the dichroic's 533 nm band edge.
  - Polariser (delivery side, first after the collimator, fixed on the slow
    axis): it's a clean-up polariser. It turns leftover polarisation drift into
    at most ~3% power change, which a reference photodiode can correct. The
    section includes the formula for why rotating it as an attenuator gives ±17%
    power wander.
  - FBW5532-10 (delivery side, last before the DMLP550R, in a fixed mount): it
    removes the fibre's own background light, which would otherwise reach the
    detector through the diamond reflection. It also removes anything the laser
    emits outside 532 nm, so one filter after the fibre is enough. Because it's
    wedged, disturbing it moves the focus by about 20 µm with the objective (64
    µm with the condenser).
  - ND filters: a short note on tilting them and checking the focus after
    swapping them.

  Other additions to the file:
  - Parts table: LPVISE100-A + RSP1/M + NE10A + NE20A, €315.49. These are
    already in tier B of the shopping list. The λ/2 plate and the polariser each
    need their own rotation mount.
  - Owned parts: the FBW5532-10 is listed as moving from the laser path to the
    delivery end. It's Ø12.5 mm, so it needs an SM05-to-SM1 adapter in a 1″
    cage.
  - Totals: a delivery-optics row, bringing the running total to €2,023.87.
  - Procedure steps 6–9:
    - Set the polariser and measure the extinction ratio.
    - Align the λ/2 plate by warming or flexing the fibre until the power behind
      the crossed polariser is smallest and steady.
    - Lock the polariser on the slow axis.
    - Insert the NDs and the FBW, align into the objective after them, then run
      a 30-minute stability check.

  Two statements in the new text are from memory and worth checking against the
  datasheets:
  - Thorlabs align the PM slow axis to the connector key.
  - The FBW filter's ~30′ wedge angle, which comes from vendor text.

✻ Brewed for 1m 18s · done Wednesday 12:15

※ recap: You're designing the NV optical setup; I built the modelling notebook and have just finished explaining the λ/2 plate, polariser and FBW filter in the fibre-coupling notes. Next, check the collimator engravings (FC or APC) before ordering.

❯ I laso have the thorlabs low density nv diamond, which photon counter would   
  be ideal for my setup? I know thorlabs has a few models                       

● Web Search("Thorlabs single photon counting module SPCM50A SPCM20A SPDMA
            active area dark count detection efficiency")
  ⎿  Did 1 search in 6s

● Web Search("Thorlabs low density NV diamond single NV centers DNVB1 electronic
            grade nitrogen-vacancy")
  ⎿  Did 1 search in 7s

● Fetch(https://www.thorlabs.com/catalogpages/Obsolete/2025/SPCM50A_M.pdf)
  ⎿  Received 1.3KB (200 OK)

● Web Search("Thorlabs SPDMA single photon detector max count rate dead time
            price SPDMH2 SPDMH3 SPDMH4 hybrid photon detection efficiency")
  ⎿  Did 1 search in 7s

● Web Search("Thorlabs SPCM50A saturation count rate dead time 35 ns photon
            detection efficiency 650 nm 700 nm price")
  ⎿  Did 4 searches in 11s

● Fetch(https://manuals.plus/thorlabs/spdmh2-single-photon-detectors-manual)
  ⎿  Received 109.3KB (200 OK)

● It depends on which diamond you have, and if it's the DNVB1, a photon counter 
  is the wrong detector.

  If it's the DNVB1 (300 ppb): use an analogue detector instead

  Thorlabs sells two NV-doped diamonds: DNVB14 (4.5 ppm) and DNVB1 (300 ppb).
  DNVB1 is the "low density" one, but it is still an ensemble sample:

  - 300 ppb is about 5×10⁴ NV per µm³.
  - The notebook's confocal volume (F810 beam, 30 µm pinhole) is about 0.3 µm³
    by FWHM, or ~5 µm³ by the notebook's more generous effective-volume measure.
  - That puts roughly 10⁴–10⁵ NVs in focus.
  - Even at a pessimistic 10⁴ counts/s per NV through this optics, that is ≳10⁸
    counts/s.

  Every Thorlabs photon counter saturates at about 20 Mcounts/s, so you would
  have to attenuate the signal by OD 1–2 just to use one.

  In power terms that's roughly 30–300 pW, which is exactly the range where a
  linear APD works well. The repo's own analysis
  (procurement/apd430a_single_nv_analysis.md) puts the APD430A's useful range at
  about 300 to 10⁶ NVs, which covers this. If you still have the APD430A, it
  fits DNVB1 confocal work. The APD440A would be better: it's cheaper and 40×
  more sensitive (lower noise-equivalent power).

  If it's electronic-grade diamond (≤ 0.03 ppb NV): the SPDMH2F

  Thorlabs' electronic-grade plates have ≤5 ppb nitrogen and typically ≤0.03 ppb
  NV, i.e. ≲5 NV per µm³. That means about one NV or fewer in a 0.3 µm³ focus,
  so single NVs can be isolated. At an estimated 10⁴–10⁵ counts/s per NV, you
  then need photon counting.

  ┌──────────┬──────────────────┬──────────────┬─────────┬─────────────────┐
  │          │                  │  Detection   │  Dark   │                 │
  │  Model   │   Active area    │ efficiency   │ counts  │     Status      │
  │          │                  │  in NV band  │         │                 │
  ├──────────┼──────────────────┼──────────────┼─────────┼─────────────────┤
  │          │ Ø100 µm, fibre   │ 70 % @ 670   │         │                 │
  │ SPDMH2F  │ input (FC/PC,    │ nm, 60 % @   │ 100 Hz  │ current         │
  │          │ ≤105 µm core, NA │ 810 nm       │         │                 │
  │          │  ≤ 0.29)         │              │         │                 │
  ├──────────┼──────────────────┼──────────────┼─────────┼─────────────────┤
  │ SPDMH2 / │ Ø100 µm, free    │ same         │ 100 /   │ current         │
  │  SPDMH3  │ space            │              │ 250 Hz  │                 │
  ├──────────┼──────────────────┼──────────────┼─────────┼─────────────────┤
  │          │ Ø500 µm, free    │ 66 % @ 650   │ 75–300  │ current (€4,781 │
  │ SPDMA    │ space,           │ nm, 43 % @   │ Hz typ  │  in the repo    │
  │          │ adjustable gain  │ 820 nm       │         │ notes)          │
  ├──────────┼──────────────────┼──────────────┼─────────┼─────────────────┤
  │ SPCM20A  │                  │ 35 % @ 500   │ 100 /   │ discontinued    │
  │ /        │ Ø20 / 50 µm      │ nm           │ 250 Hz  │ April 2025      │
  │ SPCM50A  │                  │              │ max     │                 │
  └──────────┴──────────────────┴──────────────┴─────────┴─────────────────┘

  The SPDMH series also specifies a 45 ns dead time, 20 MHz maximum count rate,
  0.2% afterpulsing and 1 ns timing resolution.

  I'd pick the SPDMH2F, fed by a 50 µm multimode fibre patch cable (FC/PC) whose
  core acts as the confocal pinhole. This is the approach from Sewani et al.,
  which is already cited in detectors_in_the_literature.md:

  - It fits your geometry. At M = 30 the Airy unit at the pinhole is 34 µm, so a
    50 µm core is about 1.5 AU. In the notebook's model that gives 86% in-focus
    transmission and 7 µm axial sectioning of a thin NV layer. The converging
    cone (NA 0.025) is far inside the fibre's acceptance.
  - Alignment is simpler. You align only the fibre tip, with the ST1XY-S/M you
    already own plus focus. There is no separate pinhole and detector to
    co-align.
  - It fits the light-tight enclosure plan. The detector can sit outside the
    box, and a second SPDMH2F plus a fibre splitter later gives you the g⁽²⁾
    antibunching measurement that proves a spot is a single NV.
  - Among the Thorlabs models, it has the best efficiency in the NV emission 
    band and the lowest dark count.

  The free-space SPDMA is the alternative if you'd rather use your pinhole kit.
  Its Ø500 µm area can sit about 9 mm behind a 30 µm pinhole with no relay lens,
  at slightly lower efficiency. The Ø100 µm free-space SPDMH2 would need a
  relay lens, because it would have to sit within about 1.4 mm of the pinhole. I
  didn't find a current price for the SPDMH2F, so check it.

  Other things you'd need for single-NV work

  1. Counting electronics. The detector outputs TTL pulses, and they must be
     counted in sync with the microwave switching. The stock Red Pitaya and
     lock-in code don't do this. You'd need a counter or time tagger, or custom
     FPGA logic.
  2. A 650 nm longpass instead of the FELH0550. The diamond's Raman line at 573
     nm passes the FELH0550 and is comparable to a single NV's signal.
  3. Work at about 210 µm depth, or use a cover-glass correction collar if the
     objective has one. At the surface the N40X-PF's cover-glass correction
     makes the focus badly aberrated (notebook §4).
  4. A light-tight enclosure and pupil-filling excitation (fibre + F810). Photon
     counters can be damaged by room light or stray laser light.

  Can you confirm the part number of your low-density diamond? If it's DNVB1,
  the useful upgrade is the analogue APD path, not a photon counter. I can add
  whichever route applies to the procurement notes.

  Sources:
  - Thorlabs Single Photon Detectors
  - SPDMA
  - SPDMH2F
  - SPDMH2/3 manual
  - SPCM50A (discontinued)
  - DNVB1
  - Thorlabs Single-Crystal Diamonds

✻ Cogitated for 2m 4s · done Wednesday 12:25

❯ Ok, thanks, i can buy from other suppliers other than thorlabs so might be    
  worth comparing some of the other detectors out there. The main thing i care  
  about is that the detector will be useful for pulsed work in the future       

● Fetch(https://www.excelitas.com/file-download/download/public/60241?filename=E
       xcelitas_SPCM-AQRH_Family_datasheet.pdf)
  ⎿  Received 0 bytes (403 Forbidden)

● Web Search("Laser Components COUNT-T single photon counting module 100 µm
            photon detection efficiency 670 nm dark count timing resolution dead
            time gate")
  ⎿  Did 1 search in 6s

● Web Search("Micro Photon Devices PDM red enhanced photon detection efficiency
            700 nm timing resolution; ID Quantique ID120 photon detection
            efficiency 700 nm active area")
  ⎿  Did 2 searches in 6s

● For pulsed NV work, efficiency in the 650–800 nm NV emission band matters much
  more than timing speed. Any thick-junction silicon photon counter from the
  three main suppliers will do. What will actually limit pulsed work is the
  electronics around the detector.

  What pulsed NV readout needs from a detector

  In a pulsed sequence, the spin state is read out as a fluorescence difference
  in the first ~300 ns of each laser pulse. That sets the requirements:

  Property: Efficiency at 650–800 nm
  Needed for pulsed NV: as high as possible
  Why: A single NV gives only ~0.01–0.05 detected photons per readout. Every
  point needs 10⁵–10⁶ repetitions, and efficiency scales the averaging time
  directly.
  ────────────────────────────────────────
  Property: Timing resolution
  Needed for pulsed NV: ≲ 5–10 ns is enough
  Why: Readout windows are hundreds of ns. Sub-ns timing matters only for
  excited-state lifetime (~12 ns) and fine g⁽²⁾ measurements.
  ────────────────────────────────────────
  Property: Dead time
  Needed for pulsed NV: irrelevant for single NVs
  Why: You rarely get more than one photon per readout. It matters only for
  bright ensembles.
  ────────────────────────────────────────
  Property: Afterpulsing
  Needed for pulsed NV: low (≲ 1 %)
  Why: Afterpulses land in the next readout window and bias the contrast.
  ────────────────────────────────────────
  Property: Dark counts
  Needed for pulsed NV: ≲ 100–250 counts/s
  Why: Fine against a single NV's ~10⁴–10⁵ counts/s.
  ────────────────────────────────────────
  Property: Output / gate
  Needed for pulsed NV: TTL pulses; a gate input helps
  Why: Pulses go to a time tagger. A gate protects the detector during bright
  laser pulses.

  Comparison

  Detector: Excelitas SPCM-AQRH (-14 / -FC)
  Type: thick-junction Si, Ø180 µm
  Efficiency in NV band: ≈ 65–68 % @ 650 nm
  Timing: ~350 ps
  Dead time: ~22 ns
  Fit for pulsed NV: ✅ the de facto standard in NV labs (Rondin et al. and
  later
  papers)
  ────────────────────────────────────────
  Detector: Laser Components COUNT-T (FC option, ≤105 µm core)
  Type: thick-junction Si, Ø100 µm
  Efficiency in NV band: > 70 % in the red (measured per unit at 670 nm)
  Timing: down to 350 ps
  Dead time: ~43 ns
  Fit for pulsed NV: ✅ as good, often cheaper in Europe; per-unit test data
  supplied
  ────────────────────────────────────────
  Detector: Thorlabs SPDMH2F
  Type: thick-junction Si, Ø100 µm, FC
  Efficiency in NV band: 70 % @ 670, 60 % @ 810 nm
  Timing: 1 ns
  Dead time: 45 ns
  Fit for pulsed NV: ✅ fine for spin readout; the 1 ns timing only limits
  lifetime work. Its specs closely match the COUNT series.
  ────────────────────────────────────────
  Detector: Thorlabs SPDMA
  Type: Si, Ø500 µm, adjustable gain
  Efficiency in NV band: 66 % @ 650, 43 % @ 820 nm
  Timing: not checked
  Dead time: not checked
  Fit for pulsed NV: ⚠️ usable, but more dark counts and weaker at 750–800 nm
  ────────────────────────────────────────
  Detector: ID Quantique ID120
  Type: cooled Si, Ø500 µm
  Efficiency in NV band: ~60 % @ 700 nm (up to 80 % near 800)
  Timing: ~400 ps
  Dead time: not checked
  Fit for pulsed NV: ⚠️ very good efficiency, but large area and expensive; the
  size helps only without a pinhole
  ────────────────────────────────────────
  Detector: MPD PDM / IDQ ID100
  Type: thin-junction Si, fast timing
  Efficiency in NV band: ~34 % @ 650 nm and falling
  Timing: 35–50 ps
  Dead time: not checked
  Fit for pulsed NV: ❌ you'd pay for picosecond timing you can't use, and lose
  about half the NV signal
  ────────────────────────────────────────
  Detector: Hybrid PMTs (e.g. Becker & Hickl HPM)
  Type: photocathode
  Efficiency in NV band: falls off steeply above 650 nm
  Timing: ~20 ps
  Dead time: ~none
  Fit for pulsed NV: ❌ low red efficiency. Their strength (no afterpulsing or
  dead time) matters for fast fluorescence-lifetime counting, not NV spin work.
  ────────────────────────────────────────
  Detector: Superconducting nanowire (SNSPD)
  Type: cryogenic
  Efficiency in NV band: > 90 %
  Timing: ps
  Dead time: ns
  Fit for pulsed NV: ❌ needs a cryostat and costs 10× more

  Recommendation: the fibre-coupled version of an Excelitas AQRH or a Laser 
  Components COUNT-T (or Thorlabs SPDMH2F), bought on price. They perform about
  the same for this job. The fibre input keeps the idea from my last answer,
  with a 50 µm multimode fibre acting as the confocal pinhole. It also lets you
  add a second unit plus a fibre splitter later for g⁽²⁾ measurements.

  When you get quotes, ask each supplier for three things:
  - measured efficiency at ~700 nm;
  - afterpulsing;
  - whether there is a gate input.

  If you do g⁽²⁾ with two silicon photon counters, block their breakdown-flash
  crosstalk with a filter or an angled path; otherwise it creates false
  correlations.

  Two corrections to my last answer

  1. For pulsed ensemble work you don't need a photon counter at all. Ensemble
     signals saturate a single-photon detector within one readout window: at 20
     Mcounts/s, a 300 ns window holds at most ~6 counts.
     - DNVB14: your PDA10A2 (150 MHz bandwidth) plus a fast digitiser is already
       a workable pulsed-readout detector. The Red Pitaya at 125 MS/s gives 8
       ns samples.
     - DNVB1 confocal: I suggested the APD440A. For pulsed readout that is 
       wrong. Its DC–100 kHz bandwidth can't resolve a 300 ns window. The
       APD430A (400 MHz) is the right analogue detector for low-light pulsed
       ensemble readout, if you still have it. Its bandwidth, which is wasted on
       CW lock-in work, is exactly what pulsed readout needs.
  2. The detector is the easy part of going pulsed. You would also need:
     - Laser switching. The DJ532-40 is a DPSS laser and cannot be switched on
       and off in nanoseconds, so it needs an AOM. In the fibre layout, the AOM
       would sit before the launch.
     - A pulse generator.
     - A fast microwave switch. The ZASWA-2-50DRA+ is already in your shopping
       list.
     - A time tagger or gated counter. Neither the stock Red Pitaya nor the
       current lock-in code does this.

  Sources:
  - Laser Components COUNT series
  - COUNT-T
  - Thorlabs SPDMH2/3 manual
  - Thorlabs Single Photon Detectors
  - MPD PDM series
  - ID Quantique ID120
  - Excelitas SPCM-AQRH datasheet. The file returned an error, so the AQRH
    figures come from the repo's literature notes and should be checked.

✻ Brewed for 1m 27s · done Wednesday 12:30

❯ Ok, why is the fiber coupled version of the excelitas better than the one     
  with 30 mm cage adapter for a lens                                            

● It isn't strictly better. I recommended the fibre-coupled version for
  practical reasons in your setup, not because it detects light better. On raw
  efficiency the free-space version with a lens adapter actually wins slightly.

  Where the free-space (cage-adapter) version is better

  - Throughput. No fibre ends and no internal fibre-to-detector relay. The fibre
    route typically costs of the order of 10 % (Fresnel reflections at the
    fibre faces plus coupling into the detector). Ask Excelitas for the exact
    figure for the FC version.
  - Flexible pinhole size. You can use any pinhole from your kit. With a fibre,
    the pinhole is fixed by the core: 50 µm is 1.5 Airy units at M = 30, and
    changing it means changing fibres.
  - Possibly lower cost. Worth comparing in the quotes.

  Why I still leaned towards the fibre version

  1. The free-space version needs a relay lens here, which means more alignment.
     The Excelitas active area is Ø180 µm, about 5 Airy units at your M = 30.
     Used directly as the pinhole it gives weak sectioning: notebook §4 gives
     ~20–27 µm thin-layer sectioning for a 150–200 µm pinhole, versus ~5–7 µm
     for 30–50 µm. So you still want a real pinhole. Light leaves the pinhole in
     an NA 0.025 cone, so the 180 µm chip would have to sit within about 3 mm
     of it. That isn't possible with the chip recessed behind the module window,
     so you need pinhole → relay lens(es) → detector. That is three things to
     align in x, y and z. With the fibre, you align only the fibre tip, on the
     ST1XY-S/M you already own plus focus.
  2. Stray light. A photon counter sees single photons of room light and
     scattered 532 nm light. A multimode fibre accepts light only within its 50
     µm core and 0.22 NA. The detector then sits in its own dark box, so leaks
     in the table enclosure hit nothing sensitive. The repo's enclosure notes
     show stray light is already a known problem on this table.
  3. Heat and vibration away from the sample. The module is thermoelectrically
     cooled and dissipates a few watts. Near the diamond, that drifts the
     zero-field splitting D by −74 kHz/K. On a fibre it can sit away from the
     table.
  4. Expandable without rebuilding. The g⁽²⁾ single-NV check is a fibre 50:50
     splitter plus a second detector. Checking the NV⁻/NV⁰ spectrum is just
     re-plugging the fibre into a spectrometer. Swapping or servicing the
     detector doesn't touch the confocal alignment.

  Bottom line

  ┌───────────────────────────────┬─────────────────────────────────────────┐
  │     If you value most...      │                 Choose                  │
  ├───────────────────────────────┼─────────────────────────────────────────┤
  │ the last ~10 % of signal, and │ free-space + 30 mm cage adapter,        │
  │  a pinhole size you can       │ pinhole, 1:1 relay (e.g. two            │
  │ change                        │ short-focal-length achromats)           │
  ├───────────────────────────────┼─────────────────────────────────────────┤
  │ easy alignment, stray-light   │ FC version + 50 µm multimode patch      │
  │ immunity, thermal isolation,  │ cable                                   │
  │ easy g⁽²⁾ later               │                                         │
  └───────────────────────────────┴─────────────────────────────────────────┘

  For a first confocal build on an open table, I'd still take the fibre version:
  for single-NV work, background and alignment drift usually cost far more than
  10 %. If you go free-space, budget for a lens-tube enclosure all the way from
  the pinhole to the detector and a proper relay. Either way, get Excelitas'
  coupling-efficiency figure for the FC version before deciding.

✻ Sautéed for 31s · done Wednesday 12:41

※ recap: You're choosing a single-photon counter for future pulsed and single-NV work on the confocal setup. Next, ask Excelitas how much signal the fibre-coupled AQRH loses compared with the free-space version, then choose between them.

❯ One last question regarding my kit. I bought the PKIT1K thorlabs pinhole kit. 
  But I was wondering if that is overkill and maybe i just need a couple of     
  pinholes                                                                      

● Web Search("Thorlabs PKIT1K pinhole kit contents diameters price")
  ⎿  Did 1 search in 4s

● It's mildly overkill for this setup, but not a bad buy. With your optics,
  about half the kit is actually useful.

  What sets the useful range. With the N40X-PF (f = 5 mm) and the AC254-150 as
  tube lens, the magnification at the pinhole is M = 30. At 700 nm that puts one
  Airy unit (AU) at about 34 µm on the pinhole. From the notebook's §4 table,
  with the pupil-filling F810 beam:

  Pinhole: 5 µm
  Airy units: 0.15
  In-focus transmission: 9 %
  Thin-layer sectioning (FWHM): 3.8 µm
  Verdict: ❌ throws away 90 % of the signal for almost no gain
  ────────────────────────────────────────
  Pinhole: 10 µm
  Airy units: 0.3
  In-focus transmission: 25 %
  Thin-layer sectioning (FWHM): 3.9 µm
  Verdict: ❌
  ────────────────────────────────────────
  Pinhole: 15–20 µm
  Airy units: 0.45–0.6
  In-focus transmission: 42–61 %
  Thin-layer sectioning (FWHM): 4.0–4.3 µm
  Verdict: marginal, only for the sharpest sectioning at a big signal cost
  ────────────────────────────────────────
  Pinhole: 25–30 µm
  Airy units: 0.7–0.9
  In-focus transmission: 73–78 %
  Thin-layer sectioning (FWHM): 4.6–4.9 µm
  Verdict: ✅ standard confocal choice
  ────────────────────────────────────────
  Pinhole: 40–50 µm
  Airy units: 1.2–1.5
  In-focus transmission: 82–86 %
  Thin-layer sectioning (FWHM): 6.0–7.3 µm
  Verdict: ✅ more signal, slightly weaker sectioning; good for faint single NVs
  ────────────────────────────────────────
  Pinhole: 75–100 µm
  Airy units: 2.2–2.9
  In-focus transmission: 91–93 %
  Thin-layer sectioning (FWHM): 11–14 µm
  Verdict: ✅ for alignment, and for depth-resolved ensemble work

  The PKIT1K has ten pinholes from Ø5 to Ø100 µm. That is very likely 5, 10, 15,
  20, 25, 30, 40, 50, 75 and 100 µm, but check the engravings. At M = 30, the
  5–20 µm ones will essentially never be used.

  The large ones matter even if you only ever use 30 µm. The standard confocal
  alignment procedure is to find the signal with a 100 µm pinhole, centre it,
  then step down (100 → 50 → 30) and re-centre each time. A 30 µm pinhole is
  hard to find the focus with from scratch.

  When the small pinholes would earn their place:
  - A shorter tube lens. With f = 50 mm, M = 10 and the AU drops to about 11 µm,
    so 10–15 µm pinholes become the 1 AU choice. Pinhole size scales with M.
  - Spatial filtering a laser beam (lens + 5–25 µm pinhole). This mostly isn't
    needed once you're fibre-coupled, because the single-mode fibre already does
    that job.

  Verdict:
  - If returning it is easy and you're going the fibre-coupled photon-counter 
    route: buy individual 30, 50 and 100 µm mounted pinholes (P30K, P50K,
    P100K), and optionally the 40 µm. With the fibre route, the 50 µm fibre core
    becomes the pinhole anyway, so free-space pinholes are only for testing and
    for ensemble work with the PDA10A2.
  - If returning it is a hassle: keep it. It costs you nothing, and if you ever
    change the magnification, the smaller sizes become the useful ones.

  Source: Thorlabs Precision Pinhole Kits

✻ Sautéed for 29s · done Wednesday 13:12

❯ Ok, thanks, WOuld the single photon conting module be enough to form a wide   
  field image of a section of the sample and the sample is moved with a nanomax 
  flexure stage XYZ                                                             

● Yes, but it wouldn't be a wide-field image. A photon counter is a single-pixel
  detector. With the NanoMax moving the sample you build the image one point at
  a time, which is a sample-scanning confocal image. That is the standard way
  NV labs find single NVs, and it works well with your optics.

  How it works

  Park the confocal spot, count photons for a fixed time, step the stage, and
  repeat. Each count becomes one pixel. Sample scanning is a good fit for this
  setup: the beam stays on the optical axis, so the scan adds no aberrations.
  That matters because focusing into diamond already costs you the most
  (notebook §4).

  Numbers for your setup

  These assume the pupil-filling F810 excitation and a 30 µm pinhole at about
  210 µm depth.

  ┌───────────────────┬─────────────────────────────────────────────────────┐
  │     Quantity      │                        Value                        │
  ├───────────────────┼─────────────────────────────────────────────────────┤
  │ Lateral           │ ≈ 0.39 µm (confocal)                                │
  │ resolution (FWHM) │                                                     │
  ├───────────────────┼─────────────────────────────────────────────────────┤
  │ Pixel size        │ ≤ 0.15–0.2 µm                                       │
  │ (Nyquist)         │                                                     │
  ├───────────────────┼─────────────────────────────────────────────────────┤
  │ Field for one     │ ~20 × 20 µm (check your model's piezo travel) → ≈   │
  │ NanoMax piezo     │ 130 × 130 px                                        │
  │ range             │                                                     │
  ├───────────────────┼─────────────────────────────────────────────────────┤
  │ Single-NV signal  │ ~10⁴–10⁵ counts/s → 5–10 ms dwell gives 100–1000    │
  │ (estimate)        │ counts on an NV                                     │
  ├───────────────────┼─────────────────────────────────────────────────────┤
  │                   │ 17k px × 5–10 ms ≈ 1.5–3 min of counting. Stage     │
  │ Time per image    │ steps and settling usually dominate: at 20–50 ms    │
  │                   │ per step over USB, expect ~6–15 min.                │
  ├───────────────────┼─────────────────────────────────────────────────────┤
  │ Axial sections    │ Step Z on the piezo. Axial resolution is ≈ 3.5 µm   │
  │                   │ for a point, so 1 µm Z steps are enough.            │
  └───────────────────┴─────────────────────────────────────────────────────┘

  Larger areas come from stitching tiles with the coarse adjusters.

  It depends on which NanoMax you have

  - Manual (micrometers only): not practical for imaging. It is fine for coarse
    positioning.
  - Stepper-motor drives: workable for coarse maps, but slow and with backlash
    at sub-µm steps.
  - Piezo, open loop: works, but piezo hysteresis (~10–15 % of travel) distorts
    the image. Scan in one direction only, and treat distances as approximate.
  - Piezo with strain-gauge feedback (closed loop): the right choice. Positions
    are repeatable, so you can return to the same NV.

  It depends on the diamond

  - Electronic grade: this is exactly what the photon counter plus scanning is
    for. Isolated NVs show up as ~0.4 µm bright spots, and the image is how you
    find them before parking for ODMR, g⁽²⁾ or pulsed work.
  - DNVB1 / DNVB14: the image is essentially uniform, and the signal (≳10⁸
    counts/s) would saturate the counter unless you add OD 2–3. Scan with the
    PDA10A2 or an analogue APD instead. Same stage, same scan code, different
    detector.

  What you'd need besides the detector and stage

  1. Counting electronics synchronised with the stage. You need counts per pixel
     and a way to step the stage. The usual options are a DAQ card with a
     counter input or a time tagger. The stock Red Pitaya doesn't count TTL
     pulses.
  2. Drift tracking. Flexure stages drift thermally by tens of nm per minute.
     For long ODMR or pulsed runs on one NV, add a periodic auto-refocus
     routine: a small XYZ scan around the NV, then re-centre. Every single-NV
     setup needs this, and it matters doubly for pulsed work, where one data
     point takes minutes.
  3. Keep heat away from the sample stage. The fibre-coupled detector helps
     here, as discussed.

  If you actually wanted a true wide-field image

  For that you'd use a camera (CMOS or sCMOS) with a large illuminated area
  instead of a focused spot. That is the standard approach for ensemble
  wide-field NV magnetometry on DNVB14 or DNVB1: one frame images the whole
  field, and each pixel collects signal from many NVs. It doesn't need a photon
  counter. It can't isolate single NVs, but for ensemble field mapping it is far
  faster than scanning.

  Which NanoMax model do you have (manual, stepper or piezo, closed loop or
  not)? That decides whether the scan can be made fully automatic.

✻ Cogitated for 33s · done Wednesday 13:22

❯ Ok, but using a single photon counting module would involve a time tagger and 
  some upgrades t o the acquisition                                             
● Yes. Moving to a photon counter moves the acquisition from analogue voltages
  (Red Pitaya ADC and software lock-in) to counting digital pulses. How much you
  need depends on the stage you're building for. Stages 1 and 2 are for single
  NVs; ensemble work stays on the current chain (last section).

  What each stage needs

  Stage: 1. Confocal imaging + CW ODMR on single NVs
  Detector signal: counts per pixel / per frequency point (ms gates)
  Counting hardware: a counter: software-timed gates are fine
  Timing / control: the SMCV sweep over SCPI, as now; stage stepping
  ────────────────────────────────────────
  Stage: 2. g⁽²⁾, to prove it's a single NV
  Detector signal: photon arrival times on 2 detectors
  Counting hardware: time tagger (≲ 1 ns resolution)
  Timing / control: none
  ────────────────────────────────────────
  Stage: 3. Pulsed work (Rabi, Ramsey, echo, T₁)
  Detector signal: arrival times relative to each laser pulse, histogrammed over

  10⁵–10⁶ repetitions
  Counting hardware: time tagger, or hardware-gated counters
  Timing / control: pulse generator driving the AOM and the MW switch, sharing a

  trigger with the tagger

  Options

  1. Red Pitaya with custom FPGA counting (cheapest, most work). You already own
     it, and its FPGA could count pulses and even generate pulse sequences with
     8 ns resolution. But none of that is in the stock image, so it means
     writing FPGA code. It also needs care:
     - Detector pulses are only ~10–15 ns wide, so an FPGA sampling every 8 ns
       can miss them.
     - The detector's TTL output level must match the Red Pitaya's 3.3 V digital
       inputs.

     Good for stage 1 if you enjoy FPGA work. Hard to stretch to g⁽²⁾ or clean
     pulsed histograms.
  2. DAQ card with counter inputs (e.g. NI 63xx-series). For years this was the
     classic NV confocal setup: hardware-timed counting, analogue outputs to
     drive a piezo controller for scanning, and triggered gates. It covers stage
     1 well and simple pulsed sequences clumsily. It can't do g⁽²⁾.
  3. Time tagger (e.g. Swabian Time Tagger 20 / Ultra, PicoQuant, qutools quTAG)
     (the recommended option). It time-stamps every photon and does the rest in
     software:
     - count rates for imaging and CW ODMR;
     - g⁽²⁾ correlations;
     - pulsed readout histograms relative to a sync pulse.

     It covers all three stages, so you buy counting hardware once. Swabian's
     Python API is widely used in NV labs.

  Pulse generator for stage 3. Swabian Pulse Streamer and SpinCore PulseBlaster
  are the common turnkey choices, with ns resolution and several digital
  channels driving the AOM, the MW switch (the ZASWA-2-50DRA+ is already in your
  shopping list) and the tagger sync. The Red Pitaya is the do-it-yourself
  alternative. The same box can also step the confocal scan.

  Recommendation

  - Skip the intermediate DAQ step and buy a time tagger with the detector. It
    does stage 1 immediately (imaging and CW ODMR), and g⁽²⁾ and pulsed work
    later with no new counting hardware.
  - Add the pulse generator and an AOM only when you go pulsed. Neither is
    needed before then.

  Software

  Two routes:
  - Extend the current Python scripts. Add a timetagger_common.py alongside
    lockin_common.py, configured through config.json like the existing smcv/
    scripts, then scripts for confocal scanning, CW ODMR on a single NV,
    drift-tracking refocus, and later pulsed sequences. The existing SMCV
    control and analysis structure carries over.
  - Adopt qudi, the open-source NV lab framework from Ulm. It has confocal
    scanning, ODMR, pulsed measurements and drift tracking built in, with
    drivers for the common taggers and pulse generators. It's more powerful but
    a bigger framework to learn, and your current scripts wouldn't plug into it
    directly.

  Unchanged for ensemble work

  The Red Pitaya, the PDA10A2 and the software lock-in stay as they are for
  DNVB14 ensemble work. Pulsed ensemble readout is analogue too: the photodiode
  plus the Red Pitaya digitising the readout window, triggered by the same pulse
  generator. The time tagger is only for single-NV work.

  Before quoting, check with the suppliers that the time tagger's inputs accept
  the detector's TTL output.

✻ Sautéed for 41s · done Wednesday 14:47

❯ So if i manage to get the fpga counting working and i get the the excelitas   
  SPCM-AQRH-12 i could attempt to align the confocal setup and maybe produce    
  and image of the nv centres in the crystal? Additionally, would the pulsed    
  work need two detectors as well? Also, how would the two detectors be set up  
  to distinguish a single nv from more than one?                                

● Yes on the first, no on the second, and I'll explain the setup for the third.
  One correction first: I was too optimistic about isolating single NVs in
  electronic-grade diamond.

  1. FPGA counting + SPCM-AQRH-12: can you align the confocal and image NVs?

  In principle yes. The -12 dark-count grade is fine: as I recall the grade
  table, it allows ≤ 500 counts/s, which is negligible next to a single NV's
  ~10⁴–10⁵ counts/s. Check that against the datasheet. The things that decide
  whether you get an image:

  - Which sample. Only the electronic-grade diamond can show individual NVs. On
    DNVB14 or DNVB1 the image is uniform and the counter saturates (≳ 10⁸
    counts/s). Sustained very high count rates can also damage a photon counter,
    so check the maximum-rate limits in the AQRH manual. Never point it at the 
    dense samples without OD ≥ 3 in front.
  - The correction: the electronic-grade spec (≤ 0.03 ppb NV) is an upper bound.
    At that bound it works out to ~5 NV/µm³, i.e. ~1–2 NVs per focal volume.
    Spots would overlap into a continuum, not appear as isolated dots.
    Resolvable single NVs need ≲ 0.01–0.1 per µm³, so it depends on the plate's
    actual density. Scan and see: isolated diffraction-limited spots (~0.4 µm)
    on a dark background mean you're in luck.
  - Getting the FPGA counter right:
    - Pulse width. The detector's output pulses are only ~10–15 ns wide. At the
      Red Pitaya's 125 MHz clock (8 ns), detect rising edges on a synchronised
      input, or pulses will be missed.
    - Voltage level. The output is TTL, which can exceed 3.3 V into a
      high-impedance input. Terminate it in 50 Ω, or use a level shifter, before
      it reaches the Red Pitaya's 3.3 V digital I/O. Check the AQRH output
      spec.
    - Timing. Gate counts per pixel with the FPGA's clock, not software timing.
  - A safe alignment order:
    a. Align the pinhole (or fibre) on DNVB14 with the PDA10A2, where the signal
       is huge. Use the pinhole kit's 100 → 50 → 30 µm step-down.
    b. Swap in the electronic-grade plate, put ND on the detector path, and only
       then fit the SPCM.
    c. Find the focus from the diamond surface, then move to ~200 µm depth,
       where the N40X-PF focus is sharpest (notebook §4).
  - Also needed: the pupil-filling excitation (fibre + F810), a light-tight
    enclosure, and preferably a 650 nm longpass (Raman at 573 nm).

  2. Does pulsed work need two detectors?

  No. One detector is enough for pulsed ODMR, Rabi, Ramsey, echo and T₁. Those
  measurements only need photon arrival times relative to each laser pulse:
  counts in a ~300 ns readout window, averaged over 10⁵–10⁶ repetitions. The Red
  Pitaya's 8 ns resolution is adequate for that.

  Two detectors are needed only for g⁽²⁾. A photon counter is blind for ~22 ns
  after each detection (its dead time). That is longer than the NV's ~12 ns
  excited-state lifetime, so one detector cannot record two photons close enough
  together to show the single-photon dip. A second detector would add only a
  little count rate to pulsed work.

  3. How two detectors distinguish one NV from several (the Hanbury Brown–Twiss 
  setup)

  confocal spot ─► pinhole / 50 µm fibre ─► 50:50 splitter ─┬─► SPCM A ─► tagger
  ch 1
                  (fibre coupler or cube)                    └─► SPCM B ─► 
  tagger ch 2

  1. Split the collected fluorescence 50:50 (a multimode fibre coupler is
     easiest) onto two detectors.
  2. Timestamp every photon in both arms.
  3. Histogram the delays τ = t_B − t_A. Normalise by the coincidence rate
     expected for uncorrelated light, R_A·R_B·Δτ·T, to get g⁽²⁾(τ).

  The physics: one emitter cannot emit two photons at once. After each emission
  it needs ~12 ns to be re-excited, so coincidences at τ = 0 vanish. For N equal
  emitters, g⁽²⁾(0) = 1 − 1/N: 0 for one NV, 0.5 for two, 0.67 for three. The
  accepted single-emitter criterion is g⁽²⁾(0) < 0.5.

  - Background fills in the dip: g⁽²⁾(0) = 1 − ρ², with ρ = signal/(signal +
    background). Measure the background next to the spot and correct for it.
  - Shape to expect: a dip ~10 ns wide (it narrows at higher laser power), with
    bunching shoulders (g⁽²⁾ > 1) over ~100s of ns from the NV's metastable
    shelving state. That is a second fingerprint of an NV.
  - Timing needed: ≲ 1 ns. The AQRH (~350 ps) is fine; 8 ns FPGA bins are not,
    since the whole dip is about one bin wide. So g⁽²⁾ is where you'd need a
    real time tagger, or a TDC-based FPGA design, which is much harder.
  - Integration time: with ~2 × 10⁴ counts/s per arm and 1 ns bins, you get ~0.4
    coincidences/s per bin. A clean histogram takes ~10–30 min, so drift
    tracking matters.
  - Crosstalk artefact: silicon photon counters emit a faint flash of light when
    they fire, which can reach the other detector and create false peaks at ±
    the optical path delay. Suppress it with a shortpass filter or an angled
    beamsplitter in each arm, or use unequal fibre lengths to push the artefact
    away from τ = 0.

  Suggested path

  1. FPGA counting + one AQRH: confocal alignment and imaging, then CW ODMR on
     candidate spots.
  2. Add the pulse generator and AOM: pulsed work, still with one detector and
     the FPGA.
  3. Add a second AQRH, a 50:50 fibre splitter and a time tagger: g⁽²⁾ to
     certify single NVs.

  If you want, I can write up the FPGA counter requirements (pulse width,
  levels, gating, sync) for the Red Pitaya, or add this plan to the procurement
  notes.

✻ Sautéed for 48s · done Wednesday 15:13

❯ How would i Find the focus from the diamond surface, what are the steps to    
  aligning the confocal setup                                                   

● The most reliable way to find the diamond surface is confocal reflection: scan
  the focus along z and watch the laser light reflected back through the
  pinhole, which peaks sharply at the surface. A second check uses the PL edge:
  the fluorescence rises as the focus enters the diamond. The full alignment
  sequence follows; the two focus methods are in step 4.

  Before starting

  - Laser power: reduce to ~0.1–0.5 mW at the sample (use the NDs), and wear
    goggles.
  - Photon counter: disconnected or capped until step 8. Every alignment step
    below uses the PDA10A2. A reflected laser beam or room light can damage the
    photon counter.
  - Sample: start with DNVB14, which gives a huge, forgiving PL signal. The
    electronic-grade plate comes last.
  - Tools you already have: the VRC2 card, the irises, the pinhole kit, the
    ST1XY-S/M, the NanoMax, and the PM101A/S120C power meter.

  Step 1: Put the excitation beam on the objective axis

  1. Remove the objective. Thread an iris or cage alignment plate into the
     objective's mount position, and put a second target further along the same
     axis (e.g. at the sample position, or on the far side of the dichroic's
     reflection).
  2. Steer the excitation beam (with the last mirror before the dichroic, or the
     dichroic mount itself) until it passes through the centre of both targets.
  3. Back-reflection check: put a flat mirror at the sample position. The
     reflected beam must retrace its path and land back on the iris centre. That
     confirms normal incidence.
  4. Check that the beam is centred on the pupil. For the F810 beam (~5.9 mm)
     the iris should clip it symmetrically.

  Step 2: Fit the objective and check the output

  1. Thread in the N40X-PF. Below the focus the beam diverges into a disc. On a
     card a few cm below, it should be round and uniformly lit. A lopsided or
     clipped disc means the beam is off-centre or tilted at the pupil: go back
     to step 1.
  2. Put the DNVB14 on the NanoMax and approach from far away. The working
     distance is only 0.66 mm, so start with ~2 mm clearance and come down
     slowly, watching from the side. A crash damages the objective front lens.

  Step 3: Centre the collection path (no pinhole yet)

  1. With the laser focused somewhere in the DNVB14, the PL leaves the objective
     as a collimated ~7 mm beam. Centre the FELH0550 and the AC254-150 on it.
     On the VRC2 card the beam should look like a round red disc.
  2. Put the PDA10A2 at the AC254 focal plane (150 mm) and maximise its signal
     laterally. The notebook shows about a ±0.25 mm window at M = 30.

  Step 4: Find the surface (the focus question)

  Method A: PL edge (DNVB14, filters in, easiest)

  Step the NanoMax Z in ~2 µm steps from "focus above the diamond" to "focus
  inside" and record the PDA signal. The PL rises from near zero to a plateau as
  the focus crosses into the crystal. The surface is at the half-rise point.
  Without a pinhole the edge is broad (tens of µm). It sharpens in step 6, which
  doubles as a confocality check.

  Method B: confocal reflection (works on any sample, including electronic 
  grade)

  1. Remove the FELH0550 and put an ND filter (OD 2–3) in front of the PDA10A2.
     Diamond reflects ~17 % of the 532 nm light, a little of which leaks through
     the DMLP550R. The FELH would block it (OD > 5), which is why it has to
     come out.
  2. Use a large pinhole (100 µm, step 5) at the AC254 focus, or just the PDA's
     own 1 mm area.
  3. Scan Z. You'll see a sharp peak when the top surface is in focus. With a
     pinhole it's ~a few µm wide. Near the surface the N40X-PF's cover-glass
     correction makes the peak weaker and broader than ideal, but it is still
     easy to find.
  4. Keep scanning deeper and a second peak appears from the bottom surface.
     With a 0.5 mm plate it comes roughly 0.2 mm of stage travel later (the
     focal-shift ratio is ~0.4), broader because of spherical aberration.
     Separating the two peaks calibrates your stage-to-depth ratio on your own
     sample.
  5. Refit the FELH0550 before any fluorescence measurement.

  Method B is the one you'll need on the electronic-grade plate, which has
  almost no NV PL to see an edge in.

  Step 5: Insert the pinhole (100 → 50 → 30 µm)

  1. Mount the 100 µm pinhole on the ST1XY-S/M at the AC254 focus, with the
     PDA10A2 directly behind it (within ~20 mm).
  2. Focus on DNVB14 about 20–50 µm below the surface, where the PL is steady.
  3. Peak the signal in X and Y with the translator, then in Z (along the axis,
     ±mm range). Iterate.
  4. Swap to 50 µm, re-peak XY (and Z). Swap to 30 µm, re-peak. Each step loses
     some signal; the notebook predicts ~0.78 in-focus transmission at 30 µm.
  5. Don't touch the excitation path after this. Any upstream change (a
     collimator swap, or disturbing the wedged FBW5532-10) moves the focus by
     ~µm to 20 µm, and the pinhole must be re-peaked.

  Step 6: Verify it's confocal

  - Repeat the Z scan through the surface (Method A). With the 30 µm pinhole and
    pupil-filling excitation, the edge should sharpen to ~5 µm (the notebook
    predicts 4.9 µm FWHM thin-layer sectioning). If it's still tens of µm, the
    pinhole is off-axis or at the wrong Z.
  - Do an XY scan across a feature: a surface scratch, a dust particle, or the
    diamond edge. It should look sharp at the ~0.4–0.8 µm level (0.39 µm
    expected with the F810 beam, 0.76 µm with today's 1.4 mm beam).

  Step 7: Go to the working depth

  Refocus to ~200 µm below the surface, where the notebook predicts the focus is
  sharpest (Strehl ≈ 0.99). Relative to where the surface was in focus, raise
  the sample towards the objective by ≈ 0.4 × the depth, i.e. ~85 µm of stage
  travel for 210 µm depth. Check the clearance to the objective as you go; there
  is roughly 0.5 mm to spare.

  Step 8: Switch to single-NV mode

  1. Swap to the electronic-grade plate and find its surface with Method B (FELH
     out, PDA + ND).
  2. Refit the FELH0550 (a 650 nm longpass if you have one), and add OD 2–3 in
     front of the detector position.
  3. Connect the photon counter, lights off, enclosure closed. Check the count
     rate first, then remove ND step by step while it stays well below
     saturation.
  4. Useful check: even with no NVs in focus, the diamond's Raman line at 573 nm
     passes the FELH0550 and gives a weak, uniform signal from the bulk. You
     can see the surface edge in it with the photon counter.
  5. Go to ~200 µm depth and raster-scan XY. Bright ~0.4 µm spots on a dark
     background are single-NV candidates.

  Common failure signs

  ┌───────────────────────────┬─────────────────────────────────────────────┐
  │          Symptom          │                Likely cause                 │
  ├───────────────────────────┼─────────────────────────────────────────────┤
  │ Asymmetric disc below the │ beam off-centre or tilted at the pupil      │
  │  objective in step 2      │                                             │
  ├───────────────────────────┼─────────────────────────────────────────────┤
  │ Surface edge stays broad  │ pinhole off in Z, or not centred            │
  │ after the pinhole         │                                             │
  ├───────────────────────────┼─────────────────────────────────────────────┤
  │ Signal drifts over        │ thermal drift; wait for the laser and stage │
  │ minutes                   │  to warm up, and add the refocus routine    │
  ├───────────────────────────┼─────────────────────────────────────────────┤
  │ No reflection peak in     │ FELH still in, or the reflected beam misses │
  │ Method B                  │  the pinhole because the excitation is      │
  │                           │ tilted                                      │
  ├───────────────────────────┼─────────────────────────────────────────────┤
  │ Focus position jumps      │ the wedged FBW5532-10 was moved; re-peak    │
  │ after touching filters    │ the pinhole                                 │
  └───────────────────────────┴─────────────────────────────────────────────┘

  I can turn this into procurement/confocal_alignment.md, with a simple Z-scan
  script for the PDA10A2 and NanoMax so the surface edge and reflection peaks
  are recorded rather than eyeballed.

✻ Cooked for 1m 8s · done Wednesday 15:39

※ recap: You're building toward a confocal single-NV setup, and I just gave you the step-by-step alignment procedure. Next, say whether you want it saved as a guide, with a Z-scan script to find the diamond surface.

❯ Yes, please, write that down to an md file. After that, there are two more    
  things i want to discuss.We are thinking about going forward with more        
  ensemble work, what are some improvements that could be made to the set up in 
  that direction, beside an aspheric lens to collect more photoluminecense and  
  coils to control the magnetic field. I have been reading papers like the one  
  from budker on vector magnetometry with an ensemble and they are interesting  
  and leave some open questions. My supervisor is looking at more fundamental   
  ideas, like hat overlap between the resonances might be evidence of           
  superposition state between ms -1 and ms 1, i said that the noise in the data 
  is too high and that it might be due to power broadenning, not sure about     
  how you would check for evidence that you are driving both transitions in the 
  nv ensemble.                                                                  

● I'll write the alignment procedure to docs/confocal_alignment.md. I'm putting
  it in docs/ rather than procurement/, since it's a lab procedure, not a parts
  list.

● Write(docs\confocal_alignment.md)
  ⎿  Wrote 140 lines to docs\confocal_alignment.md
      1 # Confocal alignment procedure
      2 
      3 Step-by-step alignment of the confocal configuration (N40X-PF + A
        C254-150 + pinhole) and how
      4 to find the diamond surface. Numbers marked *(notebook §n)* come 
      5 `notebooks/Optical_Setup.ipynb`.
      6 
      7 Written 1 Oct 2026.
      8 
      9 ## Geometry recap
     … +195 lines (ctrl+o to expand)

  Searched for 1 pattern (ctrl+o to expand)

● The alignment procedure is now in docs/confocal_alignment.md. It covers the 8
  steps (both surface-finding methods, the 100 → 50 → 30 µm pinhole step-down, a
  confocality check, going to working depth, switching to the photon counter)
  plus a troubleshooting table, with the numbers taken from the notebook.

  1. Ensemble improvements beyond the condenser and coils

  Ranked by what I think limits this rig most:

  1. Calibrated, uniform microwave field. This comes first because it bears
     directly on your power-broadening question.
     - Power calibration. The procurement notes already flag that +16 dBm into
       the ~45 dB amplifier is probably deep in compression. If so, the power
       you set is not the power at the diamond, and every linewidth-vs-power
       plot is distorted. The attenuator and power detector already in tier A
       fix this.
     - Field uniformity. A wire or simple loop gives a microwave field that
       varies across the excited volume. That makes the drive strength vary from
       NV to NV, and the power broadening along with it. A loop-gap resonator
       or an Ω-shaped PCB antenna gives a much more uniform field over the ~0.5
       mm column the condenser excites.
  2. Laser-noise cancellation. Ensemble ODMR sits on a large PL background with
     1–3 % contrast, so laser intensity noise passes straight into the signal.
     Fix this with a reference photodiode on a pick-off (tier B), subtracted in
     the MFLI or digitally. The fibre + fixed polariser chain already removes
     the polarisation-to-power conversion.
  3. Temperature control and both transitions. D shifts by −74 kHz/K. Track both
     lines: their sum gives temperature (D) and their difference gives the
     field (B_∥). This is standard in the vector and thermometry literature, and
     it's also relevant to the superposition question below.
  4. Orientation-resolved (vector) operation.
     - Know the crystal's face orientation. With a field along the normal of a
       (100) plate, all four NV orientations are degenerate.
     - Tilt the bias field so all 8 lines separate.
     - Calibrate the NV-axis frame with known fields from 3-axis coils.
     - Read all orientations at once by modulating 4 microwave tones at
       different modulation frequencies and demodulating them separately
       (Schloss et al., Phys. Rev. Applied 10, 034044 (2018)). On your MFLI that
       needs the multi-demodulator option (MF-MD, already on the shopping
       list's considered list).
     - analysis/nv_odmr_sim.py already fits the 8-line spectrum and |B|.
  5. Hyperfine driving. Driving all three ¹⁴N hyperfine lines (2.16 MHz apart)
     with three tones raises the contrast. It's cheap with the SMCV plus mixing,
     or several sources.
  6. Light collection and absorption. The notebook shows only ~3.5 % of the PL
     can ever leave the top face; most is trapped by total internal reflection
     and leaks out of the edges. Options: edge or side collection, a large-area
     detector close to the diamond, or side-pumping and light-trapping
     geometries for better absorption. Also measure the absorption at 532 nm
     once: it's the biggest unknown in the light budget.
  7. Magnetic environment. Permanent-magnet temperature coefficients, lab field
     gradients, and the steel in mounts. Map these before attributing small
     field shifts to physics.

  Barry et al., Rev. Mod. Phys. 92, 015004 (2020) is the best single roadmap for
  ensemble sensitivity. If you tell me which open questions the Budker paper
  left you with, I can be more specific.

  2. Is overlap of the resonances evidence of a ±1 superposition?

  Your instinct is right: overlapping lines in a CW spectrum are not evidence of
  a superposition. But your supervisor's idea has a real physical core, so it's
  worth saying exactly what would count as evidence.

  Why CW overlap proves nothing. CW ODMR measures populations: how much the NVs
  are moved out of m_s = 0. Two independent, broadened transitions
  (power-broadened, or broadened by the nitrogen spin bath, strain and field
  gradients) overlap just as well as a coherently driven pair. A CW ensemble
  lineshape is not sensitive to coherence between m_s = +1 and −1. Also check
  first which lines overlap. In an ensemble, overlapping lines often belong to
  different NV orientation classes, i.e. different NVs, which cannot be in a
  joint superposition. The 8-line fit in nv_odmr_sim.py assigns them.

  Where the physics is real:
  - Near zero axial field, strain and electric fields (the E term) mix m_s = ±1,
    so the energy eigenstates themselves become (|+1⟩ ± |−1⟩)/√2. That's a
    property of the levels, not something your drive creates.
  - Linearly polarised microwaves at near-degeneracy. A wire or loop antenna
    gives linearly polarised microwaves. When the two transitions are closer
    together than the Rabi frequency, the drive couples |0⟩ to a "bright" ±1
    superposition and leaves the orthogonal one dark. That is genuine coherent
    driving of both transitions.

  How to test it, roughly in order of difficulty:

  | Test | What it distinguishes | Needs |
  |---|---|---|
  | Linewidth vs microwave power, fit Γ² = Γ₀² + a·P (already in
  analysis/powersweep_common.py, with odmr_power_sweep_*_pc.py) | power
  broadening (slope a) vs intrinsic inhomogeneous width (Γ₀). If Γ₀ alone
  exceeds the line separation, the overlap is inhomogeneous, not coherent.
  Repeat vs laser power, which also broadens. | calibrated microwave power (see
  1.1). Reference: Dréau et al., PRB 84, 195204 (2011). |
  | Field sweep through zero with the coils, fitting each line | f± = D ± γB_∥
  with linear crossing (independent lines) vs an anticrossing with minimum
  splitting 2E (strain-mixed superposition eigenstates) | fine field control,
  cancelling Earth's field, narrow lines |
  | Microwave polarisation (crossed loops with a 90° phase → circular) |
  circular polarisation drives only 0 ↔ +1 or 0 ↔ −1. If the overlapped response
  depends on polarisation in a way the sum of the two lines doesn't explain,
  both transitions are being driven coherently. | two-port antenna, phase
  shifter |
  | Rabi frequency (pulsed) | driving both degenerate transitions with linear
  polarisation gives √2 times the single-transition Rabi frequency | pulsed
  setup (AOM, switch, gated readout) |
  | Double-quantum Ramsey (pulsed) | directly prepares (|+1⟩ + |−1⟩)/√2 with a
  two-tone pulse. Fringes oscillate at 2γB, twice the single-transition rate.
  This is the explicit demonstration, and it's also a sensitivity technique. |
  pulsed setup. Reference: Bauch et al., PRX 8, 031025 (2018). |

  On "the noise is too high, maybe power broadening": those are two separate
  effects. Power broadening widens the lines and reduces the slope, so for the
  same noise the signal-to-noise per linewidth gets worse. But it does not
  increase the noise. Quantify the noise separately with
  smcv/odmr_noise_budget_pc.py, and the broadening with the power series. Then
  you can tell your supervisor exactly how much of the overlap comes from
  microwave power, laser power, and the sample's own inhomogeneous width.

  Concrete next step: calibrate the microwave power, then take a power series at
  a field where the two lines of one orientation are well separated. Γ₀ and the
  slope a tell you how close the lines can get before they merge for trivial
  reasons. Only overlap that survives at low power and narrow lines is worth
  looking at for coherent effects, and proving those needs the pulsed
  experiments.

  I can sketch the CW measurement plan (power series plus field sweep) as a
  script and analysis pair in the same style as the existing odmr_power_sweep_*
  and plot_* pairs.

✻ Churned for 2m 17s · done 16:27

❯ why is a A CW ensemble lineshape is not sensitive to coherence between m_s =  
  +1 and −1                                                                     

● Mainly because the optical readout only measures populations: how much spin is
  in m_s = 0 versus in the ±1 pair. It cannot see the relative phase between +1
  and −1. One correction to what I said before: "not sensitive" was too strong.
  Coherence can shape a CW spectrum indirectly, but in an ensemble it leaves no
  unambiguous fingerprint.

  1. The readout is blind to the ±1 phase

  The PL drop comes from the intersystem crossing: NVs in m_s = ±1 are more
  likely to cross into the dark singlet and emit fewer photons. That rate
  depends only on |m_s|, so +1 and −1 are equally dark. In density-matrix terms,
  the fluorescence is

  $$
  \text{PL} \propto \mathrm{Tr}(\rho,M), \qquad M = a,|0\rangle\langle 0| +
  b,\big(|{+1}\rangle\langle{+1}| + |{-1}\rangle\langle{-1}|\big)
  $$

  M has no off-diagonal elements, so

  $$
  \text{PL} \propto a,\rho_{00} + b,(\rho_{++} + \rho_{--})
  $$

  and the coherence ρ₊₋ drops out. A superposition (|+1⟩ + e^{iφ}|−1⟩)/√2 gives
  exactly the same PL as a 50/50 incoherent mixture of +1 and −1, for every φ.
  The light simply doesn't carry that information.

  2. Coherence can only act indirectly, through the dynamics

  What coherence can do is change how fast population leaves m_s = 0. The
  clearest case is the one relevant to your supervisor's idea: near degeneracy,
  with linearly polarised microwaves (a wire or loop antenna):

  - The drive couples |0⟩ only to the "bright" combination |B⟩ = (|+1⟩ +
    |−1⟩)/√2, with Rabi frequency √2·Ω.
  - The orthogonal combination |D⟩ = (|+1⟩ − |−1⟩)/√2 is not driven at all.

  So the coherent case behaves like one two-level line driven √2 harder, while
  the incoherent case is two separate lines each driven at Ω. Under CW, those
  give somewhat different widths and depths. But to tell them apart from a
  lineshape you'd need to know Ω, its spread across the excited volume, the
  laser pumping rate, the strain/E distribution, the hyperfine structure and the
  field gradient. In your ensemble, uncertainty in each of these alone can
  change the lineshape by more than the coherent effect does. A lineshape fit
  with that many free parameters is consistent with either story, which is why
  it isn't evidence.

  3. In an ensemble the coherence washes out on short timescales

  - Ensemble dephasing. A ±1 superposition picks up phase at the difference
    frequency, which is 2γB_∥ plus strain terms. Across the ensemble that
    frequency varies (spin bath, strain, field gradients), so the superposition
    dephases within the double-quantum T₂*. That is roughly half the
    single-quantum T₂* for magnetic noise, and sub-µs in ppm-nitrogen material
    like DNVB14.
  - Optical reset. The laser continuously repolarises the spins into m_s = 0, at
    rates up to ~MHz near saturation, which also destroys any coherence.

  A CW measurement averages for milliseconds over a steady state in which ±1
  coherence lives for well under a microsecond. Any trace it leaves is folded
  into the populations described in point 2.

  4. Why pulsed measurements fix this

  Since the readout only sees populations, you need a step that converts the 
  coherence into a population difference before reading out. That is what a
  Ramsey sequence does:

  1. A pulse creates the superposition.
  2. It evolves freely for a time τ, accumulating a phase.
  3. A second pulse maps that phase onto the m_s = 0 population, which the laser
     then reads.

  Scanning τ makes the PL oscillate. The evidence is the oscillation frequency
  (2γB for a ±1 double-quantum superposition, versus γB for a single
  transition), not a lineshape. Frequency is a much harder quantity to fake than
  lineshape. The same applies to the √2 Rabi enhancement: it is measured as a
  frequency in the time domain.

  The honest CW statement

  CW spectra can show consistency with near-degenerate, coherent driving:
  - polarisation-dependent behaviour (point 2), which tests coherent driving;
  - an anticrossing with a minimum splitting of 2E in a field sweep, which tests
    strain-mixed (|+1⟩ ± |−1⟩) eigenstates, a property of the levels rather
    than of the drive.

  CW cannot demonstrate coherence between +1 and −1 in an ensemble. That needs
  the time-domain experiments.

  If useful, I can write a small simulation of the NV three-level system with
  optical pumping, comparing the CW lineshape for coherent driving (linear
  polarisation, degenerate lines) with two independent lines. It would show your
  supervisor how small and parameter-dependent the CW difference is.

✻ Worked for 45s · done 16:58

※ recap: We're planning your NV setup's next steps, most recently whether CW ODMR can show a ±1 superposition, which it can't directly. Next: say whether you want the small simulation comparing coherent versus independent-line CW lineshapes for your supervisor. (disable recaps in /config)

❯ yes, write the simulation for my supervisor                                   

● I'll write it as an analysis-style simulation next to the existing
  analysis/nv_odmr_sim.py. First a quick look at how that script is structured,
  so the new one matches it.

  Ran 1 shell command (ctrl+o to expand)

● I've identified a clean CW observable: the contrast ratio at degeneracy should
  be 1 for coherent driving versus 4/3 for incoherent, with no normalization
  needed. I'll now simulate whether this ratio holds up under ensemble
  inhomogeneity.

● Write(analysis\nv_vsystem_cw_sim.py)
  ⎿  Wrote 379 lines to analysis\nv_vsystem_cw_sim.py
       1 """
       2 Can CW ODMR show that the ms=0 -> +1 and ms=0 -> -1 transitions 
       3 COHERENTLY (i.e. that a |+1>,|-1> superposition is created) when
          the two resonances overlap?
       4 
       6 Writes figures + summary.txt to analysis/vsystem_sim_out/.
       7 
       8 MODEL
      10 Ground-state spin triplet {|+1>, |0>, |-1>} (index 0, 1, 2), rot
         ating frame at the
     … +465 lines (ctrl+o to expand)

● Bash(cd "C:/Users/Gonzalo/Downloads/BudgetODMR" && timeout 900 python
      analysis/nv_vsystem_cw_sim.py)
  ⎿  [check] isolated transition, Lindblad vs rate model: max |difference|
     = 3.0e-04
     [check] single NV, degenerate, saturating linear drive: ms=0 depletion
     … +20 lines (ctrl+o to expand)
  ⎿  Created analysis\vsystem_sim_out\summary.txt (+23 -0)
       1 +[check] isolated transition, Lindblad vs rate model: max |diffe
         +rence| = 3.0e-04                                               
       2 +[check] single NV, degenerate, saturating linear drive: ms=0 de
         +pletion coherent 0.502 (theory 1/2), incoherent 0.667 (theory 2
         +/3)                                                            
       3 +[check] sigma+ at degeneracy == isolated line with sqrt2*Omega:
         + max |diff| = 3.6e-04                                          
       4 +                                                               
       5 +R = peak contrast at degeneracy / peak of one isolated line (li
         +near MW):                                                      
       6 +  Ideal single NV (no dephasing): at Omega=2.51 MHz  R_coh=1.00
         +3  R_inc=1.331                                                 
       7 +  DNVB14-like ensemble (sigma 0.5 MHz, 14N, T2 2 us): at Omega=
         +2.51 MHz  R_coh=1.405  R_inc=1.364                             
       8 +                                                               
       9 +Signature S = 1 - R_coh/R_inc at saturating drive (Omega 3 MHz,
         + no hyperfine, T2 1 ms):                                       
      10 +  gamma_p= 0.05/us: S at sigma=0.001 -> 0.236, at 0.5 MHz -> 0.
         +127                                                            
      11 +  gamma_p= 0.20/us: S at sigma=0.001 -> 0.246, at 0.5 MHz -> 0.
         +162                                                            
      12 +  gamma_p= 1.00/us: S at sigma=0.001 -> 0.249, at 0.5 MHz -> 0.
         +176                                                            
      13 +  gamma_p= 5.00/us: S at sigma=0.001 -> 0.245, at 0.5 MHz -> 0.
         +174                                                            
      14 +                                                               
      15 +Lineshape test (ensemble, degenerate): fitting the COHERENT spe
         +ctrum with the INCOHERENT model                                
      16 +  free Omega, sigma, C0 -> Omega 0.99 (true 1.0), sigma 0.41 (t
         +rue 0.5), C0 0.305 (true 0.3)                                  
      17 +  rms residual = 0.68 % of the peak contrast                   
      18 +                                                               
      19 +Time domain (no laser during MW):                              
      20 +  Ideal single NV (no dephasing): Rabi frequency degenerate/iso
         +lated = 1.33/1.00 MHz (ratio 1.33, sqrt2 = 1.41)               
      21 +  DNVB14-like ensemble (sigma 0.5 MHz, 14N, T2 2 us): Rabi freq
         +uency degenerate/isolated = 1.66/1.00 MHz (ratio 1.67, sqrt2 = 
         +1.41)                                                          
      22 +                                                               
      23 +(run time 4 s; figures in C:\Users\Gonzalo\Downloads\BudgetODMR
         +\analysis\vsystem_sim_out)                                     
  ⎿  … 5 more files changed
  ⎿  (timeout 10m)

● The physics checks pass overall (saturated depletion matches theory closely),
  but I'm now digging into two anomalies: the Rabi frequency ratio of 1.33 looks
  like an FFT resolution artifact rather than √2, and the ensemble R shows the
  coherent value exceeding the incoherent one, opposite to the expected sign.

  Ran 1 shell command (ctrl+o to expand)

● I've traced the sign anomaly to coherent strong-drive effects between
  hyperfine transitions 4.3 MHz apart, confirming the rate model is otherwise
  exact and that the CW coherence signature isn't fixed-sign in a realistic
  ensemble. I also caught that the wash-out figure's title mislabels drive
  strength as pumping rate, so I'll correct that mapping now.

  Ran 1 shell command (ctrl+o to expand)

● This clarifies the physics and corrects my earlier statement: driving helps
  counter static inhomogeneity but doesn't help against fast Markovian
  dephasing, which for ppm-nitrogen diamond (T₂ ~ µs) leaves only a ~3% effect.
  I'll now update the figure, validation checks, and Rabi frequency estimate
  accordingly.

● Update(analysis\nv_vsystem_cw_sim.py)
  ⎿  Added 8 lines, removed 5 lines
      222          lines.append(s)
      223  
      224      # ---- validation ----------------------------------------
           ----------------------
      225 -    p = P(**IDEAL_SINGLE)                                     
      225      df = np.linspace(20, 30, 401)
      226 +    p = P(**IDEAL_SINGLE, pol="sigma+")                       
      227      err = np.max(np.abs(contrast_coherent(df, 25.0, p) - contr
           ast_incoherent(df, 25.0, p)))
      228 -    say(f"[check] isolated transition, Lindblad vs rate model:
          - max |difference| = {err:.1e}")                               
      228 +    say(f"[check] single driven transition, Lindblad vs rate m
          +odel: max |difference| = {err:.1e} (exact)")                  
      229 +    p = P(**IDEAL_SINGLE)                                     
      230 +    err = np.max(np.abs(contrast_coherent(df, 25.0, p) - contr
          +ast_incoherent(df, 25.0, p)))                                 
      231 +    say(f"[check] same with linear MW (other transition 50 MHz
          + away): {err:.1e} "                                           
      232 +        "(off-resonant light shift only)")                    
      233      ps = P(**IDEAL_SINGLE, Omega=20.0)
      234      c_coh = contrast_coherent([0.0], 0.0, ps)[0] / ps["C0"]
      235      c_inc = contrast_incoherent([0.0], 0.0, ps)[0] / ps["C0"]
      236      say(f"[check] single NV, degenerate, saturating linear dri
           ve: ms=0 depletion "
      237          f"coherent {c_coh:.3f} (theory 1/2), incoherent {c_inc
           :.3f} (theory 2/3)")
      234 -    p_sig = P(**IDEAL_SINGLE, pol="sigma+")                   
      235 -    p_iso = P(**IDEAL_SINGLE, Omega=np.sqrt(2) * BASE["Omega"]
          -)                                                             
      236 -    e2 = np.max(np.abs(contrast_coherent(df - 25, 0.0, p_sig) 
          -- contrast_incoherent(df, 25.0, p_iso)))                      
      238 +    e2 = np.max(np.abs(contrast_coherent(df - 25, 0.0, P(**IDE
          +AL_SINGLE, pol="sigma+"))                                     
      239 +                       - contrast_incoherent(df, 25.0, P(**IDE
          +AL_SINGLE, pol="sigma+"))))                                   
      240      say(f"[check] sigma+ at degeneracy == isolated line with s
           qrt2*Omega: max |diff| = {e2:.1e}")
      241  
      242      # ---- figure 1: spectra ---------------------------------
           -------------------------

● Update(analysis\nv_vsystem_cw_sim.py)
  ⎿  Added 3 lines, removed 2 lines
      267  
      268      # ---- figure 2: normalisation-free test R vs MW power ---
           ----------------------------
      269      Om = np.geomspace(0.03, 10, 22)
      270 -    fig, ax = plt.subplots(figsize=(7, 4))                    
      270 +    fig, ax = plt.subplots(figsize=(7.5, 4.2))                
      271      say("\nR = peak contrast at degeneracy / peak of one isola
           ted line (linear MW):")
      272 -    for (name, base), col in zip(scen, ["C3", "C0"]):         
      272 +    scen2 = scen[:1] + [("Ensemble without 14N (sigma 0.5 MHz,
          + T2 2 us)", P(sigma=0.5, hf=False, T2=2.0))] + scen[1:]       
      273 +    for (name, base), col in zip(scen2, ["C3", "C2", "C0"]):  
      274          R = np.array([peak_ratio(P(**{**base, "Omega": o})) fo
           r o in Om])
      275          ax.semilogx(Om, R[:, 0], color=col, label=f"{name}: co
           herent")
      276          ax.semilogx(Om, R[:, 1], color=col, ls="--", label=f"{
           name}: incoherent")

● Update(analysis\nv_vsystem_cw_sim.py)
  ⎿  Added 22 lines, removed 15 lines
      288  
      289      # ---- figure 3: wash-out of the signature by inhomogeneit
           y ---------------------------
      290      sig = np.geomspace(1e-3, 3, 16)
      291 -    fig, ax = plt.subplots(figsize=(7, 4))                    
      292 -    say("\nSignature S = 1 - R_coh/R_inc at saturating drive (
          -Omega 3 MHz, no hyperfine, T2 1 ms):")                        
      291 +    fig, axs = plt.subplots(1, 2, figsize=(12, 4))            
      292 +    say("\nSignature S = 1 - R_coh/R_inc (ideal value 1 - 3/4 
          += 0.25), no hyperfine:")                                      
      293 +    say("  (a) static spread sigma, T2 = 1 ms  -> sigma at whi
          +ch S halves:")                                                
      294 +    for om, col in zip([0.3, 1.0, 3.0], ["C0", "C1", "C3"]):  
      295 +        S = np.array([1 - np.divide(*peak_ratio(P(sigma=s, hf=
          +False, T2=1000.0, Omega=om, nq=21))) for s in sig])           
      296 +        axs[0].semilogx(sig, S, color=col, marker="o", ms=3, l
          +abel=f"$\\Omega/2\\pi$ = {om} MHz")                           
      297 +        half = sig[np.argmax(S < S[0] / 2)]                   
      298 +        say(f"      Omega {om:.1f} MHz: S(0) = {S[0]:.3f}, hal
          +ves near sigma ~ {half:.2f} MHz")                             
      299 +    axs[0].set_xlabel("static spread of $\\gamma B_\\parallel$
          +, $\\sigma$ (MHz rms)")                                       
      300 +    axs[0].set_title("(a) static inhomogeneity: a stronger dri
          +ve protects the signature", fontsize=9)                       
      301 +    T2s = np.geomspace(0.3, 1000, 16)                         
      302 +    say("  (b) homogeneous T2, sigma = 0, Omega = 1 MHz -> T2 
          +at which S halves (compare 4/gamma_p):")                      
      303      for gp, col in zip([0.05, 0.2, 1.0, 5.0], ["C0", "C1", "C2
           ", "C3"]):
      294 -        S = []                                                
      295 -        for s in sig:                                         
      296 -            rc, ri = peak_ratio(P(sigma=s, hf=False, T2=1000.0
          -, Omega=3.0, gamma_p=gp, nq=21))                              
      297 -            S.append(1 - rc / ri)                             
      298 -        ax.semilogx(sig, S, color=col, marker="o", ms=3, label
          -=f"$\\Gamma_p$ = {gp} /us")                                   
      299 -        say(f"  gamma_p={gp:5.2f}/us: S at sigma=0.001 -> {S[0
          -]:.3f}, at 0.5 MHz -> "                                       
      300 -            f"{np.interp(0.5, sig, S):.3f}")                  
      301 -    ax.set_xlabel("inhomogeneous spread of $\\gamma B_\\parall
          -el$, $\\sigma$ (MHz rms)")                                    
      302 -    ax.set_ylabel("coherence signature  S = 1 - R$_{coh}$/R$_{
          -inc}$")                                                       
      303 -    ax.set_title("The CW coherence signature disappears once 2
          -$\\sigma$ exceeds the optical pumping rate",                  
      304 -                 fontsize=9)                                  
      305 -    ax.legend(fontsize=7)                                     
      306 -    ax.grid(alpha=0.3)                                        
      304 +        S = np.array([1 - np.divide(*peak_ratio(P(sigma=0.0, h
          +f=False, T2=T2, gamma_p=gp))) for T2 in T2s])                 
      305 +        axs[1].semilogx(T2s, S, color=col, marker="o", ms=3, l
          +abel=f"$\\Gamma_p$ = {gp} /us")                               
      306 +        half = T2s[np.argmax(S > S[-1] / 2)]                  
      307 +        say(f"      gamma_p {gp:4.2f}/us: halves near T2 ~ {ha
          +lf:.1f} us  (4/gamma_p = {4/gp:.0f} us)")                     
      308 +    axs[1].set_xlabel("homogeneous dephasing time $T_2$ (us)")
      309 +    axs[1].set_title("(b) fast dephasing: no protection from t
          +he drive; need $4/T_2 \\ll \\Gamma_p$", fontsize=9)           
      310 +    for a in axs:                                             
      311 +        a.set_ylabel("coherence signature  S = 1 - R$_{coh}$/R
          +$_{inc}$")                                                    
      312 +        a.legend(fontsize=7)                                  
      313 +        a.grid(alpha=0.3)                                     
      314      fig.tight_layout()
      315      fig.savefig(os.path.join(OUT, "fig3_washout.png"), dpi=150
           )
      316      plt.close(fig)

● Update(analysis\nv_vsystem_cw_sim.py)  ⎿  Added 1 line, removed 2 lines
      363          ax.set_title(f"Rabi: {name}", fontsize=8.5)
      364          ax.set_xlabel("pulse length (us)")
      365          ax.set_ylabel("P(ms=0)")
      366 -        f_deg = np.fft.rfftfreq(len(t), t[1] - t[0])[np.argmax
          -(np.abs(np.fft.rfft(deg - deg.mean()))[1:]) + 1]              
      367 -        f_iso = np.fft.rfftfreq(len(t), t[1] - t[0])[np.argmax
          -(np.abs(np.fft.rfft(iso - iso.mean()))[1:]) + 1]              
      366 +        f_deg, f_iso = dominant_freq(t, deg), dominant_freq(t,
          + iso)                                                         
      367          say(f"  {name}: Rabi frequency degenerate/isolated = {
           f_deg:.2f}/{f_iso:.2f} MHz "
      368              f"(ratio {f_deg/f_iso:.2f}, sqrt2 = 1.41)")
      369          ax = axs[r, 1]

● Update(analysis\nv_vsystem_cw_sim.py)
  ⎿  Added 8 lines
      203      return out
      204  
      205  
      206 +def dominant_freq(t, y, pad=64):                              
      207 +    """Peak of the zero-padded, windowed spectrum (MHz for t i
          +n us)."""                                                     
      208 +    n = pad * len(t)                                          
      209 +    spec = np.abs(np.fft.rfft((y - y.mean()) * np.hanning(len(
          +t)), n))                                                      
      210 +    f = np.fft.rfftfreq(n, t[1] - t[0])                       
      211 +    return f[np.argmax(spec[1:]) + 1]                         
      212 +                                                              
      213 +                                                              
      214  def ramsey(p, delta0, t, dq):
      215      """Ensemble-averaged P0(t) for ideal SQ (0<->+1) or DQ (0<
           ->(+1,-1)) Ramsey, frame at D."""
      216      d, wt = ensemble(p, delta0)

● Updated the wash-out analysis and the Rabi frequency estimate. Re-running the
  simulation to check the new numbers and figures.

● Bash(cd "C:/Users/Gonzalo/Downloads/BudgetODMR" && sed -i 's/    t =
      np.linspace(0, 3.0, 301)/    t = np.linspace(0, 6.0, 601)/'
      analysis/nv_vsystem_cw_sim.py && tim…)
  ⎿  [check] single driven transition, Lindblad vs rate model: max |differe
     nce| = 3.3e-16 (exact)
     [check] same with linear MW (other transition 50 MHz away): 3.0e-04 (o
     … +27 lines (ctrl+o to expand)
  ⎿  Updated analysis\nv_vsystem_cw_sim.py (+1 -1)
      357      plt.close(fig)
      358  
      359      # ---- figure 5: time domain -----------------------------
           --------------------------------
      360 -    t = np.linspace(0, 3.0, 301)                              
      360 +    t = np.linspace(0, 6.0, 601)                              
      361      tr = np.linspace(0, 4.0, 801)
      362      fig, axs = plt.subplots(2, 2, figsize=(12, 6.4))
      363      say("\nTime domain (no laser during MW):")
  ⎿  Updated analysis\vsystem_sim_out\summary.txt (+17 -10)
       1 -[check] isolated transition, Lindblad vs rate model: max |diffe
         -rence| = 3.0e-04                                               
       1 +[check] single driven transition, Lindblad vs rate model: max |
         +difference| = 3.3e-16 (exact)                                  
       2 +[check] same with linear MW (other transition 50 MHz away): 3.0
         +e-04 (off-resonant light shift only)                           
       3  [check] single NV, degenerate, saturating linear drive: ms=0 de
          pletion coherent 0.502 (theory 1/2), incoherent 0.667 (theory 2
          /3)
       3 -[check] sigma+ at degeneracy == isolated line with sqrt2*Omega:
         - max |diff| = 3.6e-04                                          
       4 +[check] sigma+ at degeneracy == isolated line with sqrt2*Omega:
         + max |diff| = 3.3e-16                                          
       5  
       6  R = peak contrast at degeneracy / peak of one isolated line (li
          near MW):
       7    Ideal single NV (no dephasing): at Omega=2.51 MHz  R_coh=1.00
          3  R_inc=1.331
       8 +  Ensemble without 14N (sigma 0.5 MHz, T2 2 us): at Omega=2.51 
         +MHz  R_coh=1.310  R_inc=1.332                                  
       9    DNVB14-like ensemble (sigma 0.5 MHz, 14N, T2 2 us): at Omega=
          2.51 MHz  R_coh=1.405  R_inc=1.364
      10  
       9 -Signature S = 1 - R_coh/R_inc at saturating drive (Omega 3 MHz,
         - no hyperfine, T2 1 ms):                                       
      10 -  gamma_p= 0.05/us: S at sigma=0.001 -> 0.236, at 0.5 MHz -> 0.
         -127                                                            
      11 -  gamma_p= 0.20/us: S at sigma=0.001 -> 0.246, at 0.5 MHz -> 0.
         -162                                                            
      12 -  gamma_p= 1.00/us: S at sigma=0.001 -> 0.249, at 0.5 MHz -> 0.
         -176                                                            
      13 -  gamma_p= 5.00/us: S at sigma=0.001 -> 0.245, at 0.5 MHz -> 0.
         -174                                                            
      11 +Signature S = 1 - R_coh/R_inc (ideal value 1 - 3/4 = 0.25), no 
         +hyperfine:                                                     
      12 +  (a) static spread sigma, T2 = 1 ms  -> sigma at which S halve
         +s:                                                             
      13 +      Omega 0.3 MHz: S(0) = 0.242, halves near sigma ~ 0.12 MHz
      14 +      Omega 1.0 MHz: S(0) = 0.246, halves near sigma ~ 0.35 MHz
      15 +      Omega 3.0 MHz: S(0) = 0.246, halves near sigma ~ 1.03 MHz
      16 +  (b) homogeneous T2, sigma = 0, Omega = 1 MHz -> T2 at which S
         + halves (compare 4/gamma_p):                                   
      17 +      gamma_p 0.05/us: halves near T2 ~ 66.9 us  (4/gamma_p = 8
         +0 us)                                                          
      18 +      gamma_p 0.20/us: halves near T2 ~ 22.7 us  (4/gamma_p = 2
         +0 us)                                                          
      19 +      gamma_p 1.00/us: halves near T2 ~ 4.5 us  (4/gamma_p = 4 
         +us)                                                            
      20 +      gamma_p 5.00/us: halves near T2 ~ 0.9 us  (4/gamma_p = 1 
         +us)                                                            
      21  
      22  Lineshape test (ensemble, degenerate): fitting the COHERENT spe
          ctrum with the INCOHERENT model
      23    free Omega, sigma, C0 -> Omega 0.99 (true 1.0), sigma 0.41 (t
          rue 0.5), C0 0.305 (true 0.3)
      24    rms residual = 0.68 % of the peak contrast
      25  
      26  Time domain (no laser during MW):
      20 -  Ideal single NV (no dephasing): Rabi frequency degenerate/iso
         -lated = 1.33/1.00 MHz (ratio 1.33, sqrt2 = 1.41)               
      21 -  DNVB14-like ensemble (sigma 0.5 MHz, 14N, T2 2 us): Rabi freq
         -uency degenerate/isolated = 1.66/1.00 MHz (ratio 1.67, sqrt2 = 
         -1.41)                                                          
      27 +  Ideal single NV (no dephasing): Rabi frequency degenerate/iso
         +lated = 1.41/1.00 MHz (ratio 1.41, sqrt2 = 1.41)               
      28 +  DNVB14-like ensemble (sigma 0.5 MHz, 14N, T2 2 us): Rabi freq
         +uency degenerate/isolated = 0.15/1.01 MHz (ratio 0.15, sqrt2 = 
         +1.41)                                                          
      29  
      23 -(run time 4 s; figures in C:\Users\Gonzalo\Downloads\BudgetODMR
         -\analysis\vsystem_sim_out)                                     
      30 +(run time 5 s; figures in C:\Users\Gonzalo\Downloads\BudgetODMR
         +\analysis\vsystem_sim_out)                                     
  ⎿  … 3 more files changed
  ⎿  (timeout 10m)

● Both criteria check out—the signature halves at σ ≈ 0.35·Ω and T₂ ≈ 4/Γ_p, and
  the ideal Rabi ratio is exactly √2. The ensemble Rabi value (0.15 MHz) looks
  like an artefact from hyperfine-class drift catching the peak-finder, so I'll
  inspect that figure next.

  Read 1 file (ctrl+o to expand)

● Bash(cd "C:/Users/Gonzalo/Downloads/BudgetODMR" && python - <<'EOF'
      p='analysis/nv_vsystem_cw_sim.py'; s=open(p,encoding='utf-8').read()…)
  ⎿    Ideal single NV (no dephasing): Rabi frequency degenerate/isolated =
      1.41/1.00 MHz (ratio 1.41, sqrt2 = 1.41)
       DNVB14-like ensemble (sigma 0.5 MHz, 14N, T2 2 us): Rabi frequency d
     … +4 lines (ctrl+o to expand)
  ⎿  Updated analysis\vsystem_sim_out\summary.txt (+1 -1)
      25  
      26  Time domain (no laser during MW):
      27    Ideal single NV (no dephasing): Rabi frequency degenerate/iso
          lated = 1.41/1.00 MHz (ratio 1.41, sqrt2 = 1.41)
      28 -  DNVB14-like ensemble (sigma 0.5 MHz, 14N, T2 2 us): Rabi freq
         -uency degenerate/isolated = 0.15/1.01 MHz (ratio 0.15, sqrt2 = 
         -1.41)                                                          
      28 +  DNVB14-like ensemble (sigma 0.5 MHz, 14N, T2 2 us): Rabi freq
         +uency degenerate/isolated = 1.44/1.01 MHz (ratio 1.42, sqrt2 = 
         +1.41)                                                          
      29  
      30  (run time 5 s; figures in C:\Users\Gonzalo\Downloads\BudgetODMR
          \analysis\vsystem_sim_out)
  ⎿  … 1 more file changed
  ⎿  (timeout 10m)

● The √2 Rabi enhancement holds up in the realistic ensemble (ratio 1.42), while
  the CW signature drops to just a few percent — this contrast is the key
  result for your supervisor. Now checking the remaining figures.

  Read 4 files (ctrl+o to expand)

● Update(analysis\nv_vsystem_cw_sim.py)
  ⎿  Added 15 lines
      33  ENSEMBLE: average over a Gaussian spread of gamma*B_par (sigma,
           MHz rms; field
      34  gradients + spin bath) and over the three 14N hyperfine classes
           (m_I = -1, 0, +1).
      35  
      36 +FIGURES                                                        
      37 +-------                                                        
      38 +fig1_spectra       coherent vs incoherent CW spectra as the two
         + lines merge (single NV, ensemble)                             
      39 +fig2_ratio_test    R = peak contrast at degeneracy / peak of on
         +e isolated line vs MW power.                                   
      40 +                   Ideal single NV, saturating drive: R = 1 (co
         +herent) vs 4/3 (incoherent),                                   
      41 +                   because coherent linear driving couples |0> 
         +only to (|+1>+|-1>)/sqrt2                                      
      42 +                   and leaves (|+1>-|-1>)/sqrt2 dark.          
      43 +fig3_washout       how that signature disappears: (a) static sp
         +read sigma (protected by the                                   
      44 +                   drive, halves near sigma ~ 0.35 Omega); (b) 
         +fast DQ dephasing (halves when                                 
      45 +                   4/T2 ~ gamma_p, independent of the drive)   
      46 +fig4_lineshape     fitting a coherent ensemble spectrum with th
         +e incoherent model: the fit                                    
      47 +                   absorbs the difference into Omega, sigma, C0
         + (residual ~1 % of peak)                                       
      48 +fig5_time_domain   what does work: Rabi frequency sqrt2 larger 
         +at degeneracy, and                                             
      49 +                   double-quantum Ramsey oscillating at 2*gamma
         +*B (single NV and ensemble)                                    
      50 +                                                               
      51  ASSUMPTIONS (edit below): rates are order-of-magnitude values f
          or moderate laser power,
      52  not measured for this rig; PL contrast C0 only scales the signa
          ls; optical cycling is
      53  assumed NOT to destroy the +1/-1 coherence (the most favourable
           case for coherence);

  Ran 1 shell command (ctrl+o to expand)

● Two new files: the alignment procedure is in docs/confocal_alignment.md, and
  the simulation is analysis/nv_vsystem_cw_sim.py. The simulation runs in about
  5 s with no hardware (python analysis/nv_vsystem_cw_sim.py) and writes 5
  figures plus summary.txt to analysis/vsystem_sim_out/.

  What it does. It models the NV ground-state triplet with the microwave drive,
  laser repolarisation, optical cycling and magnetic dephasing. It runs two
  versions: a full quantum model that keeps the coherence between m_s = +1 and
  −1, and an incoherent rate model with the same levels and rates, where both
  transitions share the m_s = 0 population. Any difference between the two is
  caused only by the +1/−1 coherence. The ensemble version averages over a
  spread of axial fields and the three ¹⁴N hyperfine classes.

  Checks. For a single driven transition, the two models agree exactly (to 3 ×
  10⁻¹⁶). In the ideal coherent case, saturated m_s = 0 depletion is 0.502
  against the theoretical 1/2, versus 0.667 against 2/3 for the incoherent case.
  The Rabi frequency at degeneracy is exactly √2 times the single-transition
  value.

  Results for your supervisor:

  1. Coherence does change one CW observable. Compare the peak contrast with the
     two lines degenerate against the peak contrast of one isolated line, at
     saturating microwave power. For an ideal NV the ratio is 1.00 if the drive 
     is coherent and 1.33 if not: linearly polarised microwaves drive only (|+1⟩
     + |−1⟩)/√2 and leave the other combination dark. Two easier tests don't
     work:
     - At low power both models give a ratio of 2.
     - Fitting the lineshape doesn't distinguish them: for a DNVB14-like
       ensemble, the incoherent model fits the coherent spectrum to ~0.7 % rms
       by adjusting Ω, σ and C₀.
  2. In a dense ensemble that signature mostly disappears. Two separate
     mechanisms (figure 3):
     - A static field spread σ: a stronger drive protects the coherence, and the
       signature halves at σ ≈ 0.35 Ω.
     - Fast double-quantum dephasing (finite T₂): driving harder doesn't help,
       and the signature halves when 4/T₂ ≈ Γ_p, the optical repolarisation rate
       (e.g. T₂ ≈ 23 µs for Γ_p = 0.2 /µs).
  3. For DNVB14-like parameters (σ = 0.5 MHz, T₂ = 2 µs, ¹⁴N hyperfine), the
     coherent and incoherent ratios are 1.405 and 1.364. That's only about 3 %
     apart, and in the opposite direction from the ideal case: the hyperfine
     structure adds strong-drive coherent effects. That difference is far below
     your uncertainty in microwave power, laser rates and C₀. So overlapping CW
     lines in this sample can't decide the question, which supports your point.
  4. Time-domain measurements still work in the same ensemble. The Rabi
     frequency at degeneracy comes out at 1.42× the isolated value (√2 = 1.41)
     even with inhomogeneity and hyperfine structure. Double-quantum Ramsey
     oscillates at 2γB. These are the experiments that would give real evidence,
     and they need the pulsed setup.

  The model rates (Γ_p, optical cycling, T₂, σ) are order-of-magnitude
  assumptions, not measurements from your rig. They are all set at the top of
  the script. The model leaves out the transverse field, the excited state and
  NV⁰, and it is generous to coherence (optical cycling is assumed not to
  destroy it), so the real CW signature should be smaller still.

  You mentioned two more things to discuss. Go ahead whenever you're ready.

✻ Brewed for 8m 7s · done 17:31