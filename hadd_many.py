#!/usr/bin/env python
import os, sys, glob, subprocess

#usage
#python hadd_many "x.root" "y/z*.root"

#replacing the following command to handle >1000 input files
#haddR -f yNJets/${var}_${prod}_${k}/testDistr${l}.root yNJets/${var}_${prod}_${k}/bkg${l}/*.root

output_file = sys.argv[1]
input_selector = sys.argv[2]

print input_selector
input_files = glob.glob(input_selector)
print len(input_files)

i=0
split_number = 500
while len(input_files)>split_number:
    i=i+1
    sub_file = "temp"+str(i)+".root"
    sub_list = input_files[0:split_number-1]
    input_files[0:split_number-1] = []
    subprocess.check_call(['haddR','-f' , sub_file]+sub_list)
    input_files.append(sub_file)
    print input_files
subprocess.check_call(['haddR','-f', output_file]+input_files)
