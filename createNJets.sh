#!/bin/bash

MAINDIR=`pwd`
SCRIPTDIR=`pwd`/scripts
LOGDIR=$MAINDIR/logs
CMSDIR=$CMSSW_BASE/src

source /cvmfs/cms.cern.ch/cmsset_default.sh
cd $CMSSW_BASE
eval `scramv1 runtime -sh`

cd $CMSSW_BASE/..
tar  --exclude-caches-all -czf ${MAINDIR}/${CMSSW_VERSION}.tar.gz ${CMSSW_VERSION}/
cd $MAINDIR
echo "done copying CMSSW"


condorFile=$SCRIPTDIR/submitNJets.condor
runScript=runNJets.sh

if [ -e $condorFile ]
then
    rm -rf $condorFile
fi  
touch $condorFile

echo "universe = vanilla" >> $condorFile
echo 'Requirements = OpSys == "LINUX" && (Arch != "DUMMY" )' >> $condorFile
echo "Executable = $runScript" >> $condorFile
echo "Should_Transfer_Files = YES" >> $condorFile
echo "request_disk = 10000000" >> $condorFile
echo "request_memory = 2100" >> $condorFile
echo "WhenTOTransferOutput  = ON_EXIT_OR_EVICT" >> $condorFile
echo "Notification=never" >> $condorFile
echo "notify_user = kreis@fnal.gov" >> $condorFile
echo 'x509userproxy = $ENV(X509_USER_PROXY)' >> $condorFile
echo "Transfer_Input_Files = nJetsVars.list, ${CMSSW_VERSION}.tar.gz, nJetsEstimate_LPC.py" >> $condorFile
echo "" >> $condorFile
echo "" >> $condorFile


varFile=nJetsVars.list

parseModeList=(
"VARS"
"REGIONS"
"NUM_PRODUCTS"
"BKG_FILES"
)

VarList=()
ProdList=()
RegionList=()
BkgFileList=()
nBkgFiles=-1

# this loop parses $varFile to get variables, products, and regions 
parseMode="null"
while read line
do
  #echo $parseMode - $line
  if [[ "${line:0:1}" == "#" ]];then
    continue
  fi 
  if [ "$parseMode" == "null" ];then
    newMode=`echo $line | awk '{split($1,array,"<"); split(array[2],array2,">"); print array2[1]}'`
    #echo "new mode: " $newMode
    if [[ ! "${line:0:1}" == "<" ]];then
      continue
    elif [[ ${parseModeList[*]} =~ "$newMode" ]];then
      parseMode=$newMode
      continue
    else
      :
      #echo $newMode " is not a valid parameter in variable file: " $varFile
    fi
  elif [ "$line" == "<END>" ];then
    #echo "end mode: " $parseMode
    parseMode="null"
    continue
  fi

  if [ "$parseMode" == "VARS" ];then
    base=`echo $line | awk '{split($1,array," "); print array[1]}'`  
    VarList+=("$base")
    #echo 'VarList+='$base
  elif [ "$parseMode" == "REGIONS" ];then
    RegionList+=("$line")
    #echo 'regionList+='$line
  elif [ "$parseMode" == "NUM_PRODUCTS" ];then
    ProdList+=("$line")
    #echo 'ProdList+='$line
  elif [ "$parseMode" == "BKG_FILES" ];then
    bkgFile=`echo $line | awk '{print $1}'`
    BkgFileList+=("$bkgFile")
    ((nBkgFiles++))
    #echo 'ProdList+='$line
  fi
done < $varFile


#paths on eos to store nJets data
eos root://cmseos.fnal.gov rm -r /store/user/kreis/displaced_bkg_pt-dr/nJets/
eos root://cmseos.fnal.gov mkdir -p /store/user/kreis/displaced_bkg_pt-dr/nJets/
eos root://cmseos.fnal.gov mkdir -p /store/user/kreis/displaced_bkg_pt-dr/nJets/effiFiles

#path where analysis trees are stored
allTreesDir=/store/user/stata/AnalysisTrees


#set up nJets directory and create efficiencies
for i in "${!VarList[@]}"
do
  var=${VarList[$i]}
  for j in "${!ProdList[@]}"
  do
    prod=${ProdList[$j]}
    for k in "${!RegionList[@]}"
    do
      region=${RegionList[$k]}
      eos root://cmseos.fnal.gov mkdir -p /store/user/kreis/displaced_bkg_pt-dr/nJets/${var}_${prod}_${k}
      python -c "from nJetsEstimate_LPC import makeEffiPlot; makeEffiPlot(${i},${j},${k})"
      for l in $(seq 0 $nBkgFiles)
      do
	bkgFile=${BkgFileList[$l]}
	echo $var
	echo $product
	echo $region
        echo $bkgFile
        eos root://cmseos.fnal.gov mkdir -p /store/user/kreis/displaced_bkg_pt-dr/nJets/${var}_${prod}_${k}/bkg${l}
      done
    done
  done
done

#make condor file
node=0
for l in $(seq 0 $nBkgFiles)
do
   sample=${BkgFileList[$l]}
   eos root://cmseos.fnal.gov/ ls ${allTreesDir}/${sample} >> tmp.tmp
   while read file
   do
     echo "output = $LOGDIR/\$(Cluster)_${node}_nJets_${sample}_${file}.out" >> $condorFile
     echo "error = $LOGDIR/\$(Cluster)_${node}_nJets_${sample}_${file}.err" >> $condorFile
     echo "log = $LOGDIR/\$(Cluster)_${node}_nJets_${sample}_${file}.log" >> $condorFile
     echo "arguments = $l $file" >> $condorFile
     echo "queue" >> $condorFile
     echo "" >> $condorFile
     ((node++))
  done < tmp.tmp
  rm tmp.tmp
done

# arguments in python script:
# arg[1] = background added histo index
# arg[2] = file to run on

#make pdf of efficiencies
python -c "from nJetsEstimate_LPC import effiWriteToPDF; effiWriteToPDF()"