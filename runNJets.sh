#!/bin/bash

export VO_CMS_SW_DIR=/cvmfs/cms.cern.ch
export COIN_FULL_INDIRECT_RENDERING=1
echo $VO_CMS_SW_DIR
source $VO_CMS_SW_DIR/cmsset_default.sh
export SCRAM_ARCH=slc6_amd64_gcc493
tar xzf CMSSW_8_0_18_patch1.tar.gz
cd CMSSW_8_0_18_patch1/src
scram b ProjectRename
eval `scramv1 runtime -sh`
cd -

python nJetsEstimate_LPC.py $1 $2

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
done < nJetsVars.list


#for i in "${!VarList[@]}"
#do
#  var=${VarList[$i]}
#  for j in "${!ProdList[@]}"
#  do
#    prod=${ProdList[$j]}
#    for k in "${!RegionList[@]}"
#    do
#      xrdcp "${var}_${prod}_${k}_$1_$2" root://cmseos.fnal.gov//store/user/stata/nJets/${var}_${prod}_${k}/bkg$1/$2
#    done
#  done
#done
#%s_%s_%i_bkg%i_%s"%(var,numProduct,regionIndex,j,file)