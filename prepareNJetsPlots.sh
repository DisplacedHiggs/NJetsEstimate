#!/bin/bash

varFile=nJetsVars.list

parseModeList=(
"OUTDIR"
"INDIR_HADDED"
"INDIR_NOT_HADDED"
"VARS"
"REGIONS"
"NUM_PRODUCTS"
"BKG_FILES"
)

Outdir=""
Indir_Hadded=""
Indir_Not_Hadded=""
VarList=()
ProdList=()
RegionList=()
BkgFileList=()

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

  if [ "$parseMode" == "OUTDIR" ];then
      Outdir="$line"
      echo "Outdir: " ${Outdir}
  elif [ "$parseMode" == "INDIR_HADDED" ];then
      Indir_Hadded="$line"
      echo "Indir_Hadded: " ${Indir_Hadded}
  elif [ "$parseMode" == "INDIR_NOT_HADDED" ];then
      Indir_Not_Hadded="$line"
      echo "Indir_Not_Hadded: " ${Indir_Not_Hadded}
  elif [ "$parseMode" == "VARS" ];then
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

rm -rf yNJets
mkdir yNJets
##xrdcp -r root://cmseos.fnal.gov//store/user/"$Outdir"/nJets/ ./yNJets #ben: i don't think this works
#hack to split outdir into user and path from user (so we can use Alexx's script)
#right now set up assuming Outdir is in your eos user area.  I believe we can use "myuser" variable below as argument to movefiles otherwise
IFS=/ read myuser mypath <<< "$Outdir"
python movefiles.py T3_US_FNAL $mypath/nJets/ local $PWD/yNJets -r -p xrootd


for i in "${!VarList[@]}"
#for i in 0
do
  var=${VarList[$i]}
  for j in "${!ProdList[@]}"
  do
    prod=${ProdList[$j]}
    for k in "${!RegionList[@]}"
    do
      for l in "${!BkgFileList[@]}"
      do
        python hadd_many.py "yNJets/${var}_${prod}_${k}/testDistr${l}.root" "yNJets/${var}_${prod}_${k}/bkg${l}/*.root"
	#haddR -f yNJets/${var}_${prod}_${k}/testDistr${l}.root yNJets/${var}_${prod}_${k}/bkg${l}/*.root
	##haddR -f -c ${var}_${prod}_${k}testDistr${l}.root `xrdfs root://cmseos.fnal.gov ls /store/user/"$Outdir"/nJets/${var}_${prod}_${k}/bkg${l}/ | grep "\.root"`
	##xrdcp ${var}_${prod}_${k}testDistr${l}.root root://cmseos.fnal.gov//store/user/"$Outdir"/nJets/${var}_${prod}_${k}/testDistr${l}.root
	##rm ${var}_${prod}_${k}testDistr${l}.root
	:
      done
      python hadd_many.py "yNJets/testDistr_${var}_${prod}_${k}.root" "yNJets/${var}_${prod}_${k}/testDistr*"
      #haddR -f yNJets/testDistr_${var}_${prod}_${k}.root yNJets/${var}_${prod}_${k}/testDistr*
      ##haddR -f -c testDistr_${var}_${prod}_${k}.root `xrdfs root://cmseos.fnal.gov ls /store/user/"$Outdir"/nJets/${var}_${prod}_${k}/ | grep "testDistr"`
      ##xrdcp testDistr_${var}_${prod}_${k}.root root://cmseos.fnal.gov//store/user/"$Outdir"/nJets/testDistr_${var}_${prod}_${k}.root
      ##rm testDistr_${var}_${prod}_${k}.root
      :
    done
  done
done

python -c "from nJetsEstimate_LPC import makeEstimateHistos; makeEstimateHistos()"
python -c "from nJetsEstimate_LPC import makeSampleHistos; makeSampleHistos()"
