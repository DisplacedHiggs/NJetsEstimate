#!/bin/bash

tempfile=condorlistNJets.tmp


while true
do
  expect ~/private/gridinit.exp
  if [ -e $tempfile ]; then
    rm -rf $tempfile
  fi
  #sleep 30
  condor_q stata >> $tempfile
  if grep -q runNJets.sh "$tempfile"; then
    :
  else
    break
  fi
  echo "not done"
  sleep 2m
done

echo
echo
echo "DONE NJets"
echo
echo

rm -rf $tempfile
bash prepareNJetsPlots.sh