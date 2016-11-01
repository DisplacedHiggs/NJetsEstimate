# NJetsEstimate
code for background estimate

NOTE: The code for the N Jets Estimation is designed to run on the LPC servers.

The general workflow for how this works is as follows.

  - STEP 1:
    - Set up relevant directories
    - Create efficiency plots as functions of the variables to use in the estimation
    
  - STEP 2:
    - Run the jobs on condor.
    - These run on all of the background analysis trees that are created before hadd'ing, then creates histograms that are hadded at the end.
      - So if the hadded TTJets samples were created from 200 TTJets files, run the estimation over all of these histograms to create 200 files in eos, then add these all at the end to get the efficiencies. The adding is done at the end after this step.

  - STEP 3:
    - Scan condor every 10 minutes to see if the nJets jobs are done. If they're done, then go to step 4
    
  - STEP 4:
    - Add all of the output files, then print a pdf of the Estimates.
  
  
Here is a description of the different files used.

- nJetsVars.list
  - This is the main set up file consisting of many parts that are used across the different pieces of code
    If you comment out a line (i.e. put a '#' mark at the start of the line), it won't be read. Here are the components
    
    - VARS
      - This is where the different variables that we parameterize in terms of are defined. You can add multiple of these. Every variable will create efficiencies and estimates for this variable in all selection regions and tagged products
      - The format is for a line is:
        - Variable lowBound highBound nBins
      - So, the following line adds a PT parameterization binned from 0 -> 500 with 10 bins
        - PT 0.0 500.0 10
        
    - REGIONS
      - This is where the different selection regions are defined. These can be anything that can be interpreted by TTree::Draw
    
    - NUM_PRODUCTS
      - Different tagged products that are subsets of the untagged products. You can add multiple of these.
      
    - BKG_FILES
      - The different background processes that are used to create the background histogram. Also define cross sections here. There is are directories of analysis trees on eos (defined in nJetsEstimate_LPC.py) that contains information on where the files are.
      - The format for a line is:
        - Process xsection
      - So, the following line adds the WH_HToBB background at a cross-section of 1.369*0.577*0.324
        - WH_HToBB_WToLNu_M125_13TeV_amcatnloFXFX_madspin_pythia8 1.369*0.577*0.324
      - NOTE: the only algebraic operation supported for the cross section is multplication. So, 6.0 and 2.0*3.0 will both give cross sections of 6, but 3.0+3.0 will give undefined behavior or a crash.

    - DENOM_PRODUCT
      - The product that is used as the untagged product

- nJetsEstimate_LPC.py
  - The main piece of code for the project. The code to print the pdfs and run the actual estimation part.
  - Listed below are options that you can toggle to change the functionality
    - deltaRmode 
      - Set deltaRmode to true if we want to parameterize 2D efficiencies in terms of deltaR
      - #NOTE: currently the code is modified to parameterize with nGoodVertices instead
    - singleEffMode
      - Set singleEffMode to true if we want the total effiency not parameterized.
      - If this option is true, the first variable in the varFile will not have plots associated to it. That variable is used as a proxy to generate the plot
      - if deltaRmode == True && singleEffMode == true then we get the efficiency as a function of only deltaR instead of a 2D parameterization with the first variable
      
- bash createNJets.sh
  - This creates the set up to run the code contained in nJetsEstimate_LPC.py. This includes
    - creating the condor run-script runNJets.sh
    - setting up directories in eos to store all of the nJets information based on nJetsVars.list
      - NOTE: you will need to change filepaths in this file to set it up in your own directories
    - creating the plots of the efficiencies
    - creating a condor file submitNJets.condor
    - printing a pdf of the efficiencies

- condor_submit submitNJets.condor
  - submits job onto condor

- bash runNJets.sh
  - running the nJeta jobs. This is done on condor.

- bash scanNJets.sh
  - scans the condor queue every 10 minutes to check if nJets jobs are done. if they are, then go to prepareNJets.sh

- bash prepareNJets.sh
  - add the output files
  - print pdf of the estimates
