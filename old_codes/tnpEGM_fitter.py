
### python specific import
import argparse
import os
import sys
import pickle
import shutil
import subprocess
import time
import ROOT as rt
import math

parser = argparse.ArgumentParser(description='tnp EGM fitter')
parser.add_argument('--checkBins'  , action='store_true'  , help = 'check  bining definition')
parser.add_argument('--createBins' , action='store_true'  , help = 'create bining definition')
parser.add_argument('--createHists', action='store_true'  , help = 'create histograms')
parser.add_argument('--doFit'      , action='store_true'  , help = 'fit sample (sample should be defined in settings.py)')
parser.add_argument('--select'   , action='store_true'  )
parser.add_argument('--doPlot'     , action='store_true'  , help = 'plotting')
parser.add_argument('--sumUp'      , action='store_true'  , help = 'sum up efficiencies')
parser.add_argument('--iBin'       , dest = 'binNumber'   , type = int,  default=-1, help='bin number (to refit individual bin)')
parser.add_argument('--flag'       , default = None       , help ='WP to test')
parser.add_argument('settings'     , default = None       , help = 'setting file [mandatory]')
parser.add_argument('--condor'     , action='store_true' )
parser.add_argument('-n','--njob'  , dest = 'njob'   , type = int,  default=1)
parser.add_argument('--ijob'       , dest = 'ijob'   , type = int,  default=0)
parser.add_argument('--fit', dest = 'fit'  , type = str, default='')
parser.add_argument('--subjob'     , action='store_true' )
parser.add_argument('--doDraw'     , action='store_true' )

args = parser.parse_args()

def condor_wait(condorjoblist):
    print 'wainting for condor jobs', condorjoblist
    finished=False
    firsttry=True
    while not finished:
        if firsttry:
            firsttry=False
        else:
            time.sleep(30)
        finished=True
        for jobid in condorjoblist:
            if not int(subprocess.check_output('condor_q '+str(jobid)+'|tail -n 1|awk \'{print $1}\'',shell=True).strip())==0:
                finished=False

def print_step(step):
    print '##############################################'
    print '########## '+step+' ##########################'
    print '##############################################'


print '===> settings %s <===' % args.settings
importSetting = 'import %s as tnpConf' % args.settings.replace('/','.').split('.py')[0]
print importSetting
exec(importSetting)

if args.fit == 'stdin':
    print 'inside'
    stdinlist=[]
    for line in sys.stdin:
        stdinlist.append(line)
    for sample in tnpConf.flags.values():
        sample.fitfunctions['stdin']=stdinlist
        print sample.fitfunctions
    sys.stdin.flush()

### tnp library
import libPython.binUtils  as tnpBiner
import libPython.rootUtils as tnpRoot


if not args.flag in tnpConf.flags.keys() and not args.flag is None:
    print '[tnpEGM_fitter] flag %s not found in flags definitions' % args.flag
    print '  --> define in settings first'
    print '  In settings I found flags: '
    print tnpConf.flags.keys()
    sys.exit(1)

####################################################################
##### Create (check) Bins
####################################################################
if args.checkBins:
    print_step('checkBins')
    for flag,sample in tnpConf.flags.items() if args.flag is None else [(args.flag,tnpConf.flags[args.flag])]:
        print '############'+flag+'#############'
        tnpBins = tnpBiner.createBins(tnpConf.biningDef,sample.eventexp)
        tnpBiner.tuneCuts( tnpBins, tnpConf.additionalCuts )
        for ib in range(len(tnpBins['bins'])):
            print tnpBins['bins'][ib]['name']
            print '  - cut: ',tnpBins['bins'][ib]['cut']
    sys.exit(0)

if args.createBins:
    print_step('createBins')
    for flag,sample in tnpConf.flags.items() if args.flag is None else [(args.flag,tnpConf.flags[args.flag])]:
        print '############'+flag+'#############'
        outputDirectory = '%s/%s/' % (tnpConf.baseOutDir,flag)
        os.makedirs( outputDirectory )
        tnpBins = tnpBiner.createBins(tnpConf.biningDef,sample.eventexp)
        tnpBiner.tuneCuts( tnpBins, tnpConf.additionalCuts )
        pickle.dump( tnpBins, open( '%s/bining.pkl'%(outputDirectory),'wb') )
        print 'created dir: %s ' % outputDirectory
        print 'bining created successfully... '


####################################################################
##### Create Histograms
####################################################################
if args.createHists:
    print_step('createHists')
    if args.condor:
        waiting_list={}
        for flag,sample in tnpConf.flags.items() if args.flag is None else [(args.flag,tnpConf.flags[args.flag])]:
            waiting_list[flag]=[]
            for i in range(args.njob):
                waiting_list[flag].append(subprocess.check_output('condor_submit ARGU="'+args.settings+' --createHists --flag '+flag+' --subjob --njob '+str(args.njob)+ ' --ijob '+str(i)+'" etc/scripts/condor.jds -queue 1|tail -n 1|awk \'{print $NF}\'|sed "s/[^0-9]//g"',shell=True).strip())
        for flag,sample in tnpConf.flags.items() if args.flag is None else [(args.flag,tnpConf.flags[args.flag])]:
            condor_wait(waiting_list[flag])
            histfile='%s/%s/%s_hist.root'%(tnpConf.baseOutDir,flag,flag)
            os.system('hadd -f '+histfile+' '+histfile+'.condortmp* && rm '+histfile+'.condortmp*')
    else:
        for flag,sample in tnpConf.flags.items() if args.flag is None else [(args.flag,tnpConf.flags[args.flag])]:
            import libPython.histUtils as tnpHist
            print 'creating histogram for flag '+flag
            histfile='%s/%s/%s_hist.root'%(tnpConf.baseOutDir,flag,flag)
            var = { 'name' : 'mass', 'nbins' : sample.mass_nbin, 'min' : sample.mass_min, 'max': sample.mass_max }
            tnpBins = pickle.load( open( '%s/%s/bining.pkl'%(tnpConf.baseOutDir,flag),'rb') )
            tnpHist.makePassFailHistograms( sample.paths, 'tpTree/fitter_tree', histfile+ ('.condortmp'+str(args.ijob) if args.subjob else ''),tnpConf.passcondition, tnpBins, var,None,args.njob,args.ijob)
            


####################################################################
##### Actual Fitter
####################################################################
if  args.doFit:
    print_step('doFit')
    if args.condor:
        waiting_list=[]
        for flag,sample in tnpConf.flags.items() if args.flag is None else [(args.flag,tnpConf.flags[args.flag])]:
            for ifit in sample.fitfunctions.keys() if args.fit=='' else [args.fit,]:
                fitfile='%s/%s/%s_fit_%s.root'%(tnpConf.baseOutDir,flag,flag,ifit)
                rootfile=rt.TFile(fitfile,"recreate")
                rootfile.Close()
                print 'submit ',flag, ifit
                waiting_list.append(subprocess.check_output('condor_submit ARGU="'+args.settings+' --doFit --flag '+flag+' --subjob --fit '+ifit+'" etc/scripts/condor.jds -queue 1|tail -n 1|awk \'{print $NF}\'|sed "s/[^0-9]//g"',shell=True).strip())
        condor_wait(waiting_list)
    else:
        for flag,sample in tnpConf.flags.items() if args.flag is None else [(args.flag,tnpConf.flags[args.flag])]:
            for ifit in sample.fitfunctions.keys() if args.fit=='' else [args.fit,]:
                tnpBins = pickle.load( open( '%s/%s/bining.pkl'%(tnpConf.baseOutDir,flag),'rb') )
                for ib in range(len(tnpBins['bins'])) if args.binNumber<0 else [args.binNumber,]:
                    histfile='%s/%s/%s_hist.root'%(tnpConf.baseOutDir,flag,flag)
                    fitfile='%s/%s/%s_fit_%s.root'%(tnpConf.baseOutDir,flag,flag,ifit)
                    tnpBins = pickle.load( open( '%s/%s/bining.pkl'%(tnpConf.baseOutDir,flag),'rb') )
                    tnpRoot.histFitter(histfile,fitfile,tnpBins['bins'][ib],sample.mass_min,sample.mass_max,sample.fitfunctions[ifit],args.doDraw)

####################################################################
##### select
####################################################################
if args.select:
    print_step('select')
    if args.condor:
        waiting_list=[]
        for flag,sample in tnpConf.flags.items() if args.flag is None else [(args.flag,tnpConf.flags[args.flag])]:
            waiting_list.append(subprocess.check_output('condor_submit ARGU="'+args.settings+' --select --flag '+flag+' --subjob" etc/scripts/condor.jds -queue 1|tail -n 1|awk \'{print $NF}\'|sed "s/[^0-9]//g"',shell=True).strip())
        condor_wait(waiting_list)
        for jobid in waiting_list: os.system('cat log/out.'+jobid)

    else:
        for flag,sample in tnpConf.flags.items() if args.flag is None else [(args.flag,tnpConf.flags[args.flag])]:
            print flag
            fitfile='%s/%s/%s_fit.root'%(tnpConf.baseOutDir,flag,flag)
            tnpBins = pickle.load( open( '%s/%s/bining.pkl'%(tnpConf.baseOutDir,flag),'rb') )
            rootfile=rt.TFile(fitfile.replace('.root','_best.root'),"recreate")
            rootfile.Close()
            report=open('%s/%s/report'%(tnpConf.baseOutDir,flag),'w')
            report.write('ibin\t\t'+'\t'.join(sample.fitfunctions.keys())+'\tbestfit\tbesteff\tbesterr\n')

        ####### Won added. If binbybin selection files exist, then Do Bin-by-Bin Selection ######################
            BBB = False
            if(os.path.exists("%s/%s/binbybin_selection"%(tnpConf.baseOutDir,flag))):
                BBB = True
                bins_bbb_needed = []
                bbb_fitfct = []
                bbb = open("%s/%s/binbybin_selection"%(tnpConf.baseOutDir,flag),'r')
                lines_bbb = bbb.readlines()
                bbb.close()
                for line in lines_bbb:
                    a = line.split("\t")
                    bins_bbb_needed.append(a[0])
                    bbb_fitfct.append(a[1].rstrip("\n"))
                print bins_bbb_needed
                print bbb_fitfct
            for ib in range(len(tnpBins['bins'])):
                report.write(str(ib)+'\t\t')
                bestfit = ''
                bestval = 0
                tempfit = ''
                tempval = 99999
                for ifit in sample.fitfunctions.keys() if args.fit=='' else [args.fit,]:
                    IsExpo = ifit.find('Expo') # Using Expo only has advantage at reducing systematic error, but in BBS using RooCMSshape can be effective too.
                    Isvpv = ifit.find('vpv')
                    if IsExpo == -1 and Isvpv != -1: ## If CMS and (not altsig), then continue
                        continue
                    centralval, centralerr = tnpRoot.GetEffi(fitfile.replace('.root','_'+ifit+'.root'),tnpBins['bins'][ib]['name'])
                    scorePass, scoreFail = tnpRoot.GetScorePassFail(fitfile.replace('.root','_'+ifit+'.root'),tnpBins['bins'][ib]['name'])
                    nBkgPass = tnpRoot.GetRooFitPar(fitfile.replace('.root','_'+ifit+'.root'),tnpBins['bins'][ib]['name']+'_resP','nBkgP')
                    nBkgFail = tnpRoot.GetRooFitPar(fitfile.replace('.root','_'+ifit+'.root'),tnpBins['bins'][ib]['name']+'_resF','nBkgF')
                    nSigFail = tnpRoot.GetRooFitPar(fitfile.replace('.root','_'+ifit+'.root'),tnpBins['bins'][ib]['name']+'_resF','nSigF')
                    thisval = nBkgPass + nBkgFail * centralval / (1.01 - centralval)
                    thistempval = scorePass+scoreFail
                    report.write('(%.4f, %.4f, %.1f)\t'%(centralval, centralerr, thistempval))
                    if thisval > bestval and scorePass < 4 and scoreFail < 4 and nSigFail > 15 and nBkgFail > 20 and nBkgPass > 20 : #Minimum Bkd criteria are tried (when they are 10, fit is bad) 
                        bestval = thisval
                        bestfit = ifit
                    if thistempval < tempval:
                        tempval = thistempval
                        tempfit = ifit
                if bestfit=='':
                    print tnpBins['bins'][ib]['name'],' fail to find good result, use second option'
                    bestfit=tempfit
 
                if BBB:
                    for b in range(len(bins_bbb_needed)):
                        if ib == int(bins_bbb_needed[b]):
                            bestfit = bbb_fitfct[b]
                            print tnpBins['bins'][ib]['name'],' Choose fitfunction by Bin-by-Bin Selection :', bestfit
                report.write(bestfit+'\t')
                besteff, besterr = tnpRoot.GetEffi(fitfile.replace('.root','_'+bestfit+'.root'),tnpBins['bins'][ib]['name'])
                report.write('%.4f\t%.4f\t\n'%(besteff, besterr))
                tnpRoot.MoveTObject(fitfile.replace('.root','_'+bestfit+'.root'),fitfile.replace('.root','_best.root'),tnpBins['bins'][ib]['name']+'_resP')
                tnpRoot.MoveTObject(fitfile.replace('.root','_'+bestfit+'.root'),fitfile.replace('.root','_best.root'),tnpBins['bins'][ib]['name']+'_resF')
                tnpRoot.MoveTObject(fitfile.replace('.root','_'+bestfit+'.root'),fitfile.replace('.root','_best.root'),tnpBins['bins'][ib]['name']+'_Canv')
            report.close()

        ##### Won added. To make 1D plots for each systematic studieds ( Maybe This plots are needed in approval presentations)
            resultfile = rt.TFile('%s/%s/result_stat.root'%(tnpConf.baseOutDir,flag), 'recreate')
            reports ='%s/%s/report'%(tnpConf.baseOutDir,flag)
            result_effihist = tnpRoot.GetEffiHist(reports, tnpBins, 'stat_per_syst')
            result_effihist.Write()
            for ib in range(result_effihist.GetXaxis().GetNbins()):
                result_effihist.ProjectionY('%s_abseta%.2fto%.2f'%(flag,result_effihist.GetXaxis().GetBinLowEdge(ib+1),result_effihist.GetXaxis().GetBinLowEdge(ib+2)),ib+1,ib+1).Write()
            for ib in range(result_effihist.GetYaxis().GetNbins()):
                result_effihist.ProjectionX('%s_pt%dto%d'%(flag,result_effihist.GetYaxis().GetBinLowEdge(ib+1),result_effihist.GetYaxis().GetBinLowEdge(ib+2)),ib+1,ib+1).Write()
            resultfile.Close()
            print '%s/%s/result_stat.root'%(tnpConf.baseOutDir,flag) + ' is saved'
     
####################################################################
##### dumping plots
####################################################################
if  args.doPlot:
    print_step('doPlot')
    if args.condor:
        waiting_list=[]
        for flag,sample in tnpConf.flags.items() if args.flag is None else [(args.flag,tnpConf.flags[args.flag])]:
            for ifit in ['best']+sample.fitfunctions.keys() if args.fit=='' else [args.fit,]:
                waiting_list.append(subprocess.check_output('condor_submit ARGU="'+args.settings+' --doPlot --flag '+flag+' --subjob --fit '+ifit+'" etc/scripts/condor.jds -queue 1|tail -n 1|awk \'{print $NF}\'|sed "s/[^0-9]//g"',shell=True).strip())
        condor_wait(waiting_list)
    else:
        for flag,sample in tnpConf.flags.items() if args.flag is None else [(args.flag,tnpConf.flags[args.flag])]:
            for ifit in ['best']+sample.fitfunctions.keys() if args.fit=='' else [args.fit,]:
                fitfile = '%s/%s/%s_fit_%s.root'%(tnpConf.baseOutDir,flag,flag,ifit)
                plottingDir = '%s/%s/plots/%s' % (tnpConf.baseOutDir,flag,ifit)
                tnpBins = pickle.load( open( '%s/%s/bining.pkl'%(tnpConf.baseOutDir,flag),'rb') )
                if not os.path.exists( plottingDir ):
                    os.makedirs( plottingDir )
                shutil.copy('etc/inputs/index.php.listPlots','%s/index.php' % plottingDir)
                for ib in range(len(tnpBins['bins'])) if args.binNumber<0 else [args.binNumber,]:
                    tnpRoot.histPlotter( fitfile, tnpBins['bins'][ib], plottingDir )

                print ' ===> Plots saved in <======='
                print plottingDir


####################################################################
##### dumping egamma txt file 
####################################################################
#tnpBins = pickle.load( open( '%s/bining.pkl'%(outputDirectory),'rb') )
#outputDirectory = '%s/%s/' % (tnpConf.baseOutDir,args.flag)
#flag.histFile='%s/%s_hist.root' % ( outputDirectory , args.flag )
#flag=tnpConf.flags[args.flag]
#flag.fitFile='%s/%s_fit.root' % ( outputDirectory,args.flag )
if args.sumUp:
    
    for centralflag,syss in tnpConf.systematicDef.items():
        effFileName ='%s/muonEffi_%s.txt' % (tnpConf.baseOutDir,centralflag)
        fOut = open( effFileName,'w')
        tnpBins = pickle.load( open( '%s/%s/bining.pkl'%(tnpConf.baseOutDir,centralflag),'rb') )
        erroravg_stat=[]  #### For printing average of errors on bottom line
        erroravg_sys=[]
        erroravg_total=[]
        f_central = open( '%s/%s/report' %(tnpConf.baseOutDir,centralflag),'r') #### For printing choices of fitfunctions
        f_altsig = open( '%s/%s_altsig/report' %(tnpConf.baseOutDir,centralflag),'r')
        lines_central = f_central.readlines()
        lines_altsig = f_altsig.readlines()
        f_central.close()
        f_altsig.close()
        for ib in range(len(tnpBins['bins'])):
            if ib == 0 :
                fOut.write('ibin\tCentral\tStaterr\tSysterr\tTotalerr  [MassRange]\t[MassBin]\t[TagIso]\t[AltSig]\tCentral\taltsig\n')
            line=[]
            line.append(str(ib))
            centralval,centralerr = tnpRoot.GetEffi( '%s/%s/%s_fit_best.root'%(tnpConf.baseOutDir,centralflag,centralflag),tnpBins['bins'][ib]['name'])
            line+=['%.4f '%centralval,'%.4f '%centralerr]
            erroravg_stat.append(centralerr)
            totalsys=0
            totalerr=0
            for sys in syss:
                maxdiff=0
                for flag in sys:
                    thisval,thiserr = tnpRoot.GetEffi('%s/%s/%s_fit_best.root'%(tnpConf.baseOutDir,flag,flag),tnpBins['bins'][ib]['name'])
                    diff=thisval-centralval
                    line.append('%+.4f'%diff)
                    if abs(maxdiff)<abs(diff): maxdiff=diff
                totalsys+=maxdiff*maxdiff
            totalerr+=(centralerr*centralerr+totalsys)
            line.insert(3,'%.4f'%math.sqrt(totalsys))
            line.insert(4,'%.4f'%math.sqrt(totalerr))
            erroravg_sys.append(math.sqrt(totalsys))
            erroravg_total.append(math.sqrt(totalerr))
            a=lines_central[ib+1].split("\t") #### Print chosen fitfunctions
            a2=lines_altsig[ib+1].split("\t")
            line.append(a[-4])
            line.append(a2[-4])
            fOut.write("\t".join(line)+"\n")

            if ib is len(tnpBins['bins'])-1:   #### Print average of errors
                line_last=['Average', 'error:']
                line_last+=['%.4f '%(sum(erroravg_stat)/len(erroravg_stat)),'%.4f '%(sum(erroravg_sys)/len(erroravg_sys)),'%.4f '%(sum(erroravg_total)/len(erroravg_total))]
                fOut.write("\t".join(line_last)+'\n')
        fOut.close()
        print 'Eff is saved in file : ',  effFileName

    fOut=rt.TFile('%s/result.root'%(tnpConf.baseOutDir),'recreate')
    effihists=[]
    for centralflag,syss in tnpConf.systematicDef.items():
        effFileName ='%s/muonEffi_%s.txt' % (tnpConf.baseOutDir,centralflag)
        tnpBins = pickle.load( open( '%s/%s/bining.pkl'%(tnpConf.baseOutDir,centralflag),'rb') )
        effihist=tnpRoot.GetEffiHist(effFileName,tnpBins)
        effihist.Write()
        for ib in range(effihist.GetXaxis().GetNbins()):
            effihist.ProjectionY('%s_eta%.2fto%.2f'%(centralflag,effihist.GetXaxis().GetBinLowEdge(ib+1),effihist.GetXaxis().GetBinLowEdge(ib+2)),ib+1,ib+1).Write()
        for ib in range(effihist.GetYaxis().GetNbins()):
            effihist.ProjectionX('%s_pt%dto%d'%(centralflag,effihist.GetYaxis().GetBinLowEdge(ib+1),effihist.GetYaxis().GetBinLowEdge(ib+2)),ib+1,ib+1).Write()
        effihists.append(effihist)
    
    if len(effihists)==2:
        sfhist=effihists[0].Clone()
        sfhist.Divide(effihists[1])
        sfhist.SetNameTitle('SF_eta_pt','SF_eta_pt')
        sfhist.Write()
    fOut.Close()
    print '%s/result.root'%(tnpConf.baseOutDir) + ' is saved'

##### Won added. To draw rootfiles only including Statistical error or Systematic error. #####
    fOut_stat=rt.TFile('%s/result_stat.root'%(tnpConf.baseOutDir),'recreate')
    effihists_stat=[]
    for centralflag,syss in tnpConf.systematicDef.items():
        effFileName ='%s/muonEffi_%s.txt' % (tnpConf.baseOutDir,centralflag)
        tnpBins = pickle.load( open( '%s/%s/bining.pkl'%(tnpConf.baseOutDir,centralflag),'rb') )
        effihist=tnpRoot.GetEffiHist(effFileName,tnpBins,"stat") ## Only Staterr
        effihist.Write()
        for ib in range(effihist.GetXaxis().GetNbins()):
            effihist.ProjectionY('%s_eta%.2fto%.2f'%(centralflag,effihist.GetXaxis().GetBinLowEdge(ib+1),effihist.GetXaxis().GetBinLowEdge(ib+2)),ib+1,ib+1).Write()
        for ib in range(effihist.GetYaxis().GetNbins()):
            effihist.ProjectionX('%s_pt%dto%d'%(centralflag,effihist.GetYaxis().GetBinLowEdge(ib+1),effihist.GetYaxis().GetBinLowEdge(ib+2)),ib+1,ib+1).Write()
        effihists_stat.append(effihist)

    if len(effihists_stat)==2:
        sfhist=effihists_stat[0].Clone()
        sfhist.Divide(effihists_stat[1])
        sfhist.SetNameTitle('SF_eta_pt','SF_eta_pt')
        sfhist.Write()
    fOut_stat.Close()
    print '%s/result_stat.root'%(tnpConf.baseOutDir) + ' is saved'

    fOut_syst=rt.TFile('%s/result_syst.root'%(tnpConf.baseOutDir),'recreate')
    effihists_syst=[]
    for centralflag,syss in tnpConf.systematicDef.items():
        effFileName ='%s/muonEffi_%s.txt' % (tnpConf.baseOutDir,centralflag)
        tnpBins = pickle.load( open( '%s/%s/bining.pkl'%(tnpConf.baseOutDir,centralflag),'rb') )
        effihist=tnpRoot.GetEffiHist(effFileName,tnpBins,"syst") ## Only Systerr
        effihist.Write()
        for ib in range(effihist.GetXaxis().GetNbins()):
            effihist.ProjectionY('%s_eta%.2fto%.2f'%(centralflag,effihist.GetXaxis().GetBinLowEdge(ib+1),effihist.GetXaxis().GetBinLowEdge(ib+2)),ib+1,ib+1).Write()
        for ib in range(effihist.GetYaxis().GetNbins()):
            effihist.ProjectionX('%s_pt%dto%d'%(centralflag,effihist.GetYaxis().GetBinLowEdge(ib+1),effihist.GetYaxis().GetBinLowEdge(ib+2)),ib+1,ib+1).Write()
        effihists_syst.append(effihist)

    if len(effihists_syst)==2:
        sfhist=effihists_syst[0].Clone()
        sfhist.Divide(effihists_syst[1])
        sfhist.SetNameTitle('SF_eta_pt','SF_eta_pt')
        sfhist.Write()
    fOut_syst.Close()
    print '%s/result_syst.root'%(tnpConf.baseOutDir) + ' is saved'

#    import libPython.EGammaID_scaleFactors as egm_sf
#    egm_sf.doEGM_SFs(effFileName,sampleToFit.lumi)


