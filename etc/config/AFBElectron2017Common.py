#############################################################
########## samples definition  - preparing the samples
#############################################################
### samples are defined in etc/inputs/tnpSampleDef.py
### not: you can setup another sampleDef File in inputs
import etc.inputs.tnpSampleDef as tnpSamples
samplesDef = {
    'data'   : tnpSamples.AFB['data2017'].clone(),
    'mcNom'  : tnpSamples.AFB['mg2017'].clone(),
    'mcAlt'  : tnpSamples.AFB['amc2017'].clone(),
    'tagSel' : tnpSamples.AFB['mg2017'].clone(),
}

## some sample-based cuts... general cuts defined here after                           
## require mcTruth on MC DY samples and additional cuts                                
## all the samples MUST have different names (i.e. sample.name must be different for all)
## if you need to use 2 times the same sample, then rename the second one
#samplesDef['data'  ].set_cut('run >= 273726')
if not samplesDef['mcNom' ] is None: samplesDef['mcNom' ].set_mcTruth()      
if not samplesDef['mcAlt' ] is None: samplesDef['mcAlt' ].set_mcTruth()
if not samplesDef['tagSel'] is None: samplesDef['tagSel'].set_mcTruth()                  
if not samplesDef['tagSel'] is None:
    samplesDef['tagSel'].rename('mcAltSel_'+samplesDef['tagSel'].name)
    samplesDef['tagSel'].set_cut('tag_Ele_pt > 37')                                                                            
                                                 
## set MC weight, simple way (use tree weight)
weightName = 'totWeight'
if not samplesDef['mcNom' ] is None: samplesDef['mcNom' ].set_weight(weightName)
if not samplesDef['mcAlt' ] is None: samplesDef['mcAlt' ].set_weight(weightName)
if not samplesDef['tagSel'] is None: samplesDef['tagSel'].set_weight(weightName)
