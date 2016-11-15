from ROOT import *
from array import array
import sys
import math
import itertools
import pprint
from multiprocessing import Process, Queue
from operator import mul
import os

# arguments:
# arg[1] = background added histo index
# arg[2] = indivdual file to run on

# preliminary stuff
colors = [kGreen+4,kGreen+2,kGreen,kYellow,kRed+2,kRed,kRed-4,kMagenta+2,kMagenta,kBlue+3,kBlue,kBlue-4,kBlack,kGray+3,kGray+1,kWhite]

gStyle.SetOptStat(0)

VarList = []
LowBoundList = []
UpBoundList = []
NBinsList = []

regionList = []

numProductList = []

denomProduct = "BASICCALOJETS1"
fileDir = "root://cmseos.fnal.gov//store/user/stata/AnalysisTrees/addedHistos/"
allTreesDir = "root://cmseos.fnal.gov//store/user/stata/AnalysisTrees/"

sampleList = []
filesBkg = []
xsecs = []

varFileName = "nJetsVars.list"
varFile = open(varFileName)
parseMode = "null"
for line in varFile.readlines():
  if line[0] == '#': continue
  line = line[0:-1]
  if parseMode == "null":
    newMode = line.partition('<')[-1].rpartition('>')[0]
    if newMode in ["VARS","REGIONS","NUM_PRODUCTS","DENOM_PRODUCT","BKG_FILES","FILE_DIR"]:
      parseMode = newMode
      continue
    elif newMode == "":
      continue
    else:
      sys.exit(newMode + " is not a valid parameter in variable file: " + varFileName)
  elif line == "<END>":
      parseMode = "null"
      continue
  
  if parseMode == "VARS":
    splitLine = line.split(" ")
    VarList.append(splitLine[0])
    LowBoundList.append(float(splitLine[1]))
    UpBoundList.append(float(splitLine[2]))
    NBinsList.append(int(splitLine[3]))
  elif parseMode == "REGIONS":
    regionList.append(line)
  elif parseMode == "NUM_PRODUCTS":
    numProductList.append(line)
  elif parseMode == "DENOM_PRODUCT":
    denomProduct = line
  elif parseMode == "BKG_FILES":
    splitLine = line.split(" ")
    sample = str(splitLine[0])
    if "root://cmseos.fnal.gov" in fileDir:
      fileList = os.popen("xrdfs root://cmseos.fnal.gov/ ls %s | grep %s"%(fileDir.split("root://cmseos.fnal.gov/")[-1],sample)).read().split("\n")[:-1]
    else:
      fileList = os.popen("ls %s | grep %s"%(fileDir,sample)).read().split("\n")[:-1]
    
    #print sample
    #print fileList
    sampleList.append(sample)
    filesBkg.append(fileList)
    xsecs.append(reduce(mul,[float(i) for i in splitLine[1].split("*")],1))
  elif parseMode == "FILE_DIR":
    fileDir = line

#Set deltaRmode to true if we want to parameterize 2D efficiencies in terms of deltaR
#NOTE: the code is sometimes  modified to parameterize with nGoodVertices instead
deltaRmode = True

#Set singleEffMode to true if we want the total effiency not parameterized.
#If this option is true, the first variable in the varFile will not have plots associated to it. That variable is used as a proxy to generate the plot
#if deltaRmode == True && singleEffMode == true then we get the efficiency as a function of only deltaR instead of a 2D parameterization with the first variable 
singleEffMode = False
if singleEffMode:
  LowBoundList[0] = -1000000000
  UpBoundList[0] = 1000000000
  NBinsList[0] = 1
  

# not used in main(), called in createNJets.sh
def makeEffiPlot(i,n,r):
  print "variable:\t " + str(i)
  print "tagProd:\t " + str(n)
  print "regions:\t " + str(r)
  
  var = VarList[i]
  numProduct = numProductList[n]
  region = regionList[r]
  
  if not deltaRmode:
    numDistrTotal = TH1F("num_%s_%s_%i"%(var,numProduct,r),"num_%s_%s_%i"%(var,numProduct,r),NBinsList[i],LowBoundList[i],UpBoundList[i])
    denomDistrTotal = TH1F("denom_%s_%s_%i"%(var,numProduct,r),"denom_%s_%s_%i"%(var,numProduct,r),NBinsList[i],LowBoundList[i],UpBoundList[i])
  else:
    numDistrTotal = TH2F("DELTAR_num_%s_%s_%i"%(var,numProduct,r),"DELTAR_num_%s_%s_%i"%(var,numProduct,r),NBinsList[i],LowBoundList[i],UpBoundList[i],8,0,4)
    denomDistrTotal = TH2F("DELTAR_denom_%s_%s_%i"%(var,numProduct,r),"DELTAR_denom_%s_%s_%i"%(var,numProduct,r),NBinsList[i],LowBoundList[i],UpBoundList[i],8,0,4)

  processes = []
  queues = []
  
  for j in range(0,len(sampleList)):
    queues.append(Queue())
    processes.append(Process(target=makeNumDenom, args=(i,j,region,numProduct,queues[-1])))
    
  for p in processes:
    p.start()
    
  for p in processes:
    p.join()
  
  outfilename = "testEff_%s_%s_%i.pdf"%(var,numProduct,r)
  
  for j in range(0,len(sampleList)):
    canvas = TCanvas("testEff","",600 if not deltaRmode else 1200,600)
    canvas.Divide(1 if not deltaRmode else 2,1)
    pad = canvas.cd(1)
    
    sample = sampleList[j]
  
    numDistr = queues[j].get()
    denomDistr = queues[j].get()
    numDistrTotal.Add(numDistr)
    denomDistrTotal.Add(denomDistr)
    
    numDistr.SetTitle(sample)
    denomDistr.SetTitle(sample)
    
    # numDistr.GetYaxis().SetRangeUser(1e-8,1e4)
    # denomDistr.GetYaxis().SetRangeUser(1e-8,1e4)
    
    if not deltaRmode:
      pad.SetLogy()
      
      numDistr.SetLineColor(kRed)
      denomDistr.SetLineColor(kBlue)
      
      numDistr.SetLineWidth(1)
      denomDistr.SetLineWidth(1)
      
      numDistr.SetMarkerStyle(23)
      denomDistr.SetMarkerStyle(26)
      
      numDistr.Draw()
      denomDistr.Draw("same")
      
      legend = TLegend(0.8,0.8,0.98,0.98)
      legend.AddEntry(numDistr,"numerator","l")
      legend.AddEntry(denomDistr,"denominator","l")
      legend.Draw()
      
      latex = TLatex()
      latex.SetNDC()
      latex.SetTextFont(61)
      latex.SetTextSize(0.03)
      latex.DrawLatex(0.15,0.85,"Region: %s"%(region))
    else:
      numDistr.GetXaxis().SetTitle(var)
      numDistr.GetYaxis().SetTitle("DELTAR_SELF")
      denomDistr.GetXaxis().SetTitle(var)
      denomDistr.GetYaxis().SetTitle("DELTAR_SELF")
      
      pad.SetLogz(1)
      numDistr.Draw("colz")
      
      pad = canvas.cd(2)
      pad.SetLogz(1)
      denomDistr.Draw("colz")
    
    if j == 0: canvas.Print(outfilename+"(","pdf")
    elif j != len(sampleList)-1: canvas.Print(outfilename,"pdf")
    else: canvas.Print(outfilename+")","pdf")
    
    j+=1
    
  effi = numDistrTotal.Clone()
  effi.Divide(denomDistrTotal)
  effi.SetName("%seffi_%s_%s_%i"%("" if not deltaRmode else "DELTAR_", var,numProduct,r))
  effi.SetDirectory(0)
  
  effiFile = TFile.Open("root://cmseos.fnal.gov//store/user/kreis/displaced_bkg_pt-dr/nJets/effiFiles/effi_%s_%s_%i.root"%(var,numProduct,r),"RECREATE")
  effi.Write()
  numDistrTotal.Write()
  denomDistrTotal.Write()

# not used in main(), helper for makeEffiPlot()
def makeNumDenom(i,j,region,numProduct,queue):
  print "start: " + sampleList[j]
  var = VarList[i]
  
  for f in range(0,len(filesBkg[j])):
    inFile = fileDir + filesBkg[j][f].split('/')[-1]
    #print inFile
    ff = TFile.Open(inFile)
    treeR = ff.Get("treeR")
    treeR.SetWeight(1.0)
    if f == 0:
      nEvents = treeR.GetEntries()
    else:
      nEvents += treeR.GetEntries()      
    
    nSelected = treeR.Draw(">>elist", region, "entrylist", nEvents)
    
    if nSelected < 0:
      sys.exit("error selecting events with selection: " + region)
    
    elist = TEntryList(gDirectory.Get("elist"))
    treeR.SetEntryList(elist)
    
    if not deltaRmode:
      treeR.Draw("%s_%s>>num%i(%i,%f,%f)"%(var,numProduct,j,NBinsList[i],LowBoundList[i],UpBoundList[i]),"","goff")
      treeR.Draw("%s_%s>>den%i(%i,%f,%f)"%(var,denomProduct,j,NBinsList[i],LowBoundList[i],UpBoundList[i]),"","goff")
      hNum = TH1F(gDirectory.Get("num%i"%(j)))
      hDen = TH1F(gDirectory.Get("den%i"%(j)))
      hNum.SetDirectory(0)
      hDen.SetDirectory(0)
      if f == 0:
        numDistr = hNum
        denomDistr = hDen
      else:
        numDistr.Add(hNum)
        denomDistr.Add(hDen)
        
    else:
      treeR.Draw("BASICCALOJETS1DELTAR_%s:%s_%s>>num%i(%i,%f,%f,%i,%f,%f)"%(numProduct,var,numProduct,j,NBinsList[i],LowBoundList[i],UpBoundList[i],8,0,4),"","goff")
      treeR.Draw("SELFDELTAR_%s:%s_%s>>den%i(%i,%f,%f,%i,%f,%f)"%(denomProduct,var,denomProduct,j,NBinsList[i],LowBoundList[i],UpBoundList[i],8,0,4),"","goff")
      #treeR.Draw("NGOODVERTICES:%s_%s>>num%i(%i,%f,%f,%i,%f,%f)"%(var,numProduct,j,NBinsList[i],LowBoundList[i],UpBoundList[i],20,0,40),"","goff")
      #treeR.Draw("NGOODVERTICES:%s_%s>>den%i(%i,%f,%f,%i,%f,%f)"%(var,denomProduct,j,NBinsList[i],LowBoundList[i],UpBoundList[i],20,0,40),"","goff")
      hNum = TH2F(gDirectory.Get("num%i"%(j)))
      hDen = TH2F(gDirectory.Get("den%i"%(j)))
      hNum.SetDirectory(0)
      hDen.SetDirectory(0)
      if f == 0:
        numDistr = hNum
        denomDistr = hDen
      else:
        numDistr.Add(hNum)
        denomDistr.Add(hDen)
        
  numDistr.Sumw2()
  denomDistr.Sumw2()
  
  numDistr.Scale(xsecs[j]/nEvents)
  denomDistr.Scale(xsecs[j]/nEvents)
  
  numDistr.SetDirectory(0)
  denomDistr.SetDirectory(0)
  
  queue.put(numDistr)
  queue.put(denomDistr)

  print "done: " + sampleList[j]
  
# not used in main(), called in createNJets.sh
def effiWriteToPDF():
  outfilename = "Efficiencies.pdf"
  
  npage = 1
  
  for n in range(0,len(numProductList)):
    for i in range(0,len(VarList)):
    
      effPlots = []
      effRatios = []
      
      for r in range(0,len(regionList)):
        var = VarList[i]
        numProduct = numProductList[n]
        region = regionList[r]

        ff = TFile.Open("root://cmseos.fnal.gov//store/user/kreis/displaced_bkg_pt-dr/nJets/effiFiles/effi_%s_%s_%i.root"%(var,numProduct,r))

        if not deltaRmode:
          effiPlot = TH1F(ff.Get("effi_%s_%s_%i"%(var,numProduct,r)))
          numPlot = TH1F(ff.Get("num_%s_%s_%i"%(var,numProduct,r)))
          denomPlot = TH1F(ff.Get("denom_%s_%s_%i"%(var,numProduct,r)))
        else:
          effiPlot = TH2F(ff.Get("DELTAR_effi_%s_%s_%i"%(var,numProduct,r)))
          numPlot = TH2F(ff.Get("DELTAR_num_%s_%s_%i"%(var,numProduct,r)))
          denomPlot = TH2F(ff.Get("DELTAR_denom_%s_%s_%i"%(var,numProduct,r)))
          
        effiPlot.SetTitle("Eff %s"%(var))
        effiPlot.SetDirectory(0)
        effPlots.append(effiPlot)
        
        hTmp = effiPlot.Clone()
        if r != 0:
          hTmp.Divide(effRatios[0])
          hTmp.SetTitle("eff ratio %s"%(region))
        else:
          hTmp.SetTitle("Eff in %s"%(region))
        hTmp.SetDirectory(0)
        effRatios.append(hTmp)
        
        canvas = TCanvas("c%i%i%i"%(i,n,r),"",1600,600)
        canvas.Divide(2,1)
        
        # numPlot.GetYaxis().SetRangeUser(1e-5,1e4)
        # denomPlot.GetYaxis().SetRangeUser(1e-5,1e4)
        
        if not deltaRmode:
          numPlot.SetLineColor(kRed)
          denomPlot.SetLineColor(kBlue)
          
          numPlot.SetLineWidth(1)
          denomPlot.SetLineWidth(1)
          
          numPlot.SetMarkerStyle(23)
          denomPlot.SetMarkerStyle(26)
          pad = canvas.cd(1)
          
          effiPlot.Draw()
          
          latex = TLatex()
          latex.SetNDC()
          latex.SetTextFont(61)
          latex.SetTextSize(0.03)
          latex.DrawLatex(0.15,0.85,"Region: %s"%(region))
          latex.DrawLatex(0.15,0.80,"Product: %s"%(numProduct))
          
          pad = canvas.cd(2)
          pad.SetLogy()
          
          numPlot.Draw()
          denomPlot.Draw("same")
          
          legend = TLegend(0.8,0.8,0.98,0.98)
          legend.AddEntry(numPlot,"numerator","l")
          legend.AddEntry(denomPlot,"denominator","l")
          legend.Draw()
        else:
          for h in [effiPlot,numPlot,denomPlot]:
            h.GetXaxis().SetTitle(var)
            h.GetYaxis().SetTitle("DELTAR_BASICCALOJETS1")
            #h.GetYaxis().SetTitle("NGOODVERTICES")
            
          pad = canvas.cd(1)
          pad.SetRightMargin(0.15)
          if singleEffMode and i == 0:
            #pad.SetLogy()
            effiPlot.SetTitle("Eff wrt DR nearest")
            #effiPlot.SetTitle("Eff wrt NGOODVERTICES")
            effiPlot.ProjectionY().Draw("e1")
          else:
            # pad.SetLogz()
            effiPlot.Draw("colz")
            
          pad = canvas.cd(2)
          pad.Divide(1,2)
          
          subPad = pad.cd(1)
          # subPad.SetLogz()
          if singleEffMode and i == 0:
            numPlot.ProjectionY().Draw("e1")
          else:
            numPlot.Draw("colz")
          
          subPad = pad.cd(2)
          # subPad.SetLogz()
          if singleEffMode and i == 0:
            denomPlot.ProjectionY().Draw("e1")
          else:
            denomPlot.Draw("colz")  
          
          canvas.cd()
          latex = TLatex()
          latex.SetNDC()
          latex.SetTextFont(61)
          latex.SetTextSize(0.03)
          latex.DrawLatex(0.15,0.85,"Region: %s"%(region))
          latex.DrawLatex(0.15,0.80,"Product: %s"%(numProduct))
          
        if npage == 1:canvas.Print(outfilename+"(","pdf")
        else:canvas.Print(outfilename,"pdf")
        npage += 1
        
      latex = TLatex()
      latex.SetNDC()
      latex.SetTextFont(61)
      latex.SetTextSize(0.02)

      if not deltaRmode or (singleEffMode and i == 0):
        canRatio = TCanvas("cRat%i%i"%(i,n),"",800,400)
        canRatio.Divide(2,1)
        pad = canRatio.cd(1)
        effRatios[0].SetTitle("Eff %s"%(regionList[0]))
        if (deltaRmode and singleEffMode and i == 0): effRatios[0].ProjectionY().Draw()
        else: effRatios[0].Draw()
        
        pad = canRatio.cd(2)
        legend = TLegend(0.80,0.75,0.98,0.98)
        
        for x in range(1,len(effRatios)):
          h = effRatios[x].ProjectionY() if (deltaRmode and singleEffMode and i == 0) else effRatios[x]
          h.SetLineColor(colors[x])
          h.SetTitle("eff / eff " + regionList[0])
          legend.AddEntry(h,regionList[x],"lp")
          if x == 1: h.Draw()
          else: h.Draw("same")
          
        legend.Draw()
        
        canRatio.cd()
        latex.DrawLatex(0.1,0.8,VarList[i] if not (deltaRmode and singleEffMode and i == 0) else "DR nearest")
        latex.DrawLatex(0.1,0.85,numProductList[n])

      else:
        canRatio = TCanvas("cRat%i%i"%(i,n),"",400*len(regionList),1200)
        canRatio.Divide(len(regionList),3)
        
        hErrors = []
        
        maxEff = 0 #to put all eff plots on same scale
        for h in effPlots:
          for b in range(0,h.GetNcells()):
            if h.GetBinContent(b) > maxEff: maxEff = h.GetBinContent(b)
        
        for x in range(0,len(effRatios)):
          pad = canRatio.cd(x + 1)
          pad.SetRightMargin(0.2)
          effPlots[x].GetZaxis().SetRangeUser(0,maxEff)
          effPlots[x].Draw("colz")
        
          pad = canRatio.cd(len(regionList) + x + 1)
          pad.SetRightMargin(0.2)
          h = effRatios[x]
          hErrors.append(h.Clone())
          if x != 0:
            h.GetZaxis().SetRangeUser(0,5)
            # pad.SetLogz()
          h.Draw("colz")
          
          pad = canRatio.cd(2*len(regionList) + x + 1)
          pad.SetRightMargin(0.2)
          # h.Draw("colz")
          
          hError = hErrors[x]
          for b in range(0,h.GetNcells()):
            if x == 0:
              hError.SetBinContent(b,h.GetBinError(b))
            else:
              hError.SetBinContent(b,(h.GetBinContent(b)-1)/(h.GetBinError(b)) if h.GetBinError(b) != 0 else 0)
              hError.SetTitle("(ratio - 1)/(error of ratio)")
          
          if x != 0: hError.GetZaxis().SetRangeUser(-5,5)
          hError.SetTitle("Error: " + regionList[0] if x == 0 else "(ratio - 1)/(error of ratio)")
          hError.SetName(hError.GetTitle())
          hError.SetDirectory(0)
          hError.Draw("colz")
      
      if npage == 1:canRatio.Print(outfilename+"(","pdf")
      else:canRatio.Print(outfilename,"pdf")
      npage += 1
      
  canvas.Clear()
  canvas.Print(outfilename+")","pdf")
  
# not used in main(), called in prepareNJetsPlots.sh
def makeEstimateHistos():
  outfilename = "Estimates.pdf"
  npage = 1
  
  for i in range(0,len(VarList)):
    for r in range(0,len(regionList)):
      for n in range(0,len(numProductList)):
        var = VarList[i]
        numProduct = numProductList[n]
        region = regionList[r]

        allHistoFile = "yNJets/testDistr_%s_%s_%s.root"%(var,numProduct,r)
        
        ff = TFile.Open(allHistoFile)
        keys = ff.GetListOfKeys()
        
        estimateDists = []
        actualDists = []
        
        for k in keys:
          h = ff.Get(k.GetName())
          hname = " ".join(k.GetName().split(" ")[1:])

          if "Estimate:" in hname:
            estimateDists.append(h)
          elif "N" + numProduct in hname:
            actualDists.append(h)
          else:
            continue
            
          h.SetDirectory(0)

        canvas = TCanvas("c%i%i%i"%(i,n,r),"",1200,600)
        canvas.Divide(2,1)
        
        #sort alphabetically
        estimateDists.sort(key=lambda h: h.GetName(), reverse=False)
        actualDists.sort(key=lambda h: h.GetName(), reverse=False)
          
        nJetsDistr = TH1F("n tagged distr", "n tagged distr",10,0,10)
        hEstN = TH1F("estN_%s"%(var),"estN_%s"%(var),10,0,10)
       
        # nJetsDistr = THStack("n tagged distr", "")
        # hEstN = THStack("estN_%s"%(var), "")
        
        # legend = TLegend(0.60,0.3,0.98,0.98)
        
        # scaleAct = 0
        # scaleEst = 0
        
        # i=0
        # for h in actualDists:
          # h.SetFillColor(colors[i])
          # legend.AddEntry(h,h.GetName().split(" ")[0],"l")
          # scaleAct += h.Integral()
          # i+=1
        
        # i=0
        # for h in estimateDists:
          # h.SetFillColor(colors[i])
          # scaleEst += h.Integral()
          # i+=1 
        
        # scale stacks to unity
        # for h in actualDists:
          # h.Scale(1./scaleAct)
          # nJetsDistr.Add(h)
        
        # for h in estimateDists:
          # h.Scale(1./scaleEst)
          # hEstN.Add(h)
          
        for h in actualDists:
          nJetsDistr.Add(h)
          
        for h in estimateDists:
          hEstN.Add(h)
          
        #if nJetsDistr.Integral() > 0: nJetsDistr.Scale(1./nJetsDistr.Integral())#ben: removed
        #if hEstN.Integral() > 0: hEstN.Scale(1./hEstN.Integral())#ben: removed

        pad = canvas.cd(1)
        pad.SetLogy()
        
        # nJetsDistr.Draw()
        # hEstN.Draw("same")
        
        # pad = canvas.cd(2)
        # pad.SetLogy()
        
        # hEstN.Draw()
        # legend.Draw()

        if singleEffMode and i == 0:
          title = "Background Esimate using Total Ratio" if not deltaRmode else "Background estimate using deltaR"
        else:
          title = "Background Esimate using %s"%(var)
          
        nJetsDistr.SetTitle(title)
        hEstN.SetTitle(title)
        
        nJetsDistr.GetXaxis().SetTitle("N %s"%(numProduct))
        hEstN.GetXaxis().SetTitle("N %s"%(numProduct))
        
        ratioPlot = nJetsDistr.Clone()
        ratioPlot.Divide(hEstN)
        ratioPlot.SetTitle("actual / estimate")
        
        nJetsDistr.SetLineColor(kBlue)
        nJetsDistr.SetLineWidth(1)
        nJetsDistr.SetMarkerStyle(24)
        
        hEstN.SetLineColor(kRed)
        hEstN.SetLineWidth(1)
        hEstN.SetMarkerStyle(1)
        
        ratioPlot.SetLineColor(kGreen)
        ratioPlot.SetLineWidth(1)
        ratioPlot.SetMarkerStyle(25)
        ratioPlot.SetMinimum(0);
        ratioPlot.SetMaximum(3);

        legend = TLegend(0.80,0.75,0.98,0.98)
        legend.AddEntry(nJetsDistr,"actual distr.")
        legend.AddEntry(hEstN,"estimated")
        legend.Draw()
        
        nJetsDistr.Draw("e1")
        hEstN.Draw("same e1")
        legend.Draw()
        
        pad = canvas.cd(2)
        ratioPlot.Draw("e0")
        
        canvas.cd()
        
        latex = TLatex()
        latex.SetNDC()
        latex.SetTextFont(61)
        latex.SetTextSize(0.035)
        latex.DrawLatex(0.1,0.85,"Region: %s"%(region))
        latex.DrawLatex(0.1,0.75,"Product: %s"%(numProduct))

        if npage == 1:canvas.Print(outfilename+"(","pdf")
        else:canvas.Print(outfilename,"pdf")
        npage += 1
  
  canvas.Clear()
  canvas.Print(outfilename+")","pdf")
  
def makeSampleHistos():
  histos = dict()
  
  for r in range(0,len(regionList)):
    for i in range(0,len(VarList)):
      for n in range(0,len(numProductList)):
        var = VarList[i]
        numProduct = numProductList[n]
        region = regionList[r]

        allHistoFile = "yNJets/testDistr_%s_%s_%s.root"%(var,numProduct,r)

        ff = TFile.Open(allHistoFile)
        keys = ff.GetListOfKeys()
        
        for k in keys:
          h = ff.Get(k.GetName())

          keyName = k.GetName()
            
          sample = keyName.split(" ")[0]
          hname = " ".join(keyName.split(" ")[1:])
          
          h.SetTitle(hname)
          h.SetName(hname)
          h.SetDirectory(0)

          if sample not in histos.keys():
            histos[sample] = dict()
          if var not in histos[sample].keys():
            histos[sample][var] = dict()
          if numProduct not in histos[sample][var].keys():
            histos[sample][var][numProduct] = dict()
          if region not in histos[sample][var][numProduct].keys():
            histos[sample][var][numProduct][region] = dict()
          
          currDict = histos[sample][var][numProduct][region]
          
          if "Estimate:" in hname:
            h.SetLineColor(kRed)
            currDict["estimate"] = h
          elif hname == "N%s"%(numProduct):
            h.SetLineColor(kBlue)
            currDict["actual"] = h
          elif "_%s"%(denomProduct) in hname:
            currDict["denomDistr"] = h
          elif "_%s"%(numProduct) in hname:
            currDict["numDistr"] = h
            
        fEffi = TFile.Open("yNJets/effiFiles/effi_%s_%s_%s.root"%(var,numProduct,r))
        if not deltaRmode:
          hEffi = fEffi.Get("effi_%s_%s_%i"%(var,numProduct,r))
        else:
          hEffi = fEffi.Get("DELTAR_effi_%s_%s_%i"%(var,numProduct,r))
        hEffi.SetDirectory(0)
        
        for sample in histos.keys():
          histos[sample][var][numProduct][region]["effi"] = hEffi
            
  pprint.pprint(histos)
  for sample in histos.keys():
    outfilename = sample + ".pdf"
    npage = 1
    canvas = TCanvas("c%i%i%i"%(i,n,r),"",1200,1200)
    canvas.Divide(2,2)
    
    for i in range(0,len(VarList)):
      for r in range(0,len(regionList)):
        for n in range(0,len(numProductList)):
          var = VarList[i]
          numProduct = numProductList[n]
          region = regionList[r]
          
          currDict = histos[sample][var][numProduct][region]
          
          pad = canvas.cd(1)
          pad.SetLogy()
          legend = TLegend(0.8,0.8,0.98,0.98)
          legend.AddEntry(currDict["actual"],"actual","l")
          legend.AddEntry(currDict["estimate"],"estimate","l")
          currDict["actual"].Draw()
          currDict["estimate"].Draw("same")
          legend.Draw()
          
          pad = canvas.cd(2)
          if not deltaRmode: currDict["effi"].Draw()
          else: currDict["effi"].Draw("colz")
          
          pad = canvas.cd(3)
          if not deltaRmode: currDict["numDistr"].Draw()
          else: currDict["numDistr"].Draw("colz")
          
          pad = canvas.cd(4)
          if not deltaRmode: currDict["denomDistr"].Draw()
          else: currDict["denomDistr"].Draw("colz")
          
          canvas.cd()
          latex = TLatex()
          latex.SetNDC()
          latex.SetTextFont(61)
          latex.SetTextSize(0.035)
          latex.DrawLatex(0.2,0.5,"Region: %s"%(region))
        
          if npage == 1:canvas.Print(outfilename+"(","pdf")
          else:canvas.Print(outfilename,"pdf")
          npage += 1
          canvas.Clear()
          canvas.Divide(2,2)
    canvas.Print(outfilename+")","pdf")

    
    
    

#-----------------------------------------------------------------
#----------------------functions for main()-----------------------
#-----------------------------------------------------------------



# parse tree here
def parseTree(numProduct,regionIndex,i,j,file):
  sample = sampleList[j]
  region = regionList[regionIndex]
  var = VarList[i]
  nBinsEff = NBinsList[i]
  lowBoundEff = LowBoundList[i]
  upBoundEff = UpBoundList[i]
  inFile = allTreesDir + sample + "/" + file
  
  fEffi = TFile.Open("root://cmseos.fnal.gov//store/user/kreis/displaced_bkg_pt-dr/nJets/effiFiles/effi_%s_%s_%s.root"%(var,numProduct,regionIndex))
  if not deltaRmode:
    hEffi = fEffi.Get("effi_%s_%s_%i"%(var,numProduct,regionIndex))
  else:
    hEffi = fEffi.Get("DELTAR_effi_%s_%s_%i"%(var,numProduct,regionIndex))
  hEffi.SetDirectory(0)

  ff = TFile.Open(inFile)
  treeR = ff.Get("treeR")
  treeR.SetWeight(1.0)
  nEvents = treeR.GetEntries()
  nSelected = treeR.Draw(">>elist", region, "entrylist", nEvents)
  
  if nSelected < 0:
    sys.exit("error selecting events with selection: " + region)
  
  elist = TEntryList(gDirectory.Get("elist"))
  treeR.SetEntryList(elist)
  
  print "made entry list"

  if not deltaRmode:
    numDistr = TH1F("%s %s_%s"%(sample,var,numProduct),"%s %s_%s"%(sample,var,numProduct),nBinsEff,lowBoundEff,upBoundEff)
    denomDistr = TH1F("%s %s_%s"%(sample,var,denomProduct),"%s %s_%s"%(sample,var,denomProduct),nBinsEff,lowBoundEff,upBoundEff)
  else:
    numDistr = TH2F("%s %s_%s"%(sample,var,numProduct),"%s %s_%s"%(sample,var,numProduct),nBinsEff,lowBoundEff,upBoundEff,8,0,4)
    denomDistr = TH2F("%s %s_%s"%(sample,var,denomProduct),"%s %s_%s"%(sample,var,denomProduct),nBinsEff,lowBoundEff,upBoundEff,8,0,4)

  # hEffi = numDistr.Clone()
  # hEffi.Divide(denomDistr)
  # hEffi.SetName("%s Effi: %s"%(sample,var))
  
  nJetsBkg = TH1F("%s N%s"%(sample,numProduct),"%s N%s"%(sample,numProduct),10,0,10)
  
  hEstBkg = TH1F("estNbkg_%s"%(var),"estNbkg_%s"%(var),10,0,10)
  hEstBkg.SetName("%s Estimate: N%s %s"%(sample,numProduct,var))

  print "drew distributions"
  
  treeR.SetBranchStatus("*",0)
  for b in ["SELFDELTAR_%s"%(denomProduct),"BASICCALOJETS1DELTAR_%s"%(numProduct),"%s_%s"%(var,denomProduct),"%s_%s"%(var,numProduct),"NGOODVERTICES"]:
    treeR.SetBranchStatus(b,1)
  

  for event in range(0,elist.GetN()):
    n = elist.Next()
    treeR.GetEntry(n)
    
    vectVals = getattr(treeR,"%s_%s"%(var,denomProduct))
    taggedVals = getattr(treeR,"%s_%s"%(var,numProduct))
  
    if not deltaRmode:
      for x in vectVals: denomDistr.Fill(x)
      for x in taggedVals: numDistr.Fill(x)
    else:
      vectValsDeltaR   = getattr(treeR,"SELFDELTAR_%s"%(denomProduct))
      taggedValsDeltaR = getattr(treeR,"BASICCALOJETS1DELTAR_%s"%(numProduct))
      #vectValsDeltaR = list(treeR.NGOODVERTICES)
      #taggedValsDeltaR = list(treeR.NGOODVERTICES)
      
      #print statements for debugging
      #print "//////////////////////////////"
      #print "Event Number: " + str(n)
      #print "full val - " + str(len(vectVals)) 
      #print list(vectVals)
      #print "full deltaR - " + str(len(vectValsDeltaR)) 
      #print list(vectValsDeltaR)
      #print "--------------------"
      #print "tagged val - " + str(len(taggedVals)) 
      #print list(taggedVals)
      #print "tagged deltaR - " + str(len(taggedValsDeltaR)) 
      #print list(taggedValsDeltaR)
      
      # next two blocks commented out b/c NGOODVERTCIES

      #if len(taggedVals) == 1:
        #numDistr.Fill(taggedVals[0],0)
      #else:
        #for itr in range(0,len(taggedVals)):
          #numDistr.Fill(taggedVals[itr],taggedValsDeltaR[itr])
      for itr in range(0,len(taggedVals)):
        numDistr.Fill(taggedVals[itr],taggedValsDeltaR[0])

    
      #if len(vectVals) == 1:
        #denomDistr.Fill(vectVals[0],0)
      #else:
        #for itr in range(0,len(vectVals)):
          #denomDistr.Fill(vectVals[itr],vectValsDeltaR[itr])
      for itr in range(0,len(vectVals)):
        denomDistr.Fill(vectVals[itr],vectValsDeltaR[0])

    
    nTagged = len(taggedVals)
    nJetsBkg.Fill(nTagged)
    
    # if no jets. no error associated with this
    if len(vectVals) == 0:
      hEstBkg.Fill(0)
      continue
    
    # get vector of probabilities
    vectProb = []
    if not deltaRmode:
      for x in vectVals:
        vectProb.append(hEffi.GetBinContent(hEffi.FindBin(x)))
    else:
      for itr in range(0,len(vectVals)):
        vectProb.append(hEffi.GetBinContent(hEffi.FindBin(vectVals[itr],vectValsDeltaR[itr])))
        #vectProb.append(hEffi.GetBinContent(hEffi.FindBin(vectVals[itr],vectValsDeltaR[0]))) #NGOODVERTICES
       
    vectError = []
    if not deltaRmode:
      for x in vectVals:
        vectError.append(hEffi.GetBinError(hEffi.FindBin(x)))
    else:
      for itr in range(0,len(vectVals)):
        vectError.append(hEffi.GetBinError(hEffi.FindBin(vectVals[itr],vectValsDeltaR[itr])))
        #vectError.append(hEffi.GetBinError(hEffi.FindBin(vectVals[itr],vectValsDeltaR[0]))) #NGOODVERTICES

    for k in range(0,10):
      hEstBkg.Fill(k,binomialTerm(vectProb,k))
      newErr2 = hEstBkg.GetBinError(k) + errorTermSq(vectProb,vectError,k) # increment err^2, will sqrt total error at end
      hEstBkg.SetBinError(k,newErr2)
    
    
  numDistr.Sumw2()
  denomDistr.Sumw2()
  nJetsBkg.Sumw2()
  
  for k in range(0,10): # sqrt errors here
    hEstBkg.SetBinError(k,math.sqrt(hEstBkg.GetBinError(k)))
  
  # scale by number of total events in hadded files
  for f in range(0,len(filesBkg[j])):
    fTotal = TFile.Open(fileDir + filesBkg[j][f].split('/')[-1])
    treeRtotal = fTotal.Get("treeR")
    if f == 0:
      nEventsTotal = treeRtotal.GetEntries()
    else:
      nEventsTotal += treeRtotal.GetEntries()
  
  if nEventsTotal > 0:
    nJetsBkg.Scale(1./nEventsTotal)
    hEstBkg.Scale(1./nEventsTotal)
  
  hList = [nJetsBkg, hEstBkg, numDistr, denomDistr]
  for h in hList:
    h.SetDirectory(0)
    
  return hList  

def errorTermSq(probList,errorList,k):
  if len(probList) < k:
    return 0
  
  retval=0
  
  for n in range(0,len(probList)):
    derivative=0
    for combo in itertools.combinations(range(0,len(probList)),k):
      addTerm = 1
      for i in range(0,len(probList)):
        if i == n: 
          addTerm *= (1 if i in combo else -1)
        elif i in combo:
          addTerm*=probList[i]
        else:
          addTerm*=(1-probList[i])
          
      derivative+=addTerm
      
    retval+=math.pow(derivative*errorList[n],2)
    
  return retval

def binomialTerm(probList,k):
  if len(probList) < k:
    return 0
  
  retval=0
  for combo in itertools.combinations(range(0,len(probList)),k):
    addTerm=1
    for i in range(0,len(probList)):
      if i in combo:
        addTerm*=probList[i]
      else:
        addTerm*=(1-probList[i])
    retval+=addTerm
    
  return retval

def main():
  # ########################### #
  # BACKGROUND NJETS ESTIMATION #
  # ########################### #
  j = int(sys.argv[1])
  file = sys.argv[2]
  
  for regionIndex in range(0,len(regionList)):
    for i in range(0,len(VarList)):
      for n in range(0,len(numProductList)):
        numProduct = numProductList[n]
        var = VarList[i]

        #print sampleList[j]

        retHistos = parseTree(numProduct,regionIndex,i,j,file)

        nJetsBkg = retHistos[0]
        hEstBkg = retHistos[1]
        
        nJetsBkg.Scale(xsecs[j])
        hEstBkg.Scale(xsecs[j])
        
        testFile = TFile.Open("root://cmseos.fnal.gov//store/user/kreis/displaced_bkg_pt-dr/nJets/%s_%s_%i/bkg%i/%s"%(var,numProduct,regionIndex,j,file),"RECREATE")
        for h in retHistos: h.Write()

if __name__ == '__main__': main()
