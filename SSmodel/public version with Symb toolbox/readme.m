
This folder contains Matlab code for simulating models of human causal
induction, used in Lu, Yuille,Liljeholm, Cheng & Holyoak (2008).  

The folder contains **** files:

README			This file
****************************
Major computation functions
****************************

SSmodelmain.m	Main program applying computational models to contingencies and behavioral data. Three types of models are included (Bayesian model with NS prior, Bayesian model with Unif prior, Chi-square) 

priormain.m     script applying Bayesian models (either using numerical integration (fast) or analytic integration (slow))

supanalypriorsim.m      Bayesian model using numerical integration (adaptive Lobatto quadrature method)

supanalypriorana.m      Bayesian model using analytic integration (requires MATLAB symbolic toolbox)

chi2HLfunc.m        Chi-square model


****************************
Computation tool functions
****************************

likedistcal2.m      A subfunction to speed up analytic integration

nchoosekHL.m        This is the number of combinations of N things taken K at a time, N!/K!(N-K)!.

powertransform.m	Power transformation used in optimizing model fits (from the program developed by Griffiths & Tenenbaum, (2005) http://cocosci.berkeley.edu/tom/)

bootcheck.m         Bootstrap code for computing confidence intervals on model (from the program developed by Griffiths & Tenenbaum, (2005) , http://cocosci.berkeley.edu/tom/)
                          fits
                          

****************************
Input files
****************************

see example files as exp1gendata.m, exp1prevdata.m, 


****************************
Outputs
****************************
predicted support or mean strength values will be listed in the window main window

Note: with pre-specified causal directions (generative or preventive),  mean strength values will be listed within the range of [0,1]
      with unknown causal directions,  mean strength values will be listed within the range of [-1 1]. 

'rawrst.%d.%3.1f.%s.mat':  support estimate result file (without transformation)
'rawstrrst.%d.%3.1f.%s.mat':  strength estimate result file 


****************************
All references appear in the bibliography of
****************************

Lu, H., Yuille, A., Liljeholm, M., Cheng, P. W., Holyoak, K. J. (2008). 
Bayesian generic priors for causal learning.  Psychological Review.

Lu, H., Yuille, A., Liljeholm, M., Cheng, P. W., & Holyoak, K. J. (2006). 
Modeling causal learning using Bayesian generic priors on generative and preventive powers. 
In R. Sun & N. Miyake (Eds.), Proceedings of the 28th Annual Conference of the Cognitive Science Society 
(pp. 519-524). Mahwah, NJ: Erlbaum.

