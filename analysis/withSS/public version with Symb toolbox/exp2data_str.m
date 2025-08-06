%Input contingency data file

% expname: experiment label that will be used for naming the output file
expname='exp2';

% datacont: experimental conditions and causal direction index
% a: C, E
% b: C, not-E
% c: not-C, E
% d: not-C, not-E
% causal direction: 1: generative; -1: preventive; 0: unknown
datacont = [6	18	6	6  0
            6	6	18	6  0
            6	6	6	18 0
            4	4	0	8  1
            6	2	4	4  1];
        
% human: human mean rating in strength judgment
% humanste: standard error of human rating
% condsort: reorder contingency conditions if needed        
human=[-52 -22 23 57 47]/100;
condsort = [1 2 3 4 5 ];
     
        
% GenProv: causal direction, 1: generative; -1: preventive; 0: unknown
% master_n_m: sample size N(c-)
% master_n: sample size N(c-) N(c+)
% master_obsprobec: N(e+|c+)
% master_obsprobe_c: N(e+|c-)
master_n_m = [datacont(:,3)+datacont(:,4) ];    
master_n = [datacont(:,3)+datacont(:,4) datacont(:,1)+datacont(:,2)];
master_obsprobe_c = round(datacont(:,3));
master_obsprobec = round(datacont(:,1));
GenProv = datacont(:,5)'; % 1: generative; -1: preventive; 0: causal direction is unknown


